"""Forced alignment of the known script text to voice.wav with stable-ts (task p1-align).

The words always come from the script; only their timings come from the audio. Heavy libraries
(`stable_whisper`, `torch`) are imported inside functions, never at module top.
"""

from pathlib import Path

from pipeline.schema import WordTiming


class AlignError(RuntimeError):
    """Alignment failed or its output could not be mapped back to the script words."""


def align_words(audio: Path, text: str, cache_dir: Path) -> list[WordTiming]:
    """Align `text` to `audio` on CPU and return one WordTiming per word of `text.split()`.

    Uses the ALIGN_MODEL_NAME whisper model, downloaded once into `cache_dir` (whisper's
    `download_root`), so the caller can cache that folder between runs, as for Kokoro.

    Same words, same order, punctuation and unicode unchanged. Timings follow the rules of
    `to_word_timings`. Raises AlignError for blank text (before loading the model), unreadable
    audio or aligner failure.
    """
    raise NotImplementedError


def to_word_timings(
    script_words: list[str],
    pieces: list[tuple[str, float, float]],
    audio_duration: float,
) -> list[WordTiming]:
    """Map the aligner's word pieces `(text, start, end)` back onto `script_words`.

    The aligner may split a script word into several pieces and pads pieces with spaces. Once
    whitespace is removed, the pieces joined must equal the script words joined; otherwise raise
    AlignError. Each script word starts at the start of the piece holding its first character and
    ends at the end of the piece holding its last character.

    The result always satisfies: `word` equals the script word exactly; 0 <= start <= end <=
    audio_duration; starts and ends never decrease from one word to the next. Pieces that break
    these rules (end before start, times past the audio) are clamped, not passed through.
    """
    raise NotImplementedError
