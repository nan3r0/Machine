"""Loudness of the voice track per window, for the host's lip flap (task p3b-lipsync-wiring)."""

import wave
from pathlib import Path

import numpy as np

from pipeline.constants import MOUTH_LEVEL_PERCENTILE, MOUTH_WINDOW_S


def voice_levels(wav: Path) -> list[float]:
    """One level per full MOUTH_WINDOW_S window of `wav`, in order; a last partial window is dropped.

    A level is the window's RMS divided by the MOUTH_LEVEL_PERCENTILE percentile of all window
    RMS values, capped at 1, so 0 is silence and the loud part of the voice is near 1. An all-silent
    file gives all zeros. Reads mono 16-bit PCM with the stdlib `wave` module (numpy allowed);
    raises ValueError for any other sample width or channel count.
    """
    with wave.open(str(wav), "rb") as f:
        if f.getnchannels() != 1 or f.getsampwidth() != 2:
            raise ValueError(f"{wav}: need mono 16-bit PCM")
        window = round(f.getframerate() * MOUTH_WINDOW_S)
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float64)
    count = len(samples) // window
    if count == 0:
        return []
    rms = np.sqrt((samples[: count * window].reshape(count, window) ** 2).mean(axis=1))
    ref = float(np.percentile(rms, MOUTH_LEVEL_PERCENTILE))
    if ref == 0.0:
        return [0.0] * count
    return [float(v) for v in np.minimum(rms / ref, 1.0)]
