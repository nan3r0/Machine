"""Checks a script must pass before it is voiced or published (CSO P1-3, phase review N5).

Task p2-validate. Pure function, no IO. Numbers come from pipeline/constants.py.
"""

import re
import unicodedata
from collections.abc import Iterator
from typing import Any

from pipeline.constants import (
    CAMERA_MOVES,
    DESCRIPTION_MAX_CHARS,
    NARRATION_MAX_CHARS,
    POSES,
    SCENES_MAX,
    SET_IDS,
    TAG_MAX_CHARS,
    TAGS_MAX,
    TAGS_TOTAL_MAX_CHARS,
    TIKTOK_WORDS,
    TITLE_MAX_CHARS,
    VISUAL_DATA_SCENES_MAX,
    VISUAL_ITEMS_MAX,
    VISUAL_LABEL_MAX_CHARS,
    VISUAL_TEXT_MAX_CHARS,
    VISUAL_VALUE_MAX_CHARS,
)
from pipeline.schema import Script

# Every default-ignorable code point is Cf or Cn (rejected here), Mn (dropped by _normalised) or a
# Hangul filler (a letter, so it joins a domain rather than splitting it).
_BAD_CATEGORIES = {"Cf", "Cn", "Co", "Cs"}
_MARK_CATEGORIES = {"Mn", "Me"}
# The exact fact-check reads ASCII 0 to 9 only; NFKC would fold full-width digits but not Arabic-Indic ones.
_NUMBER_CATEGORIES = {"Nd", "Nl", "No"}
# A TLD needs 2+ letters, so "3.5", "U.S." and "a.m." pass; no letters follow the first dot in "wait...".
# Unicode letters count too, so an internationalised domain ("пример.рф") is caught.
_DOMAIN_LIKE = re.compile(r"[\w-]+\.[^\W\d_]{2,}")
_VISUAL_CHOICES = {"set": SET_IDS, "pose": POSES, "camera": CAMERA_MOVES}
_VISUAL_KEYS = {*_VISUAL_CHOICES, "items"}
_ITEM_TYPES = {"chart", "steps", "map"}
# ASCII digits only, thousands commas and one decimal part; "3,219" and "1997" pass, "lots" does not.
_PLAIN_NUMBER = re.compile(r"[0-9][0-9,]*(\.[0-9]+)?")


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
    """NFKD folds full-width forms; it leaves the ideographic full stops alone, and IDNA treats
    them as dots, so they are mapped by hand. Marks (Mn, Me) are then dropped so an invisible one,
    such as a variation selector, cannot split a domain. Decomposing first means an accent leaves
    its letter behind ("café" reads as "cafe") and "<" + U+0338 reads as "<", where NFC would
    compose it into U+226E."""
    folded = unicodedata.normalize("NFKD", text).replace("。", ".").replace("｡", ".")
    return "".join(char for char in folded if unicodedata.category(char) not in _MARK_CATEGORIES)


def _hides_ascii_digit(char: str) -> bool:
    """Some symbols (U+32C0 "1月", U+3358 "0点") are not number categories but fold to ASCII digits."""
    return any("0" <= part <= "9" for part in unicodedata.normalize("NFKD", char))


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
        if char > "\x7f" and (category in _NUMBER_CATEGORIES or _hides_ascii_digit(char)):
            return f"{label}: contains a non-ASCII number character (U+{ord(char):04X})"
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


def _item_problems(where: str, kind: str, items: Any) -> Iterator[str]:
    """Rules for one scene's `items`; `where` is "scene N"."""
    if kind not in _ITEM_TYPES:
        yield f"{where} items: not allowed on a {kind} scene"
        return
    if not isinstance(items, list) or not 1 <= len(items) <= VISUAL_ITEMS_MAX:
        yield f"{where} items: must be a list of 1 to {VISUAL_ITEMS_MAX} label and value pairs"
        return
    if kind == "map" and len(items) != 1:
        yield f"{where} items: a map scene has exactly one item"
    for number, item in enumerate(items, 1):
        label = f"{where} item {number}"
        if not (isinstance(item, dict) and set(item) == {"label", "value"}
                and all(isinstance(item[k], str) for k in item)):
            yield f"{label}: items must be label and value strings only"
            continue
        yield from _item_text_problems(label, item)
    values = [i["value"] for i in items if isinstance(i, dict) and isinstance(i.get("value"), str)]
    if kind == "steps" and len({bool(v) for v in values}) > 1:
        yield f"{where} items value: steps values must be all empty or all set"
    if kind == "chart" and len(items) >= 2:
        for number, value in enumerate(values, 1):
            if not _PLAIN_NUMBER.fullmatch(value):
                yield f"{where} item {number} value: a chart with 2 or more items needs plain numbers"


