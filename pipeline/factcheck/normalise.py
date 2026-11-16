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


import re
import string
from collections.abc import Iterator
from decimal import Decimal, localcontext

_SMALL = {word: value for value, word in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen".split())}
_TENS = {word: 10 * value for value, word in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split(), start=2)}
_BIG = {"thousand": 10**3, "million": 10**6, "billion": 10**9, "trillion": 10**12}
_SCALE_WORDS = {"hundred": 100, **_BIG}
_SCALES = {"k": 10**3, "m": 10**6, "b": 10**9, "bn": 10**9, **_SCALE_WORDS}

_LETTER = r"[^\W\d_]"
_TOKEN = re.compile(
    r"(?P<digits>(?:[0-9]{1,3}(?:,[0-9]{3}(?![0-9]))+|[0-9]+)(?:\.[0-9]+)?)"
    rf"(?:(?:st|nd|rd|th|s)(?!{_LETTER})"
    rf"|(?P<glued>bn|[kmb])(?!{_LETTER})"
    rf"|\s+(?P<word>hundred|thousand|million|billion|trillion)(?!{_LETTER}))?"
    rf"|(?P<w>{_LETTER}+)",
    re.IGNORECASE,
)
_JOIN = re.compile(r"[\s\-‐‑]+")

_PUNCT = string.punctuation + "‘’“”«»…–—"
_CLOSERS = "\"')]}”’»"
_PRONOUNS = {"I", "I'm", "I've", "I'd", "I'll"}

Parsed = tuple[int, int]  # value, index just after the phrase


def _digit_number(match: re.Match[str]) -> str:
    raw = match.group("digits").replace(",", "")
    scale = _SCALES.get((match.group("glued") or match.group("word") or "").lower(), 1)
    with localcontext() as context:
        context.prec = len(raw) + 20  # exact for any digit count; scales add at most 12 digits
        return format((Decimal(raw) * scale).normalize(), "f")


def _group(run: list[str], i: int) -> Parsed | None:
    """A number from zero to 99: a small word, or a ten with an optional unit."""
    if i >= len(run):
        return None
    word = run[i]
    if word in _SMALL:
        return _SMALL[word], i + 1
    if word in _TENS:
        unit = _SMALL.get(run[i + 1], 0) if i + 1 < len(run) else 0
        return (_TENS[word] + unit, i + 2) if 1 <= unit <= 9 else (_TENS[word], i + 1)
    return None


def _below_thousand(run: list[str], i: int) -> Parsed | None:
    group = _group(run, i)
    if group is None:
        return None
    value, j = group
    if not (1 <= value <= 99 and run[j:j + 1] == ["hundred"]):
        return value, j
    j += 1
    rest = _group(run, j + 1 if run[j:j + 1] == ["and"] else j)
    if rest is None or rest[0] == 0:
        return value * 100, j
    return value * 100 + rest[0], rest[1]


def _scaled(run: list[str], i: int) -> Parsed | None:
    """Chunks below 1000, each optionally followed by a scale word, with "and" after a scale."""
    total, end, j = 0, i, i
    while (chunk := _below_thousand(run, j)) is not None:
        value, k = chunk
        scale = _BIG.get(run[k]) if k < len(run) else None
        if scale is None:
            return total + value, k
        total += value * scale
        end = j = k + 1
        if run[j:j + 1] == ["and"]:
            j += 1
    return (total, end) if end > i else None


def _year(run: list[str], i: int) -> Parsed | None:
    """Two groups of 10 to 99 ("nineteen eighty-four"), or one and "oh" plus a unit."""
    high = _group(run, i)
    if high is None or not 10 <= high[0] <= 99:
        return None
    j = high[1]
    low = _group(run, j)
    if low is not None and 10 <= low[0] <= 99:
        return high[0] * 100 + low[0], low[1]
    unit = _SMALL.get(run[j + 1], 0) if run[j:j + 1] == ["oh"] and j + 1 < len(run) else 0
    return (high[0] * 100 + unit, j + 2) if 1 <= unit <= 9 else None


def _phrase(run: list[str], i: int) -> Parsed | None:
    if run[i] == "a" and run[i + 1:i + 2] and run[i + 1] in _SCALE_WORDS:
        parsed = _scaled(["one"] + run[i + 1:], 0)  # "a" stands in for "one"
        return None if parsed is None else (parsed[0], i + parsed[1])
    return _year(run, i) or _scaled(run, i)


def _word_numbers(run: list[str]) -> list[str]:
    found: list[str] = []
    i = 0
    while i < len(run):
        phrase = _phrase(run, i)
        if phrase is None:
            i += 1
            continue
        value, end = phrase
        if not (end - i == 1 and value <= 9):  # a lone zero to nine is rarely a quantity
            found.append(str(value))
        i = end
    return found


def numbers(text: str) -> list[str]:
    """Every number in `text` in canonical form, in order of appearance, repeats kept."""
    found: list[str] = []
    run: list[str] = []  # consecutive words, joined by spaces or hyphens only
    previous_end = 0
    for match in _TOKEN.finditer(text):
        if match.group("digits") is not None:
            found += _word_numbers(run)
            run = []
            found.append(_digit_number(match))
            continue
        if run and not _JOIN.fullmatch(text, previous_end, match.start()):
            found += _word_numbers(run)
            run = []
        run.append(match.group("w").lower())
        previous_end = match.end()
    return found + _word_numbers(run)


def _clean(raw: str) -> str:
    word = raw.replace("’", "'").strip(_PUNCT)
    return word[:-2] if word.endswith("'s") else word


def _ends_sentence(raw: str) -> bool:
    return raw.rstrip(_CLOSERS).endswith((".", "!", "?"))


def _words(text: str) -> Iterator[tuple[str, bool]]:
    """Each cleaned word with whether it opens a sentence."""
    opens = True
    for raw in text.split():
        word = _clean(raw)
        if word:
            yield word, opens
        opens = _ends_sentence(raw) or (opens and not word)


def _is_name(word: str, opens: bool) -> bool:
    return sum(char.isupper() for char in word) >= 2 or (word[0].isupper() and not opens)


def proper_nouns(text: str) -> list[str]:
    """Every proper noun in `text`, lowercased, in order of appearance, repeats kept."""
    return [word.lower() for word, opens in _words(text)
            if word not in _PRONOUNS and _is_name(word, opens)]


def plain_words(text: str) -> set[str]:
    """Every word in `text`, punctuation and possessive stripped, lowercased."""
    return {word.lower() for word, _ in _words(text)}
