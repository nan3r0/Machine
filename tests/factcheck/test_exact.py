"""R9: exact fact-check layer, numbers and proper nouns (task p2-factcheck-exact).

Expected values are literals from PLAN.md section 5 and the normalise.py docstring, or come from
the independent number-to-words oracle below, never from the code under test.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pipeline.factcheck.exact import unsupported
from pipeline.factcheck.normalise import numbers, plain_words, proper_nouns

UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
         "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = [(1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")]


def under_thousand(n: int) -> str:
    """American English words for 1 <= n < 1000, tens and units hyphenated."""
    hundreds, rest = divmod(n, 100)
    parts = [f"{UNITS[hundreds]} hundred"] if hundreds else []
    if rest >= 20:
        tens, unit = divmod(rest, 10)
        parts.append(f"{TENS[tens]}-{UNITS[unit]}" if unit else TENS[tens])
    elif rest:
        parts.append(UNITS[rest])
    return " ".join(parts)


def words(n: int) -> str:
    """Independent oracle: American English words for 1 <= n < 10**12, no "and"."""
    parts = []
    for size, name in SCALES:
        count, n = divmod(n, size)
        if count:
            parts.append(f"{under_thousand(count)} {name}")
    if n:
        parts.append(under_thousand(n))
    return " ".join(parts)


def test_oracle_spells_known_values() -> None:
    assert words(45) == "forty-five"
    assert words(2024) == "two thousand twenty-four"
    assert words(45_000_000) == "forty-five million"
    assert words(105) == "one hundred five"


@pytest.mark.parametrize(("text", "expected"), [
    ("$45M", ["45000000"]),
    ("45 million dollars", ["45000000"]),
    ("45,000,000", ["45000000"]),
    ("2024", ["2024"]),
    ("twenty twenty-four", ["2024"]),
    ("12%", ["12"]),
    ("12 percent", ["12"]),
    ("1.50", ["1.5"]),
    ("2.0", ["2"]),
    ("$1.2B", ["1200000000"]),
    ("3.2 million", ["3200000"]),
    ("5k", ["5000"]),
    ("2bn", ["2000000000"]),
    ("45 thousand", ["45000"]),
    ("21st", ["21"]),
    ("the 1990s", ["1990"]),
    ("1998-03-03", ["1998", "3", "3"]),
    ("3:15", ["3", "15"]),
    ("It ended in 1998.", ["1998"]),
    ("1, 2 and 3", ["1", "2", "3"]),
    ("1,200 people", ["1200"]),
    ("In 1977 it lasted 72 seconds", ["1977", "72"]),
    ("72 and 72", ["72", "72"]),
    ("7 days", ["7"]),
    ("seven days", []),
    ("one night, no one came", []),
    ("one hundred and five", ["105"]),
    ("a hundred years", ["100"]),
    ("nineteen eighty-four", ["1984"]),
    ("Nineteen Eighty-Four", ["1984"]),
    ("nineteen oh five", ["1905"]),
    ("nineteen hundred", ["1900"]),
    ("two thousand and five", ["2005"]),
    ("forty five", ["45"]),
    ("Forty-Five", ["45"]),
    ("hundreds of letters", []),
    ("one point five", []),
    ("no numbers here", []),
    ("", []),
])
def test_numbers(text: str, expected: list[str]) -> None:
    assert numbers(text) == expected


@given(st.integers(min_value=0, max_value=10**12))
def test_digit_forms_agree(n: int) -> None:
    assert numbers(str(n)) == [str(n)]
    assert numbers(f"{n:,}") == [str(n)]
    assert numbers(f"about {n:,} of them.") == [str(n)]


@given(st.integers(min_value=10, max_value=10**12 - 1))
def test_number_words_agree_with_digits(n: int) -> None:
    assert numbers(words(n)) == [str(n)]
    assert numbers(f"It took {words(n)} tries.") == [str(n)]


@given(st.integers(min_value=10, max_value=99), st.integers(min_value=10, max_value=99))
def test_two_word_groups_read_as_a_year(high: int, low: int) -> None:
    assert numbers(f"in {words(high)} {words(low)}") == [str(high * 100 + low)]


@pytest.mark.parametrize(("text", "expected"), [
    ("The signal came from Sagittarius. Nobody saw it again.", ["sagittarius"]),
    ("NASA confirmed it", ["nasa"]),
    ("the McDonald's menu", ["mcdonald"]),
    ("and I'm sure I saw it, I'll say I've seen it and I'd agree", []),
    ("Astronomer Jerry Ehman’s note", ["jerry", "ehman"]),
    ('"Wow!" He wrote it in red. Then Ohio State kept it.', ["ohio", "state"]),
    ("near Area 51", ["area"]),
    ("In 1977, Big Ear heard it", ["big", "ear"]),
    ("Who sent it? Nobody knows. (Really.) Maybe aliens.", []),
    ("they met Ehman, then Ehman left", ["ehman", "ehman"]),
    ("", []),
])
def test_proper_nouns(text: str, expected: list[str]) -> None:
    assert proper_nouns(text) == expected


def test_plain_words_strip_punctuation_and_possessive() -> None:
    assert plain_words("Ehman's note, NASA! (Big Ear’s)") == {"ehman", "note", "nasa", "big", "ear"}


def test_acceptance() -> None:
    """PLAN.md section 5: each number and name must appear in the linked facts, in any standard form."""
    facts = ["The Big Ear telescope at Ohio State picked up the signal on 15 August 1977.",
             "It lasted 72 seconds, and the project cost $45M."]
    assert unsupported("In nineteen seventy-seven, Big Ear heard it for seventy-two seconds.", facts) == []
    assert unsupported("The project cost forty-five million dollars.", facts) == []
    assert unsupported("It lasted 74 seconds near Jupiter, in 1977.", facts) == ["74", "jupiter"]


def test_names_supported_at_the_start_of_a_fact() -> None:
    assert unsupported("the team at Ohio State", ["Ohio State ran Big Ear."]) == []


def test_numbers_come_before_names_each_in_first_appearance_order_without_repeats() -> None:
    line = "Then Ohio heard 74, then Ohio heard 75 and 74 again near Mars"
    assert unsupported(line, []) == ["74", "75", "ohio", "mars"]


def test_support_may_come_from_any_linked_fact() -> None:
    assert unsupported("Ehman wrote Wow in 1977", ["Jerry Ehman wrote it.", "That was in 1977.",
                                                    "He wrote Wow."]) == []


def test_line_with_nothing_checkable_passes_without_facts() -> None:
    assert unsupported("nobody could explain it for years.", []) == []


@given(st.integers(min_value=10, max_value=10**12))
def test_any_other_number_is_unsupported(n: int) -> None:
    assert unsupported(f"it was {n:,} units", [f"exactly {n} units"]) == []
    assert unsupported(f"it was {n + 1:,} units", [f"exactly {n} units"]) == [str(n + 1)]
