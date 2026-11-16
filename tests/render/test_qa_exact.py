"""QA boundaries and the measure step with ffprobe and FFmpeg faked.

Task p1-qa-tests, QA lead items 7 and 8. Boundaries come from pipeline.constants; float limits are
tested just inside and just outside, since the exact limit is at the mercy of float rounding.
"""

import dataclasses
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pipeline import constants
from pipeline.render import qa
from pipeline.render.qa import VideoStats
from pipeline.schema import WordTiming

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ffmpeg"
SILENCE_LOG = (FIXTURES / "silencedetect.log").read_text(encoding="utf-8")
PROBE_VIDEO = (FIXTURES / "ffprobe_video.json").read_text(encoding="utf-8")
PROBE_VOICE = (FIXTURES / "ffprobe_voice.json").read_text(encoding="utf-8")
# Expected values read from the fixtures here, independently of qa.py, so a swap to a fresh capture
# needs no edits below.
VIDEO_INFO = json.loads(PROBE_VIDEO)
STREAM = VIDEO_INFO["streams"][0]
VIDEO_S = float(VIDEO_INFO["format"]["duration"])
VOICE_S_PROBED = float(json.loads(PROBE_VOICE)["format"]["duration"])
RUNS = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", SILENCE_LOG)]
LONGEST_RUN = max(RUNS)


def probe_video_with(**stream: str) -> str:
    return json.dumps({**VIDEO_INFO, "streams": [{**STREAM, **stream}]})

RETENTION_MAX_WORDS = constants.RETENTION_WORDS[1]
TIKTOK_MIN_WORDS = RETENTION_MAX_WORDS + 1
TOL = constants.DURATION_MATCH_TOLERANCE_S
SLACK = constants.ALIGNMENT_SLACK_S


def words(count: int) -> list[str]:
    return [f"w{i}" for i in range(count)]


def even_timings(script: list[str], total: float) -> list[WordTiming]:
    step = total / len(script)
    return [WordTiming(word=w, start=i * step, end=(i + 1) * step) for i, w in enumerate(script)]


def stats(duration: float, voice: float | None = None, **changes: Any) -> VideoStats:
    good = VideoStats(duration_s=duration, voice_duration_s=duration if voice is None else voice,
                      width=constants.WIDTH, height=constants.HEIGHT, fps=float(constants.FPS),
                      file_bytes=5_000_000, longest_silence_s=0.5)
    return dataclasses.replace(good, **changes)


def failed(video: VideoStats, word_count: int, timings: list[WordTiming] | None = None) -> set[str]:
    script = words(word_count)
    shortest = min(video.duration_s, video.voice_duration_s)
    t = even_timings(script, shortest - 1) if timings is None else timings
    report = qa.evaluate(video, t, script)
    assert report.passed == (not report.failures)
    return {f.check for f in report.failures}


# --- item 7: boundaries and direction -------------------------------------------------------------

RANGES = [(RETENTION_MAX_WORDS, constants.RETENTION_SECONDS), (TIKTOK_MIN_WORDS, constants.TIKTOK_SECONDS)]


@pytest.mark.parametrize(("count", "bounds"), RANGES)
def test_duration_range_edges_pass(count: int, bounds: tuple[float, float]) -> None:
    low, high = bounds
    assert failed(stats(low), count) == set()
    assert failed(stats(high), count) == set()


@pytest.mark.parametrize(("count", "bounds"), RANGES)
def test_duration_just_outside_the_range_fails(count: int, bounds: tuple[float, float]) -> None:
    low, high = bounds
    assert failed(stats(low - 0.1), count) == {"duration"}
    assert failed(stats(high + 0.1), count) == {"duration"}


def test_word_count_switches_the_range() -> None:
    """The live 65 s format: one word past RETENTION_WORDS max means TIKTOK_SECONDS applies."""
    assert failed(stats(constants.TIKTOK_SECONDS[0]), RETENTION_MAX_WORDS) == {"duration"}
    assert failed(stats(constants.RETENTION_SECONDS[1]), TIKTOK_MIN_WORDS) == {"duration"}
    assert failed(stats(65.0), TIKTOK_MIN_WORDS) == set()


