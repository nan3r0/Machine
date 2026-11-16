"""Exact caption text: escaping and the current-word highlight (task p1-qa-tests, QA lead items 1, 2)."""

import pytest

from pipeline import constants
from pipeline.render.captions_ass import build_ass, escape_ass_text
from pipeline.schema import WordTiming

ZWSP = "​"
HIGHLIGHT_ON = "{\\1c&H0000FFFF&}"
HIGHLIGHT_OFF = "{\\r}"
POS = f"{{\\pos({(constants.SAFE_LEFT_PX + constants.SAFE_RIGHT_PX) / 2:g},{constants.HEIGHT / 2:g})}}"


@pytest.mark.parametrize(("word", "expected"), [
    ("{x}", "\\{x\\}"),
    ("a}b{c", "a\\}b\\{c"),
    ("\\N", "\\" + ZWSP + "N"),
    ("\\", "\\" + ZWSP),
    ("{\\b1}bold", "\\{\\" + ZWSP + "b1\\}bold"),
    ("café", "café"),
])
def test_escape_gives_exact_text(word: str, expected: str) -> None:
    assert escape_ass_text(word) == expected


def dialogue_texts(ass: str) -> list[str]:
    return [line.split(",", 9)[9] for line in ass.splitlines() if line.startswith("Dialogue:")]


def test_only_the_current_word_is_highlighted() -> None:
    """R4: each event shows its line with exactly the current word in yellow, the rest plain."""
    words = ["one", "{two}", "three", "four", "\\N"]
    timings = [WordTiming(word=w, start=i * 0.5, end=i * 0.5 + 0.4) for i, w in enumerate(words)]
    texts = dialogue_texts(build_ass(timings, words_per_line=3))

    def on(word: str) -> str:
        return HIGHLIGHT_ON + word + HIGHLIGHT_OFF

    assert texts == [
        POS + " ".join([on("one"), "\\{two\\}", "three"]),
        POS + " ".join(["one", on("\\{two\\}"), "three"]),
        POS + " ".join(["one", "\\{two\\}", on("three")]),
        POS + " ".join([on("four"), "\\" + ZWSP + "N"]),
        POS + " ".join(["four", on("\\" + ZWSP + "N")]),
    ]
