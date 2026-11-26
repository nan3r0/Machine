"""Data cards (task p3-cards): text exact, inside the panel and window, staggered."""

import re
from collections.abc import Callable

import pytest

from pipeline import constants as c
from pipeline.visuals import cards
from tests.visuals.ass_parse import Event, events, pos, shown_text

Layout = Callable[[list[tuple[str, str]], float, float], list[str]]
STEPS = [("Listening", ""), ("The {Bloop}", ""), ("Café guesses", ""), ("A very long label for a card", "")]
YEARS = [("Heard", "1997"), ("Found", "2005")]
PLACE = [("Southern Pacific", "3,219 km")]


def first_shown(evs: list[Event], text: str) -> float:
    return min(e.start for e in evs if shown_text(e.text) and text in shown_text(e.text))


def check_common(evs: list[Event], items: list[tuple[str, str]], start: float, end: float) -> None:
    assert evs and all(start <= e.start <= e.end <= end and e.layer >= c.ASS_LAYER_CARD for e in evs)
    left, top, right, bottom = c.DATA_PANEL
    for e in evs:
        p = pos(e.text)
        if p:
            assert left <= p[0] <= right and top <= p[1] <= bottom, e.text[:60]
    texts = [shown_text(e.text) for e in evs]
    for label, value in items:
        assert any(label in t for t in texts) and (not value or any(value in t for t in texts))


@pytest.mark.parametrize(
    ("layout", "items"),
    [(cards.steps_events, STEPS), (cards.timeline_events, YEARS), (cards.place_events, PLACE)],
)
def test_text_exact_inside_panel_and_window(layout: Layout, items: list[tuple[str, str]]) -> None:
    check_common(events(layout(items, 12.0, 19.5)), items, 12.0, 19.5)


@pytest.mark.parametrize(("layout", "items"), [(cards.steps_events, STEPS), (cards.timeline_events, YEARS)])
def test_items_appear_one_after_another(layout: Layout, items: list[tuple[str, str]]) -> None:
    evs = events(layout(items, 0.0, 8.0))
    times = [first_shown(evs, label) for label, _ in items]
    assert times == sorted(times) and len(set(times)) == len(times)


def test_steps_are_numbered() -> None:
    texts = [shown_text(e.text).strip() for e in events(cards.steps_events(STEPS, 0, 8))]
    assert all(str(n) in texts for n in range(1, len(STEPS) + 1))


BADGE_X = c.DATA_PANEL[0] + 60
# Advance of "A" in Montserrat Bold per unit of font size (Pillow, em-based). libass draws smaller,
# since it sizes the font to ascent + descent (1.219 em), so this over-estimates the drawn width.
CAP_EM = 0.756
LONG_LABELS = ["A" * 24, "THE MARY CELESTE MYSTERY"]


def font_size(text: str) -> float:
    found = re.search(r"\\fs([\d.]+)", text)
    assert found, text[:60]
    return float(found.group(1))


@pytest.mark.parametrize("label", LONG_LABELS)
@pytest.mark.parametrize("layout", [cards.steps_events, cards.timeline_events])
def test_long_label_fits_between_badge_and_panel_edge(layout: Layout, label: str) -> None:
    evs = events(layout([(label, "1997")], 0.0, 8.0))
    shown = [e for e in evs if label in shown_text(e.text)]
    assert shown
    for e in shown:
        x = pos(e.text)[0]  # type: ignore[index]
        assert "\\an4" in e.text and x > BADGE_X + 18
        assert x + font_size(e.text) * len(label) * CAP_EM <= c.DATA_PANEL[2]


@pytest.mark.parametrize("label", LONG_LABELS)
def test_long_place_name_fits_the_panel(label: str) -> None:
    left, _, right, _ = c.DATA_PANEL
    shown = [e for e in events(cards.place_events([(label, "")], 0.0, 8.0)) if label in shown_text(e.text)]
    assert shown
    for e in shown:
        half = font_size(e.text) * len(label) * CAP_EM / 2
        x = pos(e.text)[0]  # type: ignore[index]
        assert left <= x - half and x + half <= right


def test_acceptance() -> None:
    test_text_exact_inside_panel_and_window(cards.steps_events, STEPS)
    test_text_exact_inside_panel_and_window(cards.timeline_events, YEARS)
    test_text_exact_inside_panel_and_window(cards.place_events, PLACE)
    test_items_appear_one_after_another(cards.steps_events, STEPS)
