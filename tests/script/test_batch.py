"""R10.3 to R10.5, R11.2, R11.3, R13.1: the weekly batch end to end with a fake Gemini (task p2-batch).

Only gemini.generate_json is faked, so the real writer, exact check and meaning check run, and the
call budgets are counted where they are spent: per model id at the Gemini boundary.
"""

import logging
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from pipeline import constants
from pipeline.schema import Flag, Script, SourceFile
from pipeline.script import batch, gemini
from pipeline.script.gemini import GeminiError
from tests.script.scripts import FILLER, make_source, scene

RUN_DATE = date(2026, 11, 22)  # a Sunday, like the scheduled run
MONDAY = date(2026, 11, 23)
SHORT = " ".join(FILLER.split()[:11])
REWRITE = FILLER  # 22 plain words: no number or name for the exact check to miss
EXHAUSTED = re.compile(r"(\d+) of 7: sources exhausted")


def slug(n: int) -> str:
    return f"case-{n:02d}"


def source(n: int) -> SourceFile:
    return make_source(n * 100, f"Mystery number {n}")


def writer_answer(src: SourceFile, extra: str = "") -> dict[str, Any]:
    """7 scenes, each one fact text plus 11 plain words: 2 + 7 * 22 + 2 = 158 words."""
    scenes = [{"narration": f"{fact.text} {SHORT}.", "on_screen_text": "case", "source_fact_ids": [fact.id]}
              for fact in src.facts[:7]]
    scenes[0]["narration"] += extra
    return {"template": "story", "hook": "Listen closely.", "scenes": scenes, "loop_line": "Still listening.",
            "title": f"Mystery {src.facts[0].id // 100} solved", "description": "Source: Harbor Office.",
            "tags": ["mystery"]}


Policy = Callable[[str, int], Any]


class FakeGemini:
    """Answers writer and checker calls for the fixture sources. Each policy gets the source slug
    and how many calls of that kind the source has had (0 first) and returns the answer; the
    default answers pass every check."""

    def __init__(self, sources: dict[str, SourceFile]) -> None:
        self.sources = sources
        self.calls: list[tuple[str, str, str]] = []  # (model, slug, kind)
        self.prompts: list[str] = []
        self.write: Policy = lambda name, n: writer_answer(self.sources[name])
        self.rewrite: Policy = lambda name, n: {"narration": REWRITE}
        self.check: Callable[[str, int, int], str] = lambda name, n, index: "SUPPORTED"

    def slug_of(self, prompt: str) -> str:
        found = [name for name, src in self.sources.items() if any(f.text in prompt for f in src.facts)]
        assert len(found) == 1, "each prompt carries the facts of exactly one source"
        return found[0]

    def __call__(self, model: str, prompt: str, schema: dict[str, Any], temperature: Any = None) -> Any:
        name = self.slug_of(prompt)
        keys = set(schema["properties"])
        kind = "check" if keys == {"verdicts"} else "rewrite" if keys == {"narration"} else "write"
        count = sum(1 for c in self.calls if c[1] == name and c[2] == kind)
        self.calls.append((model, name, kind))
        self.prompts.append(prompt)
        if kind == "write":
            return self.write(name, count)
        if kind == "rewrite":
            return self.rewrite(name, count)
        base = self.sources[name].facts[0].id - 1
        verdicts = []
        for i in range(7):
            verdict = self.check(name, count, i)
            verdicts.append({"index": i, "verdict": verdict, "reason": f"checker says {verdict.lower()} {i}",
                             "fact_ids": [] if verdict == "UNSUPPORTED" else [base + 1 + i]})
        return {"verdicts": verdicts}

    def count(self, model: str) -> int:
        return sum(1 for c in self.calls if c[0] == model)


class Dirs:
    def __init__(self, root: Path) -> None:
        self.sources, self.queue, self.out = root / "sources", root / "queue", root / "out"
        self.sources.mkdir()

    def written(self) -> dict[str, Script]:
        return {p.stem: Script.model_validate_json(p.read_text(encoding="utf-8"))
                for p in sorted((self.queue / "approved").glob("*.json"))}

    def body(self) -> str:
        return (self.out / "pr_body.md").read_text(encoding="utf-8")


def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int = 7) -> tuple[Dirs, FakeGemini]:
    dirs = Dirs(tmp_path)
    known = {slug(n): source(n) for n in range(1, count + 1)}
    for name, src in known.items():
        (dirs.sources / f"{name}.yaml").write_text(yaml.safe_dump(src.model_dump()), encoding="utf-8")
    fake = FakeGemini(known)
    monkeypatch.setattr(gemini, "generate_json", fake)
    return dirs, fake


