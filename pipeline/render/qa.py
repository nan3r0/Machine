"""Automated QA gate for a rendered video (task p1-qa).

QA problems are data, not exceptions: every check that fails becomes a QAFailure in the report.
"""

import dataclasses
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pipeline import constants
from pipeline.schema import QAFailure, QAReport, WordTiming

_SILENCE_START = re.compile(r"silence_start: (-?[\d.]+)")
_SILENCE_DURATION = re.compile(r"silence_duration: ([\d.]+)")

Check = Literal["duration", "silence", "alignment", "resolution", "fps", "file_size"]


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


def _duration_failure(stats: VideoStats) -> str | None:
    low, high = constants.TIKTOK_SECONDS
    if not low <= stats.duration_s <= high:
        return f"duration {stats.duration_s:.1f}s outside {low:g}-{high:g}s"
    gap = abs(stats.duration_s - stats.voice_duration_s)
    if gap > constants.DURATION_MATCH_TOLERANCE_S:
        return (f"video {stats.duration_s:.2f}s and voice {stats.voice_duration_s:.2f}s differ by "
                f"{gap:.2f}s, limit {constants.DURATION_MATCH_TOLERANCE_S}s")
    return None


def _alignment_failure(timings: list[WordTiming], script_words: list[str], voice_s: float) -> str | None:
    if len(timings) != len(script_words):
        return f"{len(timings)} word timings for {len(script_words)} script words"
    for index, (timing, word) in enumerate(zip(timings, script_words, strict=True)):
        if timing.word != word:
            return f"timing {index} is {timing.word!r}, script word is {word!r}"
        if index and (timing.start < timings[index - 1].start or timing.end < timings[index - 1].end):
            return f"timing {index} ({word!r}) goes backwards"
        if timing.end > voice_s + constants.ALIGNMENT_SLACK_S:
            return f"timing {index} ({word!r}) ends at {timing.end:.2f}s, after the {voice_s:.2f}s voice"
    return None


def evaluate(stats: VideoStats, timings: list[WordTiming], script_words: list[str]) -> QAReport:
    """Run every check on measured values and return the report. Pure, never raises.

    Checks, named as in QAFailure.check, all thresholds from constants.py:
    - duration: inside TIKTOK_SECONDS whatever the word count (every video is over a minute), and within
      DURATION_MATCH_TOLERANCE_S of the voice duration
    - silence: longest silence no longer than MAX_SILENCE_S
    - alignment: one timing per script word with the same word in the same order; starts and
      ends never decrease; every end within ALIGNMENT_SLACK_S of the voice duration or earlier
    - resolution: exactly WIDTH x HEIGHT
    - fps: FPS
    - file_size: between MIN_FILE_BYTES and MAX_FILE_BYTES

    `measured` holds every VideoStats field by name.
    """
    reasons: list[tuple[Check, str | None]] = [
        ("duration", _duration_failure(stats)),
        ("silence", None if stats.longest_silence_s <= constants.MAX_SILENCE_S else
         f"silence of {stats.longest_silence_s:.2f}s, limit {constants.MAX_SILENCE_S}s"),
        ("alignment", _alignment_failure(timings, script_words, stats.voice_duration_s)),
        ("resolution", None if (stats.width, stats.height) == (constants.WIDTH, constants.HEIGHT) else
         f"{stats.width}x{stats.height}, expected {constants.WIDTH}x{constants.HEIGHT}"),
        ("fps", None if abs(stats.fps - constants.FPS) <= constants.QA_FPS_TOLERANCE else
         f"{stats.fps:g} fps, expected {constants.FPS}"),
        ("file_size", None if constants.MIN_FILE_BYTES <= stats.file_bytes <= constants.MAX_FILE_BYTES else
         f"{stats.file_bytes} bytes, expected {constants.MIN_FILE_BYTES}-{constants.MAX_FILE_BYTES}"),
    ]
    failures = [QAFailure(check=check, reason=reason) for check, reason in reasons if reason]
    return QAReport(passed=not failures, failures=failures, measured=dataclasses.asdict(stats))


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a tool with an argument list. Raises RuntimeError with the stderr tail on any failure."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=constants.QA_TOOL_TIMEOUT_S, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"could not run {args[0]}: {exc}") from exc
    if result.returncode != 0:
        tail = "\n".join(result.stderr.splitlines()[-constants.QA_STDERR_TAIL_LINES:])
        raise RuntimeError(f"{args[0]} exited {result.returncode} on {args[-1]}:\n{tail}")
    return result


def _probe(path: Path, *entries: str) -> dict[str, Any]:
    """ffprobe `path` and return the requested format and first video stream fields."""
    result = _run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-of", "json",
                   "-show_entries", ":".join(entries), str(path)])
    try:
        return json.loads(result.stdout)  # type: ignore[no-any-return]
    except ValueError as exc:
        raise RuntimeError(f"ffprobe gave unreadable output for {path}") from exc


def _fps(rate: str) -> float:
    numerator, _, denominator = rate.partition("/")
    return float(numerator) / float(denominator or 1)


def _longest_silence(video: Path, duration_s: float) -> float:
    """Longest run reported by silencedetect; a run still open at the end counts up to `duration_s`."""
    filter_ = f"silencedetect=noise={constants.SILENCE_NOISE_DB}dB:d={constants.MAX_SILENCE_S}"
    log = _run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "info", "-i", str(video),
                "-vn", "-af", filter_, "-f", "null", "-"]).stderr
    longest, open_since = 0.0, None
    for line in log.splitlines():
        if start := _SILENCE_START.search(line):
            open_since = float(start.group(1))
        elif duration := _SILENCE_DURATION.search(line):
            longest, open_since = max(longest, float(duration.group(1))), None
    if open_since is not None:
        longest = max(longest, duration_s - open_since)
    return longest


def measure(video: Path, voice: Path) -> VideoStats:
    """Probe `video` with ffprobe and run silencedetect (SILENCE_NOISE_DB) on its audio.

    Raises RuntimeError if the files cannot be read; `run_qa` turns that into a failed report.
    """
    try:
        info = _probe(video, "format=duration", "stream=width,height,r_frame_rate")
        voice_info = _probe(voice, "format=duration")
        stream = info["streams"][0]
        duration_s = float(info["format"]["duration"])
        return VideoStats(
            duration_s=duration_s,
            voice_duration_s=float(voice_info["format"]["duration"]),
            width=int(stream["width"]),
            height=int(stream["height"]),
            fps=_fps(stream["r_frame_rate"]),
            file_bytes=video.stat().st_size,
            longest_silence_s=_longest_silence(video, duration_s),
        )
    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, OSError) as exc:
        raise RuntimeError(f"could not read measurements from {video}: {exc!r}") from exc


def run_qa(video: Path, voice: Path, timings: list[WordTiming], script_words: list[str]) -> QAReport:
    """Measure and evaluate `video`. Never raises on a bad video: an unreadable file gives a
    failed report with a "duration" failure whose reason says the file could not be read."""
    try:
        stats = measure(video, voice)
    except RuntimeError as exc:
        return QAReport(passed=False, failures=[QAFailure(check="duration", reason=f"unreadable: {exc}")],
                        measured={})
    return evaluate(stats, timings, script_words)
