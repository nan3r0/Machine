"""R1: script JSON is validated before any work. Also pins WordTiming and QAReport invariants."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from pipeline import constants
from pipeline.schema import QAFailure, QAReport, Script, WordTiming

SAMPLE = Path(__file__).resolve().parent.parent / "queue" / "approved" / "sample-40s.json"


def sample_dict() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return data


def validate(data: dict[str, Any]) -> Script:
    return Script.model_validate_json(json.dumps(data))


def error_fields(exc: ValidationError) -> set[str]:
    return {".".join(str(p) for p in err["loc"]) for err in exc.errors()}


def test_acceptance() -> None:
    """R1.1 and R1.2: the sample validates and fits the retention format; a bad field is named."""
    script = Script.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
    low, high = constants.RETENTION_WORDS
    assert low <= len(script.narration_words()) <= high
    assert script.id == SAMPLE.stem, "queue files are named <id>.json"

    data = sample_dict()
    data["scenes"][0]["source_fact_ids"] = ["one"]
    with pytest.raises(ValidationError) as exc:
        validate(data)
    assert "scenes.0.source_fact_ids.0" in error_fields(exc.value)


@pytest.mark.parametrize("field", ["id", "topic", "template", "hook", "scenes", "loop_line", "title",
                                   "description", "tags", "platforms", "publish_after"])
def test_missing_field_is_named(field: str) -> None:
    data = sample_dict()
    del data[field]
    with pytest.raises(ValidationError) as exc:
        validate(data)
    assert field in error_fields(exc.value)


@pytest.mark.parametrize(("field", "value"), [
    ("hook", 5),
    ("scenes", "not a list"),
    ("tags", "one tag"),
    ("publish_after", "next tuesday"),
    ("template", "slideshow"),
    ("platforms", ["myspace"]),
])
def test_wrong_type_is_named(field: str, value: object) -> None:
    data = sample_dict()
    data[field] = value
    with pytest.raises(ValidationError) as exc:
        validate(data)
    assert any(loc.split(".")[0] == field for loc in error_fields(exc.value))


def test_numeric_string_is_not_coerced_to_int() -> None:
    data = sample_dict()
    data["scenes"][0]["source_fact_ids"] = ["12"]
    with pytest.raises(ValidationError):
        validate(data)


def test_unknown_field_is_rejected() -> None:
    data = sample_dict()
    data["voice"] = "someone"
    with pytest.raises(ValidationError) as exc:
        validate(data)
    assert "voice" in error_fields(exc.value)


@pytest.mark.parametrize("bad_id", ["../etc/passwd", "Has Caps", "", "a/b", "trailing-"])
def test_id_must_be_a_safe_slug(bad_id: str) -> None:
    data = sample_dict()
    data["id"] = bad_id
    with pytest.raises(ValidationError):
        validate(data)


@pytest.mark.parametrize("field", ["hook", "loop_line", "title", "topic"])
def test_blank_text_is_rejected(field: str) -> None:
    data = sample_dict()
    data[field] = "   "
    with pytest.raises(ValidationError):
        validate(data)


def test_empty_scenes_rejected() -> None:
    data = sample_dict()
    data["scenes"] = []
    with pytest.raises(ValidationError):
        validate(data)


def test_narration_text_joins_parts_with_single_spaces() -> None:
    data = sample_dict()
    data["hook"] = "Hook  line."
    data["scenes"] = [dict(data["scenes"][0], narration="First\nscene."),
                      dict(data["scenes"][0], narration="Café {x} 2013,")]
    data["loop_line"] = "Loop."
    script = validate(data)
    assert script.narration_text() == "Hook line. First scene. Café {x} 2013, Loop."
    assert script.narration_words() == ["Hook", "line.", "First", "scene.", "Café", "{x}", "2013,", "Loop."]


def test_word_timing_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        WordTiming(word="a", start=1.0, end=0.5)
    with pytest.raises(ValidationError):
        WordTiming(word="a", start=-0.1, end=0.5)
    assert WordTiming(word="a", start=0.5, end=0.5).end == 0.5


def test_qa_report_passed_must_match_failures() -> None:
    failure = QAFailure(check="silence", reason="2.0 s silence > 1.5 s")
    with pytest.raises(ValidationError):
        QAReport(passed=True, failures=[failure], measured={})
    with pytest.raises(ValidationError):
        QAReport(passed=False, failures=[], measured={})
    assert not QAReport(passed=False, failures=[failure], measured={"x": 1.0}).passed


def test_qa_failure_check_names_are_fixed() -> None:
    with pytest.raises(ValidationError):
        QAFailure(check="vibes", reason="bad")
