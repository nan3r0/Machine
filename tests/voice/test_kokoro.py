"""R2: Kokoro voice (task p1-tts-kokoro)."""

import hashlib
import os
import subprocess
import sys
import wave
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from pipeline import constants, render_one
from pipeline.voice import kokoro
from pipeline.voice.kokoro import VoiceError
from tests.wavs import write_wav

ROOT = Path(__file__).resolve().parent.parent.parent
TEXT = (ROOT / "tests" / "fixtures" / "align_sample.txt").read_text(
    encoding="utf-8").strip()


@pytest.fixture(scope="module")
def cache_dir() -> Path:
    """The folder CI caches between runs, so heavy tests do not download the weights each time."""
    return ROOT / render_one.DEFAULT_CACHE_DIR


def expected_seconds(text: str) -> float:
    return len(text.split()) / constants.SPEECH_WPM * 60


DEFAULT_VOICE_FILES = {"config.json", "kokoro-v1_0.pth", f"voices/{constants.VOICE_NAME}.pt"}


def fake_bytes(repo_path: str) -> bytes:
    return f"fake {repo_path}".encode()


@pytest.fixture
def fake_kokoro(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Replace huggingface_hub and kokoro with fakes, so synthesize runs without heavy packages.

    The fake download writes small files into cache_dir, and the pinned hashes are set to match them.
    A repo path added to `tampered` gets other bytes, so its hash no longer matches.
    """
    fake = SimpleNamespace(downloads=[], tampered=set(), module=ModuleType("kokoro"))

    def hf_hub_download(repo_id: str, filename: str, **kwargs: Any) -> str:
        fake.downloads.append({"repo_id": repo_id, "filename": filename, **kwargs})
        path = Path(kwargs["cache_dir"]) / "fake" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"tampered" if filename in fake.tampered else fake_bytes(filename))
        return str(path)

    hub = ModuleType("huggingface_hub")
    hub.hf_hub_download = hf_hub_download  # type: ignore[attr-defined]
    fake.module.KModel = MagicMock(name="KModel")
    fake.module.KPipeline = MagicMock(name="KPipeline")
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setitem(sys.modules, "kokoro", fake.module)
    for repo_path in constants.VOICE_FILE_SHA256:
        digest = hashlib.sha256(fake_bytes(repo_path)).hexdigest()
        monkeypatch.setitem(constants.VOICE_FILE_SHA256, repo_path, digest)
    return fake


def assert_pinned_downloads(downloads: list[dict[str, Any]], cache: Path) -> None:
    assert {d["filename"] for d in downloads} == DEFAULT_VOICE_FILES
    for d in downloads:
        assert d["repo_id"] == constants.VOICE_REPO_ID
        assert d.get("revision") == constants.VOICE_REPO_REVISION
        assert Path(d.get("cache_dir", "")) == cache


@pytest.mark.heavy
def test_acceptance(tmp_path: Path, cache_dir: Path) -> None:
    """R2.1 and R2.2: a mono wav at the right rate, length fits ~160 wpm, weights in cache_dir."""
    out = kokoro.synthesize(TEXT, tmp_path / "voice.wav", cache_dir)
    assert out == tmp_path / "voice.wav"
    with wave.open(str(out), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == constants.VOICE_SAMPLE_RATE
    duration = kokoro.check_wav(out)
    expected = expected_seconds(TEXT)
    assert abs(duration - expected) <= expected * constants.SPEECH_RATE_TOLERANCE
    repo_folder = "models--" + constants.VOICE_REPO_ID.replace("/", "--")
    snapshot = cache_dir / repo_folder / "snapshots" / constants.VOICE_REPO_REVISION
    assert snapshot.is_dir(), "weights were not downloaded at VOICE_REPO_REVISION into cache_dir"


@pytest.mark.heavy
def test_second_run_uses_cache_offline(tmp_path: Path, cache_dir: Path) -> None:
    """R2.2: once cached, synthesis needs no network.

    The offline run is a fresh process with every socket connection refused before anything is
    imported, so a download by any library (Hugging Face, spaCy, misaki) fails the test.
    """
    kokoro.synthesize("Warm the cache.", tmp_path / "warm.wav", cache_dir)
    out = tmp_path / "offline.wav"
    code = """
import socket
import sys
from pathlib import Path

def refuse(*args, **kwargs):
    raise OSError("network is blocked in the offline test")

socket.socket.connect = refuse
socket.socket.connect_ex = refuse
socket.create_connection = refuse

from pipeline.voice import kokoro

kokoro.synthesize("Cached voice works offline.", Path(sys.argv[1]), Path(sys.argv[2]))
"""
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    result = subprocess.run([sys.executable, "-c", code, str(out), str(cache_dir)], cwd=ROOT, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-2000:]
    assert kokoro.check_wav(out) > 0


def test_unpinned_voice_fails_before_any_download(tmp_path: Path) -> None:
    """R2.3: a voice without a pinned hash raises, leaves no file and downloads nothing."""
    out = tmp_path / "voice.wav"
    cache = tmp_path / "cache"
    with pytest.raises(VoiceError):
        kokoro.synthesize(TEXT, out, cache, voice="zz_no_such_voice")
    assert not out.exists()
    assert not cache.exists() or not any(cache.iterdir())


@pytest.mark.parametrize("tampered", sorted(DEFAULT_VOICE_FILES))
def test_tampered_weights_fail_before_kokoro_loads(tmp_path: Path, fake_kokoro: SimpleNamespace,
                                                   tampered: str) -> None:
    """R2.3: one pinned file with the wrong bytes raises before any Kokoro class is constructed."""
    fake_kokoro.tampered.add(tampered)
    out = tmp_path / "voice.wav"
    with pytest.raises(VoiceError):
        kokoro.synthesize(TEXT, out, tmp_path / "cache")
    assert not out.exists()
    assert tampered in {d["filename"] for d in fake_kokoro.downloads}, "the tampered file was never fetched"
    assert fake_kokoro.module.KModel.call_count == 0
    assert fake_kokoro.module.KPipeline.call_count == 0


def test_kokoro_failure_raises_voice_error(tmp_path: Path, fake_kokoro: SimpleNamespace) -> None:
    """R2.3: an error inside Kokoro's synthesis becomes VoiceError and leaves no file."""
    pipeline = fake_kokoro.module.KPipeline.return_value
    pipeline.side_effect = RuntimeError("Kokoro failed mid-synthesis")
    out = tmp_path / "voice.wav"
    cache = tmp_path / "cache"
    with pytest.raises(VoiceError):
        kokoro.synthesize(TEXT, out, cache)
    assert pipeline.call_count == 1, "the error must come from Kokoro's synthesis, not before it"
    assert not out.exists()
    assert_pinned_downloads(fake_kokoro.downloads, cache)


@pytest.mark.heavy
def test_unicode_and_digits_are_spoken(tmp_path: Path, cache_dir: Path) -> None:
    text = "In 1938, a café pen cost $10, about 25% of a week's pay."
    duration = kokoro.check_wav(kokoro.synthesize(text, tmp_path / "v.wav", cache_dir))
    assert duration > 1.0


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_blank_text_raises_before_loading_kokoro(tmp_path: Path, text: str) -> None:
    """R2.3: blank text is rejected up front, without importing or running Kokoro."""
    out = tmp_path / "voice.wav"
    with pytest.raises(VoiceError):
        kokoro.synthesize(text, out, tmp_path / "cache")
    assert not out.exists()


def test_check_wav_returns_duration(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "ok.wav", 2.0, constants.VOICE_SAMPLE_RATE)
    assert kokoro.check_wav(path) == pytest.approx(2.0, abs=0.01)


def test_check_wav_rejects_silence(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "silent.wav", 2.0, constants.VOICE_SAMPLE_RATE, amplitude=0.0)
    with pytest.raises(VoiceError):
        kokoro.check_wav(path)


def test_check_wav_rejects_near_silence(tmp_path: Path) -> None:
    quiet = constants.VOICE_MIN_PEAK / 2
    path = write_wav(tmp_path / "quiet.wav", 2.0, constants.VOICE_SAMPLE_RATE, amplitude=quiet)
    with pytest.raises(VoiceError):
        kokoro.check_wav(path)


def test_check_wav_rejects_empty(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "empty.wav", 0.0, constants.VOICE_SAMPLE_RATE)
    with pytest.raises(VoiceError):
        kokoro.check_wav(path)


def test_check_wav_rejects_stereo(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "stereo.wav", 1.0, constants.VOICE_SAMPLE_RATE, channels=2)
    with pytest.raises(VoiceError):
        kokoro.check_wav(path)


def test_check_wav_rejects_wrong_rate(tmp_path: Path) -> None:
    path = write_wav(tmp_path / "rate.wav", 1.0, 16_000)
    with pytest.raises(VoiceError):
        kokoro.check_wav(path)


def test_check_wav_rejects_missing_and_garbage(tmp_path: Path) -> None:
    with pytest.raises(VoiceError):
        kokoro.check_wav(tmp_path / "missing.wav")
    garbage = tmp_path / "garbage.wav"
    garbage.write_bytes(os.urandom(64))
    with pytest.raises(VoiceError):
        kokoro.check_wav(garbage)
