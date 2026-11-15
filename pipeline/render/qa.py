"""Automated QA gate for a rendered video (task p1-qa).

QA problems are data, not exceptions: every check that fails becomes a QAFailure in the report.
"""

from dataclasses import dataclass
from pathlib import Path

from pipeline.schema import QAReport, WordTiming


@dataclass(frozen=True)
class VideoStats:
    """What `measure` reads from a rendered video and its voice track."""

    duration_s: float
    voice_duration_s: float
    width: int
    height: int
    fps: float
    file_bytes: int
    longest_silence_s: float


def duration_range_for(word_count: int) -> tuple[float, float]:
    """RETENTION_SECONDS for scripts of up to RETENTION_WORDS max words, else TIKTOK_SECONDS."""
    raise NotImplementedError


def evaluate(stats: VideoStats, timings: list[WordTiming], script_words: list[str]) -> QAReport:
    """Run every check on measured values and return the report. Pure, never raises.

    Checks, named as in QAFailure.check, all thresholds from constants.py:
    - duration: inside `duration_range_for(len(script_words))`, and within
      DURATION_MATCH_TOLERANCE_S of the voice duration
    - silence: longest silence no longer than MAX_SILENCE_S
    - alignment: one timing per script word with the same word in the same order; starts and
      ends never decrease; every end within ALIGNMENT_SLACK_S of the voice duration or earlier
    - resolution: exactly WIDTH x HEIGHT
    - fps: FPS
    - file_size: between MIN_FILE_BYTES and MAX_FILE_BYTES

    `measured` holds every VideoStats field by name.
    """
    raise NotImplementedError


def measure(video: Path, voice: Path) -> VideoStats:
    """Probe `video` with ffprobe and run silencedetect (SILENCE_NOISE_DB) on its audio.

    Raises RuntimeError if the files cannot be read; `run_qa` turns that into a failed report.
    """
    raise NotImplementedError


def run_qa(video: Path, voice: Path, timings: list[WordTiming], script_words: list[str]) -> QAReport:
    """Measure and evaluate `video`. Never raises on a bad video: an unreadable file gives a
    failed report with a "duration" failure whose reason says the file could not be read."""
    raise NotImplementedError