def run(dirs: Dirs) -> int:
    return batch.run(dirs.sources, dirs.queue, dirs.out, RUN_DATE)


def flagged(body: str, reason: str) -> list[str]:
    """For each place `reason` shows in the flags, the last script id named in the 200 characters
    before it (the flag's own header, whatever its layout)."""
    return [re.findall(r"case-\d\d", body[max(0, m.start() - 200):m.start()])[-1]
            for m in re.finditer(re.escape(reason), body)]


def use_up(dirs: Dirs, folder: str, n: int) -> None:
    """Put a script citing one fact of source n into queue/<folder>/."""
    (dirs.queue / folder).mkdir(parents=True, exist_ok=True)
    data = writer_answer(source(n))
    script = Script.model_validate({
        **data, "id": f"old-{n}", "topic": "old", "platforms": ["youtube"], "publish_after": date(2026, 1, 5),
        "scenes": [scene(s["narration"], [n * 100 + 3]) for s in data["scenes"]]})
    (dirs.queue / folder / f"old-{n}.json").write_text(script.model_dump_json(), encoding="utf-8")


# --- picking and writing --------------------------------------------------------------------------

def test_seven_sources_give_seven_scripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch)
    assert run(dirs) == 0
    written = dirs.written()
    assert list(written) == [slug(n) for n in range(1, 8)]
    assert [s.publish_after for s in written.values()] == [MONDAY + timedelta(days=i) for i in range(7)]
    assert fake.count(constants.WRITER_MODEL) == 7 and fake.count(constants.CHECKER_MODEL) == 7
    body = dirs.body()
    for script in written.values():
        assert script.title in body and script.hook in body
    assert not EXHAUSTED.search(body)


def test_a_monday_run_starts_the_next_monday(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, _ = setup(tmp_path, monkeypatch, count=1)
    assert batch.run(dirs.sources, dirs.queue, dirs.out, MONDAY) == 0
    assert [s.publish_after for s in dirs.written().values()] == [MONDAY + timedelta(days=7)]


def test_used_sources_are_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R10.3: a source cited by a script in queue/approved/ or queue/published/ is never picked."""
    dirs, fake = setup(tmp_path, monkeypatch, count=9)
    use_up(dirs, "approved", 2)
    use_up(dirs, "published", 5)
    assert run(dirs) == 0
    new = [name for name in dirs.written() if not name.startswith("old-")]
    assert new == [slug(n) for n in (1, 3, 4, 6, 7, 8, 9)]
    assert {c[1] for c in fake.calls} == set(new)


def test_short_batch_says_sources_exhausted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R10.5: fewer unused sources than 7 still makes a PR, and its body says so."""
    dirs, _ = setup(tmp_path, monkeypatch, count=4)
    use_up(dirs, "published", 1)
    assert run(dirs) == 0
    assert len([n for n in dirs.written() if not n.startswith("old-")]) == 3
    match = EXHAUSTED.search(dirs.body())
    assert match and match.group(1) == "3"


def test_no_unused_source_fails_without_a_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R10.5: with nothing left the run fails visibly and opens no PR."""
    dirs, fake = setup(tmp_path, monkeypatch, count=2)
    use_up(dirs, "published", 1)
    use_up(dirs, "approved", 2)
    assert run(dirs) != 0
    assert not (dirs.out / "pr_body.md").exists()
    assert fake.calls == []
    assert sorted(dirs.written()) == ["old-2"]


# --- fact-check outcomes --------------------------------------------------------------------------

def test_failed_line_rewritten_once_then_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    fake.check = lambda name, n, i: "UNSUPPORTED" if n == 0 and i == 2 else "SUPPORTED"
    assert run(dirs) == 0
    script = dirs.written()[slug(1)]
    assert script.scenes[2].narration == REWRITE
    assert [c[2] for c in fake.calls] == ["write", "check", "rewrite", "check"]
    assert "checker says unsupported 2" not in dirs.body()


def test_exact_failure_rewrites_with_the_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    fake.write = lambda name, n: writer_answer(fake.sources[name], extra=" It began in 1850.")
    assert run(dirs) == 0
    kinds = [c[2] for c in fake.calls]
    assert kinds.count("rewrite") == 1
    assert "1850" in fake.prompts[kinds.index("rewrite")]
    assert dirs.written()[slug(1)].scenes[0].narration == REWRITE


def test_line_still_failing_is_flagged_not_dropped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R11.2: the script stays, with a flag naming the line and the reason, listed before the scripts."""
    dirs, fake = setup(tmp_path, monkeypatch, count=2)
    fake.check = lambda name, n, i: "PARTIAL" if name == slug(2) and i == 4 else "SUPPORTED"
    assert run(dirs) == 0
    assert sorted(dirs.written()) == [slug(1), slug(2)]
    assert [c[2] for c in fake.calls if c[1] == slug(2)].count("rewrite") == 1
    body = dirs.body()
    reason = "checker says partial 4"
    assert reason in body
    first_script = min(body.index(s.hook) for s in dirs.written().values())
    assert body.index(reason) < first_script
    assert flagged(body, reason) == [slug(2)]


def test_gemini_error_leaves_one_script_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=3)

    def write(name: str, n: int) -> Any:
        if name == slug(2):
            raise GeminiError("HTTP 404: model gemini-x not found")
        return writer_answer(fake.sources[name])

    fake.write = write
    assert run(dirs) == 0
    assert sorted(dirs.written()) == [slug(1), slug(3)]
    assert flagged(dirs.body(), "HTTP 404") == [slug(2)]