VOICE_S = sum(constants.TIKTOK_SECONDS) / 2


@pytest.mark.parametrize("offset", [TOL - 0.01, -(TOL - 0.01)])
def test_video_close_to_the_voice_passes(offset: float) -> None:
    assert failed(stats(VOICE_S + offset, VOICE_S), TIKTOK_MIN_WORDS) == set()


@pytest.mark.parametrize("offset", [TOL + 0.01, -(TOL + 0.01), -0.5])
def test_video_longer_or_shorter_than_the_voice_fails(offset: float) -> None:
    """A video shorter than its voice cuts the narration off; that fails as surely as a longer one."""
    assert failed(stats(VOICE_S + offset, VOICE_S), TIKTOK_MIN_WORDS) == {"duration"}


@pytest.mark.parametrize("fps", [constants.FPS + 0.009, constants.FPS - 0.009])
def test_fps_within_rounding_passes(fps: float) -> None:
    assert failed(stats(VOICE_S, fps=fps), TIKTOK_MIN_WORDS) == set()


@pytest.mark.parametrize("fps", [constants.FPS + 0.011, constants.FPS - 0.011])
def test_fps_off_by_more_than_rounding_fails(fps: float) -> None:
    assert failed(stats(VOICE_S, fps=fps), TIKTOK_MIN_WORDS) == {"fps"}


@pytest.mark.parametrize("size", [constants.MIN_FILE_BYTES, constants.MAX_FILE_BYTES])
def test_file_size_limits_are_inclusive(size: int) -> None:
    assert failed(stats(VOICE_S, file_bytes=size), TIKTOK_MIN_WORDS) == set()


def test_end_going_backwards_alone_fails_alignment() -> None:
    script = words(TIKTOK_MIN_WORDS)
    t = even_timings(script, VOICE_S - 1)
    before = t[10]
    t[11] = WordTiming(word=script[11], start=(before.start + before.end) / 2, end=before.end - 0.01)
    assert failed(stats(VOICE_S), TIKTOK_MIN_WORDS, t) == {"alignment"}


def last_word_ending_at(end: float) -> list[WordTiming]:
    t = even_timings(words(TIKTOK_MIN_WORDS), VOICE_S - 1)
    t[-1] = t[-1].model_copy(update={"end": end})
    return t


def test_end_within_slack_after_the_voice_passes() -> None:
    assert failed(stats(VOICE_S), TIKTOK_MIN_WORDS, last_word_ending_at(VOICE_S + SLACK / 2)) == set()


def test_end_past_the_slack_fails() -> None:
    t = last_word_ending_at(VOICE_S + SLACK + 0.01)
    assert failed(stats(VOICE_S), TIKTOK_MIN_WORDS, t) == {"alignment"}


# --- item 8: measure with the tools faked ---------------------------------------------------------

class FakeTools:
    """ffprobe returns the fixture JSON for the video or the voice; FFmpeg prints the silencedetect log."""

    def __init__(self, video: Path) -> None:
        self.video = video
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.probe_video = PROBE_VIDEO
        self.silence_log = SILENCE_LOG
        self.error: Exception | None = None
        self.fail_with: str | None = None

    def run(self, args: list[str], **kwargs: Any) -> SimpleNamespace:
        self.calls.append((list(args), kwargs))
        if self.error:
            raise self.error
        if self.fail_with is not None:
            return SimpleNamespace(args=args, returncode=1, stdout="", stderr=self.fail_with)
        if args[0] == "ffprobe":
            stdout = self.probe_video if args[-1] == str(self.video) else PROBE_VOICE
            return SimpleNamespace(args=args, returncode=0, stdout=stdout, stderr="")
        return SimpleNamespace(args=args, returncode=0, stdout="", stderr=self.silence_log)


@pytest.fixture
def files(tmp_path: Path) -> SimpleNamespace:
    video = tmp_path / "final.mp4"
    video.write_bytes(b"x" * 1234)
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"RIFF")
    return SimpleNamespace(video=video, voice=voice)


