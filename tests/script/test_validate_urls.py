"""CSO P2-3: bare domains and look-alike forms count as URLs; decimals and abbreviations do not
(task p2-validate-urls, R12.1). Cases come from docs/threat-model.md and the p2-cso handoff."""

import pytest

from pipeline.script import validate
from tests.script.scripts import make_script
from tests.script.test_validate import FIELDS, with_text

BARE_DOMAINS = [
    "example.net",
    "full story at example.net/case",
    "bit.ly/x",
    "EXAMPLE.NET",
    "see Example.Com/Case",
    "visit example.net.",
]
LOOK_ALIKES = {
    "full-width www": "ｗｗｗ．example．com",
    "full-width domain": "ｅｘａｍｐｌｅ．ｎｅｔ",
    "full-width scheme": "ｈｔｔｐｓ：／／x．io",
    "ideographic full stop": "example。net",
    "halfwidth ideographic full stop": "example｡net",
}
ORDINARY = [
    "3.5",
    "about 1.5 million",
    "version 2.0",
    "the U.S. Navy",
    "at 4 a.m. local",
    "Dr. Ray said",
    "No. 5",
    "wait… and",
    "wait…and",
]


def label(field: str) -> str:
    return "tag" if field == "tags" else field


def assert_url_problem(field: str, text: str) -> None:
    found = validate.problems(make_script(**with_text(field, text)))
    assert any(label(field) in m and "URL" in m for m in found), found


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", BARE_DOMAINS)
def test_bare_domains_rejected_in_every_field(field: str, text: str) -> None:
    assert_url_problem(field, text)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", LOOK_ALIKES.values(), ids=LOOK_ALIKES.keys())
def test_look_alike_forms_rejected_in_every_field(field: str, text: str) -> None:
    assert_url_problem(field, text)


@pytest.mark.parametrize("field", FIELDS)
def test_full_width_angle_bracket_rejected(field: str) -> None:
    found = validate.problems(make_script(**with_text(field, "a ＜b＞ c")))
    assert any(label(field) in m and "<" in m for m in found), found


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ORDINARY)
def test_decimals_and_abbreviations_pass(field: str, text: str) -> None:
    assert validate.problems(make_script(**with_text(field, text))) == []


def test_acceptance() -> None:
    """A bare domain and a full-width www are caught in the description, the field the CSO scenario
    names, and in narration; a decimal and an abbreviation still pass."""
    for field in ("description", "narration"):
        assert_url_problem(field, "full story at example.net/case")
        assert_url_problem(field, LOOK_ALIKES["full-width www"])
        assert validate.problems(make_script(**with_text(field, "about 3.5 million in the U.S."))) == []
