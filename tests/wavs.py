"""Write small test wavs with the standard library only."""

import array
import math
import wave
from pathlib import Path


def write_wav(path: Path, seconds: float, rate: int, channels: int = 1, amplitude: float = 0.5) -> Path:
    """A 440 Hz tone (or silence for amplitude 0) as 16-bit PCM."""
    frames = int(seconds * rate)
    samples = array.array("h", (
        int(amplitude * 32767 * math.sin(2 * math.pi * 440 * (i // channels) / rate))
        for i in range(frames * channels)
    ))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(samples.tobytes())
    return path
