"""Review round 1 of p2-validate-urls: invisible combining marks and variation selectors must not
split a domain past the URL check, and non-Latin domains and dot look-alikes stay rejected.

NFKC leaves these marks alone and they are not Cf, Co or Cs, so "example.c<U+034F>om" read as no
URL at all. A fix may report them as a URL or as an invisible character; either names the field.
Accented letters, precomposed or decomposed, must still pass."""

import pytest

from pipeline.script import validate
from tests.script.scripts import make_script
from tests.script.test_validate import FIELDS, with_text
from tests.script.test_validate_urls import assert_url_problem, label

# Each mark sits before the dot or inside the TLD, where it breaks the domain match today.
MARK_SPLIT = {
    "U+034F in TLD": "full story at example.c͏om",
    "U+FE0F before dot": "example️.com",
    "U+180B in TLD": "example.c᠋om",
    "U+180C before dot": "example᠌.net",
    "U+180D in TLD": "example.n᠍et",
    "U+17B4 in TLD": "example.c឴om",
    "U+17B5 before dot": "example឵.com",
    "U+E0100 in TLD": "example.c\U000e0100om",
    "U+E01EF before dot": "example\U000e01ef.net",
}
NON_LATIN_DOMAINS = ["пример.рф", "例え.日本"]
DOT_LOOK_ALIKES = {"U+FF0E": "example．com", "U+2024": "example․com"}
ACCENTED = ["café", "naïve", "café au lait", "naïve", "about 3.5 million", "the U.S. Navy"]


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", MARK_SPLIT.values(), ids=MARK_SPLIT.keys())
def test_mark_split_domain_rejected(field: str, text: str) -> None:
    found = validate.problems(make_script(**with_text(field, text)))
    assert any(label(field) in m for m in found), found


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", NON_LATIN_DOMAINS)
def test_non_latin_domain_rejected(field: str, text: str) -> None:
    assert_url_problem(field, text)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", DOT_LOOK_ALIKES.values(), ids=DOT_LOOK_ALIKES.keys())
def test_dot_look_alike_rejected(field: str, text: str) -> None:
    assert_url_problem(field, text)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ACCENTED)
def test_accented_text_passes(field: str, text: str) -> None:
    assert validate.problems(make_script(**with_text(field, text))) == []