@pytest.fixture
def tools(monkeypatch: pytest.MonkeyPatch, files: SimpleNamespace) -> FakeTools:
    fake = FakeTools(files.video)
    monkeypatch.setattr(subprocess, "run", fake.run)
    return fake


def test_measure_reads_probe_and_silence_output(files: SimpleNamespace, tools: FakeTools) -> None:
    result = qa.measure(files.video, files.voice)
    assert result == VideoStats(duration_s=VIDEO_S, voice_duration_s=VOICE_S_PROBED,
                                width=STREAM["width"], height=STREAM["height"], fps=float(constants.FPS),
                                file_bytes=1234, longest_silence_s=LONGEST_RUN)
    silence_args = next(args for args, _ in tools.calls if args[0] == "ffmpeg")
    assert silence_args[silence_args.index("-af") + 1] == (
        f"silencedetect=noise={constants.SILENCE_NOISE_DB}dB:d={constants.MAX_SILENCE_S}")
    assert str(files.video) in silence_args
    for args, kwargs in tools.calls:
        assert 0 < kwargs["timeout"] < float("inf"), f"{args[0]} must not hang the run"
        assert not kwargs.get("shell")


def test_silence_still_open_at_the_end_counts_to_the_end(files: SimpleNamespace, tools: FakeTools) -> None:
    open_run = LONGEST_RUN + 1.0
    start_line = next(line for line in SILENCE_LOG.splitlines() if "silence_start" in line)
    late_start = re.sub(r"silence_start: [\d.]+", f"silence_start: {VIDEO_S - open_run}", start_line)
    assert late_start != start_line
    tools.silence_log = SILENCE_LOG + late_start + "\n"
    assert qa.measure(files.video, files.voice).longest_silence_s == pytest.approx(open_run)


def test_silence_fixture_has_the_longest_run_first() -> None:
    """Otherwise taking the last run instead of the longest would go unnoticed."""
    assert len(RUNS) >= 2 and RUNS[0] == LONGEST_RUN > min(RUNS)


@pytest.mark.parametrize(("rate", "fps"), [("30000/1001", 30000 / 1001), ("30", 30.0), ("25/1", 25.0)])
def test_frame_rate_forms(files: SimpleNamespace, tools: FakeTools, rate: str, fps: float) -> None:
    tools.probe_video = probe_video_with(r_frame_rate=rate)
    assert qa.measure(files.video, files.voice).fps == pytest.approx(fps)


@pytest.mark.parametrize("change", [
    {"probe_video": probe_video_with(r_frame_rate="0/0")},
    {"probe_video": "Invalid data found when processing input"},
    {"probe_video": json.dumps({**VIDEO_INFO, "format": {}})},
    {"error": subprocess.TimeoutExpired(["ffprobe"], 300)},
    {"error": FileNotFoundError("ffprobe not found")},
])
def test_unreadable_measurement_raises_and_fails_the_report(files: SimpleNamespace, tools: FakeTools,
                                                            change: dict[str, Any]) -> None:
    for name, value in change.items():
        setattr(tools, name, value)
    with pytest.raises(RuntimeError):
        qa.measure(files.video, files.voice)
    report = qa.run_qa(files.video, files.voice, [], [])
    assert not report.passed
    assert [f.check for f in report.failures] == ["duration"]
    assert report.measured == {}


def test_tool_failure_message_ends_with_its_stderr(files: SimpleNamespace, tools: FakeTools) -> None:
    lines = [f"ffprobe complaint {i:02d}" for i in range(20)]
    tools.fail_with = "\n".join(lines) + "\n"
    with pytest.raises(RuntimeError) as exc:
        qa.measure(files.video, files.voice)
    assert str(exc.value).endswith(lines[-1])
    assert lines[0] not in str(exc.value)


def test_good_stats_from_the_real_render_pass() -> None:
    """The 65 s render the owner approved (run 43873059742) passes with a matching script."""
    real = stats(69.6, 69.525, file_bytes=2_394_147, longest_silence_s=0.0)
    assert failed(real, 167) == set()
