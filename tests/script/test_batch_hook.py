"""Phase review N1: the hook and loop line are spoken, so the exact layer checks them too
(task p2b-hook-check, PLAN.md section 5 "each narration line").

They cite no fact of their own, so they are checked against every fact the script's scenes cite.
A failure is flagged for the owner (a Flag with scene None and a reason starting "hook:" or
"loop line:"); it is never rewritten and costs no Gemini call. Same fake Gemini as test_batch.py.
"""

from pathlib import Path

import pytest
import yaml

from pipeline import constants
from pipeline.schema import Flag
from pipeline.script import batch, gemini
from tests.script.scripts import make_source
from tests.script.test_batch import (
    RUN_DATE,
    Dirs,
    FakeGemini,
    capped_script,
    capped_source,
    run,
    setup,
    slug,
    writer_answer,
)

# Source 1 (make_source(100, ...)) has facts 101 to 107; fact 100 + k ends "closed in {1901 + k}."


def flag_lines(body: str, script_id: str) -> list[str]:
    return [line for line in body.splitlines() if line.startswith(f"- {script_id}")]


def kinds(fake: FakeGemini, name: str) -> list[str]:
    return [kind for _, slug_, kind in fake.calls if slug_ == name]


def with_answer(fake: FakeGemini, **overrides: str) -> None:
    fake.write = lambda name, n: {**writer_answer(fake.sources[name]), **overrides}


def test_made_up_number_in_the_hook_is_flagged_not_rewritten(tmp_path: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    with_answer(fake, hook="In 1777 it began.")
    assert run(dirs) == 0
    assert list(dirs.written()) == [slug(1)]
    [line] = flag_lines(dirs.body(), slug(1))
    assert "hook" in line and "1777" in line and "scene" not in line
    assert kinds(fake, slug(1)) == ["write", "check"]


def test_unknown_name_in_the_loop_line_is_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    with_answer(fake, loop_line="Still listening for Zanzibar.")
    assert run(dirs) == 0
    [line] = flag_lines(dirs.body(), slug(1))
    assert "loop line" in line and "zanzibar" in line.lower() and "hook" not in line
    assert kinds(fake, slug(1)) == ["write", "check"]


def test_hook_and_loop_line_backed_by_cited_facts_pass(tmp_path: Path,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    with_answer(fake, hook="In 1902 the Harbor Office knew.", loop_line="Back to 1908.")
    assert run(dirs) == 0
    assert flag_lines(dirs.body(), slug(1)) == []
    assert "## Flags" not in dirs.body()


def test_a_fact_no_scene_cites_does_not_back_the_hook(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    dirs = Dirs(tmp_path)
    known = {slug(1): make_source(100, "Mystery number 1", count=8)}  # fact 108 (1909) uncited
    (dirs.sources / f"{slug(1)}.yaml").write_text(yaml.safe_dump(known[slug(1)].model_dump()),
                                                  encoding="utf-8")
    fake = FakeGemini(known)
    monkeypatch.setattr(gemini, "generate_json", fake)
    with_answer(fake, hook="In 1909 it began.")
    assert batch.run(dirs.sources, dirs.queue, dirs.out, RUN_DATE) == 0
    [line] = flag_lines(dirs.body(), slug(1))
    assert "hook" in line and "1909" in line


def test_hook_flag_is_clipped_like_any_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    years = " ".join(str(1500 + i) for i in range(40))  # 41 words keeps the script inside TIKTOK_WORDS
    with_answer(fake, hook=f"Years {years}.")
    assert run(dirs) == 0
    [line] = flag_lines(dirs.body(), slug(1))
    reason = line.split("`", 1)[1].strip("` ")
    assert reason.startswith("hook") and len(reason) <= constants.REASON_MAX_CHARS


def test_body_with_hook_and_loop_flags_still_fits() -> None:
    """test_batch.py sizes the body for SCENES_MAX scene flags plus one script flag per script; a
    script can now also carry a hook and a loop line flag, so two script flags each."""
    written = [(capped_script(n, src), src) for n in range(1, 8) for src in [capped_source(n)]]
    reason = "r" * constants.REASON_MAX_CHARS
    flags = [Flag(script_id=s.id, scene=i, reason=reason)
             for s, _ in written for i in range(constants.SCENES_MAX)]
    flags += [Flag(script_id=s.id, scene=None, reason=f"{label}: " + reason)
              for s, _ in written for label in ("hook", "loop line")]
    assert len(batch.pr_body(written, flags, [], exhausted=False)) <= constants.PR_BODY_MAX_CHARS


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=2)
    fake.write = lambda name, n: {**writer_answer(fake.sources[name]),
                                  "hook": "In 1777 it began." if name == slug(1) else "Listen closely."}
    assert run(dirs) == 0
    assert sorted(dirs.written()) == [slug(1), slug(2)]
    [line] = flag_lines(dirs.body(), slug(1))
    assert "hook" in line and "1777" in line
    assert flag_lines(dirs.body(), slug(2)) == []
    assert "rewrite" not in kinds(fake, slug(1))
