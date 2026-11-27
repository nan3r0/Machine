"""Loudness of the voice track per window, for the host's lip flap (task p3b-lipsync-wiring)."""

from pathlib import Path


def voice_levels(wav: Path) -> list[float]:
    """One level per full MOUTH_WINDOW_S window of `wav`, in order; a last partial window is dropped.

    A level is the window's RMS divided by the MOUTH_LEVEL_PERCENTILE percentile of all window
    RMS values, capped at 1, so 0 is silence and the loud part of the voice is near 1. An all-silent
    file gives all zeros. Reads mono 16-bit PCM with the stdlib `wave` module (numpy allowed);
    raises ValueError for any other sample width or channel count.
    """
    raise NotImplementedError("p3b-lipsync-wiring")
