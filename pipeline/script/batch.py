"""Weekly batch, the entry point of Workflow A (task p2-batch, PLAN.md sections 5 and 7).

Usage: python -m pipeline.script.batch SOURCES_DIR QUEUE_DIR OUT_DIR

Steps are called through their modules (`sources.load_sources`, `generate.write_script`,
`exact.unsupported`, `semantic.check_script`, ...), never imported by name, so tests can fake them.
Logs and prints counts and script ids only: never prompts, model output, fact text or the key.
"""

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from pipeline.schema import Flag, Script, SourceFile


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
       scene with the reason. A fact-check result never stops the run.
    3. Budgets: never more than `WRITER_MAX_CALLS_PER_BATCH` writer calls (each write_script and
       rewrite_line is one) or `CHECKER_MAX_CALLS_PER_BATCH` checker calls (one per check_script),
       counted as they are made. Rewrites never spend what the scripts still to be written need
       (SCRIPT_ATTEMPTS writer calls and one checker call each), so all 7 scripts get written and
       checked before any line is flagged for lack of budget. With too little left, flag instead
       of rewriting.
    4. GeminiError or GenerateError while writing or checking a script: the script is left out and
       listed in the PR body with the reason (a Flag with scene None).
    5. Writes each script to `queue_dir/approved/<id>.json` and the body to `out_dir/pr_body.md`.
       Flag reasons are clipped to `REASON_MAX_CHARS`.

    Returns 0 when at least one script was written. With no unused source, or no script written,
    returns 1 and writes no PR body (the workflow run fails and opens no PR).
    """
    raise NotImplementedError


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
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parses SOURCES_DIR QUEUE_DIR OUT_DIR and calls `run` with today's UTC date."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