def test_invalid_twice_leaves_the_script_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=2)
    fake.write = lambda name, n: {"hook": "broken"} if name == slug(1) else writer_answer(fake.sources[name])
    assert run(dirs) == 0
    assert sorted(dirs.written()) == [slug(2)]
    assert slug(1) in dirs.body()


def test_no_script_written_fails_without_a_body(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=3)
    fake.write = lambda name, n: {"hook": "broken"}
    assert run(dirs) != 0
    assert dirs.written() == {}
    assert not (dirs.out / "pr_body.md").exists()


# --- budgets (R11.3) ------------------------------------------------------------------------------

def within_budget(fake: FakeGemini) -> None:
    assert fake.count(constants.WRITER_MODEL) <= constants.WRITER_MAX_CALLS_PER_BATCH
    assert fake.count(constants.CHECKER_MODEL) <= constants.CHECKER_MAX_CALLS_PER_BATCH
    assert {c[0] for c in fake.calls} <= {constants.WRITER_MODEL, constants.CHECKER_MODEL}


def test_retries_use_the_writer_budget_so_lines_are_flagged(tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch)
    fake.write = lambda name, n: {"hook": "broken"} if n == 0 else writer_answer(fake.sources[name])
    fake.check = lambda name, n, i: "UNSUPPORTED" if i == 0 else "SUPPORTED"
    assert run(dirs) == 0
    within_budget(fake)
    assert len(dirs.written()) == 7
    assert [c[2] for c in fake.calls].count("rewrite") == 0
    assert sorted(flagged(dirs.body(), "checker says unsupported 0")) == sorted(fake.sources)


def test_every_line_failing_stays_within_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch)
    fake.check = lambda name, n, i: "UNSUPPORTED"
    assert run(dirs) == 0
    within_budget(fake)
    assert len(dirs.written()) == 7, "rewrites must not starve later scripts"


# --- logs ---------------------------------------------------------------------------------------

def test_logs_hold_no_model_output_or_facts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                            capsys: pytest.CaptureFixture[str],
                                            caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    dirs, fake = setup(tmp_path, monkeypatch, count=2)
    fake.check = lambda name, n, i: "PARTIAL" if i == 1 else "SUPPORTED"
    assert run(dirs) == 0
    out = capsys.readouterr()
    logged = out.out + out.err + caplog.text
    assert "Harbor Office" not in logged and SHORT not in logged and "checker says" not in logged


