"""Forced alignment of the known script text to voice.wav with stable-ts (task p1-align).

The words always come from the script; only their timings come from the audio. Heavy libraries
(`stable_whisper`, `torch`) are imported inside functions, never at module top.
"""

import wave
from pathlib import Path

from pipeline.constants import ALIGN_MODEL_NAME
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
    script_words = text.split()
    if not script_words:
        raise AlignError("script text is blank")
    duration = _wav_seconds(audio)
    try:
        import stable_whisper

        model = stable_whisper.load_model(ALIGN_MODEL_NAME, device="cpu", download_root=str(cache_dir))
        result = model.align(str(audio), " ".join(script_words), language="en")
    except Exception as exc:  # noqa: BLE001 - torch, whisper and ffmpeg raise many unrelated types
        raise AlignError(f"alignment failed: {exc}") from exc
    pieces = [(w.word, w.start, w.end) for w in result.all_words()]
    return to_word_timings(script_words, pieces, duration)


def _wav_seconds(audio: Path) -> float:
    try:
        with wave.open(str(audio), "rb") as wav:
            return wav.getnframes() / wav.getframerate()
    except (wave.Error, EOFError, OSError, ZeroDivisionError) as exc:
        raise AlignError(f"cannot read audio {audio.name}: {exc}") from exc


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
    char_piece: list[int] = []
    clamped: list[tuple[float, float]] = []
    for text, start, end in pieces:
        squeezed = "".join(text.split())
        if not squeezed:
            continue
        low = min(max(start, 0.0), audio_duration)
        high = min(max(end, low), audio_duration)
        char_piece.extend([len(clamped)] * len(squeezed))
        clamped.append((low, high))
    if "".join("".join(t.split()) for t, _, _ in pieces) != "".join(script_words):
        raise AlignError("aligner output does not match the script words")

    timings: list[WordTiming] = []
    offset = 0
    prev_start = prev_end = 0.0
    for word in script_words:
        first, last = char_piece[offset], char_piece[offset + len(word) - 1]
        offset += len(word)
        start = max(prev_start, clamped[first][0])
        end = max(prev_end, start, clamped[last][1])
        timings.append(WordTiming(word=word, start=start, end=end))
        prev_start, prev_end = start, end
    return timings
