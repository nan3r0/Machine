"""Behaviour tests for the real gaps in the 2026-11-21 mutation report (task p2c-survivor-tests).

The Architect's triage is in .harness/handoffs/p2c-plan.md. Each test pins a behaviour the
contract states and no earlier test checked; mutant ids shift as the code changes, so none is named
here. Expected values come from the contracts and pipeline/constants.py (lessons.md 2026-11-16).
"""

import io
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml

from pipeline import constants
from pipeline.schema import Flag, Script, SourceFile
from pipeline.script import batch, gemini, generate, sources, validate
from pipeline.script.gemini import GeminiError
from tests.script.gemini_fakes import REFERENCE, FakeUrlopen, as_json, interaction
from tests.script.scripts import make_script, scene, source_dict
from tests.script.test_batch import MONDAY, RUN_DATE, slug, source, writer_answer
from tests.script.test_batch import run as run_batch
from tests.script.test_batch import setup as make_batch

KEY = "AIzaFAKE-survivor-key-0123456789"
SCHEMA = {"type": "object", "properties": {"narration": {"type": "string"}}, "required": ["narration"]}
ANSWER = {"narration": "The sound was ice."}
GOOD_TEXT = as_json(ANSWER)


# --- gemini --------------------------------------------------------------------------------------

@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waited: list[float] = []
    monkeypatch.setattr(time, "sleep", waited.append)
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    return waited


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeUrlopen:
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    return fake


def call() -> dict[str, Any]:
    return gemini.generate_json(constants.WRITER_MODEL, "Write one line.", SCHEMA)


def test_text_split_over_two_steps_is_joined_in_order(monkeypatch: pytest.MonkeyPatch,
                                                      sleeps: list[float]) -> None:
    head, tail = GOOD_TEXT[:12], GOOD_TEXT[12:]
    steps = [{"type": "model_output", "content": [{"type": "text", "text": head}]},
             {"type": "thought", "content": [{"type": "text", "text": "not json"}]},
             {"type": "model_output", "content": [{"type": "text", "text": tail}]}]
    install(monkeypatch, {**REFERENCE, "steps": steps})
    assert call() == ANSWER


@pytest.mark.parametrize("part", [5, "str", None, {"type": "thought", "text": "thinking"},
                                  {"type": "text"}, {"type": "text", "text": 5},
                                  {"type": "text", "text": None}])
def test_parts_that_are_not_text_are_skipped(monkeypatch: pytest.MonkeyPatch, sleeps: list[float],
                                             part: Any) -> None:
    body = interaction(GOOD_TEXT)
    body["steps"][0]["content"].insert(0, part)
    install(monkeypatch, body)
    assert call() == ANSWER


def test_two_bare_timeouts_are_gemini_error(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    fake = install(monkeypatch, TimeoutError(), TimeoutError())
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 2
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]


def test_url_error_from_a_timeout_is_retried_once(monkeypatch: pytest.MonkeyPatch,
                                                  sleeps: list[float]) -> None:
    fake = install(monkeypatch, urllib.error.URLError(TimeoutError()), interaction(GOOD_TEXT))
    assert call() == ANSWER
    assert len(fake.requests) == 2
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]


def test_url_error_from_two_timeouts_is_gemini_error(monkeypatch: pytest.MonkeyPatch,
                                                     sleeps: list[float]) -> None:
    fake = install(monkeypatch, urllib.error.URLError(TimeoutError()), urllib.error.URLError(TimeoutError()))
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 2
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]


def test_url_error_for_another_reason_is_not_retried(monkeypatch: pytest.MonkeyPatch,
                                                     sleeps: list[float]) -> None:
    fake = install(monkeypatch, urllib.error.URLError(ConnectionRefusedError()), interaction(GOOD_TEXT))
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 1
    assert sleeps == []


def test_error_body_that_is_not_utf8_is_gemini_error(monkeypatch: pytest.MonkeyPatch,
                                                     sleeps: list[float]) -> None:
    error = urllib.error.HTTPError(constants.GEMINI_ENDPOINT, 400, "bad request", None,  # type: ignore[arg-type]
                                   io.BytesIO(b"\xff" + KEY.encode("utf-8") + b"\xfe"))
    fake = install(monkeypatch, error)
    with pytest.raises(GeminiError) as raised:
        call()
    assert KEY not in str(raised.value)
    assert len(fake.requests) == 1


# --- batch ---------------------------------------------------------------------------------------

def test_out_dir_under_a_missing_parent_is_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """out/ does not exist on a fresh runner."""
    dirs, _ = make_batch(tmp_path, monkeypatch, count=1)
    out_dir = tmp_path / "out" / "batch"
    assert not out_dir.parent.exists()
    assert batch.run(dirs.sources, dirs.queue, out_dir, RUN_DATE) == 0
    assert (out_dir / "pr_body.md").is_file()


def test_rewrite_gets_the_failure_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = make_batch(tmp_path, monkeypatch, count=1)
    fake.check = lambda name, n, i: "UNSUPPORTED" if n == 0 and i == 2 else "SUPPORTED"
    seen: list[tuple[int, str]] = []
    real = generate.rewrite_line

    def recording(script: Script, index: int, source: SourceFile, reason: str) -> Script:
        seen.append((index, reason))
        return real(script, index, source, reason)

    monkeypatch.setattr(generate, "rewrite_line", recording)
    assert run_batch(dirs) == 0
    assert len(seen) == 1
    index, reason = seen[0]
    assert index == 2 and "checker says unsupported 2" in reason


