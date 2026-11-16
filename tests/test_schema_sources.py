"""R8.1, R11.1 shapes: Fact, SourceFile, Flag and LineVerdict (task p2-contracts, spec.md section 3)."""

from typing import Any

import pytest
from pydantic import ValidationError

from pipeline.schema import Fact, Flag, LineVerdict, SourceFile

FACT = {"id": 101, "text": "NOAA recorded the Bloop in 1997.", "url": "https://oceanservice.noaa.gov/facts/bloop.html"}
SOURCE = {"topic": "The Bloop", "facts": [FACT, {**FACT, "id": 102}]}
FLAG = {"script_id": "the-bloop", "scene": 2, "reason": "1850 is in no linked fact"}
VERDICT = {"index": 0, "verdict": "SUPPORTED", "reason": "fact 101 says so", "fact_ids": [101]}


def rejects(model: Any, data: dict[str, Any], field: str) -> None:
    with pytest.raises(ValidationError) as caught:
        model.model_validate(data)
    assert field in str(caught.value)


def test_good_shapes_parse() -> None:
    assert Fact.model_validate(FACT).id == 101
    assert len(SourceFile.model_validate(SOURCE).facts) == 2
    assert Flag.model_validate(FLAG).scene == 2
    assert Flag.model_validate({**FLAG, "scene": None}).scene is None
    assert LineVerdict.model_validate(VERDICT).fact_ids == [101]
    assert LineVerdict.model_validate({**VERDICT, "verdict": "PARTIAL"}).verdict == "PARTIAL"
    assert LineVerdict.model_validate({**VERDICT, "verdict": "UNSUPPORTED", "fact_ids": []}).fact_ids == []


@pytest.mark.parametrize("url", [
    "http://oceanservice.noaa.gov/facts/bloop.html",
    "ftp://example.org/a",
    "javascript:alert(1)",
    "https://",
    "https:// example.org",
    "https://example.org/a b",
    "oceanservice.noaa.gov/facts/bloop.html",
    "",
])
def test_fact_url_must_be_https(url: str) -> None:
    rejects(Fact, {**FACT, "url": url}, "url")


@pytest.mark.parametrize(("field", "value"), [
    ("id", 0), ("id", -3), ("id", "101"), ("id", 1.5), ("text", ""), ("text", "  \n"),
])
def test_fact_rejects_bad_field(field: str, value: Any) -> None:
    rejects(Fact, {**FACT, field: value}, field)


def test_fact_rejects_extra_and_missing_fields() -> None:
    rejects(Fact, {**FACT, "note": "x"}, "note")
    rejects(Fact, {"id": 1, "text": "t"}, "url")


def test_source_file_rejects_bad_fields() -> None:
    rejects(SourceFile, {**SOURCE, "facts": []}, "facts")
    rejects(SourceFile, {**SOURCE, "topic": " "}, "topic")
    rejects(SourceFile, {"facts": SOURCE["facts"]}, "topic")


def test_source_file_rejects_repeated_fact_id() -> None:
    with pytest.raises(ValidationError, match="fact ids"):
        SourceFile.model_validate({**SOURCE, "facts": [FACT, FACT]})


@pytest.mark.parametrize(("field", "value"), [
    ("script_id", ""), ("scene", -1), ("scene", "2"), ("reason", " "),
])
def test_flag_rejects_bad_field(field: str, value: Any) -> None:
    rejects(Flag, {**FLAG, field: value}, field)


@pytest.mark.parametrize(("field", "value"), [
    ("index", -1), ("verdict", "supported"), ("verdict", "MAYBE"), ("reason", ""), ("fact_ids", ["101"]),
])
def test_line_verdict_rejects_bad_field(field: str, value: Any) -> None:
    rejects(LineVerdict, {**VERDICT, field: value}, field)


@pytest.mark.parametrize("verdict", ["SUPPORTED", "PARTIAL"])
def test_support_without_a_fact_id_is_rejected(verdict: str) -> None:
    """Owner decision D5 and R11.1: a verdict that names no fact cannot count as support."""
    with pytest.raises(ValidationError, match="fact id"):
        LineVerdict.model_validate({**VERDICT, "verdict": verdict, "fact_ids": []})


def test_shapes_are_frozen() -> None:
    fact = Fact.model_validate(FACT)
    with pytest.raises(ValidationError):
        fact.url = "http://example.org"  # type: ignore[misc]


def test_acceptance() -> None:
    """Every new shape accepts good input and rejects a bad field by name; urls are https only."""
    test_good_shapes_parse()
    rejects(Fact, {**FACT, "url": "http://oceanservice.noaa.gov/facts/bloop.html"}, "url")
    rejects(SourceFile, {**SOURCE, "facts": []}, "facts")
    rejects(Flag, {**FLAG, "reason": ""}, "reason")
    rejects(LineVerdict, {**VERDICT, "verdict": "MAYBE"}, "verdict")
    with pytest.raises(ValidationError):
        LineVerdict.model_validate({**VERDICT, "fact_ids": []})
