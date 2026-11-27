"""The host character as ASS events (task p3-character). Pure functions, no IO."""

import math
from collections.abc import Sequence

from pipeline import constants as c
from pipeline.schema import WordTiming
from pipeline.visuals.art import HostArt, Shape, load_host
from pipeline.visuals.ass_kit import shape_event


def host_origin() -> tuple[float, float]:
    """Screen position of the art box origin (top-left) at rest: the asset's `ground` anchor at
    HOST_SCALE lands on (HOST_GROUND_X, HOST_GROUND_Y). The same in every scene."""
    gx, gy = load_host().anchors["ground"]
    return c.HOST_GROUND_X - gx * c.HOST_SCALE, c.HOST_GROUND_Y - gy * c.HOST_SCALE


def _bob_level(t: float, start: float) -> float:
    """0 at rest, 1 at the top of the bob; a triangle wave on IDLE_HALF_CYCLE_S half-cycles."""
    k, frac = divmod((t - start) / c.IDLE_HALF_CYCLE_S, 1.0)
    return frac if int(k) % 2 == 0 else 1.0 - frac


def _boundaries(start: float, end: float) -> list[float]:
    cuts = {start, end}
    for k in range(math.ceil((end - start) / c.IDLE_HALF_CYCLE_S)):
        cuts.add(start + k * c.IDLE_HALF_CYCLE_S)
    k = 0
    while (blink := start + c.BLINK_FIRST_S + k * c.BLINK_EVERY_S) < end:
        cuts.update((blink, blink + c.BLINK_S))
        k += 1
    return sorted({round(t, 2) for t in cuts if start <= t <= end})


def _window_level(i: int, levels: Sequence[float] | None, timings: list[WordTiming]) -> float:
    if levels is not None:
        return levels[i] if i < len(levels) else 0.0
    mid = (i + 0.5) * c.MOUTH_WINDOW_S
    return 1.0 if any(w.start <= mid < w.end for w in timings) else 0.0


def _open_shape(level: float) -> str:
    return next(shape for floor, shape in c.MOUTH_SHAPES if level >= floor)


def _mouth_states(first: int, last: int, levels: Sequence[float] | None,
                  timings: list[WordTiming]) -> dict[int, str | None]:
    """The mouth per window (None is closed) for windows first..last, by the host_events rules."""
    hold = round(c.MOUTH_HOLD_S / c.MOUTH_WINDOW_S)
    cap = round(c.MOUTH_OPEN_MAX_S / c.MOUTH_WINDOW_S)
    states: dict[int, str | None] = {}
    shape: str | None = None
    held, open_for = hold, 0  # windows in this state, windows since the mouth last opened
    for i in range(first, last + 1):
        mid = (i + 0.5) * c.MOUTH_WINDOW_S
        if not timings or not timings[0].start <= mid <= timings[-1].end:
            want, force = None, True
        else:
            level = _window_level(i, levels, timings)
            force = False
            if shape is None:
                want = _open_shape(level) if level >= c.MOUTH_OPEN_LEVEL else None
            elif level < c.MOUTH_CLOSE_LEVEL or open_for >= cap:
                want = None
            else:
                # A late shape change would still be inside its hold at the cap and overrun it.
                want = _open_shape(level) if open_for + hold <= cap else shape
        if want != shape and (force or held >= hold):
            shape, held = want, 1
        else:
            held += 1
        open_for = 0 if shape is None else open_for + 1
        states[i] = shape
    return states


def _blinking(t: float, start: float) -> bool:
    since = t - start - c.BLINK_FIRST_S
    return since >= 0 and since % c.BLINK_EVERY_S < c.BLINK_S


