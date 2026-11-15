"""Kokoro CPU voice: narration text to a mono voice.wav (task p1-tts-kokoro).

Heavy libraries (`kokoro`, `torch`) are imported inside functions, never at module top, so this
module imports on a machine without them.
"""

import hashlib
import wave
from pathlib import Path

import numpy as np

from pipeline.constants import (
    VOICE_FILE_SHA256,
    VOICE_LANG_CODE,
    VOICE_MIN_PEAK,
    VOICE_NAME,
    VOICE_REPO_ID,
    VOICE_REPO_REVISION,
    VOICE_SAMPLE_RATE,
    VOICE_SPEED,
)


class VoiceError(RuntimeError):
    """Voice synthesis failed. The run must stop; it never continues with a bad wav."""


def synthesize(
    text: str,
    out_path: Path,
    cache_dir: Path,
    voice: str = VOICE_NAME,
    speed: float = VOICE_SPEED,
) -> Path:
    """Speak `text` with Kokoro and write a mono 16-bit wav at VOICE_SAMPLE_RATE to `out_path`.

    Model weights and voices download once into `cache_dir` (used as the Hugging Face cache), so
    the caller can cache that folder between runs. Returns `out_path`.

    Weights are pinned: each of `config.json`, `kokoro-v1_0.pth` and `voices/<voice>.pt` comes from
    `hf_hub_download(VOICE_REPO_ID, <repo path>, revision=VOICE_REPO_REVISION, cache_dir=cache_dir)`,
    and all three sha256 hashes must equal their VOICE_FILE_SHA256 entries before anything from
    kokoro is constructed. Kokoro is then given the local paths, so it never downloads by itself
    without the revision: `KPipeline(lang_code=VOICE_LANG_CODE, model=KModel(config=..., model=...))`,
    called with the text, the voice `.pt` path and `speed`.

    The only heavy imports, made inside this function, are `from huggingface_hub import
    hf_hub_download` and `from kokoro import KModel, KPipeline`; torch is not imported directly
    (Kokoro's audio converts with numpy). Kokoro loads on every call, never cached at module level.
    The non-heavy tests replace both modules in `sys.modules` and rely on this.

    Raises VoiceError for blank text or a voice with no `voices/<voice>.pt` entry in
    VOICE_FILE_SHA256, both checked before kokoro or torch is imported and before any download;
    also for a hash mismatch, any Kokoro failure, or output that
    `check_wav` rejects. On any error no file is left at `out_path`. No retry.
    """
    if not text.strip():
        raise VoiceError("narration text is blank")
    voice_file = f"voices/{voice}.pt"
    repo_files = ["config.json", "kokoro-v1_0.pth", voice_file]
    if voice_file not in VOICE_FILE_SHA256:
        raise VoiceError(f"voice {voice!r} has no pinned hash in VOICE_FILE_SHA256")
    try:
        paths = _download_pinned(repo_files, cache_dir)
        _write_speech(text, out_path, paths, voice_file, speed)
        check_wav(out_path)
    except Exception as err:
        out_path.unlink(missing_ok=True)
        if isinstance(err, VoiceError):
            raise
        raise VoiceError(f"Kokoro voice failed: {err}") from err
    return out_path


def _download_pinned(repo_files: list[str], cache_dir: Path) -> dict[str, str]:
    """Download each repo file at VOICE_REPO_REVISION and check its sha256. Returns local paths."""
    from huggingface_hub import hf_hub_download

    paths = {}
    for repo_path in repo_files:
        local = hf_hub_download(
            VOICE_REPO_ID, repo_path, revision=VOICE_REPO_REVISION, cache_dir=cache_dir
        )
        digest = hashlib.sha256(Path(local).read_bytes()).hexdigest()
        if digest != VOICE_FILE_SHA256[repo_path]:
            raise VoiceError(f"{repo_path} does not match its pinned sha256")
        paths[repo_path] = local
    return paths


def _write_speech(
    text: str, out_path: Path, paths: dict[str, str], voice_file: str, speed: float
) -> None:
    from kokoro import KModel, KPipeline

    model = KModel(config=paths["config.json"], model=paths["kokoro-v1_0.pth"])
    pipeline = KPipeline(lang_code=VOICE_LANG_CODE, model=model)
    chunks = [
        result.audio.numpy()
        for result in pipeline(text, voice=paths[voice_file], speed=speed)
        if result.audio is not None
    ]
    if not chunks:
        raise VoiceError("Kokoro produced no audio")
    samples = np.clip(np.concatenate(chunks), -1.0, 1.0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(VOICE_SAMPLE_RATE)
        wav.writeframes((samples * 32767).astype("<i2").tobytes())


def check_wav(path: Path) -> float:
    """Return the duration in seconds of a usable voice wav.

    Raises VoiceError if the file is missing, has no samples, is not mono, is not at
    VOICE_SAMPLE_RATE, or is silent (peak amplitude below VOICE_MIN_PEAK, full scale 1.0).
    """
    try:
        with wave.open(str(path), "rb") as wav:
            channels, width = wav.getnchannels(), wav.getsampwidth()
            rate, frames = wav.getframerate(), wav.getnframes()
            data = wav.readframes(frames)
    except (OSError, EOFError, wave.Error) as err:
        raise VoiceError(f"cannot read {path}: {err}") from err
    if channels != 1 or rate != VOICE_SAMPLE_RATE or width != 2:
        raise VoiceError(f"{path} is not mono 16-bit at {VOICE_SAMPLE_RATE} Hz")
    if frames == 0:
        raise VoiceError(f"{path} has no samples")
    peak = np.abs(np.frombuffer(data, dtype="<i2").astype(np.float64)).max() / 32768
    if peak < VOICE_MIN_PEAK:
        raise VoiceError(f"{path} is silent (peak {peak:.4f})")
    return frames / rate
