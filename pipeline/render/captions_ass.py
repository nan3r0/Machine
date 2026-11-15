"""Word-by-word .ass captions for a 1080x1920 frame (task p1-captions-ass). Pure functions, no IO."""

from pipeline.constants import CAPTION_MAX_WORDS_PER_LINE
from pipeline.schema import WordTiming


def escape_ass_text(word: str) -> str:
    """Make `word` safe as ASS dialogue text, so it shows exactly as written.

    `{` and `}` must not open or close an override block: each is written as `\\{` and `\\}`.
    A backslash must not form a control code such as `\\N`, `\\n` or `\\h`. Text without these
    characters, including any unicode, is returned unchanged.
    """
    raise NotImplementedError


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
    raise NotImplementedError
