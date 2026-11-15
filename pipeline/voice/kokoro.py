"""Kokoro CPU voice: narration text to a mono voice.wav (task p1-tts-kokoro).

Heavy libraries (`kokoro`, `torch`) are imported inside functions, never at module top, so this
module imports on a machine without them.
"""

from pathlib import Path

from pipeline.constants import VOICE_NAME, VOICE_SPEED


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
    raise NotImplementedError


def check_wav(path: Path) -> float:
    """Return the duration in seconds of a usable voice wav.

    Raises VoiceError if the file is missing, has no samples, is not mono, is not at
    VOICE_SAMPLE_RATE, or is silent (peak amplitude below VOICE_MIN_PEAK, full scale 1.0).
    """
    raise NotImplementedError
