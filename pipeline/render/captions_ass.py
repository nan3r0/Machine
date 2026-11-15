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
    - Each Dialogue places its text with `\\pos(x,y)`, inside the safe zone from constants.py
      (SAFE_LEFT_PX <= x <= SAFE_RIGHT_PX, SAFE_TOP_PX <= y <= SAFE_BOTTOM_PX).
    - The style uses CAPTION_FONT_NAME at CAPTION_FONT_SIZE.

    Raises ValueError if `timings` is empty or `words_per_line` is below 1.
    """
    raise NotImplementedError
