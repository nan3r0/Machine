"""ASS drawing kit for scenes.ass (task p3-ass-kit). Pure functions, no IO.

Text goes through `pipeline.render.captions_ass.escape_ass_text`; never copy it.
"""

from pipeline.visuals.art import Shape

SHAPE_STYLE = "Shape"
CARD_STYLE = "Card"


def header() -> str:
    """The `[Script Info]`, `[V4+ Styles]` and `[Events]` sections, ending with the events
    `Format:` line and a newline.

    - `PlayResX: WIDTH`, `PlayResY: HEIGHT`, `WrapStyle` not 2, `ScaledBorderAndShadow: yes`.
    - Style SHAPE_STYLE: Alignment 7 (top left), no outline or shadow of its own.
    - Style CARD_STYLE: CAPTION_FONT_NAME at CARD_FONT_SIZE, Alignment 5, MarginL ==
      DATA_PANEL[0] and MarginR == WIDTH - DATA_PANEL[2], so a long card line wraps inside the
      panel instead of running past it.
    """
    raise NotImplementedError


def ass_time(seconds: float) -> str:
    """`H:MM:SS.cc`, rounded to the nearest centisecond. Raises ValueError below 0."""
    raise NotImplementedError


def ass_colour(rgb: str) -> str:
    """RGB hex (`"E3A332"`) as an ASS colour value `&HBBGGRR&` (`"&H32A3E3&"`).
    Raises ValueError unless `rgb` is six hex digits."""
    raise NotImplementedError


def dialogue(start: float, end: float, layer: int, text: str, style: str = SHAPE_STYLE) -> str:
    """One line `Dialogue: <layer>,<start>,<end>,<style>,,0,0,0,,<text>` with ass_time times.
    `text` is used as given (override tags allowed). Raises ValueError if end < start or layer < 0."""
    raise NotImplementedError


def shape_event(shape: Shape, palette: dict[str, str], outline_rgb: str, start: float, end: float,
                layer: int, pos: tuple[float, float], scale: float = 1.0, tags: str = "") -> str:
    """A SHAPE_STYLE dialogue drawing `shape`.

    The text is one override block then `shape.path` verbatim and `{\\p0}`. The block holds
    `\\pos(x,y)` (unless `tags` holds a `\\move`), `\\fscx` and `\\fscy` of `scale * 100`,
    `\\1c` of the shape's palette fill, `\\3c` of `outline_rgb`, `\\bord<shape.outline>`,
    `\\1a&H<shape.alpha>&`, then `tags`, then `\\p1`. The art origin (0, 0) lands at `pos`.
    """
    raise NotImplementedError


def text_event(text: str, start: float, end: float, layer: int, pos: tuple[float, float],
               size: int, rgb: str, tags: str = "") -> str:
    """A CARD_STYLE dialogue showing `text` exactly: `{\\pos(x,y)\\fs<size>\\1c<colour><tags>}`
    then `escape_ass_text(text)`."""
    raise NotImplementedError
