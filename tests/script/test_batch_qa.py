"""QA lead's batch gaps, ranks 1 to 4 (task p2b-qa-tests-batch, phase review N4).

Every count below is derived by hand from the batch rules in PLAN.md section 7 and the
`run` docstring, with the numbers in pipeline/constants.py: WRITER = CHECKER = 14 calls,
SCRIPT_ATTEMPTS = 2, SCRIPTS_PER_BATCH = 7, REASON_MAX_CHARS = 120. A rewrite never spends what
the scripts still to come need: SCRIPT_ATTEMPTS writer calls and one checker call each.
"""

import re
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.script.gemini import GeminiError
from tests.script.test_batch import EXHAUSTED, REWRITE, FakeGemini, slug, writer_answer
from tests.script.test_batch import run as run_batch
from tests.script.test_batch import setup as make_batch

WRITER, CHECKER = constants.WRITER_MODEL, constants.CHECKER_MODEL


def kinds(fake: FakeGemini, name: str | None = None) -> list[str]:
    return [c[2] for c in fake.calls if name is None or c[1] == name]


def flag_lines(body: str) -> list[str]:
    return re.findall(r"^- case-\d\d.*$", body, re.MULTILINE)


def reason_of(body: str, where: str) -> str:
    """The reason in the one flag line that starts with `where`, without its code span ticks."""
    found = re.findall(rf"^- {re.escape(where)}: `+ (.*) `+$", body, re.MULTILINE)
    assert len(found) == 1, f"one flag line for {where}"
    return str(found[0])


def all_unsupported(name: str, n: int, index: int) -> str:
    return "UNSUPPORTED"


# --- rank 1: a rewrite that raises keeps the script, flagged ---------------------------------------

def rewrite_raises(error: str) -> Any:
    def rewrite(name: str, n: int) -> Any:
        if error == "gemini":
            raise GeminiError("HTTP 429: quota")
        return {"narration": "see www.example.org for the rest"}  # validate: contains a URL
    return rewrite


@pytest.mark.parametrize("error", ["gemini", "generate"])
def test_rewrite_error_keeps_the_script_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                error: str) -> None:
    """R11.2: GeminiError or GenerateError from rewrite_line leaves the script in, unchanged, with
    the first check's reason flagged on that scene and no recheck (no rewrite landed). Targets
    `_check_and_repair` 8 to 40."""
    dirs, fake = make_batch(tmp_path, monkeypatch, count=1)
    fake.check = lambda name, n, i: "UNSUPPORTED" if n == 0 and i == 2 else "SUPPORTED"
    fake.rewrite = rewrite_raises(error)
    assert run_batch(dirs) == 0
    script = dirs.written()[slug(1)]
    assert script.scenes[2].narration == writer_answer(fake.sources[slug(1)])["scenes"][2]["narration"]
    assert kinds(fake) == ["write", "check", "rewrite"]
    body = dirs.body()
    assert reason_of(body, "case-01, scene 3") == "checker says unsupported 2"
    assert len(flag_lines(body)) == 1


# --- rank 2: exact budget counts ---------------------------------------------------------------------

