"""Phase review N2 and QA lead rank 1: no non-ASCII number characters in spoken or published text
(task p2b-unicode-digits).

The exact layer reads ASCII 0 to 9 only, so "７２ seconds" or Arabic-Indic digits would carry a
wrong number past R9.1. NFKC folds the full-width forms but not Arabic-Indic and the other decimal
digit scripts, so validate rejects by category instead (lessons.md 2026-11-18): any character whose
Unicode category is Nd, Nl or No, other than ASCII 0 to 9. Every such code point is tested.
"""

import sys
import unicodedata

import pytest

from pipeline.script import validate
from tests.script.scripts import FILLER, make_script, scene

NUMBER_CHARS = [chr(c) for c in range(sys.maxunicode + 1)
                if unicodedata.category(chr(c)) in {"Nd", "Nl", "No"} and not "0" <= chr(c) <= "9"]


def field_problems(found: list[str], label: str) -> list[str]:
    return [p for p in found if p.startswith(label + ":")]


def test_the_category_list_is_the_one_meant() -> None:
    for char in "０７٧۷७௭๗٣²½Ⅻ⑦":
        assert char in NUMBER_CHARS, f"U+{ord(char):04X}"
    assert len(NUMBER_CHARS) > 1000


def test_every_non_ascii_number_character_is_rejected() -> None:
    missed = []
    for char in NUMBER_CHARS:
        found = validate.problems(make_script(hook=f"Listen {char} closely."))
        if not field_problems(found, "hook"):
            missed.append(f"U+{ord(char):04X}")
    assert not missed, f"{len(missed)} passed, first: {missed[:10]}"


@pytest.mark.parametrize("char", ["７", "٧", "²", "Ⅻ"])
def test_problem_names_the_field_and_the_code_point(char: str) -> None:
    found = validate.problems(make_script(loop_line=f"Still {char} listening."))
    assert any(f"U+{ord(char):04X}" in p for p in field_problems(found, "loop_line")), found


def every_field(char: str) -> dict[str, list[str]]:
    script = make_script(
        title=f"Solved {char}", description=f"Case {char}", tags=["ocean", f"x{char}"],
        hook=f"Listen {char}.", loop_line=f"Gone {char}.",
        scenes=[scene(f"{FILLER} {char}", [101]) |{"on_screen_text": f"t{char}"}] +
               [scene(FILLER, [102 + i]) for i in range(6)])
    found = validate.problems(script)
    labels = ["title", "description", "tag 2", "hook", "scene 1 narration",
              "scene 1 on_screen_text", "loop_line"]
    return {label: field_problems(found, label) for label in labels}


def test_every_spoken_and_published_field_is_checked() -> None:
    for label, found in every_field("٧").items():
        assert found, label


def test_ascii_digits_still_pass() -> None:
    script = make_script(hook="In 1987 it began.", loop_line="Still 3.5 km down.",
                         title="Case 12, solved", tags=["ocean", "2024"])
    assert validate.problems(script) == []


def test_acceptance() -> None:
    assert field_problems(validate.problems(make_script(hook="It ran ７２ seconds.")), "hook")
    assert field_problems(validate.problems(make_script(hook="It ran ٧٢ seconds.")), "hook")
    assert validate.problems(make_script(hook="It ran 72 seconds.")) == []
