"""voice_levels: loudness per MOUTH_WINDOW_S of voice.wav (task p3b-lipsync-wiring)."""

import math
import wave
from pathlib import Path

import pytest

from pipeline import constants as c
from pipeline.voice.levels import voice_levels
from tests.wavs import write_wav

RATE = c.VOICE_SAMPLE_RATE


def tone_wav(path: Path, parts: list[tuple[float, float]]) -> Path:
    """Mono 16-bit PCM: a 220 Hz tone at each (seconds, amplitude) part in turn."""
    frames = bytearray()
    for seconds, amplitude in parts:
        for i in range(round(seconds * RATE)):
            sample = round(amplitude * 32767 * math.sin(2 * math.pi * 220 * i / RATE))
            frames += sample.to_bytes(2, "little", signed=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(bytes(frames))
    return path


def per_window(seconds: float) -> int:
    return round(seconds / c.MOUTH_WINDOW_S)


def test_levels_follow_the_loudness(tmp_path: Path) -> None:
    parts = [(0.4, 0.0), (0.8, 0.5), (0.4, 0.1), (0.2, 0.0)]
    levels = voice_levels(tone_wav(tmp_path / "v.wav", parts))
    assert len(levels) == per_window(sum(s for s, _ in parts))
    assert all(0.0 <= v <= 1.0 for v in levels)
    silent, loud, quiet, tail = (per_window(s) for s, _ in parts)
    assert levels[:silent] == [0.0] * silent and levels[-tail:] == [0.0] * tail
    assert levels[silent:silent + loud] == pytest.approx([1.0] * loud, abs=0.02)
    assert levels[silent + loud:silent + loud + quiet] == pytest.approx([0.2] * quiet, abs=0.03)


def test_partial_last_window_is_dropped(tmp_path: Path) -> None:
    levels = voice_levels(tone_wav(tmp_path / "v.wav", [(0.4 + c.MOUTH_WINDOW_S / 2, 0.5)]))
    assert len(levels) == per_window(0.4)


def test_silence_gives_zeros(tmp_path: Path) -> None:
    assert voice_levels(write_wav(tmp_path / "v.wav", 1.0, RATE, amplitude=0.0)) == [0.0] * per_window(1.0)


def test_stereo_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        voice_levels(write_wav(tmp_path / "v.wav", 0.4, RATE, channels=2))


def test_acceptance(tmp_path: Path) -> None:
    test_levels_follow_the_loudness(tmp_path)
    test_silence_gives_zeros(tmp_path)
