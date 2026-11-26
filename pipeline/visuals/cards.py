"""Data card layouts: numbered steps, timeline, place card (task p3-cards). No IO.

Items are (label, value) pairs from a validated scene. Every event lies inside [start, end], uses
ASS layer ASS_LAYER_CARD or above, and every `\\pos` lies inside DATA_PANEL. Text events are
ass_kit.text_event (CARD_STYLE). Each text is shrunk to fit one line of a 720 px column, so a label
of up to 24 characters never wraps, overlaps the badge or runs past the panel edge.
"""

from pipeline import constants as c
from pipeline.visuals.ass_kit import ass_colour, dialogue, text_event

_LEFT, _TOP, _RIGHT, _BOTTOM = c.DATA_PANEL
_MID_X = (_LEFT + _RIGHT) / 2
_BADGE_X = _LEFT + 60
_TEXT_X = _LEFT + 100  # label column starts right of the badge
_COLUMN_PX = _RIGHT - _TEXT_X
# Per character, of the font size: "A" in Montserrat Bold is 0.756 em (Pillow), above the 0.735 em
# capital average. libass draws about 18% smaller (it sizes to ascent + descent), so this is a margin.
_CHAR_WIDTH = 0.76
_ROW_MAX = 190
_RING_COUNT = 3
_POP_MS = 200
_LAYER = c.ASS_LAYER_CARD + 1


def _circle(r: int) -> str:
    """A circle of radius r centred on the drawing origin, as an ASS drawing."""
    k = round(r * 0.5523)
    return (f"m {-r} 0 b {-r} {-k} {-k} {-r} 0 {-r} b {k} {-r} {r} {-k} {r} 0 "
            f"b {r} {k} {k} {r} 0 {r} b {-k} {r} {-r} {k} {-r} 0")


def _drawing(start: float, end: float, layer: int, pos: tuple[float, float], rgb: str, path: str,
             extra: str = "") -> str:
    tags = f"{{\\pos({pos[0]:g},{pos[1]:g})\\1c{ass_colour(rgb)}\\bord0{extra}\\p1}}"
    return dialogue(start, end, layer, f"{tags}{path}{{\\p0}}")


def _panel(start: float, end: float) -> str:
    path = f"m 0 0 l {_RIGHT - _LEFT} 0 {_RIGHT - _LEFT} {_BOTTOM - _TOP} 0 {_BOTTOM - _TOP}"
    return _drawing(start, end, c.ASS_LAYER_CARD, (_LEFT, _TOP), c.CARD_PANEL_RGB, path)


def _fit(text: str, size: int) -> int:
    """`size`, shrunk so `text` fits one line of the _COLUMN_PX column."""
    return min(size, int(_COLUMN_PX / (len(text) * _CHAR_WIDTH)))


def _pop() -> str:
    return f"\\alpha&HFF&\\t(0,{_POP_MS},\\alpha&H00&)"


def _rows(items: list[tuple[str, str]], start: float, end: float, dots: bool) -> list[str]:
    """The panel plus one staggered row per item: a number or a dot, then label and value."""
    evs = [_panel(start, end)]
    row = min(_ROW_MAX, (_BOTTOM - _TOP) / len(items))
    step = (end - start) / (len(items) + 1)
    accent = c.CARD_ACCENT_RGB
    for k, (label, value) in enumerate(items):
        t, y = start + k * step, _TOP + row * (k + 0.5)
        label_part = (label, c.CARD_LABEL_FONT_SIZE, c.CARD_TEXT_RGB)
        if dots:
            evs.append(_drawing(t, end, _LAYER, (_BADGE_X, y), accent, _circle(18), "\\an5" + _pop()))
            parts, offsets = [(value, c.CARD_FONT_SIZE, accent), label_part], (-0.28, 0.22)
        else:
            evs.append(text_event(str(k + 1), t, end, _LAYER, (_BADGE_X, y), c.CARD_FONT_SIZE,
                                  accent, _pop()))
            parts, offsets = [label_part, (value, c.CARD_LABEL_FONT_SIZE, accent)], (-0.22, 0.25)
        shown = [(part, off) for part, off in zip(parts, offsets, strict=True) if part[0]]
        for (text, size, rgb), off in shown:
            dy = row * off if len(shown) > 1 else 0
            evs.append(text_event(text, t, end, _LAYER, (_TEXT_X, y + dy), _fit(text, size), rgb,
                                  "\\an4" + _pop()))
    if dots:
        length = int(row * (len(items) - 1))
        line = f"m 0 0 l 6 0 6 {length} 0 {length}"
        evs.insert(1, _drawing(start, end, c.ASS_LAYER_CARD, (_BADGE_X - 3, _TOP + row * 0.5),
                               c.CARD_TEXT_RGB, line))
    return evs


def steps_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """Numbered cards ("1", "2", ...) with each label (and value, if not empty) shown exactly,
    appearing one at a time: item k+1 appears later than item k."""
    return _rows(items, start, end, dots=False)


def timeline_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """Dots on a line; each value (a year) and label shown exactly, popping in staggered in
    item order."""
    return _rows(items, start, end, dots=True)


def place_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """A pin with sonar rings, the single item's label (the place) and its value if not empty."""
    label, value = items[0]
    pin = (_MID_X, _TOP + 200)
    evs = [_panel(start, end), _drawing(start, end, _LAYER, pin, c.CARD_ACCENT_RGB, _circle(24),
                                            "\\an5" + _pop())]
    ring_ms = round((end - start) * 1000 / _RING_COUNT)
    for k in range(_RING_COUNT):
        t = start + k * (end - start) / _RING_COUNT
        grow = (f"\\an5\\1a&HFF&\\3c{ass_colour(c.CARD_ACCENT_RGB)}\\bord4"
                f"\\t(0,{ring_ms},\\fscx400\\fscy400\\3a&HFF&)")
        evs.append(_drawing(t, end, _LAYER, pin, c.CARD_ACCENT_RGB, _circle(24), grow))
    evs.append(text_event(label, start, end, _LAYER, (_MID_X, _TOP + 420),
                          _fit(label, c.CARD_FONT_SIZE), c.CARD_TEXT_RGB, _pop()))
    if value:
        evs.append(text_event(value, start, end, _LAYER, (_MID_X, _TOP + 580),
                              _fit(value, c.CARD_LABEL_FONT_SIZE), c.CARD_ACCENT_RGB, _pop()))
    return evs