def test_main_uses_todays_utc_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The clock is frozen (QA lead: a run across UTC midnight made the real clock flaky). Sunday
    23:30 UTC is already Monday in UTC+1, so a local-time date would start a week later."""
    dirs, _ = setup(tmp_path, monkeypatch, count=1)

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> "FrozenClock":
            assert tz is timezone.utc, "main must ask for UTC"
            return cls(2026, 11, 22, 23, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(batch, "datetime", FrozenClock)
    assert batch.main([str(dirs.sources), str(dirs.queue), str(dirs.out)]) == 0
    [script] = dirs.written().values()
    assert script.publish_after == MONDAY


# --- the PR body (R13.1) --------------------------------------------------------------------------

def capped_source(n: int) -> SourceFile:
    """FACTS_PER_SOURCE_MAX facts, each text and url at its cap."""
    facts = [{"id": n * 100 + k, "text": f"{k:02d} " + "f" * (constants.FACT_TEXT_MAX_CHARS - 3),
              "url": f"https://example.org/{n}/{k:02d}/".ljust(constants.FACT_URL_MAX_CHARS, "u")}
             for k in range(1, constants.FACTS_PER_SOURCE_MAX + 1)]
    return SourceFile.model_validate({"topic": f"Topic {n}", "facts": facts})


def capped_script(n: int, src: SourceFile) -> Script:
    """Every published field at its cap, SCENES_MAX scenes, NARRATION_MAX_CHARS of narration."""
    spaces = constants.SCENES_MAX + 1
    per_scene = (constants.NARRATION_MAX_CHARS - 2 * 10 - spaces) // constants.SCENES_MAX
    return Script.model_validate({
        "id": slug(n), "topic": src.topic, "template": "story", "hook": "h" * 10, "loop_line": "l" * 10,
        "scenes": [scene("n" * per_scene, [src.facts[i % len(src.facts)].id])
                   for i in range(constants.SCENES_MAX)],
        "title": f"{n}" + "t" * (constants.TITLE_MAX_CHARS - 1),
        "description": "d" * constants.DESCRIPTION_MAX_CHARS,
        "tags": [f"{k}" + "g" * (constants.TAG_MAX_CHARS - 1) for k in range(constants.TAGS_MAX)],
        "platforms": ["youtube", "instagram", "tiktok"], "publish_after": MONDAY})


def test_body_at_every_cap_fits(tmp_path: Path) -> None:
    """Worst case per script: title 100 (twice), narration 1500, 10 facts of 160 + 100, description
    1000, tags 10 * 30, 11 flags of 120: about 6900 characters, 48500 for 7, which leaves about
    11000 for headings, labels and fences under PR_BODY_MAX_CHARS."""
    written = [(capped_script(n, src), src) for n in range(1, 8) for src in [capped_source(n)]]
    reason = "r" * constants.REASON_MAX_CHARS
    flags = [Flag(script_id=s.id, scene=i, reason=reason)
             for s, _ in written for i in range(constants.SCENES_MAX)]
    flags += [Flag(script_id=s.id, scene=None, reason=reason) for s, _ in written]
    assert constants.NARRATION_MAX_CHARS >= len(written[0][0].narration_text())
    body = batch.pr_body(written, flags, [], exhausted=False)
    assert len(body) <= constants.PR_BODY_MAX_CHARS
    for script, src in written:
        assert script.description in body
        for fact in src.facts:
            assert fact.text in body and fact.url in body


def test_over_long_body_raises_instead_of_cutting() -> None:
    src = SourceFile.model_validate({"topic": "Huge", "facts": [
        {"id": 100 + k, "text": "x" * 20_000, "url": f"https://example.org/{k}"} for k in range(1, 5)]})
    script = Script.model_validate({
        "id": "huge", "topic": "Huge", "template": "story", "hook": "Listen.", "loop_line": "Gone.",
        "scenes": [scene("line", [100 + k]) for k in range(1, 5)], "title": "Huge", "description": "",
        "tags": [], "platforms": ["youtube"], "publish_after": MONDAY})
    with pytest.raises(ValueError):
        batch.pr_body([(script, src)], [], [], exhausted=False)


def fenced_block(body: str, start: int, end: int) -> tuple[str, str]:
    """The fence opened last before body[start:end] and the block text up to where it closes."""
    fences = list(re.finditer(r"^(`{3,}|~{3,})[^\n]*$", body[:start], re.MULTILINE))
    assert fences, "published fields sit in a fenced block"
    fence = fences[-1].group(1)
    closing = re.search(rf"^{re.escape(fence)}[`~]*\s*$", body[end:], re.MULTILINE)
    assert closing, "the fence closes after the fields"
    return fence, body[fences[-1].end():end + closing.start()]


def test_published_fields_verbatim_in_a_fence_that_cannot_be_closed_early() -> None:
    src = source(1)
    description = "Source: Harbor Office.\n````\n#mystery"
    script = Script.model_validate({**writer_answer(src), "id": slug(1), "topic": src.topic,
                                    "platforms": ["youtube"], "publish_after": MONDAY,
                                    "description": description, "tags": ["mystery", "harbor office"],
                                    "scenes": [scene(s["narration"], s["source_fact_ids"])
                                               for s in writer_answer(src)["scenes"]]})
    body = batch.pr_body([(script, src)], [], [], exhausted=False)
    at = body.index(description)
    fence, block = fenced_block(body, at, at + len(description))
    assert fence[0] == "~" or len(fence) > 4, "a line of four backticks in the description would close it"
    assert script.title in block and description in block
    for tag in script.tags:
        assert tag in block
    for scene_ in script.scenes:
        assert scene_.narration in body
    for fact in src.facts[:7]:
        assert fact.text in body and fact.url in body


def outside_code(body: str) -> str:
    """What GitHub renders as Markdown: `body` without fenced blocks (opened at line start, closed by
    a line of the same character at least as long) and without inline code spans, which count only
    when they close on the same line. Simplified on purpose: anything it cannot see as code stays
    visible, so the test fails safe."""
    kept, fence = [], ""
    for line in body.split("\n"):
        if fence:
            closing = re.match(r"^ {0,3}(`{3,}|~{3,})\s*$", line)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= len(fence):
                fence = ""
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if opening and not (opening.group(1)[0] == "`" and "`" in line[opening.end():]):
            fence = opening.group(1)
            continue
        kept.append(re.sub(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", "", line))
    return "\n".join(kept)


EVIL = ("it ``` was ```` not\n</details> [x](http://evil.example) ![i](http://evil.example/i.png) "
        "@someone <!-- hide")


def test_model_text_cannot_escape_its_code_span() -> None:
    """Security review of p2-batch: reasons, hook, narration, loop line, title, description and tags
    are model output. In the body they sit inside code, so no link, image, HTML, comment or @mention
    renders and nothing after them is swallowed."""
    src = source(1)
    data = writer_answer(src)
    script = Script.model_validate({
        **data, "id": slug(1), "topic": src.topic, "platforms": ["youtube"], "publish_after": MONDAY,
        "hook": "Listen @someone [x](evil).", "loop_line": "Gone </details> @someone.",
        "title": "@someone [x](evil) `tick`", "description": "@someone\n</details>\n````",
        "tags": ["@someone"],
        "scenes": [scene(f"{s['narration']} @someone [x](evil) ``", s["source_fact_ids"])
                   for s in data["scenes"]]})
    flag = Flag(script_id=slug(1), scene=2, reason=EVIL)
    gone = Flag(script_id=slug(2), scene=None, reason=EVIL)
    body = batch.pr_body([(script, src)], [flag], [gone], exhausted=False)
    visible = outside_code(body)
    for token in ("</details>", "[x](", "![i]", "@someone", "<!--", "evil.example"):
        assert token not in visible, token
    for fact in src.facts[:7]:
        assert fact.url in visible, "owner-reviewed fact urls stay plain, clickable text after the code"


def test_outside_code_sees_through_a_short_fence() -> None:
    """The detector itself: a fence shorter than a backtick run in the text is closed early."""
    assert "@someone" in outside_code("```\nnot the end\n```\n@someone\n```")
    assert "@someone" in outside_code("`a` @someone `b`")
    assert "@someone" not in outside_code("````\n```\n@someone\n````")


def test_flags_and_left_out_come_first() -> None:
    src = source(1)
    data = writer_answer(src)
    script = Script.model_validate({**data, "id": slug(1), "topic": src.topic, "platforms": ["youtube"],
                                    "publish_after": MONDAY,
                                    "scenes": [scene(s["narration"], s["source_fact_ids"])
                                               for s in data["scenes"]]})
    flag = Flag(script_id=slug(1), scene=3, reason="1850 is in no linked fact")
    gone = Flag(script_id=slug(9), scene=None, reason="writer output invalid twice")
    body = batch.pr_body([(script, src)], [flag], [gone], exhausted=True)
    assert body.index(flag.reason) < body.index(script.hook)
    assert body.index(gone.reason) < body.index(script.hook)
    match = EXHAUSTED.search(body)
    assert match and match.group(1) == "1"


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """7 unused sources give 7 approved scripts and a PR body; a failing line is rewritten once and
    then flagged; budgets hold; an over-long body raises."""
    dirs, fake = setup(tmp_path, monkeypatch, count=8)
    use_up(dirs, "published", 8)
    fake.check = lambda name, n, i: "UNSUPPORTED" if name == slug(3) and i == 6 else "SUPPORTED"
    assert run(dirs) == 0
    written = dirs.written()
    assert sorted(n for n in written if not n.startswith("old-")) == [slug(n) for n in range(1, 8)]
    within_budget(fake)
    assert [c[2] for c in fake.calls if c[1] == slug(3)].count("rewrite") == 1
    body = dirs.body()
    assert body.index("checker says unsupported 6") < min(body.index(s.hook) for s in written.values()
                                                          if not s.id.startswith("old-"))
    for name in (slug(n) for n in range(1, 8)):
        assert written[name].description in body
    test_over_long_body_raises_instead_of_cutting()
