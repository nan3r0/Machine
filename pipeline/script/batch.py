"""Weekly batch, the entry point of Workflow A (task p2-batch, PLAN.md sections 5 and 7).

Usage: python -m pipeline.script.batch SOURCES_DIR QUEUE_DIR OUT_DIR

Steps are called through their modules (`sources.load_sources`, `generate.write_script`,
`exact.unsupported`, `semantic.check_script`, ...), never imported by name, so tests can fake them.
Logs counts, script ids and the clipped reason a script was left out (the same text the PR body
shows, which can quote up to REASON_MAX_CHARS of model output); never prompts, fact text or the key.
"""

import argparse
import logging
import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline import constants
from pipeline.factcheck import exact, semantic
from pipeline.schema import Flag, LineVerdict, Script, SourceFile
from pipeline.script import gemini, generate, sources

log = logging.getLogger(__name__)


class _Budget:
    """Gemini calls made so far, and how many a rewrite may still spend."""

    def __init__(self) -> None:
        self.writes = 0
        self.checks = 0

    def spare_writes(self, scripts_left: int) -> int:
        return constants.WRITER_MAX_CALLS_PER_BATCH - self.writes - constants.SCRIPT_ATTEMPTS * scripts_left

    def spare_checks(self, scripts_left: int) -> int:
        return constants.CHECKER_MAX_CALLS_PER_BATCH - self.checks - scripts_left


