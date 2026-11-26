"""ASS drawing kit for scenes.ass (task p3-ass-kit). Pure functions, no IO.

Text goes through `pipeline.render.captions_ass.escape_ass_text`; never copy it.
"""

import re

from pipeline.constants import CAPTION_FONT_NAME, CARD_FONT_SIZE, DATA_PANEL, HEIGHT, WIDTH
from pipeline.render.captions_ass import escape_ass_text
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
    fmt = (
        "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    white, black = "&H00FFFFFF", "&H00000000"
    shape = (
        f"{SHAPE_STYLE},{CAPTION_FONT_NAME},20,{white},{white},{black},{black},"
        "0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1"
    )
    card = (
        f"{CARD_STYLE},{CAPTION_FONT_NAME},{CARD_FONT_SIZE},{white},{white},{black},{black},"
        f"1,0,0,0,100,100,0,0,1,0,0,5,{DATA_PANEL[0]},{WIDTH - DATA_PANEL[2]},0,1"
    )
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}",
        "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", f"Format: {fmt}", f"Style: {shape}", f"Style: {card}", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", "",
    ])


def ass_time(seconds: float) -> str:
    """`H:MM:SS.cc`, rounded to the nearest centisecond. Raises ValueError below 0."""
    if seconds < 0:
        raise ValueError(f"negative time {seconds}")
    hours, rest = divmod(round(seconds * 100), 360000)
    minutes, rest = divmod(rest, 6000)
    return f"{hours}:{minutes:02d}:{rest // 100:02d}.{rest % 100:02d}"


def ass_colour(rgb: str) -> str:
    """RGB hex (`"E3A332"`) as an ASS colour value `&HBBGGRR&` (`"&H32A3E3&"`).
    Raises ValueError unless `rgb` is six hex digits."""
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", rgb):
        raise ValueError(f"not an RGB hex colour: {rgb!r}")
    return f"&H{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}&".upper()


def dialogue(start: float, end: float, layer: int, text: str, style: str = SHAPE_STYLE) -> str:
    """One line `Dialogue: <layer>,<start>,<end>,<style>,,0,0,0,,<text>` with ass_time times.
    `text` is used as given (override tags allowed). Raises ValueError if end < start or layer < 0."""
    if end < start or layer < 0:
        raise ValueError(f"bad dialogue: start {start}, end {end}, layer {layer}")
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}"


def shape_event(shape: Shape, palette: dict[str, str], outline_rgb: str, start: float, end: float,
                layer: int, pos: tuple[float, float], scale: float = 1.0, tags: str = "") -> str:
    """A SHAPE_STYLE dialogue drawing `shape`.

    The text is one override block then `shape.path` verbatim and `{\\p0}`. The block holds
    `\\pos(x,y)` (unless `tags` holds a `\\move`), `\\fscx` and `\\fscy` of `scale * 100`,
    `\\1c` of the shape's palette fill, `\\3c` of `outline_rgb`, `\\bord<shape.outline>`,
    `\\1a&H<shape.alpha>&`, then `tags`, then `\\p1`. The art origin (0, 0) lands at `pos`.
    """
    place = "" if "\\move" in tags else f"\\pos({pos[0]:g},{pos[1]:g})"
    pct = f"{scale * 100:g}"
    block = (
        f"{{{place}\\fscx{pct}\\fscy{pct}\\1c{ass_colour(palette[shape.fill])}"
        f"\\3c{ass_colour(outline_rgb)}\\bord{shape.outline}\\1a&H{shape.alpha}&{tags}\\p1}}"
    )
    return dialogue(start, end, layer, f"{block}{shape.path}{{\\p0}}")


def text_event(text: str, start: float, end: float, layer: int, pos: tuple[float, float],
               size: int, rgb: str, tags: str = "") -> str:
    """A CARD_STYLE dialogue showing `text` exactly: `{\\pos(x,y)\\fs<size>\\1c<colour><tags>}`
    then `escape_ass_text(text)`."""
    block = f"{{\\pos({pos[0]:g},{pos[1]:g})\\fs{size}\\1c{ass_colour(rgb)}{tags}}}"
    return dialogue(start, end, layer, block + escape_ass_text(text), CARD_STYLE)