def test_writer_that_always_fails_is_asked_script_attempts_times(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, _ = make_batch(tmp_path, monkeypatch, count=2)
    calls: list[str] = []
    real = generate.write_script

    def writer(source: SourceFile, script_id: str, publish_after: Any) -> Script:
        calls.append(script_id)
        if script_id == slug(1):
            raise generate.GenerateError("writer output invalid")
        return real(source, script_id, publish_after)

    monkeypatch.setattr(generate, "write_script", writer)
    assert run_batch(dirs) == 0
    assert calls.count(slug(1)) == constants.SCRIPT_ATTEMPTS
    assert sorted(dirs.written()) == [slug(2)]
    assert slug(1) in dirs.body()


def numbered_script() -> tuple[Script, SourceFile]:
    src = source(1)
    data = writer_answer(src)
    script = Script.model_validate({**data, "id": slug(1), "topic": src.topic, "platforms": ["youtube"],
                                    "publish_after": MONDAY,
                                    "scenes": [scene(s["narration"], s["source_fact_ids"])
                                               for s in data["scenes"]]})
    return script, src


def test_pr_body_numbers_scenes_from_one_like_the_flags() -> None:
    """Read without relying on the code span layout: the last "scene N" before each narration."""
    script, src = numbered_script()
    flag = Flag(script_id=slug(1), scene=3, reason="flagged line reason")
    body = batch.pr_body([(script, src)], [flag], [], exhausted=False)
    flag_line = next(line for line in body.splitlines() if flag.reason in line)
    assert re.findall(r"(?i)\bscene\s+(\d+)", flag_line) == ["4"]
    start = body.index(script.hook)
    for k, scene_ in enumerate(script.scenes):
        at = body.index(scene_.narration, start)
        numbers = re.findall(r"(?i)\bscene\s+(\d+)", body[start:at])
        assert numbers and numbers[-1] == str(k + 1), k
        start = at + len(scene_.narration)


# --- validate ------------------------------------------------------------------------------------

def hides_digit(char: str) -> bool:
    return (char > "\x7f" and unicodedata.category(char) not in {"Nd", "Nl", "No"}
            and any("0" <= part <= "9" for part in unicodedata.normalize("NFKD", char)))


HIDDEN_DIGITS = [chr(c) for c in range(sys.maxunicode + 1) if hides_digit(chr(c))]


def hook_problems(hook: str) -> list[str]:
    return [p for p in validate.problems(make_script(hook=hook)) if p.startswith("hook:")]


def test_the_hidden_digit_class_is_the_one_meant() -> None:
    for char in ("\u32c0", "\u3358", "\u32c8"):
        assert char in HIDDEN_DIGITS, f"U+{ord(char):04X}"
    assert len(HIDDEN_DIGITS) > 50


def test_every_symbol_that_folds_to_a_digit_is_rejected() -> None:
    """lessons.md 2026-11-18: the whole class, computed from this Python's Unicode tables."""
    missed = [f"U+{ord(c):04X}" for c in HIDDEN_DIGITS
              if not any(f"U+{ord(c):04X}" in p for p in hook_problems(f"Listen {c} closely."))]
    assert not missed, f"{len(missed)} passed, first: {missed[:10]}"


@pytest.mark.parametrize("hook", ["Listen x://y closely.", "Listen X://Y closely.",
                                  "See www. now.", "See WWW. now.", "See Www. now."])
def test_scheme_or_www_without_a_domain_is_a_url(hook: str) -> None:
    """PRD R12.1: no "://" and no "www.", any case, even with no dotted host after them."""
    assert hook_problems(hook)


def at_cap_script(extra: int) -> Script:
    """Plain letter words padded so narration_text() is NARRATION_MAX_CHARS + extra characters."""
    words = ["sound"] * 25
    scenes = [scene(" ".join(words), [101 + i]) for i in range(7)]
    base = make_script(hook="Listen.", loop_line="Gone.", scenes=scenes)
    pad = constants.NARRATION_MAX_CHARS + extra - len(base.narration_text())
    assert pad > 0
    scenes[0] = scene(" ".join(words[:-1] + ["sound" + "s" * pad]), [101])
    return make_script(hook="Listen.", loop_line="Gone.", scenes=scenes)


def test_narration_at_its_cap_passes_and_one_more_fails() -> None:
    at_cap = at_cap_script(0)
    assert len(at_cap.narration_text()) == constants.NARRATION_MAX_CHARS
    low, high = constants.TIKTOK_WORDS
    assert low <= len(at_cap.narration_words()) <= high
    assert validate.problems(at_cap) == []
    over = at_cap_script(1)
    assert len(over.narration_text()) == constants.NARRATION_MAX_CHARS + 1
    assert len(over.narration_words()) == len(at_cap.narration_words())
    found = validate.problems(over)
    assert len(found) == 1 and found[0].startswith("narration")


# --- sources -------------------------------------------------------------------------------------

def test_sources_load_in_slug_order(tmp_path: Path) -> None:
    """Sorted by full file name, bloop-2.yaml would come before bloop.yaml."""
    for name, base in (("bloop-2", 200), ("bloop", 100)):
        (tmp_path / f"{name}.yaml").write_text(yaml.safe_dump(source_dict(base, name)), encoding="utf-8")
    assert list(sources.load_sources(tmp_path)) == ["bloop", "bloop-2"]


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    """One gap from each module: gemini retries, batch out_dir, validate digits, source order."""
    test_url_error_from_a_timeout_is_retried_once(monkeypatch, sleeps)
    for part in ("batch", "sources"):
        (tmp_path / part).mkdir()
    test_out_dir_under_a_missing_parent_is_created(tmp_path / "batch", monkeypatch)
    assert hook_problems("Listen \u32c0 closely.") and hook_problems("Listen \u32c8 closely.")
    test_sources_load_in_slug_order(tmp_path / "sources")
