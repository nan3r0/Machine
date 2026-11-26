"""Set layers as libass events: parallax drift, push-in, scene fade (task p3-sets). No IO."""

from pipeline.visuals.art import SetArt


def drift_px(depth: str, camera: str, seconds: float) -> float:
    """Signed x distance a layer of `depth` moves over a scene of `seconds`.

    push_in: -min(DRIFT_PX_PER_S[depth] * seconds, SET_LAYER_MARGIN_PX) (content drifts left);
    pan_right: the same with PAN_PX_PER_S; pan_left: the positive of that; still: 0.
    Raises ValueError for an unknown depth or camera, or seconds < 0.
    """
    raise NotImplementedError


def set_events(art: SetArt, start: float, end: float, camera: str, dim: bool = False,
               fade_in: float = 0.0) -> list[str]:
    """Dialogue lines drawing every shape of `art` from `start` to `end`.

    - Each shape is one event spanning the window, on ASS layer ASS_LAYER_SET plus its layer's
      index (back to front), moved with `\\move(x0,y,x1,y)` where x1 - x0 is
      drift_px(depth, camera, end - start).
    - push_in adds `\\org(WIDTH/2,HEIGHT/2)` and a `\\t(` to `\\fscx` and `\\fscy` of
      PUSH_IN_SCALE * 100 over the window; other cameras do not scale.
    - With `dim`, a full-frame black shape at alpha SET_DIM_ALPHA on ASS_LAYER_DIM.
    - With `fade_in` > 0, a full-frame black shape on ASS_LAYER_FADE starting at `start` with
      `\\fad(0,<fade_in in ms>)`.
    Raises ValueError for an unknown camera or end < start.
    """
    raise NotImplementedError
