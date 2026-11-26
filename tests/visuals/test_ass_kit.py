"""ASS drawing kit (task p3-ass-kit)."""

import pytest

from pipeline import constants as c
from pipeline.visuals import ass_kit
from pipeline.visuals.art import Shape
from tests.visuals.ass_parse import drawing, events, pos, shown_text

SHAPE = Shape(layer=3, fill="coat", outline=5, path="m 0 0 l 10 0 l 10 10", alpha="A0")
PALETTE = {"coat": "E3A332", "outline": "1F1A24"}


def style(header: str, name: str) -> list[str]:
    fmt = next(line for line in header.splitlines() if line.startswith("Format:") and "Fontname" in line)
    line = next(line for line in header.splitlines() if line.startswith(f"Style: {name},"))
    keys = [k.strip() for k in fmt[len("Format:") :].split(",")]
    return dict(zip(keys, line[len("Style:") :].split(","), strict=True))  # type: ignore[return-value]


def test_header_frame_and_styles() -> None:
    header = ass_kit.header()
    assert f"PlayResX: {c.WIDTH}" in header and f"PlayResY: {c.HEIGHT}" in header
    assert "WrapStyle: 2" not in header
    assert header.rstrip().splitlines()[-1].startswith("Format: Layer, Start, End, Style")
    shape = style(header, ass_kit.SHAPE_STYLE)
    assert shape["Alignment"] == "7"  # type: ignore[index]
    card = style(header, ass_kit.CARD_STYLE)
    assert card["Fontname"] == c.CAPTION_FONT_NAME and card["Alignment"] == "5"  # type: ignore[index]
    assert int(card["MarginL"]) == c.DATA_PANEL[0]  # type: ignore[index]
    assert int(card["MarginR"]) == c.WIDTH - c.DATA_PANEL[2]  # type: ignore[index]


@pytest.mark.parametrize(
    ("seconds", "text"), [(0, "0:00:00.00"), (3723.456, "1:02:03.46"), (59.996, "0:01:00.00")]
)
def test_ass_time(seconds: float, text: str) -> None:
    assert ass_kit.ass_time(seconds) == text


def test_bad_inputs_raise() -> None:
    with pytest.raises(ValueError):
        ass_kit.ass_time(-1)
    with pytest.raises(ValueError):
        ass_kit.ass_colour("E3A33")
    with pytest.raises(ValueError):
        ass_kit.dialogue(2.0, 1.0, 0, "x")


def test_colour_is_bgr() -> None:
    assert ass_kit.ass_colour("E3A332") == "&H32A3E3&"


def test_dialogue_line() -> None:
    line = ass_kit.dialogue(1.0, 2.5, 7, "{\\p1}m 0 0 l 1 1")
    assert line == f"Dialogue: 7,0:00:01.00,0:00:02.50,{ass_kit.SHAPE_STYLE},,0,0,0,,{{\\p1}}m 0 0 l 1 1"


def test_shape_event() -> None:
    line = ass_kit.shape_event(SHAPE, PALETTE, "1F1A24", 0.0, 1.0, 43, (100, 200), 0.85)
    ev = events([line])[0]
    assert (ev.layer, ev.start, ev.end, ev.style) == (43, 0.0, 1.0, ass_kit.SHAPE_STYLE)
    assert drawing(ev.text) == SHAPE.path and pos(ev.text) == (100, 200)
    for tag in ("\\fscx85", "\\fscy85", "\\1c&H32A3E3&", "\\3c&H241A1F&", "\\bord5", "\\1a&HA0&"):
        assert tag in ev.text
    moved = ass_kit.shape_event(SHAPE, PALETTE, "1F1A24", 0, 1, 0, (0, 0), tags="\\move(1,2,3,4)")
    assert "\\pos(" not in moved and "\\move(1,2,3,4)" in moved


@pytest.mark.parametrize("text", ["3,219 km", "{evil}", "back\\slash \\N", "Café 東京"])
def test_text_event_shows_text_exactly(text: str) -> None:
    ev = events([ass_kit.text_event(text, 0, 1, 20, (500, 600), 72, "FFFFFF")])[0]
    assert ev.style == ass_kit.CARD_STYLE and pos(ev.text) == (500, 600)
    assert shown_text(ev.text) == text


def test_acceptance() -> None:
    test_header_frame_and_styles()
    test_colour_is_bgr()
    test_dialogue_line()
    test_shape_event()