def every_line_failing_spends_the_budget_exactly(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Script k (0 to 6) starts with 2k writer and 2k checker calls spent and 6 - k scripts to come.
    Write: 2k + 1. Spare writes 14 - (2k + 1) - 2 * (6 - k) = 1, so one rewrite, on scene 0.
    Spare checks 14 - (2k + 1) - (6 - k) = 7 - k >= 1, so the rewrite runs and one recheck follows.
    Totals: writer 7 + 7 = 14, checker 7 + 7 = 14; 7 scenes still failing in 7 scripts: 49 flags."""
    dirs, fake = make_batch(root, monkeypatch)
    fake.check = all_unsupported
    assert run_batch(dirs) == 0
    assert fake.count(WRITER) == 14 and fake.count(CHECKER) == 14
    written = dirs.written()
    assert list(written) == [slug(n) for n in range(1, 8)]
    for name, script in written.items():
        assert kinds(fake, name) == ["write", "check", "rewrite", "check"]
        original = writer_answer(fake.sources[name])["scenes"]
        assert script.scenes[0].narration == REWRITE
        assert [s.narration for s in script.scenes[1:]] == [s["narration"] for s in original[1:]]
    assert len(flag_lines(dirs.body())) == 49


def test_every_line_failing_spends_the_budget_exactly(tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """Targets `_Budget.__init__` 2 and 4, `run` 56 to 59, `_write` 2, `_check` 1 to 3."""
    every_line_failing_spends_the_budget_exactly(tmp_path, monkeypatch)


def test_one_script_rewrites_every_failing_line_then_rechecks_once(tmp_path: Path,
                                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """One script, nothing to come: spare writes 14 - 1 = 13 >= 7, spare checks 14 - 1 = 13. All 7
    scenes are rewritten, then one recheck."""
    dirs, fake = make_batch(tmp_path, monkeypatch, count=1)
    fake.check = all_unsupported
    assert run_batch(dirs) == 0
    assert kinds(fake) == ["write", "check"] + ["rewrite"] * 7 + ["check"]
    assert [s.narration for s in dirs.written()[slug(1)].scenes] == [REWRITE] * 7
    assert len(flag_lines(dirs.body())) == 7


def test_checker_budget_binds_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CHECKER = 8. Script 0: check 1, spare checks 8 - 1 - 6 = 1, spare writes 14 - 1 - 12 = 1:
    one rewrite and a recheck (checks 2). Script k >= 1: check k + 2, spare checks
    8 - (k + 2) - (6 - k) = 0: no rewrite. Totals: checker 8, writer 7 + 1 = 8, one rewrite, all 7
    written. Targets `_Budget.spare_checks` 1 and 2, `_check_and_repair` 8 to 26."""
    monkeypatch.setattr(constants, "CHECKER_MAX_CALLS_PER_BATCH", 8)
    dirs, fake = make_batch(tmp_path, monkeypatch)
    fake.check = all_unsupported
    assert run_batch(dirs) == 0
    assert fake.count(CHECKER) == 8 and fake.count(WRITER) == 8
    assert [c[1] for c in fake.calls if c[2] == "rewrite"] == [slug(1)]
    assert len(dirs.written()) == 7


def test_retries_spend_the_writer_budget_exactly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every first writer answer is invalid: script k spends 2 writer calls, so it starts its check
    with 2k + 2 spent and spare writes 14 - (2k + 2) - 2 * (6 - k) = 0. No rewrite; writer 14,
    checker 7; scene 1 of every script flagged."""
    dirs, fake = make_batch(tmp_path, monkeypatch)
    fake.write = lambda name, n: {"hook": "broken"} if n == 0 else writer_answer(fake.sources[name])
    fake.check = lambda name, n, i: "UNSUPPORTED" if i == 0 else "SUPPORTED"
    assert run_batch(dirs) == 0
    assert fake.count(WRITER) == 14 and fake.count(CHECKER) == 7
    assert "rewrite" not in kinds(fake)
    body = dirs.body()
    for n in range(1, 8):
        assert reason_of(body, f"{slug(n)}, scene 1") == "checker says unsupported 0"


# --- rank 3: flag content ----------------------------------------------------------------------------

def test_exact_failure_after_the_rewrite_names_the_new_tokens(tmp_path: Path,
                                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag comes from the recheck: the rewrite swaps 1850 for 1851 and 1852, and the flag names
    those. Targets `_check` 14 to 37."""
    dirs, fake = make_batch(tmp_path, monkeypatch, count=1)
    fake.write = lambda name, n: writer_answer(fake.sources[name], extra=" It began in 1850.")
    fake.rewrite = lambda name, n: {"narration": f"{REWRITE} in 1851 and 1852"}
    assert run_batch(dirs) == 0
    assert kinds(fake) == ["write", "check", "rewrite", "check"]
    reason = reason_of(dirs.body(), "case-01, scene 1")
    prefix = "not in the linked facts: "
    assert reason.startswith(prefix)
    assert set(reason[len(prefix):].split(", ")) == {"1851", "1852"}


def test_both_layers_failing_give_one_flag_with_both_reasons(tmp_path: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = make_batch(tmp_path, monkeypatch, count=1)
    fake.write = lambda name, n: writer_answer(fake.sources[name], extra=" It began in 1850.")
    fake.rewrite = lambda name, n: {"narration": f"{REWRITE} in 1851"}
    fake.check = lambda name, n, i: "PARTIAL" if i == 0 else "SUPPORTED"
    assert run_batch(dirs) == 0
    body = dirs.body()
    assert len(flag_lines(body)) == 1
    parts = reason_of(body, "case-01, scene 1").split("; ")
    assert set(parts) == {"not in the linked facts: 1851", "checker says partial 0"}


def left_out_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, message: str) -> str:
    dirs, fake = make_batch(tmp_path, monkeypatch, count=2)

    def write(name: str, n: int) -> Any:
        if name == slug(1):
            raise GeminiError(message)
        return writer_answer(fake.sources[name])

    fake.write = write
    assert run_batch(dirs) == 0
    assert list(dirs.written()) == [slug(2)]
    return reason_of(dirs.body(), slug(1))


def test_long_reason_is_clipped_to_the_cap_with_whitespace_collapsed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 7-character unit does not divide 120, so the clip ends on a letter, not on a space the
    strip would remove. Targets `_flag` 5, 11 and 12."""
    reason = left_out_reason(tmp_path, monkeypatch, "abcdef \n\t " * 300)
    expected = ("abcdef " * 18)[:120]
    assert len(expected) == constants.REASON_MAX_CHARS
    assert reason == expected


@pytest.mark.parametrize("message", ["", " \n\t "])
def test_empty_reason_says_no_reason_given(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                           message: str) -> None:
    assert left_out_reason(tmp_path, monkeypatch, message) == "no reason given"


def test_flag_names_the_scene_from_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Index 4 is scene 5 in the body. Targets `_flag_line` 3, 5 and 6."""
    dirs, fake = make_batch(tmp_path, monkeypatch, count=2)
    fake.check = lambda name, n, i: "PARTIAL" if name == slug(2) and i == 4 else "SUPPORTED"
    assert run_batch(dirs) == 0
    assert flag_lines(dirs.body()) == ["- case-02, scene 5: ` checker says partial 4 `"]


# --- rank 4: at most SCRIPTS_PER_BATCH picked ---------------------------------------------------------

def test_nine_unused_sources_write_the_first_seven(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Targets `run` 10 to 13. An out_dir that already exists is no error."""
    dirs, fake = make_batch(tmp_path, monkeypatch, count=9)
    dirs.out.mkdir()
    assert run_batch(dirs) == 0
    assert list(dirs.written()) == [slug(n) for n in range(1, 8)]
    assert {c[1] for c in fake.calls} == {slug(n) for n in range(1, 8)}
    assert not EXHAUSTED.search(dirs.body())


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact 14/14 budget with every line failing, and a rewrite error that keeps its script."""
    for name in ("budget", "rewrite"):
        (tmp_path / name).mkdir()
    every_line_failing_spends_the_budget_exactly(tmp_path / "budget", monkeypatch)
    test_rewrite_error_keeps_the_script_flagged(tmp_path / "rewrite", monkeypatch, "gemini")
