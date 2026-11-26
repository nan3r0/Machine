"""The host character as ASS events (task p3-character). Pure functions, no IO."""

from pipeline.schema import WordTiming
from pipeline.visuals.art import HostArt


def host_origin() -> tuple[float, float]:
    """Screen position of the art box origin (top-left) at rest: the asset's `ground` anchor at
    HOST_SCALE lands on (HOST_GROUND_X, HOST_GROUND_Y). The same in every scene."""
    raise NotImplementedError


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
    raise NotImplementedError
