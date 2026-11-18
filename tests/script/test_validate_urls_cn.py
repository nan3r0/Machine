"""Review round 2 of p2-validate-urls: unassigned default-ignorable code points (category Cn) must
not split a domain, and a "<" or ">" followed by a combining mark must still count as an angle bracket.

Cn is not Cf, Co or Cs, NFKC leaves it alone and it is not a word character, so
"example<U+2065>.com" read as no URL. NFC composes "<" + U+0338 into U+226E, so a check on composed
text misses the raw "<". A fix may report a Cn case as a URL or as an invisible character; either
names the field. Every code point here is unassigned in Unicode 14 and 15 alike. Ordinary text with
accents, an emoji with its variation selector, decimals, abbreviations and an ellipsis must still pass."""

import pytest

from pipeline.script import validate
from tests.script.scripts import make_script
from tests.script.test_validate import FIELDS, with_text
from tests.script.test_validate_urls import label

CN_SPLIT = {
    "U+E01F0 in TLD": "evil.c\U000e01f0om",
    "U+2065 before dot": "example⁥.com",
    "U+E0080 in TLD": "example.c\U000e0080om",
    "U+E00FF before dot": "example\U000e00ff.net",
    "U+FFF0 in TLD": "example.c￰om",
    "U+FFF8 before dot": "example￸.net",
}
ANGLE_WITH_MARK = {"< U+0338": "a ≮ b", "> U+0338": "a ≯ b"}
ORDINARY = [
    "café",
    "café",
    "naïve",
    "❤️ the mystery",
    "about 3.5 million",
    "the U.S. Navy",
    "wait… and then",
]


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", CN_SPLIT.values(), ids=CN_SPLIT.keys())
def test_unassigned_code_point_split_rejected(field: str, text: str) -> None:
    found = validate.problems(make_script(**with_text(field, text)))
    assert any(label(field) in m for m in found), found


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ANGLE_WITH_MARK.values(), ids=ANGLE_WITH_MARK.keys())
def test_angle_bracket_with_mark_rejected(field: str, text: str) -> None:
    found = validate.problems(make_script(**with_text(field, text)))
    assert any(label(field) in m and "<" in m for m in found), found


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ORDINARY)
def test_ordinary_text_passes(field: str, text: str) -> None:
    assert validate.problems(make_script(**with_text(field, text))) == []
