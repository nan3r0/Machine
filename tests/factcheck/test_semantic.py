"""R11.1: the meaning check, one checker call per script and one verdict per line (task p2-semantic).

gemini.generate_json is replaced by a fake returning hand-built answers in the shape semantic.py
documents. A broken answer must never come back as a pass.
"""

from typing import Any

import pytest

from pipeline import constants
from pipeline.factcheck import semantic
from pipeline.schema import LineVerdict
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError
from tests.script.scripts import make_script, make_source

SOURCE = make_source(100, "The Bloop")
FACTS = SOURCE.facts
# Scene i cites fact 101 + i.
SCRIPT = make_script()
N = len(SCRIPT.scenes)


def verdict(index: int, kind: str = "SUPPORTED", fact_ids: list[int] | None = None,
            reason: str = "ok") -> dict[str, Any]:
    return {"index": index, "verdict": kind, "reason": reason,
            "fact_ids": [101 + index] if fact_ids is None else fact_ids}


def all_supported() -> list[dict[str, Any]]:
    return [verdict(i) for i in range(N)]


def install(monkeypatch: pytest.MonkeyPatch, *answers: Any) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    queue = list(answers)

    def fake(model: str, prompt: str, schema: dict[str, Any], temperature: Any = None) -> Any:
        calls.append((model, prompt, schema, temperature))
        outcome = queue.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(gemini, "generate_json", fake)
    return calls


def kinds(verdicts: list[LineVerdict]) -> list[str]:
    assert [v.index for v in verdicts] == list(range(N))
    return [v.verdict for v in verdicts]


def test_one_checker_call_at_temperature_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = install(monkeypatch, {"verdicts": all_supported()}, {"verdicts": all_supported()})
    semantic.check_script(SCRIPT, FACTS)
    [(model, prompt, schema, temperature)] = calls
    assert model == constants.CHECKER_MODEL
    assert model != constants.WRITER_MODEL
    assert temperature == constants.CHECKER_TEMPERATURE == 0
    assert set(schema["properties"]) == {"verdicts"}
    for scene, fact in zip(SCRIPT.scenes, FACTS, strict=False):
        assert scene.narration in prompt
        assert fact.text in prompt
    for word in ("SUPPORTED", "UNSUPPORTED", "PARTIAL", "rewording"):
        assert word in prompt


def test_good_answer_kept_in_scene_order(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = all_supported()
    answers[2] = verdict(2, "PARTIAL", reason="the year is not in the fact")
    answers[5] = verdict(5, "UNSUPPORTED", fact_ids=[], reason="no fact says this")
    install(monkeypatch, {"verdicts": list(reversed(answers))})
    result = semantic.check_script(SCRIPT, FACTS)
    assert kinds(result) == ["SUPPORTED", "SUPPORTED", "PARTIAL", "SUPPORTED", "SUPPORTED", "UNSUPPORTED",
                             "SUPPORTED"]
    assert result[2].reason == "the year is not in the fact"
    assert result[0].fact_ids == [101]


def test_missing_verdict_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, {"verdicts": [v for v in all_supported() if v["index"] != 3]})
    result = semantic.check_script(SCRIPT, FACTS)
    assert kinds(result)[3] == "UNSUPPORTED"
    assert kinds(result).count("SUPPORTED") == N - 1
    assert result[3].reason.strip()


def test_repeated_verdict_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, {"verdicts": [*all_supported(), verdict(4)]})
    assert kinds(semantic.check_script(SCRIPT, FACTS))[4] == "UNSUPPORTED"


def test_extra_index_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, {"verdicts": [*all_supported(), verdict(99, fact_ids=[101])]})
    assert kinds(semantic.check_script(SCRIPT, FACTS)) == ["SUPPORTED"] * N


@pytest.mark.parametrize("answer", [
    {}, {"verdicts": "all good"}, {"verdicts": None}, {"verdicts": [{"index": 0}] * N},
    {"verdicts": [{**v, "verdict": "LIKELY"} for v in all_supported()]},
    {"verdicts": [{**v, "verdict": "supported"} for v in all_supported()]},
    {"verdicts": [{**v, "index": str(v["index"])} for v in all_supported()]},
    {"verdicts": [{**v, "fact_ids": "101"} for v in all_supported()]},
    {"verdicts": ["SUPPORTED"] * N},
], ids=["empty", "string", "null", "index only", "unknown kind", "lower case", "string index",
        "string fact ids", "bare strings"])
def test_malformed_answer_is_never_a_pass(answer: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, answer)
    assert kinds(semantic.check_script(SCRIPT, FACTS)) == ["UNSUPPORTED"] * N


@pytest.mark.parametrize("kind", ["SUPPORTED", "PARTIAL"])
def test_support_without_a_linked_fact_is_unsupported(kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """D5: the verdict must name a fact linked to that scene."""
    answers = all_supported()
    answers[0] = verdict(0, kind, fact_ids=[])
    answers[1] = verdict(1, kind, fact_ids=[107])  # a real fact, but scene 1 cites 102 only
    answers[2] = verdict(2, kind, fact_ids=[999])
    answers[3] = verdict(3, kind, fact_ids=[104, 105])  # one linked, one not
    install(monkeypatch, {"verdicts": answers})
    result = kinds(semantic.check_script(SCRIPT, FACTS))
    assert result[:4] == ["UNSUPPORTED"] * 4
    assert result[4:] == ["SUPPORTED"] * (N - 4)


def test_reasons_are_clipped(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, {"verdicts": [verdict(i, "PARTIAL", reason="x" * 5000) for i in range(N)]})
    for item in semantic.check_script(SCRIPT, FACTS):
        assert 0 < len(item.reason) <= constants.REASON_MAX_CHARS


def test_gemini_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, GeminiError("HTTP 429"))
    with pytest.raises(GeminiError):
        semantic.check_script(SCRIPT, FACTS)


def test_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    """One checker call per script; one verdict per scene in order; a short answer leaves the
    missing lines UNSUPPORTED."""
    calls = install(monkeypatch, {"verdicts": all_supported()[:4]})
    result = semantic.check_script(SCRIPT, FACTS)
    assert len(calls) == 1
    assert kinds(result) == ["SUPPORTED"] * 4 + ["UNSUPPORTED"] * (N - 4)
