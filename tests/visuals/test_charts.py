"""Charts (task p3-charts): count-up and bars."""

import re

import pytest

from pipeline import constants as c
from pipeline.visuals import charts
from tests.visuals.ass_parse import drawing, events, pos, shown_text


@pytest.mark.parametrize(
    ("value", "number"), [("3,219", 3219), ("95", 95), ("2.5", 2.5), ("1,000,000.5", 1000000.5), ("0", 0)]
)
def test_plain_numbers(value: str, number: float) -> None:
    assert charts.plain_number(value) == number


@pytest.mark.parametrize(
    "value", ["", "1997s", "3,21", "1,0000", "-5", "٣", "1e5", "about 9", "3.2.1", ",100"]
)
def test_not_plain_numbers(value: str) -> None:
    assert charts.plain_number(value) is None


@pytest.mark.parametrize(
    ("value", "shape"), [("3,219", r"\d{1,3}(,\d{3})*"), ("2.5", r"\d+\.\d"), ("95", r"\d+")]
)
def test_counter_counts_up_in_the_value_format(value: str, shape: str) -> None:
    frames = charts.counter_frames(value)
    assert len(frames) == c.COUNTER_STEPS and frames[-1] == value
    assert all(re.fullmatch(shape, f) for f in frames)
    numbers = [float(f.replace(",", "")) for f in frames]
    assert numbers[0] == 0 and numbers == sorted(numbers)


def test_counter_pops_in_a_non_number() -> None:
    assert charts.counter_frames("eight years") == ["eight years"]


def test_bar_lengths() -> None:
    assert charts.bar_lengths(["10", "5", "2,5"[:1]], 600) == pytest.approx([600, 300, 120])
    assert charts.bar_lengths(["0", "0"], 600) == [0.0, 0.0]
    assert charts.bar_lengths(["7", "7"], 600) == [600, 600]
    assert charts.bar_lengths(["1,000", "250"], 400) == pytest.approx([400, 100])
    with pytest.raises(ValueError):
        charts.bar_lengths(["ten", "5"], 600)


@pytest.mark.parametrize(
    ("layout", "items"),
    [
        (charts.counter_events, [("Kilometres apart", "3,219")]),
        (charts.counter_events, [("Time to solve", "8 years")]),
        (charts.bars_events, [("Bloop", "3,219"), ("Whale", "0"), ("Ship", "120"), ("Quake {x}", "3,219")]),
    ],
)
def test_values_exact_inside_panel_and_window(layout: object, items: list[tuple[str, str]]) -> None:
    evs = events(layout(items, 5.0, 12.0))  # type: ignore[operator]
    assert evs and all(5.0 <= e.start <= e.end <= 12.0 and e.layer >= c.ASS_LAYER_CARD for e in evs)
    left, top, right, bottom = c.DATA_PANEL
    assert all(left <= p[0] <= right and top <= p[1] <= bottom for e in evs if (p := pos(e.text)))
    texts = [shown_text(e.text) for e in evs]
    for label, value in items:
        assert any(label in t for t in texts) and any(value in t for t in texts)
    last = max(e.end for e in evs)
    assert last == 12.0, "the final value holds to the end"


@pytest.mark.parametrize(
    ("layout", "items"),
    [
        (charts.counter_events, [("Kilometres apart", "3,219")]),
        (charts.bars_events, [("Bloop", "3,219"), ("Whale", "0"), ("Ship", "120")]),
    ],
)
def test_override_tags_reach_libass(layout: object, items: list[tuple[str, str]]) -> None:
    r"""Regression: tags written as "\an5" in a plain string become BEL, form feed or TAB bytes."""
    lines = layout(items, 5.0, 12.0)  # type: ignore[operator]
    assert not any(ord(ch) < 0x20 for line in lines for ch in line), "control byte in an event"
    evs = events(lines)
    texts = [e.text for e in evs if not drawing(e.text)]
    assert texts
    if layout is charts.counter_events:
        assert all("\\an5" in t for t in texts), "counter and label are centred"
        return
    assert all("\\an4" in t for t in texts), "bar labels and values are left aligned"
    bars = [e.text for e in evs if drawing(e.text) and "\\fscx1\\" in e.text]
    assert len(bars) == len(items), "one growing bar per item"
    for bar in bars:
        assert "\\an7" in bar and re.search(r"\\t\([^)]*\\fscx100\)", bar), "bar grows from x 1% to 100%"


def test_acceptance() -> None:
    test_plain_numbers("3,219", 3219)
    test_counter_counts_up_in_the_value_format("3,219", r"\d{1,3}(,\d{3})*")
    test_bar_lengths()
