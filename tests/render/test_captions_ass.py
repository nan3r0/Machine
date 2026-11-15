"""R4: word-by-word .ass captions (task p1-captions-ass)."""

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline import constants
from pipeline.render import captions_ass
from pipeline.render.captions_ass import build_ass, escape_ass_text
from pipeline.schema import WordTiming

CS = 0.011  # one centisecond of ASS time rounding, plus float noise
OVERRIDE = re.compile(r"(?<!\\)\{.*?(?<!\\)\}")
POS = re.compile(r"\\pos\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")


def ass_time(text: str) -> float:
    hours, minutes, seconds = text.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def dialogues(ass: str) -> list[tuple[float, float, str]]:
    events = []
    for line in ass.splitlines():
        if line.startswith("Dialogue:"):
            fields = line[len("Dialogue:"):].split(",", 9)
            events.append((ass_time(fields[1]), ass_time(fields[2]), fields[9]))
    return events


def timings_for(words: list[str], step: float = 0.4, gap: float = 0.05) -> list[WordTiming]:
    return [WordTiming(word=w, start=round(i * step, 2), end=round(i * step + step - gap, 2))
            for i, w in enumerate(words)]


def assert_captions_match(ass: str, timings: list[WordTiming], words_per_line: int) -> None:
    """R4.1 and R4.2 for any timings."""
    events = dialogues(ass)
    assert len(events) == len(timings)
    for i, ((start, end, text), timing) in enumerate(zip(events, timings, strict=True)):
        later = timings[i + 1].start if i + 1 < len(timings) else timing.end
        assert start == pytest.approx(timing.start, abs=CS)
        assert timing.end - CS <= end <= max(timing.end, later) + CS
        plain = OVERRIDE.sub("", text)
        assert escape_ass_text(timing.word) in plain
        assert len(plain.split()) <= words_per_line
        match = POS.search(text)
        assert match, f"no \\pos in {text!r}"
        x, y = float(match.group(1)), float(match.group(2))
        assert constants.SAFE_LEFT_PX <= x <= constants.SAFE_RIGHT_PX
        assert constants.SAFE_TOP_PX <= y <= constants.SAFE_BOTTOM_PX


def test_acceptance() -> None:
    """R4.1 to R4.3 on narration with digits, punctuation, unicode and ASS control characters."""
    words = "In 1938, a {ballpoint} pen cost $10 \\N about café 25% «why?»".split()
    timings = timings_for(words)
    ass = build_ass(timings)
    assert f"PlayResX: {constants.WIDTH}" in ass
    assert f"PlayResY: {constants.HEIGHT}" in ass
    styles = [line for line in ass.splitlines() if line.startswith("Style:")]
    assert styles and all(constants.CAPTION_FONT_NAME in s for s in styles)
    assert any(f",{constants.CAPTION_FONT_SIZE}," in s for s in styles)
    assert_captions_match(ass, timings, constants.CAPTION_MAX_WORDS_PER_LINE)


@pytest.mark.parametrize("word", ["{\\b1}bold", "a}b{c", "\\N", "\\n", "\\h", "back\\slash", "{", "}", "\\"])
def test_escape_blocks_overrides_and_control_codes(word: str) -> None:
    escaped = escape_ass_text(word)
    assert OVERRIDE.search(escaped) is None
    assert re.search(r"(?<!\\)[{}]", escaped) is None, "every brace must be escaped as \\{ or \\}"
    assert re.search(r"\\[nNh]", escaped) is None


@pytest.mark.parametrize("word", ["plain", "café", "日本語", "1938,", "$10", "«why?»", "emoji🙂"])
def test_escape_leaves_ordinary_text_alone(word: str) -> None:
    assert escape_ass_text(word) == word


def test_escape_keeps_distinct_words_distinct() -> None:
    assert escape_ass_text("a{b") != escape_ass_text("a}b")
    assert escape_ass_text("\\N") != escape_ass_text("N")


def test_empty_timings_rejected() -> None:
    with pytest.raises(ValueError):
        build_ass([])


def test_words_per_line_must_be_positive() -> None:
    with pytest.raises(ValueError):
        build_ass(timings_for(["a"]), words_per_line=0)


@pytest.mark.parametrize("per_line", [1, 2, 5])
def test_words_per_line_is_respected(per_line: int) -> None:
    timings = timings_for([f"w{i}" for i in range(11)])
    assert_captions_match(build_ass(timings, words_per_line=per_line), timings, per_line)


def test_single_word_and_long_script() -> None:
    one = timings_for(["Hi."])
    assert_captions_match(build_ass(one), one, constants.CAPTION_MAX_WORDS_PER_LINE)
    many = timings_for([f"word{i}" for i in range(300)], step=0.3)
    assert_captions_match(build_ass(many), many, constants.CAPTION_MAX_WORDS_PER_LINE)


def test_overlapping_timings_are_allowed() -> None:
    timings = [WordTiming(word="ten", start=0.2, end=0.9), WordTiming(word="dollars", start=0.2, end=0.9)]
    assert_captions_match(build_ass(timings), timings, constants.CAPTION_MAX_WORDS_PER_LINE)


def test_module_is_pure() -> None:
    source = open(captions_ass.__file__, encoding="utf-8").read()
    for forbidden in ("open(", "subprocess", "write_text"):
        assert forbidden not in source


word = st.text(st.characters(categories=["L", "N", "P", "S"]), min_size=1, max_size=12)


@settings(deadline=None, max_examples=150)
@given(words=st.lists(word, min_size=1, max_size=40), data=st.data(),
       per_line=st.integers(min_value=1, max_value=6))
def test_every_word_shown_once_in_order_inside_the_audio(words: list[str], data: st.DataObject,
                                                         per_line: int) -> None:
    """Property: for any words and monotonic timings, each word gets one event, in order, on time."""
    bounds = sorted(data.draw(st.lists(st.floats(min_value=0, max_value=600, allow_nan=False),
                                       min_size=2 * len(words), max_size=2 * len(words))))
    timings = [WordTiming(word=w, start=bounds[2 * i], end=bounds[2 * i + 1]) for i, w in enumerate(words)]
    ass = build_ass(timings, words_per_line=per_line)
    assert_captions_match(ass, timings, per_line)
    assert max(end for _, end, _ in dialogues(ass)) <= timings[-1].end + CS
