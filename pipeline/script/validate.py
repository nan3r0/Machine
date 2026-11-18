"""Checks a script must pass before it is voiced or published (CSO P1-3, phase review N5).

Task p2-validate. Pure function, no IO. Numbers come from pipeline/constants.py.
"""

import re
import unicodedata
from collections.abc import Iterator

from pipeline.constants import (
    DESCRIPTION_MAX_CHARS,
    NARRATION_MAX_CHARS,
    SCENES_MAX,
    TAG_MAX_CHARS,
    TAGS_MAX,
    TAGS_TOTAL_MAX_CHARS,
    TIKTOK_WORDS,
    TITLE_MAX_CHARS,
)
from pipeline.schema import Script

_BAD_CATEGORIES = {"Cf", "Co", "Cs"}
_MARK_CATEGORIES = {"Mn", "Me"}
# A TLD needs 2+ letters, so "3.5", "U.S." and "a.m." pass; no letters follow the first dot in "wait...".
# Unicode letters count too, so an internationalised domain ("пример.рф") is caught.
_DOMAIN_LIKE = re.compile(r"[\w-]+\.[^\W\d_]{2,}")


def _fields(script: Script) -> Iterator[tuple[str, str]]:
    """Every spoken or published text with its label."""
    yield "title", script.title
    yield "description", script.description
    for number, tag in enumerate(script.tags, 1):
        yield f"tag {number}", tag
    yield "hook", script.hook
    for number, scene in enumerate(script.scenes, 1):
        yield f"scene {number} narration", scene.narration
        yield f"scene {number} on_screen_text", scene.on_screen_text
    yield "loop_line", script.loop_line


def _normalised(text: str) -> str:
    """NFKC folds full-width forms; it leaves the ideographic full stops alone, and IDNA treats
    them as dots, so they are mapped by hand. Marks (Mn, Me) are dropped after NFKC so an invisible
    one, such as a variation selector, cannot split a domain; composed accents survive NFKC first."""
    folded = unicodedata.normalize("NFKC", text).replace("。", ".").replace("｡", ".")
    return "".join(char for char in folded if unicodedata.category(char) not in _MARK_CATEGORIES)


def _text_problem(label: str, text: str) -> str | None:
    folded = _normalised(text)
    lowered = folded.lower()
    if "://" in lowered or "www." in lowered or _DOMAIN_LIKE.search(folded):
        return f"{label}: contains a URL"
    if "<" in folded or ">" in folded:
        return f"{label}: contains < or >"
    for char in text:
        category = unicodedata.category(char)
        newline_ok = char == "\n" and label == "description"
        if category in _BAD_CATEGORIES or (category == "Cc" and not newline_ok):
            return f"{label}: contains a control or invisible character (U+{ord(char):04X})"
    return None


def _length_problems(script: Script) -> Iterator[str]:
    low, high = TIKTOK_WORDS
    words = len(script.narration_words())
    if not low <= words <= high:
        yield f"narration: {words} words, must be {low} to {high}"
    chars = len(script.narration_text())
    if chars > NARRATION_MAX_CHARS:
        yield f"narration: {chars} characters, at most {NARRATION_MAX_CHARS}"
    if len(script.scenes) > SCENES_MAX:
        yield f"scenes: {len(script.scenes)} scenes, at most {SCENES_MAX}"
    if len(script.title) > TITLE_MAX_CHARS:
        yield f"title: {len(script.title)} characters, at most {TITLE_MAX_CHARS}"
    if len(script.description) > DESCRIPTION_MAX_CHARS:
        yield f"description: {len(script.description)} characters, at most {DESCRIPTION_MAX_CHARS}"
    if len(script.tags) > TAGS_MAX:
        yield f"tags: {len(script.tags)} tags, at most {TAGS_MAX}"
    for number, tag in enumerate(script.tags, 1):
        if not tag.strip():
            yield f"tag {number}: blank"
        elif len(tag) > TAG_MAX_CHARS:
            yield f"tag {number}: {len(tag)} characters, at most {TAG_MAX_CHARS}"
    total = sum(len(tag) for tag in script.tags)
    if total > TAGS_TOTAL_MAX_CHARS:
        yield f"tags: {total} characters in total, at most {TAGS_TOTAL_MAX_CHARS}"


def problems(script: Script) -> list[str]:
    """Every reason `script` may not be published, one short line each naming the field
    (for example "title: 104 characters, at most 100"). Empty means the script is fine.

    Rules:
    - Word count of `script.narration_words()` inside `TIKTOK_WORDS` (inclusive), and
      `len(script.narration_text())` at most `NARRATION_MAX_CHARS`.
    - At most `SCENES_MAX` scenes.
    - Title at most `TITLE_MAX_CHARS` characters, description at most `DESCRIPTION_MAX_CHARS`, at
      most `TAGS_MAX` tags, each non-blank and at most `TAG_MAX_CHARS`, `TAGS_TOTAL_MAX_CHARS` summed.
    - Spoken and published fields (title, description, every tag, hook, every scene's narration and
      on_screen_text, loop_line) contain no URL: no `://`, no `www.` and no bare domain (Unicode
      letters, digits, underscores or hyphens, a dot, then a TLD of 2 or more letters), any case.
      Text is NFKC-normalised first, with U+3002 and U+FF61 read as dots, so full-width look-alikes
      count, and combining marks (Mn, Me) are dropped so an invisible one cannot split a domain.
      Decimals ("3.5") and one-letter abbreviations ("U.S.") are not domains.
    - The same fields contain no `<` or `>`, full-width forms included (YouTube rejects them in
      titles and descriptions, and in the PR body they could hide text as HTML), no control
      character (Unicode category Cc, except a newline in the description), and no format,
      private-use or surrogate character (Cf, Co, Cs: bidi controls and zero-width characters).
      The control and invisible check runs on the raw text, so NFKC cannot hide one.
    """
    found = list(_length_problems(script))
    found += [m for label, text in _fields(script) if (m := _text_problem(label, text))]
    return found
