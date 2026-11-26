"""The host character as ASS events (task p3-character). Pure functions, no IO."""

import math

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


def _boundaries(start: float, end: float, timings: list[WordTiming]) -> list[float]:
    cuts = {start, end}
    for k in range(math.ceil((end - start) / c.IDLE_HALF_CYCLE_S)):
        cuts.add(start + k * c.IDLE_HALF_CYCLE_S)
    k = 0
    while (blink := start + c.BLINK_FIRST_S + k * c.BLINK_EVERY_S) < end:
        cuts.update((blink, blink + c.BLINK_S))
        k += 1
    for w in timings:
        cuts.update((w.start, w.end))
    return sorted({round(t, 2) for t in cuts if start <= t <= end})


def _mouth_at(art: HostArt, pose: str, t: float, timings: list[WordTiming]) -> str:
    talking = [m for m in art.talking_mouths if m != "rest"]
    for i, w in enumerate(timings):
        if w.start <= t < w.end:
            return talking[i % len(talking)]
    return art.poses[pose].mouth


def _blinking(t: float, start: float) -> bool:
    since = t - start - c.BLINK_FIRST_S
    return since >= 0 and since % c.BLINK_EVERY_S < c.BLINK_S


def host_events(art: HostArt, start: float, end: float, pose: str,
                timings: list[WordTiming]) -> list[str]:
    """Dialogue lines (ass_kit) drawing the host in `pose` from `start` to `end` seconds.

    - Every event lies inside [start, end]. Shapes use SHAPE_STYLE on ASS layer
      ASS_LAYER_HOST + shape.layer, scale HOST_SCALE, placed with `\\pos` or `\\move` whose
      x is host_origin()'s x and whose y is between host_origin()'s y - BOB_PX and its y.
    - Body and the pose's arms show for the whole window. The bob is always on: positions move
      on IDLE_HALF_CYCLE_S half-cycles. Only `wave` swings its right arm, by ARM_SWING_DEG about
      the `shoulder_right` anchor.
    - Mouth: while a word of `timings` inside the window is spoken, a talking mouth other than
      "rest" shows (changing word to word through art.talking_mouths); between words the pose's
      own mouth shows. Exactly one mouth shows at any time.
    - Eyes: the pose's eyes, except closed for BLINK_S at start + BLINK_FIRST_S + k * BLINK_EVERY_S.
      Exactly one eyes variant shows at any time. No randomness: same input, same output.
    Raises ValueError for a pose not in art.poses or end < start.
    """
    if pose not in art.poses or end < start:
        raise ValueError(f"bad host window: pose {pose!r}, start {start}, end {end}")
    spec = art.poses[pose]
    ox, oy = host_origin()
    sx, sy = art.anchors["shoulder_right"]
    cuts = _boundaries(start, end, timings)
    lines: list[str] = []
    for t0, t1 in zip(cuts, cuts[1:], strict=False):
        mid = (t0 + t1) / 2
        eyes = "closed" if _blinking(mid, start) else spec.eyes
        face = [*art.eyes[eyes], *art.brows[spec.brows], *art.mouths[_mouth_at(art, pose, mid, timings)]]
        y0 = oy - c.BOB_PX * _bob_level(t0, start)
        # t1 - 1e-6: a segment ends on the level it reaches, not the next half-cycle's start.
        y1 = oy - c.BOB_PX * _bob_level(t1 - 1e-6, start)
        move = f"\\move({ox:g},{y0:g},{ox:g},{y1:g})"
        a0 = (2 * _bob_level(t0, start) - 1) * c.ARM_SWING_DEG
        a1 = (2 * _bob_level(t1 - 1e-6, start) - 1) * c.ARM_SWING_DEG
        org = f"\\org({ox + sx * c.HOST_SCALE:g},{(y0 + y1) / 2 + sy * c.HOST_SCALE:g})"
        wave = f"{move}{org}\\frz{a0:g}\\t(\\frz{a1:g})"
        groups: list[tuple[list[Shape], str]] = [
            (art.body, move), (face, move), (spec.arm_left, move),
            (spec.arm_right, wave if pose == "wave" else move),
        ]
        for shapes, tags in groups:
            lines.extend(
                shape_event(s, art.palette, art.palette[art.outline_colour], t0, t1,
                            c.ASS_LAYER_HOST + s.layer, (ox, y0), c.HOST_SCALE, tags)
                for s in shapes
            )
    return lines