def host_events(art: HostArt, start: float, end: float, pose: str,
                timings: list[WordTiming], *, levels: Sequence[float] | None = None) -> list[str]:
    """Dialogue lines (ass_kit) drawing the host in `pose` from `start` to `end` seconds.

    - Every event lies inside [start, end]. Shapes use SHAPE_STYLE on ASS layer
      ASS_LAYER_HOST + shape.layer, scale HOST_SCALE, placed with `\\pos` or `\\move` whose
      x is host_origin()'s x and whose y is between host_origin()'s y - BOB_PX and its y.
    - Body and the pose's arms show for the whole window. The bob is always on: positions move
      on IDLE_HALF_CYCLE_S half-cycles. Only `wave` swings its right arm, by ARM_SWING_DEG about
      the `shoulder_right` anchor.
    - Mouth (lip flap, p3b-plan): exactly one mouth shows at any time. `levels[i]` is the voice's
      loudness (0 to 1, voice_levels) over [i, i + 1) * MOUTH_WINDOW_S; past its end the level is 0.
      With `levels` None a window's level is 1 if its midpoint is inside a word span, else 0.
      A state machine over those windows decides the mouth:
      - Closed outside the narration [timings[0].start, timings[-1].end] whatever the level.
        Closed shows the pose's mouth if it is in HOST_CLOSED_MOUTHS, else "rest".
      - Closed opens at a level >= MOUTH_OPEN_LEVEL; open closes below MOUTH_CLOSE_LEVEL.
      - An open mouth closes for MOUTH_HOLD_S once it has been open MOUTH_OPEN_MAX_S.
      - No mouth state (closed or one open shape) shows for less than MOUTH_HOLD_S.
      - The open shape is the first MOUTH_SHAPES entry whose level the window reaches.
      Mouth events are cut only where the mouth changes and on bob half-cycles, not the body:
      the body, eyes, brows and arms are not re-cut at mouth changes. At any moment every host
      shape sits at the same bob height.
    - Eyes: the pose's eyes, except closed for BLINK_S at start + BLINK_FIRST_S + k * BLINK_EVERY_S.
      Exactly one eyes variant shows at any time. No randomness: same input, same output.
    Raises ValueError for a pose not in art.poses or end < start.
    """
    if pose not in art.poses or end < start:
        raise ValueError(f"bad host window: pose {pose!r}, start {start}, end {end}")
    spec = art.poses[pose]
    ox, oy = host_origin()
    sx, sy = art.anchors["shoulder_right"]
    closed = spec.mouth if spec.mouth in c.HOST_CLOSED_MOUTHS else "rest"
    cuts = _boundaries(start, end)
    # Windows sit on the absolute voice timeline (t / MOUTH_WINDOW_S), the same as the timings.
    states = _mouth_states(math.floor(start / c.MOUTH_WINDOW_S), math.ceil(end / c.MOUTH_WINDOW_S),
                           levels, timings)

    first, last = min(states), max(states)

    def mouth_at(t: float) -> str:
        # Clamped: float error at a window edge must not leave the computed range.
        return states[min(max(math.floor(t / c.MOUTH_WINDOW_S), first), last)] or closed

    mouth_cuts = {start, end, *cuts}
    for i in states:
        edge = round(i * c.MOUTH_WINDOW_S, 2)
        if start < edge < end and mouth_at(edge - 1e-6) != mouth_at(edge + 1e-6):
            mouth_cuts.add(edge)
    lines: list[str] = []

    def emit(t0: float, t1: float, y0: float, groups: list[tuple[list[Shape], str]]) -> None:
        for shapes, tags in groups:
            lines.extend(
                shape_event(s, art.palette, art.palette[art.outline_colour], t0, t1,
                            c.ASS_LAYER_HOST + s.layer, (ox, y0), c.HOST_SCALE, tags)
                for s in shapes
            )

    def bob(t0: float, t1: float) -> tuple[float, float, str]:
        # t1 - 1e-6: a segment ends on the level it reaches, not the next half-cycle's start.
        y0 = oy - c.BOB_PX * _bob_level(t0, start)
        y1 = oy - c.BOB_PX * _bob_level(t1 - 1e-6, start)
        return y0, y1, f"\\move({ox:g},{y0:g},{ox:g},{y1:g})"

    for t0, t1 in zip(cuts, cuts[1:], strict=False):
        y0, y1, move = bob(t0, t1)
        a0 = (2 * _bob_level(t0, start) - 1) * c.ARM_SWING_DEG
        a1 = (2 * _bob_level(t1 - 1e-6, start) - 1) * c.ARM_SWING_DEG
        org = f"\\org({ox + sx * c.HOST_SCALE:g},{(y0 + y1) / 2 + sy * c.HOST_SCALE:g})"
        wave = f"{move}{org}\\frz{a0:g}\\t(\\frz{a1:g})"
        eyes = "closed" if _blinking((t0 + t1) / 2, start) else spec.eyes
        emit(t0, t1, y0, [
            (art.body, move), ([*art.eyes[eyes], *art.brows[spec.brows]], move),
            (spec.arm_left, move), (spec.arm_right, wave if pose == "wave" else move),
        ])
    cuts_m = sorted({round(t, 2) for t in mouth_cuts})
    for t0, t1 in zip(cuts_m, cuts_m[1:], strict=False):
        y0, _, move = bob(t0, t1)
        emit(t0, t1, y0, [(art.mouths[mouth_at((t0 + t1) / 2)], move)])
    return lines
