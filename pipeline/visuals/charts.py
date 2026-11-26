"""Chart layouts: count-up number and growing bars (task p3-charts). No IO.

Same rules as cards.py: events inside [start, end], ASS layer ASS_LAYER_CARD or above, every
`\\pos` inside DATA_PANEL, text through ass_kit.text_event. Each text is shrunk to fit its column,
and the bar-end value gets its own column, so the largest bar never pushes text past the panel.
"""

import re

from pipeline import constants as c
from pipeline.visuals.ass_kit import text_event
from pipeline.visuals.cards import _drawing, _panel, _pop

_PLAIN = re.compile(r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
_LEFT, _TOP, _RIGHT, _BOTTOM = c.DATA_PANEL
_MID_X = (_LEFT + _RIGHT) / 2
_MARGIN = 40
_INNER_PX = _RIGHT - _LEFT - 2 * _MARGIN
# Per character, of the font size: "A" in Montserrat Bold is 0.756 em (Pillow), see cards.py.
_CHAR_WIDTH = 0.76
_LAYER = c.ASS_LAYER_CARD + 1
_POP = _pop()
_COUNTER_SIZE = 160
_COUNTER_Y = _TOP + 260
_COUNTER_LABEL_Y = _TOP + 470
_ROW_MAX = 190
_BAR_PX = 44
_VALUE_COL_PX = 240
_VALUE_GAP_PX = 16
_BAR_MAX_PX = _INNER_PX - _VALUE_COL_PX - _VALUE_GAP_PX
_GROW_S = 0.6


def plain_number(value: str) -> float | None:
    """The number in a plain-number value ("3,219", "95", "2.5", "1,000,000.5"), or None.
    Plain means ASCII digits with optional comma thousands groups and one optional decimal part."""
    if not _PLAIN.fullmatch(value):
        return None
    return float(value.replace(",", ""))


def counter_frames(value: str) -> list[str]:
    """The texts a counter shows. For a plain number: COUNTER_STEPS texts counting up from 0,
    numerically non-decreasing, formatted like `value` (thousands commas and decimal places kept),
    the last exactly `value`. Otherwise `[value]` (it pops in)."""
    number = plain_number(value)
    if number is None:
        return [value]
    decimals = len(value.partition(".")[2])
    spec = f"{',' if ',' in value else ''}.{decimals}f"
    last = c.COUNTER_STEPS - 1
    return [format(number * k / last, spec) for k in range(last)] + [value]


def bar_lengths(values: list[str], full_px: float) -> list[float]:
    """Bar lengths proportional to the plain-number `values`; the largest is `full_px`.
    All zero gives all 0.0 (no division by zero). Raises ValueError for a value that is not a
    plain number or a negative full_px."""
    if full_px < 0:
        raise ValueError(f"negative bar length {full_px}")
    numbers = []
    for value in values:
        number = plain_number(value)
        if number is None:
            raise ValueError(f"not a plain number: {value!r}")
        numbers.append(number)
    top = max(numbers, default=0.0)
    return [full_px * n / top if top else 0.0 for n in numbers]


def _fit(text: str, size: int, width: float) -> int:
    """`size`, shrunk so `text` fits one line of `width` px."""
    return max(1, min(size, int(width / (max(len(text), 1) * _CHAR_WIDTH))))


def counter_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """One item: counter_frames(value) shown one after another COUNTER_STEP_S apart (the last
    holds to `end`), the label below it, shown exactly."""
    if len(items) != 1:
        raise ValueError(f"a counter takes 1 item, got {len(items)}")
    label, value = items[0]
    frames = counter_frames(value)
    size = _fit(value, _COUNTER_SIZE, _INNER_PX)  # sized from the final text so digits do not jump
    step = min(c.COUNTER_STEP_S, (end - start) / len(frames))
    times = [start + k * step for k in range(len(frames))] + [end]
    pop = _POP if len(frames) == 1 else ""
    evs = [_panel(start, end)]
    for k, frame in enumerate(frames):
        evs.append(text_event(frame, times[k], times[k + 1], _LAYER, (_MID_X, _COUNTER_Y), size,
                              c.CARD_ACCENT_RGB, "\\an5" + pop))
    evs.append(text_event(label, start, end, _LAYER, (_MID_X, _COUNTER_LABEL_Y),
                          _fit(label, c.CARD_LABEL_FONT_SIZE, _INNER_PX), c.CARD_TEXT_RGB,
                          "\\an5" + _POP))
    return evs


def bars_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """2 to VISUAL_ITEMS_MAX items: bars of bar_lengths growing one after another, each label
    and the exact value string at each bar's end."""
    if not 2 <= len(items) <= c.VISUAL_ITEMS_MAX:
        raise ValueError(f"bars need 2 to {c.VISUAL_ITEMS_MAX} items, got {len(items)}")
    lengths = bar_lengths([value for _, value in items], _BAR_MAX_PX)
    row = min(_ROW_MAX, (_BOTTOM - _TOP) / len(items))
    first = _TOP + ((_BOTTOM - _TOP) - row * len(items)) / 2  # rows centred in the panel
    value_size = min(_fit(value, c.CARD_FONT_SIZE, _VALUE_COL_PX) for _, value in items)
    step = (end - start) / (len(items) + 1)
    grow = min(_GROW_S, step)
    x0 = _LEFT + _MARGIN
    evs = [_panel(start, end)]
    for k, ((label, value), length) in enumerate(zip(items, lengths, strict=True)):
        t, top = start + k * step, first + row * k
        bar_y = top + row * 0.5
        evs.append(text_event(label, t, end, _LAYER, (x0, top + row * 0.28),
                              _fit(label, c.CARD_LABEL_FONT_SIZE, _INNER_PX), c.CARD_TEXT_RGB,
                              "\\an4" + _POP))
        path = f"m 0 0 l {length:g} 0 {length:g} {_BAR_PX} 0 {_BAR_PX}"
        evs.append(_drawing(t, end, _LAYER, (x0, bar_y), c.CARD_ACCENT_RGB, path,
                            f"\\an7\\fscx1\\t(0,{round(grow * 1000)},\\fscx100)"))
        evs.append(text_event(value, t + grow, end, _LAYER,
                              (x0 + length + _VALUE_GAP_PX, bar_y + _BAR_PX / 2), value_size,
                              c.CARD_TEXT_RGB, "\\an4" + _POP))
    return evs