def _item_text_problems(label: str, item: dict[str, str]) -> Iterator[str]:
    if not item["label"].strip():
        yield f"{label} label: blank"
    for field, cap in (("label", VISUAL_LABEL_MAX_CHARS), ("value", VISUAL_VALUE_MAX_CHARS)):
        if len(item[field]) > cap:
            yield f"{label} {field}: {len(item[field])} characters, at most {cap}"
        if message := _text_problem(f"{label} {field}", item[field]):
            yield message


def _visual_problems(script: Script) -> Iterator[str]:
    data_scenes = 0
    text_chars = 0
    for number, scene in enumerate(script.scenes, 1):
        where = f"scene {number}"
        for key, value in scene.visual.data.items():
            if key not in _VISUAL_KEYS:
                yield f"{where} {key!r}: not an allowed visual key"
            elif key in _VISUAL_CHOICES and value not in _VISUAL_CHOICES[key]:
                yield f"{where} {key}: not an approved {key}"
        if "items" not in scene.visual.data:
            continue
        data_scenes += 1
        items = scene.visual.data["items"]
        yield from _item_problems(where, scene.visual.type, items)
        if isinstance(items, list):
            text_chars += sum(
                len(item[k]) for item in items if isinstance(item, dict) for k in ("label", "value")
                if isinstance(item.get(k), str)
            )
    if data_scenes > VISUAL_DATA_SCENES_MAX:
        yield f"visual: {data_scenes} data scenes, at most {VISUAL_DATA_SCENES_MAX}"
    if text_chars > VISUAL_TEXT_MAX_CHARS:
        yield f"visual items: {text_chars} characters in total, at most {VISUAL_TEXT_MAX_CHARS}"


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
      Text is NFKD-normalised first, with U+3002 and U+FF61 read as dots, so full-width look-alikes
      count, and combining marks (Mn, Me) are dropped so an invisible one cannot split a domain.
      Decimals ("3.5") and one-letter abbreviations ("U.S.") are not domains.
    - The same fields contain no `<` or `>`, full-width forms and ones followed by a combining mark
      included (YouTube rejects them in titles and descriptions, and in the PR body they could hide
      text as HTML), no control character (Unicode category Cc, except a newline in the
      description), and no format, unassigned, private-use or surrogate character (Cf, Cn, Co, Cs:
      bidi controls, zero-width characters and reserved default-ignorables). The control and
      invisible check runs on the raw text, so normalisation cannot hide one.
    - The same fields contain no number character other than ASCII 0 to 9 (Unicode category Nd,
      Nl or No, or any character that NFKD-folds to an ASCII digit: full-width and Arabic-Indic
      digits, superscripts, fractions, Roman numerals, "1月" symbols), so the exact fact-check
      cannot be passed a wrong number it does not read. Checked on the raw text.
    - Scene `visual.data` holds only set, pose, camera and items (all optional). Set, pose and
      camera must be approved values (`HOST_BACKDROP_SET` is not a scene set). Items are allowed on
      chart, steps and map only: 1 to `VISUAL_ITEMS_MAX` `{label, value}` strings, label non-blank
      and at most `VISUAL_LABEL_MAX_CHARS`, value at most `VISUAL_VALUE_MAX_CHARS`, both through the
      text checks above. A chart of 2 or more items needs plain-number values, steps values are all
      empty or all set, a map has one item. At most `VISUAL_DATA_SCENES_MAX` scenes carry items and
      their labels and values sum to at most `VISUAL_TEXT_MAX_CHARS`.
    """
    found = list(_length_problems(script))
    found += [m for label, text in _fields(script) if (m := _text_problem(label, text))]
    found += _visual_problems(script)
    return found
