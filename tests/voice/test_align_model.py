"""The stable-ts call and exact piece mapping (task p1-qa-tests, QA lead items 9 and 10).

stable_whisper is faked in sys.modules, so these run without torch or a model download.
"""

import inspect
import struct
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline import constants
from pipeline.voice import align
from pipeline.voice.align import AlignError
from tests.wavs import write_wav

TEXT = "In 1938, a café pen"


def load_model_call(name: str, device: str | None = None, download_root: str | None = None,
                    in_memory: bool = False) -> None:
    """The signature of stable_whisper.load_model, to read a recorded call however it was made."""


def align_call(audio: str, text: str, language: str | None = None, **options: Any) -> None:
    """The signature of the model's align method."""


def piece(word: str, start: float, end: float) -> SimpleNamespace:
    return SimpleNamespace(word=word, start=start, end=end)


@pytest.fixture
def whisper(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = ModuleType("stable_whisper")
    module.load_model = MagicMock(name="load_model")  # type: ignore[attr-defined]
    model = module.load_model.return_value
    model.align.return_value.all_words.return_value = [
        piece(" In", 0.1, 0.3), piece(" 1938,", 0.3, 1.0), piece(" ", 1.0, 1.05),
        piece(" a", 1.05, 1.1), piece(" caf", 1.1, 1.3), piece("é", 1.3, 1.4), piece(" pen", 1.4, 1.8)]
    monkeypatch.setitem(sys.modules, "stable_whisper", module)
    return module


@pytest.fixture
def wav(tmp_path: Path) -> Path:
    return write_wav(tmp_path / "voice.wav", 2.0, constants.VOICE_SAMPLE_RATE)


def test_model_and_align_get_cpu_cache_text_and_english(whisper: ModuleType, wav: Path,
                                                        tmp_path: Path) -> None:
    timings = align.align_words(wav, "  In 1938,\n a   café pen ", tmp_path / "models")
    load = whisper.load_model.call_args  # type: ignore[attr-defined]
    loaded = inspect.signature(load_model_call).bind(*load.args, **load.kwargs).arguments
    assert loaded == {"name": constants.ALIGN_MODEL_NAME, "device": "cpu",
                      "download_root": str(tmp_path / "models")}
    call = whisper.load_model.return_value.align.call_args  # type: ignore[attr-defined]
    aligned = inspect.signature(align_call).bind(*call.args, **call.kwargs).arguments
    assert (aligned["audio"], aligned["text"], aligned["language"]) == (str(wav), TEXT, "en")
    assert [(t.word, t.start, t.end) for t in timings] == [
        ("In", 0.1, 0.3), ("1938,", 0.3, 1.0), ("a", 1.05, 1.1), ("café", 1.1, 1.4), ("pen", 1.4, 1.8)]


@pytest.mark.parametrize("error", [RuntimeError("cuda?"), ValueError("bad text"), OSError("no ffmpeg")])
def test_aligner_failure_becomes_align_error(whisper: ModuleType, wav: Path, tmp_path: Path,
                                             error: Exception) -> None:
    whisper.load_model.return_value.align.side_effect = error  # type: ignore[attr-defined]
    with pytest.raises(AlignError):
        align.align_words(wav, TEXT, tmp_path)


def test_model_load_failure_becomes_align_error(whisper: ModuleType, wav: Path, tmp_path: Path) -> None:
    whisper.load_model.side_effect = OSError("download failed")  # type: ignore[attr-defined]
    with pytest.raises(AlignError):
        align.align_words(wav, TEXT, tmp_path)


def zero_rate_wav(path: Path) -> Path:
    fmt = struct.pack("<HHIIHH", 1, 1, 0, 0, 2, 16)
    data = b"\x00\x10" * 100
    body = b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(data)) + data
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    return path


@pytest.mark.parametrize("make", [
    lambda p: p.write_bytes(b"not audio at all"),
    lambda p: p.write_bytes(b""),
    zero_rate_wav,
])
def test_unreadable_audio_raises_before_the_model_loads(whisper: ModuleType, tmp_path: Path,
                                                        make: Any) -> None:
    bad = tmp_path / "bad.wav"
    make(bad)
    with pytest.raises(AlignError):
        align.align_words(bad, TEXT, tmp_path)
    assert whisper.load_model.call_count == 0  # type: ignore[attr-defined]


def test_whitespace_piece_in_the_middle_is_skipped() -> None:
    pieces = [(" one", 0.0, 0.4), ("  ", 0.4, 0.5), (" two", 0.5, 0.9), (" three", 0.9, 1.3)]
    timings = align.to_word_timings(["one", "two", "three"], pieces, 2.0)
    assert [(t.word, t.start, t.end) for t in timings] == [
        ("one", 0.0, 0.4), ("two", 0.5, 0.9), ("three", 0.9, 1.3)]


# --- item 10: exact times when the aligner output is already valid --------------------------------

word = st.text(st.characters(categories=["L", "N", "P", "S"]), min_size=1, max_size=8)


@settings(deadline=None, max_examples=200)
@given(words=st.lists(word, min_size=1, max_size=30), data=st.data())
def test_valid_pieces_give_exactly_their_times(words: list[str], data: st.DataObject) -> None:
    """Sorted pieces inside the audio pass through unchanged: first piece's start, last piece's end."""
    duration = 120.0
    joined = "".join(words)
    cuts = sorted(data.draw(st.sets(st.integers(1, max(1, len(joined) - 1)), max_size=len(joined))))
    bounds = [0, *(c for c in cuts if c < len(joined)), len(joined)]
    times = sorted(data.draw(st.lists(st.floats(0, duration), min_size=2 * (len(bounds) - 1),
                                      max_size=2 * (len(bounds) - 1))))
    pieces = [(" " + joined[a:b], times[2 * i], times[2 * i + 1])
              for i, (a, b) in enumerate(zip(bounds, bounds[1:], strict=False))]

    expected, offset = [], 0
    starts = [a for a, _ in zip(bounds, bounds[1:], strict=False)]
    for w in words:
        first = max(i for i, a in enumerate(starts) if a <= offset)
        last = max(i for i, a in enumerate(starts) if a <= offset + len(w) - 1)
        expected.append((w, pieces[first][1], pieces[last][2]))
        offset += len(w)
    assert [(t.word, t.start, t.end) for t in align.to_word_timings(words, pieces, duration)] == expected
