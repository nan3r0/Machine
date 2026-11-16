"""Pull the checkable tokens out of text, in one standard form (PLAN.md section 5, task p2-factcheck-exact).

Pure functions, standard library only. Imports nothing from `pipeline` except the contracts.

Numbers. `numbers(text)` returns every number in `text` as a canonical decimal string, in order of
appearance: digits only, no sign, no thousands separators, no trailing zeros after a decimal point
and no trailing point ("1.50" -> "1.5", "2.0" -> "2"). Currency symbols and units are dropped, so
`$45M`, `45 million dollars` and `45,000,000` all give "45000000", and `12%` and `12 percent` give "12".
- Digit forms: integers with or without comma thousands separators ("1,200": a comma followed by
  exactly three digits; "1, 2" is two numbers), decimals ("3.5"), an
  ordinal or decade suffix ("21st", "1990s" -> "21", "1990"), a scale suffix glued to the digits
  (k, m, b, bn, any case: "$1.2B" -> "1200000000") or a scale word after them ("3.2 million",
  "45 thousand"). Scale words: hundred, thousand, million, billion, trillion.
- Any character other than a digit, `.` between digits or `,` between digit groups ends a number,
  so "1998-03-03" gives "1998", "3", "3" and "3:15" gives "3", "15". There are no negative numbers.
- Number words (any case, hyphenated or not): zero to nineteen, the tens, the scale words, "a"
  before a scale word ("a hundred" -> "100") and "and" inside a phrase after a scale word ("one
  hundred and five" -> "105"). Two groups of 10 to 99 in a row read as a year ("twenty twenty-four"
  -> "2024", "nineteen eighty-four" -> "1984"), and a group of 10 to 99 followed by "oh" and one to
  nine too ("nineteen oh five" -> "1905"). A ten and a unit word make one group ("forty five" and
  "forty-five" -> "45"). Plural scale words ("hundreds of", "millions") are not numbers.
- A number phrase made only of one word from zero to nine ("one night", "no one", "two of them")
  is ignored, because those words are mostly not quantities. Digits always count ("1", "7").
- "point" is not read ("one point five" yields nothing checkable).

Proper nouns. `proper_nouns(text)` returns, lowercased and in order of appearance, every word that
either has two or more uppercase letters ("NASA", "McDonald") or starts with an uppercase letter
and is not the first word of a sentence. A sentence starts at the beginning of `text` and after a
word ending in `.`, `!` or `?` (closing quotes and brackets after the mark do not matter). Words are
split on whitespace; leading and trailing punctuation and a trailing possessive ('s or ’s) are
removed first. The pronoun forms "I", "I'm", "I've", "I'd" and "I'll" are never proper nouns. A
word made only of digits and punctuation is never a proper noun.

`plain_words(text)` is the set of every word in `text`, prepared the same way and lowercased. The
exact check compares a narration's proper nouns against the plain words of its facts, because a
fact may start a sentence with the same name.
"""


def numbers(text: str) -> list[str]:
    """Every number in `text` in canonical form, in order of appearance, repeats kept."""
    raise NotImplementedError


def proper_nouns(text: str) -> list[str]:
    """Every proper noun in `text`, lowercased, in order of appearance, repeats kept."""
    raise NotImplementedError


def plain_words(text: str) -> set[str]:
    """Every word in `text`, punctuation and possessive stripped, lowercased."""
    raise NotImplementedError
