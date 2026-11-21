"""QA lead ranks 6 and 7 (phase review N4): exhaustive number-word loops and decimal scales.

Expected values come from the words() oracle in tests/factcheck/test_exact.py, a Fraction oracle
below, or literals from the normalise.py docstring; never from the code under test. Loops collect
every mismatch so one run shows them all.
"""

from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pipeline.factcheck.exact import unsupported
from pipeline.factcheck.normalise import numbers, proper_nouns
from tests.factcheck.test_exact import UNITS, words

TWO_DIGITS = range(10, 100)
SCALE_FORMS = [("", 1), ("k", 10**3), ("K", 10**3), ("m", 10**6), ("M", 10**6), ("b", 10**9),
               ("B", 10**9), ("bn", 10**9), ("BN", 10**9), (" hundred", 100),
               (" thousand", 10**3), (" Million", 10**6), (" billion", 10**9), (" trillion", 10**12)]


def mismatches(cases: list[tuple[str, list[str]]]) -> list[tuple[str, list[str], list[str]]]:
    return [(text, numbers(text), want) for text, want in cases if numbers(text) != want]


def test_every_number_below_ten_thousand_in_words() -> None:
    cases = []
    for n in range(1, 10_000):
        want = [] if n <= 9 else [str(n)]  # a lone zero to nine is ignored
        text = words(n)
        cases += [(text, want), (text.replace("-", " "), want), (text.upper(), want),
                  (text.replace("hundred ", "hundred and "), want)]
    assert mismatches(cases) == []


def test_every_hundreds_count_to_ninety_nine() -> None:
    cases = [(f"{words(h)} hundred", [str(h * 100)]) for h in range(1, 100)]
    assert mismatches(cases) == []


def test_every_two_group_year() -> None:
    cases = [(f"{words(high)} {words(low)}", [str(high * 100 + low)])
             for high in TWO_DIGITS for low in TWO_DIGITS]
    assert mismatches(cases) == []


def test_every_oh_year() -> None:
    cases = [(f"{words(high)} oh {UNITS[unit]}", [str(high * 100 + unit)])
             for high in TWO_DIGITS for unit in range(1, 10)]
    assert mismatches(cases) == []


@pytest.mark.parametrize(("text", "expected"), [
    ("twenty ten", ["2010"]),
    ("nine lives", []),
    ("ten men", ["10"]),
    ("a thousand and one nights", ["1001"]),
    ("one hundred one", ["101"]),
    ("nineteen five", ["19"]),
    ("nineteen oh five forty-two", ["1905", "42"]),
    ("nineteen oh ten", ["19", "10"]),
    ("nineteen oh dear", ["19"]),
    ("nineteen oh", ["19"]),
    ("give me a", []),
    ("ninety-nine hundred", ["9900"]),
    ("a hundred", ["100"]),
    ("a thousand", ["1000"]),
    ("a million", ["1000000"]),
    ("a billion", ["1000000000"]),
    ("a trillion", ["1000000000000"]),
    ("one trillion", ["1000000000000"]),
])
def test_number_word_literals(text: str, expected: list[str]) -> None:
    assert numbers(text) == expected


@pytest.mark.parametrize(("text", "expected"), [
    ("McDonald ran it.", ["mcdonald"]),
    ("UK police", ["uk"]),
])
def test_two_capitals_open_a_sentence_as_a_name(text: str, expected: list[str]) -> None:
    assert proper_nouns(text) == expected


def canonical(value: Fraction) -> str:
    """Independent oracle: value has at most three decimal places."""
    thousandths = value * 1000
    assert thousandths.denominator == 1
    whole, rest = divmod(thousandths.numerator, 1000)
    return str(whole) if rest == 0 else f"{whole}.{rest:03d}".rstrip("0")


@given(st.integers(min_value=0, max_value=10**7), st.integers(min_value=0, max_value=3),
       st.sampled_from(SCALE_FORMS), st.booleans(), st.booleans())
def test_decimal_with_scale_matches_fraction_oracle(
        mantissa: int, places: int, scale: tuple[str, int], dollar: bool, commas: bool) -> None:
    whole, fraction = divmod(mantissa, 10**places)
    head = f"{whole:,}" if commas else str(whole)
    digits = f"{head}.{fraction:0{places}d}" if places else head
    suffix, factor = scale
    text = f"it cost {'$' if dollar else ''}{digits}{suffix} in all"
    assert numbers(text) == [canonical(Fraction(mantissa, 10**places) * factor)]


@given(st.integers(min_value=10, max_value=10**12 - 1))
def test_words_digits_and_commas_support_each_other(n: int) -> None:
    for line, fact in [(words(n), f"{n:,}"), (f"{n:,}", words(n)), (str(n), f"{n:,}")]:
        assert unsupported(f"it was {line} units", [f"exactly {fact} units"]) == []


def test_acceptance() -> None:
    """QA lead rank 6: "twenty ten" reads as 2010 and a lone small word is not a number."""
    assert numbers("in twenty ten") == ["2010"]
    assert numbers("nine lives, ten men") == ["10"]
    assert numbers("nineteen oh five forty-two") == ["1905", "42"]
