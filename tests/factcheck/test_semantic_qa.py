"""QA lead rank 5 (phase review N4): exact reasons and edge cases of the meaning check.

Reasons are the literals the p2-semantic contract gives: a missing, repeated or malformed verdict
says the checker gave no answer, and SUPPORTED or PARTIAL naming an unlinked fact says so (D5).
The linked-facts-per-scene and DATA_END cases live in tests/script/test_prompt_data.py.
"""

import pytest

from pipeline import constants
from pipeline.factcheck import semantic
from tests.factcheck.test_semantic import FACTS, SCRIPT, N, all_supported, install, verdict

NO_VERDICT = "checker gave no answer for this line (no verdict)"
REPEATED = "checker gave no answer for this line (more than one verdict)"
MALFORMED = "checker gave no answer for this line (malformed verdict)"
UNLINKED = "checker named no fact linked to this line"


def check_one(monkeypatch: pytest.MonkeyPatch, answers: list[object], index: int) -> tuple[str, str]:
    install(monkeypatch, {"verdicts": answers})
    result = semantic.check_script(SCRIPT, FACTS)
    assert [v.index for v in result] == list(range(N))
    return result[index].verdict, result[index].reason


def test_bool_index_does_not_fill_a_missing_scene(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = all_supported()
    answers[1] = {**verdict(1), "index": True}
    assert check_one(monkeypatch, answers, 1) == ("UNSUPPORTED", NO_VERDICT)


def test_missing_verdict_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = [v for v in all_supported() if v["index"] != 3]
    assert check_one(monkeypatch, answers, 3) == ("UNSUPPORTED", NO_VERDICT)


def test_repeated_verdict_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = [*all_supported(), verdict(4)]
    assert check_one(monkeypatch, answers, 4) == ("UNSUPPORTED", REPEATED)


def test_malformed_verdict_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = all_supported()
    answers[2] = verdict(2, "supported")
    assert check_one(monkeypatch, answers, 2) == ("UNSUPPORTED", MALFORMED)


@pytest.mark.parametrize("kind", ["SUPPORTED", "PARTIAL"])
def test_unlinked_fact_reason(kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    answers = all_supported()
    answers[0] = verdict(0, kind, fact_ids=[999])
    assert check_one(monkeypatch, answers, 0) == ("UNSUPPORTED", UNLINKED)


def test_unsupported_naming_an_unlinked_fact_keeps_its_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """D5 turns only SUPPORTED and PARTIAL into UNSUPPORTED; an UNSUPPORTED answer stands."""
    answers = all_supported()
    answers[5] = verdict(5, "UNSUPPORTED", fact_ids=[999], reason="no fact says this")
    assert check_one(monkeypatch, answers, 5) == ("UNSUPPORTED", "no fact says this")


def test_long_reason_is_stripped_then_clipped(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = all_supported()
    answers[6] = verdict(6, "PARTIAL", reason="  " + "y" * 200)
    assert check_one(monkeypatch, answers, 6) == ("PARTIAL", "y" * constants.REASON_MAX_CHARS)
