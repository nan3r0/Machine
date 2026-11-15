"""Word-by-word .ass captions for a 1080x1920 frame (task p1-captions-ass). Pure functions, no IO."""

from pipeline.constants import (
    CAPTION_FONT_NAME,
    CAPTION_FONT_SIZE,
    CAPTION_MAX_WORDS_PER_LINE,
    HEIGHT,
    SAFE_LEFT_PX,
    SAFE_RIGHT_PX,
    WIDTH,
)
from pipeline.schema import WordTiming

STYLE_NAME = "Caption"
# ASS colours are &HAABBGGRR; the current word is yellow, the rest white.
WHITE = "&H00FFFFFF"
HIGHLIGHT = "&H0000FFFF"
BLACK = "&H00000000"
POS_X = (SAFE_LEFT_PX + SAFE_RIGHT_PX) / 2
POS_Y = HEIGHT / 2
# Zero-width space: stops a backslash from forming a control code (\N, \n, \h) with the next character.
ZWSP = "​"


def escape_ass_text(word: str) -> str:
    """Make `word` safe as ASS dialogue text, so it shows exactly as written.

    `{` and `}` must not open or close an override block: each is written as `\\{` and `\\}`.
    A backslash must not form a control code such as `\\N`, `\\n` or `\\h`. Text without these
    characters, including any unicode, is returned unchanged.
    """
    # Backslash first, so the ones added for the braces are not touched. ASS has no escape for a
    # literal backslash, so a zero-width space after it keeps it from joining the next character.
    return word.replace("\\", "\\" + ZWSP).replace("{", "\\{").replace("}", "\\}")


def _ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, rest = divmod(centiseconds, 360000)
    minutes, rest = divmod(rest, 6000)
    return f"{hours}:{minutes:02d}:{rest // 100:02d}.{rest % 100:02d}"


def _header() -> list[str]:
    style_format = (
        "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
    )
    style = (
        f"{STYLE_NAME},{CAPTION_FONT_NAME},{CAPTION_FONT_SIZE},{WHITE},{WHITE},{BLACK},{BLACK},"
        f"1,0,0,0,100,100,0,0,1,6,0,5,{SAFE_LEFT_PX},{WIDTH - SAFE_RIGHT_PX},0,1"
    )
    return [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "",
        "[V4+ Styles]",
        f"Format: {style_format}",
        f"Style: {style}",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]


def _line_text(words: list[str], current: int) -> str:
    shown = [
        f"{{\\1c{HIGHLIGHT}&}}{word}{{\\r}}" if i == current else word
        for i, word in enumerate(map(escape_ass_text, words))
    ]
    return f"{{\\pos({POS_X:g},{POS_Y:g})}}" + " ".join(shown)


def build_ass(timings: list[WordTiming], words_per_line: int = CAPTION_MAX_WORDS_PER_LINE) -> str:
    """Return the text of a complete .ass file showing `timings` word by word.

    - `[Script Info]` sets `PlayResX: 1080` and `PlayResY: 1920` (WIDTH and HEIGHT).
    - `[Events]` holds exactly one `Dialogue:` line per word, in word order. Its Start is the
      word's start; its End is no earlier than the word's end and no later than the next word's
      start, or the word's own end if that is later (the last word ends at its own end). Times use
      `H:MM:SS.cc`, rounded to the nearest centisecond.
    - Each Dialogue shows the current line of at most `words_per_line` words with the current
      word highlighted; its text contains `escape_ass_text(word)` outside override blocks.
    - Each Dialogue places its text with one `\\pos(x,y)`, x and y plain numbers, at the
      horizontal centre of the safe zone (x == (SAFE_LEFT_PX + SAFE_RIGHT_PX) / 2) and with room
      for wrapped lines above and below (SAFE_TOP_PX + 2 * CAPTION_FONT_SIZE <= y <=
      SAFE_BOTTOM_PX - 2 * CAPTION_FONT_SIZE).
    - Nothing is cut off: libass wraps every event, `\\pos` or not, to the width the margins
      leave. So the style has Alignment 5 (centred), MarginL == SAFE_LEFT_PX and
      MarginR == WIDTH - SAFE_RIGHT_PX; each Dialogue's own MarginL and MarginR are 0 (use the
      style's); `WrapStyle` is not 2 and no override uses `\\q2` or `\\an`. A line too wide for
      the safe zone then wraps inside it instead of running past its edges.
    - The style uses CAPTION_FONT_NAME at CAPTION_FONT_SIZE.

    Raises ValueError if `timings` is empty or `words_per_line` is below 1.
    """
    if not timings:
        raise ValueError("timings must not be empty")
    if words_per_line < 1:
        raise ValueError("words_per_line must be at least 1")
    lines = _header()
    for i, timing in enumerate(timings):
        first = i - i % words_per_line
        line_words = [t.word for t in timings[first:first + words_per_line]]
        # The caption stays up until the next word starts, so there is no flicker between words.
        end = max(timing.end, timings[i + 1].start) if i + 1 < len(timings) else timing.end
        text = _line_text(line_words, i - first)
        lines.append(f"Dialogue: 0,{_ass_time(timing.start)},{_ass_time(end)},{STYLE_NAME},,0,0,0,,{text}")
    return "\n".join(lines) + "\n"