def run(sources_dir: Path, queue_dir: Path, out_dir: Path, run_date: date) -> int:
    """Write up to `constants.SCRIPTS_PER_BATCH` scripts and the PR body; return the exit code.

    1. The first SCRIPTS_PER_BATCH unused sources (`sources.unused_sources`), in slug order. The
       script id is the source slug. publish_after is one day each, in order, starting the Monday
       after `run_date` (a Monday run starts a week later).
    2. Each script: `generate.write_script` (one writer call; on GenerateError asked again, up to
       `SCRIPT_ATTEMPTS` calls in all); then each scene through `exact.unsupported` against its
       linked fact texts, and the script once through `semantic.check_script`. A scene that fails
       either layer (exact tokens, UNSUPPORTED or PARTIAL) is rewritten once (`generate.rewrite_line`)
       and re-checked (exact for that scene, the meaning check again once for the script). Still
       failing, or a rewrite that raises GenerateError: the script stays and gets a Flag for that
       scene with the reason. Then the hook and the loop line go through `exact.unsupported`
       against the union of the facts the scenes cite; a failure is a Flag with scene None
       ("hook: not in the cited facts: ..."), never rewritten, no Gemini call. A fact-check
       result never stops the run.
    3. Budgets: never more than `WRITER_MAX_CALLS_PER_BATCH` writer calls (each write_script and
       rewrite_line is one) or `CHECKER_MAX_CALLS_PER_BATCH` checker calls (one per check_script),
       counted as they are made. Rewrites never spend what the scripts still to be written need
       (SCRIPT_ATTEMPTS writer calls and one checker call each), so all 7 scripts get written and
       checked before any line is flagged for lack of budget. With too little left, flag instead
       of rewriting.
    4. GeminiError or GenerateError while writing or checking a script: the script is left out and
       listed in the PR body with the reason (a Flag with scene None). The same clipped reason is
       logged as a warning; when every script fails there is no PR body, so the log is then the
       only copy.
    5. Writes each script to `queue_dir/approved/<id>.json` and the body to `out_dir/pr_body.md`.
       Flag reasons are clipped to `REASON_MAX_CHARS`.

    Returns 0 when at least one script was written. With no unused source, or no script written,
    returns 1 and writes no PR body (the workflow run fails and opens no PR).
    """
    unused = sources.unused_sources(sources.load_sources(sources_dir), queue_dir)
    picked = list(unused.items())[: constants.SCRIPTS_PER_BATCH]
    if not picked:
        log.error("no unused source")
        return 1
    first_day = run_date + timedelta(days=7 - run_date.weekday())
    budget = _Budget()
    written: list[tuple[Script, SourceFile]] = []
    flags: list[Flag] = []
    left_out: list[Flag] = []
    for number, (slug, source) in enumerate(picked):
        scripts_left = len(picked) - number - 1
        try:
            script = _write(source, slug, first_day + timedelta(days=number), budget)
            script, failures = _check_and_repair(script, source, scripts_left, budget)
        except (generate.GenerateError, gemini.GeminiError) as error:
            flag = _flag(slug, None, str(error))
            left_out.append(flag)
            log.warning("script %s left out: %s", slug, flag.reason)
            continue
        written.append((script, source))
        flags += [_flag(slug, index, reason) for index, reason in failures.items()]
        flags += [_flag(slug, None, reason) for reason in _check_spoken_extras(script, source)]
    log.info("%d of %d scripts written, %d flags", len(written), len(picked), len(flags))
    if not written:
        return 1
    body = pr_body(written, flags, left_out, exhausted=len(picked) < constants.SCRIPTS_PER_BATCH)
    approved = queue_dir / "approved"
    approved.mkdir(parents=True, exist_ok=True)
    for script, _ in written:
        (approved / f"{script.id}.json").write_text(script.model_dump_json(indent=2) + "\n", encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pr_body.md").write_text(body, encoding="utf-8")
    return 0


def _flag(script_id: str, scene: int | None, reason: str) -> Flag:
    clipped = " ".join(reason.split())[: constants.REASON_MAX_CHARS].strip()
    return Flag(script_id=script_id, scene=scene, reason=clipped or "no reason given")


def _write(source: SourceFile, script_id: str, publish_after: date, budget: _Budget) -> Script:
    """One writer call, asked once more if the answer was rejected. GenerateError after the last."""
    for _ in range(constants.SCRIPT_ATTEMPTS - 1):
        budget.writes += 1
        try:
            return generate.write_script(source, script_id, publish_after)
        except generate.GenerateError:
            log.info("writer answer rejected for %s, asking again", script_id)
    budget.writes += 1
    return generate.write_script(source, script_id, publish_after)


def _check(script: Script, source: SourceFile, budget: _Budget) -> dict[int, str]:
    """The failing scenes of `script` (index to reason) after the exact and the meaning layer."""
    budget.checks += 1
    verdicts: list[LineVerdict] = semantic.check_script(script, source.facts)
    texts = {fact.id: fact.text for fact in source.facts}
    failures: dict[int, str] = {}
    for index, (scene, verdict) in enumerate(zip(script.scenes, verdicts, strict=True)):
        reasons = []
        missing = exact.unsupported(scene.narration, [texts[i] for i in scene.source_fact_ids])
        if missing:
            reasons.append("not in the linked facts: " + ", ".join(missing))
        if verdict.verdict != "SUPPORTED":
            reasons.append(verdict.reason)
        if reasons:
            failures[index] = "; ".join(reasons)
    return failures


def _check_spoken_extras(script: Script, source: SourceFile) -> list[str]:
    """Reasons the hook or loop line holds a number or name that no cited fact backs. They are
    spoken but cite no fact, so the union of the facts the scenes cite stands in. Never rewritten."""
    texts = {fact.id: fact.text for fact in source.facts}
    cited_ids = {i for scene in script.scenes for i in scene.source_fact_ids}
    cited = [texts[i] for i in sorted(cited_ids)]
    reasons = []
    for label, text in (("hook", script.hook), ("loop line", script.loop_line)):
        missing = exact.unsupported(text, cited)
        if missing:
            reasons.append(f"{label}: not in the cited facts: " + ", ".join(missing))
    return reasons


def _check_and_repair(
    script: Script, source: SourceFile, scripts_left: int, budget: _Budget
) -> tuple[Script, dict[int, str]]:
    """Check once, rewrite each failing scene once while the budget allows, check again if any
    rewrite landed. Returns the script and the scenes that still fail."""
    failures = _check(script, source, budget)
    if not failures or budget.spare_checks(scripts_left) < 1:
        return script, failures
    rewritten = False
    for index, reason in failures.items():
        if budget.spare_writes(scripts_left) < 1:
            break
        budget.writes += 1
        try:
            script = generate.rewrite_line(script, index, source, reason)
        except (generate.GenerateError, gemini.GeminiError):
            log.info("rewrite of %s scene %d failed", script.id, index + 1)
        else:
            rewritten = True
    if rewritten:
        failures = _check(script, source, budget)
    return script, failures


def _longest_run(text: str) -> int:
    return max((len(run) for run in re.findall(r"`+", text)), default=0)


def _code(text: str) -> str:
    """One line of model text as an inline code span whose ticks outnumber any run in it."""
    flat = " ".join(text.split())
    ticks = "`" * (_longest_run(flat) + 1)
    return f"{ticks} {flat} {ticks}"


def _fenced(text: str) -> str:
    fence = "`" * max(3, _longest_run(text) + 1)
    return f"{fence}\n{text}\n{fence}"


def _flag_line(flag: Flag) -> str:
    where = flag.script_id if flag.scene is None else f"{flag.script_id}, scene {flag.scene + 1}"
    return f"- {where}: {_code(flag.reason)}"


def _script_section(script: Script, source: SourceFile) -> str:
    facts = {fact.id: fact for fact in source.facts}
    shown: set[int] = set()
    lines = [f"## {script.id}", f"Hook: {_code(script.hook)}"]
    for number, scene in enumerate(script.scenes, 1):
        lines.append(f"Scene {number}: {_code(scene.narration)}")
        for fact_id in scene.source_fact_ids:
            if fact_id not in shown:
                shown.add(fact_id)
                lines.append(f"- {facts[fact_id].text} {facts[fact_id].url}")
    lines.append(f"Loop line: {_code(script.loop_line)}")
    published = "\n".join([f"Title: {script.title}", f"Description: {script.description}",
                           f"Tags: {', '.join(script.tags)}"])
    return "\n".join(lines) + "\n\n" + _fenced(published)


def pr_body(
    written: Sequence[tuple[Script, SourceFile]],
    flags: Sequence[Flag],
    left_out: Sequence[Flag],
    exhausted: bool,
) -> str:
    """The approval PR body in Markdown, readable on a phone (no wide tables).

    Order: when `exhausted` (fewer unused sources than SCRIPTS_PER_BATCH), a line containing
    "N of 7: sources exhausted" (N scripts written, 7 being SCRIPTS_PER_BATCH); every flag (script id,
    scene number, reason); every left-out script with its reason; then per written script a heading
    naming its id, the hook, each scene's narration with the text and url of each fact it cites
    (each fact's text and url at most once per script, as plain text so the links work), the loop
    line, and the title, description and tags verbatim together in one fenced code block.

    Model output never renders as Markdown (security review of p2-batch): every model-derived string
    (reasons, hook, narration, loop line, title, description, tags) sits inside a fenced code block
    opened at the start of a line, or an inline code span closed on the same line, whose fence is
    longer than any backtick run in the text. So no link, image, HTML tag or comment, and no
    @mention (GitHub notifies on a bare @name), can come from the model. Only fact texts and urls
    (owner-reviewed sources), script ids and fixed labels are plain text.
    Raises ValueError when the body would exceed `PR_BODY_MAX_CHARS`; never truncates.
    """
    parts = ["# Weekly scripts for approval"]
    if exhausted:
        parts.append(f"{len(written)} of {constants.SCRIPTS_PER_BATCH}: sources exhausted")
    if flags:
        parts.append("## Flags\n" + "\n".join(_flag_line(flag) for flag in flags))
    if left_out:
        parts.append("## Left out\n" + "\n".join(_flag_line(flag) for flag in left_out))
    parts += [_script_section(script, source) for script, source in written]
    body = "\n\n".join(parts) + "\n"
    if len(body) > constants.PR_BODY_MAX_CHARS:
        raise ValueError(f"PR body is {len(body)} characters, over {constants.PR_BODY_MAX_CHARS}")
    return body


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parses SOURCES_DIR QUEUE_DIR OUT_DIR and calls `run` with today's UTC date."""
    parser = argparse.ArgumentParser(prog="pipeline.script.batch")
    parser.add_argument("sources_dir", type=Path)
    parser.add_argument("queue_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    return run(args.sources_dir, args.queue_dir, args.out_dir, datetime.now(timezone.utc).date())


if __name__ == "__main__":
    raise SystemExit(main())
