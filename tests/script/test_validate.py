"""R12.1: what a script may contain before it is voiced or published (task p2-validate, CSO P1-3)."""

from typing import Any

import pytest

from pipeline import constants
from pipeline.script import validate
from tests.script.scripts import FILLER, make_script, scene, script_dict, script_with_words

LOW, HIGH = constants.TIKTOK_WORDS


def one_problem_naming(field: str, **overrides: Any) -> None:
    found = validate.problems(make_script(**overrides))
    assert found, f"no problem reported for {field}"
    assert any(field in message for message in found), found


def with_text(field: str, text: str) -> dict[str, Any]:
    """Overrides that put `text` into one spoken or published field of the base script."""
    base = script_dict()
    if field == "tags":
        return {"tags": [*base["tags"], text]}
    if field in ("narration", "on_screen_text"):
        scenes = [dict(s) for s in base["scenes"]]
        scenes[3] = {**scenes[3], field: f"{scenes[3][field]} {text}"}
        return {"scenes": scenes}
    return {field: f"{base[field]} {text}"}


FIELDS = ["title", "description", "tags", "hook", "narration", "on_screen_text", "loop_line"]


def test_good_script_has_no_problems() -> None:
    assert validate.problems(make_script()) == []


@pytest.mark.parametrize("count", [LOW, HIGH, constants.TARGET_WORDS])
def test_word_count_inside_bounds_passes(count: int) -> None:
    assert validate.problems(script_with_words(count)) == []


@pytest.mark.parametrize("count", [LOW - 1, HIGH + 1, 40, 400])
def test_word_count_outside_bounds_fails(count: int) -> None:
    found = validate.problems(script_with_words(count))
    assert any("word" in message for message in found), found
    assert any(str(count) in message for message in found), found


def test_narration_characters_capped() -> None:
    long_words = make_script(hook="Listen.", loop_line="Gone.", scenes=[
        scene(" ".join(["remarkable"] * 25), [101]) for _ in range(7)])
    assert len(long_words.narration_words()) <= HIGH
    assert len(long_words.narration_text()) > constants.NARRATION_MAX_CHARS
    assert any("narration" in message for message in validate.problems(long_words))


def test_scene_count_capped() -> None:
    words = " ".join(FILLER.split()[:14])
    too_many = constants.SCENES_MAX + 1
    script = make_script(scenes=[scene(words, [101]) for _ in range(too_many)])
    assert LOW <= len(script.narration_words()) <= HIGH
    assert any("scene" in message for message in validate.problems(script))
    at_cap = make_script(scenes=[scene(words + " now", [101]) for _ in range(constants.SCENES_MAX)])
    assert validate.problems(at_cap) == []


def test_title_cap() -> None:
    assert validate.problems(make_script(title="t" * constants.TITLE_MAX_CHARS)) == []
    one_problem_naming("title", title="t" * (constants.TITLE_MAX_CHARS + 1))


def test_description_cap() -> None:
    assert validate.problems(make_script(description="d" * constants.DESCRIPTION_MAX_CHARS)) == []
    one_problem_naming("description", description="d" * (constants.DESCRIPTION_MAX_CHARS + 1))


def test_tag_caps() -> None:
    at_cap = [f"{i}" + "t" * (constants.TAG_MAX_CHARS - 1) for i in range(constants.TAGS_MAX)]
    assert validate.problems(make_script(tags=at_cap)) == []
    one_problem_naming("tag", tags=[*at_cap, "one more"])
    one_problem_naming("tag", tags=["t" * (constants.TAG_MAX_CHARS + 1)])
    one_problem_naming("tag", tags=["ocean", "  "])


def test_no_tags_is_allowed() -> None:
    assert validate.problems(make_script(tags=[])) == []


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ["https://evil.example/x", "HTTP://EVIL.EXAMPLE", "www.evil.example",
                                  "WWW.Evil.Example", "see ftp://files.example"])
def test_urls_rejected_in_every_field(field: str, text: str) -> None:
    one_problem_naming(field if field != "tags" else "tag", **with_text(field, text))


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("text", ["<!-- hidden", "a > b", "<b>bold</b>"])
def test_angle_brackets_rejected_in_every_field(field: str, text: str) -> None:
    one_problem_naming(field if field != "tags" else "tag", **with_text(field, text))


BAD_CHARS = {
    "bell (Cc)": "\x07", "tab (Cc)": "\t", "delete (Cc)": "\x7f", "C1 control (Cc)": "\x85",
    "zero-width space (Cf)": "​", "zero-width joiner (Cf)": "‍", "byte order mark (Cf)": "﻿",
    "right-to-left override (Cf)": "‮", "left-to-right isolate (Cf)": "⁦",
    "private use (Co)": "", "lone surrogate (Cs)": "\ud800",
}


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("char", BAD_CHARS.values(), ids=BAD_CHARS.keys())
def test_control_bidi_and_invisible_characters_rejected(field: str, char: str) -> None:
    one_problem_naming(field if field != "tags" else "tag", **with_text(field, f"odd{char}text"))


@pytest.mark.parametrize("field", [f for f in FIELDS if f != "description"])
def test_newline_rejected_outside_description(field: str) -> None:
    one_problem_naming(field if field != "tags" else "tag", **with_text(field, "line\nbreak"))


def test_newline_allowed_in_description() -> None:
    assert validate.problems(make_script(description="Source: NOAA.\n\n#ocean #mystery")) == []


def test_ordinary_unicode_is_allowed() -> None:
    """Accents, curly quotes, dashes and a plain emoji are not control or format characters."""
    script = make_script(title="Café Ñandú: the “Bloop” – solved",
                         description="Source: NOAA – Ocean Facts. Ça va 🌊", tags=["océan", "mystère"])
    assert validate.problems(script) == []


def test_messages_fit_one_line_and_name_each_problem() -> None:
    script = make_script(title="t" * 101, description="d" * 1001, hook="Listen www.x.io",
                         tags=["x" * 31])
    found = validate.problems(script)
    for field in ("title", "description", "hook", "tag"):
        assert any(field in message for message in found), (field, found)
    for message in found:
        assert "\n" not in message and 0 < len(message) <= 200


def test_acceptance() -> None:
    """A good script passes; each rule of R12.1 and the word bounds rejects with a message naming
    the field."""
    assert validate.problems(make_script()) == []
    assert validate.problems(script_with_words(LOW)) == []
    assert any("word" in m for m in validate.problems(script_with_words(LOW - 1)))
    assert any("word" in m for m in validate.problems(script_with_words(HIGH + 1)))
    one_problem_naming("title", title="t" * 101)
    one_problem_naming("description", description="d" * 1001)
    one_problem_naming("tag", tags=["t"] * 11)
    one_problem_naming("narration", **with_text("narration", "www.evil.example"))
    one_problem_naming("description", description="see https://evil.example")
    one_problem_naming("loop_line", loop_line="Gone ‮.")
    one_problem_naming("hook", hook="Listen <!-- x -->")
    one_problem_naming("title", title="Line\nbreak")
