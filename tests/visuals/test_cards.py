"""Data cards (task p3-cards): text exact, inside the panel and window, staggered."""

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


def test_acceptance() -> None:
    test_text_exact_inside_panel_and_window(cards.steps_events, STEPS)
    test_text_exact_inside_panel_and_window(cards.timeline_events, YEARS)
    test_text_exact_inside_panel_and_window(cards.place_events, PLACE)
    test_items_appear_one_after_another(cards.steps_events, STEPS)
