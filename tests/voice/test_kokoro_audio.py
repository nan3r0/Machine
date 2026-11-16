"""Kokoro's audio reaching voice.wav, and check_wav edge cases (task p1-qa-tests, QA lead items 6, 12).

Kokoro and huggingface_hub are faked in sys.modules, so these run without torch. The fake pipeline
yields real numpy audio, which the heavy tests alone could never check sample by sample.
"""

import array
import hashlib
import inspect
import math
import struct
import sys
import wave
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

from pipeline import constants
from pipeline.voice import kokoro
from pipeline.voice.kokoro import VoiceError
from tests.wavs import write_wav

VOICE_FILE = f"voices/{constants.VOICE_NAME}.pt"


def kpipeline_call(text: str, voice: str | None = None, speed: float = 1.0, split_pattern: str | None = None,
                   model: object = None) -> None:
    """The signature of kokoro.KPipeline.__call__, to read a recorded call however it was made."""


def chunk(values: list[float] | None) -> SimpleNamespace:
    audio = None if values is None else SimpleNamespace(numpy=lambda: np.array(values, dtype=np.float32))
    return SimpleNamespace(audio=audio)


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    """huggingface_hub writes small files with matching pinned hashes; KPipeline yields `chunks`."""
    state = SimpleNamespace(chunks=[], cache=tmp_path / "cache", module=ModuleType("kokoro"))

    def hf_hub_download(repo_id: str, filename: str, **kwargs: Any) -> str:
        path = Path(kwargs["cache_dir"]) / "fake" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(filename.encode())
        return str(path)

    hub = ModuleType("huggingface_hub")
    hub.hf_hub_download = hf_hub_download  # type: ignore[attr-defined]
    state.module.KModel = MagicMock(name="KModel")
    state.module.KPipeline = MagicMock(name="KPipeline")
    state.module.KPipeline.return_value.side_effect = lambda *a, **k: iter(state.chunks)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setitem(sys.modules, "kokoro", state.module)
    for repo_path in constants.VOICE_FILE_SHA256:
        digest = hashlib.sha256(repo_path.encode()).hexdigest()
        monkeypatch.setitem(constants.VOICE_FILE_SHA256, repo_path, digest)
    return state


def local(state: SimpleNamespace, repo_path: str) -> str:
    return str(state.cache / "fake" / repo_path)


def read_samples(path: Path) -> tuple[Any, list[int]]:
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        data = wav.readframes(params.nframes)
    return params, list(struct.unpack(f"<{len(data) // 2}h", data))


def test_kokoro_gets_the_pinned_files_language_voice_and_speed(tmp_path: Path, fake: SimpleNamespace) -> None:
    fake.chunks = [chunk([0.5, -0.5])]
    kokoro.synthesize("Hello there.", tmp_path / "voice.wav", fake.cache)
    fake.module.KModel.assert_called_once_with(config=local(fake, "config.json"),
                                               model=local(fake, "kokoro-v1_0.pth"))
    fake.module.KPipeline.assert_called_once_with(lang_code=constants.VOICE_LANG_CODE,
                                                  model=fake.module.KModel.return_value)
    call = fake.module.KPipeline.return_value.call_args
    bound = inspect.signature(kpipeline_call).bind(*call.args, **call.kwargs)
    assert bound.arguments["text"] == "Hello there."
    assert bound.arguments["voice"] == local(fake, VOICE_FILE)
    assert bound.arguments["speed"] == constants.VOICE_SPEED


def test_a_custom_speed_reaches_kokoro(tmp_path: Path, fake: SimpleNamespace) -> None:
    fake.chunks = [chunk([0.5, -0.5])]
    kokoro.synthesize("Hello there.", tmp_path / "voice.wav", fake.cache, speed=1.25)
    call = fake.module.KPipeline.return_value.call_args
    assert inspect.signature(kpipeline_call).bind(*call.args, **call.kwargs).arguments["speed"] == 1.25


def test_audio_is_written_as_mono_little_endian_16_bit(tmp_path: Path, fake: SimpleNamespace) -> None:
    """Chunks in order, the empty one skipped, values scaled to 16 bits and clipped at full scale."""
    fake.chunks = [chunk([0.5, -0.25]), chunk(None), chunk([1.5, -1.5, 0.0])]
    out = kokoro.synthesize("Hello there.", tmp_path / "nested" / "voice.wav", fake.cache)
    params, samples = read_samples(out)
    assert (params.nchannels, params.sampwidth, params.framerate) == (1, 2, constants.VOICE_SAMPLE_RATE)
    assert len(samples) == 5
    for got, want in zip(samples, [16383.5, -8191.75, 32767, -32767, 0], strict=True):
        assert abs(got - want) <= 1
    assert samples[2:4] == [32767, -32767]


def test_no_audio_from_kokoro_raises_and_leaves_no_file(tmp_path: Path, fake: SimpleNamespace) -> None:
    fake.chunks = [chunk(None), chunk(None)]
    out = tmp_path / "voice.wav"
    with pytest.raises(VoiceError):
        kokoro.synthesize("Hello there.", out, fake.cache)
    assert not out.exists()


# --- item 12: check_wav ---------------------------------------------------------------------------

def write_raw_wav(path: Path, width: int, frames: bytes) -> Path:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(width)
        wav.setframerate(constants.VOICE_SAMPLE_RATE)
        wav.writeframes(frames)
    return path


@pytest.mark.parametrize("width", [1, 3, 4])
def test_check_wav_rejects_other_sample_widths(tmp_path: Path, width: int) -> None:
    loud = bytes([0x40] * width * constants.VOICE_SAMPLE_RATE)
    with pytest.raises(VoiceError):
        kokoro.check_wav(write_raw_wav(tmp_path / "w.wav", width, loud))


def test_check_wav_rejects_zero_byte_and_truncated_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    good = write_wav(tmp_path / "good.wav", 1.0, constants.VOICE_SAMPLE_RATE)
    truncated = tmp_path / "truncated.wav"
    truncated.write_bytes(good.read_bytes()[:20])
    for path in (empty, truncated):
        with pytest.raises(VoiceError):
            kokoro.check_wav(path)


def peak_wav(path: Path, peak: int) -> Path:
    return write_raw_wav(path, 2, array.array("h", [0, peak, -peak // 2] * 1000).tobytes())


def test_peak_just_above_the_floor_passes_and_just_below_fails(tmp_path: Path) -> None:
    floor = constants.VOICE_MIN_PEAK * 32768
    assert kokoro.check_wav(peak_wav(tmp_path / "above.wav", int(floor) + 1)) > 0
    with pytest.raises(VoiceError):
        kokoro.check_wav(peak_wav(tmp_path / "below.wav", math.ceil(floor) - 1))
