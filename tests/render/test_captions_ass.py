"""R4: word-by-word .ass captions (task p1-captions-ass)."""

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline import constants
from pipeline.render import captions_ass
from pipeline.render.captions_ass import build_ass, escape_ass_text
from pipeline.schema import WordTiming
from tests import media

CS = 0.011  # one centisecond of ASS time rounding, plus float noise
OVERRIDE = media.ASS_OVERRIDE
SAFE_CENTRE_X = (constants.SAFE_LEFT_PX + constants.SAFE_RIGHT_PX) / 2
LINE_ROOM = 2 * constants.CAPTION_FONT_SIZE


def ass_time(text: str) -> float:
    hours, minutes, seconds = text.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def dialogue_fields(ass: str) -> list[list[str]]:
    prefix = "Dialogue:"
    return [line[len(prefix):].split(",", 9) for line in ass.splitlines() if line.startswith(prefix)]


def dialogues(ass: str) -> list[tuple[float, float, str]]:
    return [(ass_time(f[1]), ass_time(f[2]), f[9]) for f in dialogue_fields(ass)]


def styles(ass: str) -> dict[str, dict[str, str]]:
    """Each `Style:` line of [V4+ Styles] as {field name: value}, keyed by style name."""
    lines = ass.splitlines()
    start = lines.index("[V4+ Styles]")
    names: list[str] = []
    found = {}
    for line in lines[start + 1:]:
        if line.startswith("["):
            break
        key, _, value = line.partition(":")
        if key == "Format":
            names = [n.strip() for n in value.split(",")]
        elif key == "Style":
            style = dict(zip(names, (v.strip() for v in value.split(",")), strict=True))
            found[style["Name"]] = style
    return found


def assert_wraps_inside_safe_zone(ass: str) -> None:
    """Every event wraps to the safe width, centred on it, so no line can run past its edges."""
    assert not re.search(r"(?m)^WrapStyle:\s*2\s*$", ass)
    used = styles(ass)
    for fields in dialogue_fields(ass):
        style = used[fields[3].strip()]
        assert style["Alignment"] == "5"
        assert int(style["MarginL"]) == constants.SAFE_LEFT_PX
        assert int(style["MarginR"]) == constants.WIDTH - constants.SAFE_RIGHT_PX
        assert int(fields[5]) == 0 and int(fields[6]) == 0, "event margins would replace the style's"
        blocks = "".join(OVERRIDE.findall(fields[9]))
        assert "\\q2" not in blocks and "\\an" not in blocks


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
        # Independent oracle: undo the escaping by hand, never with escape_ass_text itself.
        assert timing.word in plain.replace("\\{", "{").replace("\\}", "}").replace("\\​", "\\")
        assert len(plain.split()) <= words_per_line
        # Only override blocks count: an escaped word may show "\pos(...)" as plain text.
        positions = media.ASS_POS.findall("".join(OVERRIDE.findall(text)))
        assert len(positions) == 1, f"need exactly one \\pos in {text!r}"
        x, y = map(float, positions[0])
        assert x == pytest.approx(SAFE_CENTRE_X)
        assert constants.SAFE_TOP_PX + LINE_ROOM <= y <= constants.SAFE_BOTTOM_PX - LINE_ROOM
    assert_wraps_inside_safe_zone(ass)


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
