"""push_in zooms about the frame centre (task p3b-host-placement).

libass scales a `\\p1` drawing about its `\\pos`/`\\move` point (the drawing's (0,0)); `\\org` only
moves the rotation centre. Evidence in .harness/handoffs/p3b-plan.md: in render run 45917646665
the shore_night moon (art y 420) sat at y 441 and the sand top (art y 960) at y 1010 at scale
1.0525, so the set grew from its top-left corner and slid its ground down under the host.
A point p of the art is drawn at anchor(t) + scale(t) * p, with both linear over the event.
"""

import re

import pytest

from pipeline import constants as c
from pipeline.visuals import sets
from tests.visuals.ass_parse import Event, drawing, events, move
from tests.visuals.test_sets import ART, SHAPE_PATHS

CENTRE = (c.WIDTH / 2, c.HEIGHT / 2)


def depth_of(e: Event) -> str:
    return next(layer.depth for layer in ART.layers if drawing(e.text) in {s.path for s in layer.shapes})


def scales(text: str) -> tuple[float, float]:
    """(scale at the event start, scale at its end) from `\\fscy` before and inside `\\t(0,<end>,...)`."""
    start = re.search(r"\\fscy(-?\d+(?:\.\d+)?)", text)
    grow = re.search(r"\\t\(0,\d+,[^)]*\\fscy(-?\d+(?:\.\d+)?)", text)
    assert start, text
    return float(start.group(1)) / 100, (float(grow.group(1)) / 100 if grow else float(start.group(1)) / 100)


@pytest.mark.parametrize("start,end", [(0.0, 7.0), (12.02, 20.7), (3.0, 3.5)])
def test_push_in_keeps_the_frame_centre_still(start: float, end: float) -> None:
    evs = events(sets.set_events(ART, start, end, "push_in"))
    shapes = [e for e in evs if drawing(e.text) in SHAPE_PATHS]
    assert len(shapes) == len(SHAPE_PATHS)
    for e in shapes:
        x0, y0, x1, y1 = move(e.text)  # type: ignore[misc]
        s0, s1 = scales(e.text)
        assert (s0, s1) == pytest.approx((1.0, c.PUSH_IN_SCALE))
        assert f"\\t(0,{round((end - start) * 1000)}," in e.text, "the zoom spans the whole event"
        dx = sets.drift_px(depth_of(e), "push_in", end - start)
        assert (x0 + s0 * CENTRE[0], y0 + s0 * CENTRE[1]) == pytest.approx(CENTRE, abs=0.5)
        moved = (CENTRE[0] + dx, CENTRE[1])
        assert (x1 + s1 * CENTRE[0], y1 + s1 * CENTRE[1]) == pytest.approx(moved, abs=0.5)


def test_push_in_ground_does_not_slide_under_the_host() -> None:
    """The set's ground at the host's feet moves at most (S - 1) * (HOST_GROUND_Y - HEIGHT/2)."""
    for e in events(sets.set_events(ART, 0.0, 7.0, "push_in")):
        if drawing(e.text) in SHAPE_PATHS:
            _, y0, _, y1 = move(e.text)  # type: ignore[misc]
            s0, s1 = scales(e.text)
            shift = (y1 + s1 * c.HOST_GROUND_Y) - (y0 + s0 * c.HOST_GROUND_Y)
            assert abs(shift) <= (c.PUSH_IN_SCALE - 1) * (c.HOST_GROUND_Y - CENTRE[1]) + 0.5


def test_acceptance() -> None:
    test_push_in_keeps_the_frame_centre_still(0.0, 7.0)
    test_push_in_ground_does_not_slide_under_the_host()
