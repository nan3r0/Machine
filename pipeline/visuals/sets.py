"""Set layers as libass events: parallax drift, push-in, scene fade (task p3-sets). No IO."""

from pipeline import constants as c
from pipeline.visuals.art import SetArt, Shape
from pipeline.visuals.ass_kit import shape_event

_BLACK = {"k": "000000"}
_FRAME_PATH = f"m 0 0 l {c.WIDTH} 0 l {c.WIDTH} {c.HEIGHT} l 0 {c.HEIGHT}"


def drift_px(depth: str, camera: str, seconds: float) -> float:
    """Signed x distance a layer of `depth` moves over a scene of `seconds`.

    push_in: -min(DRIFT_PX_PER_S[depth] * seconds, SET_LAYER_MARGIN_PX) (content drifts left);
    pan_right: the same with PAN_PX_PER_S; pan_left: the positive of that; still: 0.
    Raises ValueError for an unknown depth or camera, or seconds < 0.
    """
    if depth not in c.SET_DEPTHS or camera not in c.CAMERA_MOVES or seconds < 0:
        raise ValueError(f"bad drift: {depth!r}, {camera!r}, {seconds}")
    if camera == "still":
        return 0.0
    speeds = c.DRIFT_PX_PER_S if camera == "push_in" else c.PAN_PX_PER_S
    distance = min(speeds[depth] * seconds, c.SET_LAYER_MARGIN_PX)
    return distance if camera == "pan_left" else -distance


def _frame_black(start: float, end: float, layer: int, alpha: str, tags: str = "") -> str:
    shape = Shape(layer=0, fill="k", outline=0, path=_FRAME_PATH, alpha=alpha)
    return shape_event(shape, _BLACK, "000000", start, end, layer, (0, 0), tags=tags)


def set_events(art: SetArt, start: float, end: float, camera: str, dim: bool = False,
               fade_in: float = 0.0) -> list[str]:
    """Dialogue lines drawing every shape of `art` from `start` to `end`.

    - Each shape is one event spanning the window, on ASS layer ASS_LAYER_SET plus its layer's
      index (back to front), moved with `\\move(0,0,dx,0)`, dx = drift_px(depth, camera, end - start).
    - push_in adds a `\\t(` over the whole window to `\\fscx` and `\\fscy` of PUSH_IN_SCALE * 100.
      libass scales a drawing about its `\\pos`/`\\move` point (`\\org` only moves the rotation
      centre), so push_in moves that point from (0,0) to (dx + WIDTH/2 * (1 - S), HEIGHT/2 * (1 - S)),
      S = PUSH_IN_SCALE: the frame centre stays put (plus the drift) instead of the set growing down
      and right from its top-left corner. Other cameras do not scale.
    - With `dim`, a full-frame black shape at alpha SET_DIM_ALPHA on ASS_LAYER_DIM.
    - With `fade_in` > 0, a full-frame black shape on ASS_LAYER_FADE starting at `start` with
      `\\fad(0,<fade_in in ms>)`.
    Raises ValueError for an unknown camera or end < start.
    """
    if camera not in c.CAMERA_MOVES or end < start:
        raise ValueError(f"bad set window: {camera!r}, {start}..{end}")
    seconds = end - start
    out: list[str] = []
    for index, layer in enumerate(art.layers):
        dx = drift_px(layer.depth, camera, seconds)
        end_x, end_y = dx, 0.0
        grow = ""
        if camera == "push_in":
            pct = f"{c.PUSH_IN_SCALE * 100:g}"
            grow = f"\\t(0,{round(seconds * 1000)},\\fscx{pct}\\fscy{pct})"
            end_x += c.WIDTH / 2 * (1 - c.PUSH_IN_SCALE)
            end_y = c.HEIGHT / 2 * (1 - c.PUSH_IN_SCALE)
        tags = f"\\move(0,0,{end_x:g},{end_y:g}){grow}"
        out += [
            shape_event(s, art.palette, art.palette[art.outline_colour], start, end,
                        c.ASS_LAYER_SET + index, (0, 0), tags=tags)
            for s in layer.shapes
        ]
    if dim:
        out.append(_frame_black(start, end, c.ASS_LAYER_DIM, c.SET_DIM_ALPHA))
    if fade_in > 0:
        # \fad's second argument fades out at the event's end, so the event must end with the fade.
        fade_end = min(end, start + fade_in)
        fade_ms = round((fade_end - start) * 1000)
        out.append(_frame_black(start, fade_end, c.ASS_LAYER_FADE, "00", f"\\fad(0,{fade_ms})"))
    return out
