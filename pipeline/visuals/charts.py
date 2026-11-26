"""Chart layouts: count-up number and growing bars (task p3-charts). No IO.

Same rules as cards.py: events inside [start, end], ASS layer ASS_LAYER_CARD or above, every
`\\pos` inside DATA_PANEL, text through ass_kit.text_event.
"""


def plain_number(value: str) -> float | None:
    """The number in a plain-number value ("3,219", "95", "2.5", "1,000,000.5"), or None.
    Plain means ASCII digits with optional comma thousands groups and one optional decimal part."""
    raise NotImplementedError


def counter_frames(value: str) -> list[str]:
    """The texts a counter shows. For a plain number: COUNTER_STEPS texts counting up from 0,
    numerically non-decreasing, formatted like `value` (thousands commas and decimal places kept),
    the last exactly `value`. Otherwise `[value]` (it pops in)."""
    raise NotImplementedError


def bar_lengths(values: list[str], full_px: float) -> list[float]:
    """Bar lengths proportional to the plain-number `values`; the largest is `full_px`.
    All zero gives all 0.0 (no division by zero). Raises ValueError for a value that is not a
    plain number or a negative full_px."""
    raise NotImplementedError


def counter_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """One item: counter_frames(value) shown one after another COUNTER_STEP_S apart (the last
    holds to `end`), the label below it, shown exactly."""
    raise NotImplementedError


def bars_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """2 to VISUAL_ITEMS_MAX items: bars of bar_lengths growing one after another, each label
    and the exact value string at each bar's end."""
    raise NotImplementedError
