"""R6.1: the QA gate (task p1-qa)."""

import dataclasses
import subprocess
from pathlib import Path

import pytest

from pipeline import constants
from pipeline.render import qa
from pipeline.render.qa import VideoStats
from pipeline.schema import WordTiming
from tests.wavs import write_wav

WORDS = [f"w{i}" for i in range(100)]
GOOD = VideoStats(duration_s=65.0, voice_duration_s=65.0, width=constants.WIDTH, height=constants.HEIGHT,
                  fps=float(constants.FPS), file_bytes=5_000_000, longest_silence_s=0.5)


def timings(words: list[str] = WORDS, total: float = 64.0) -> list[WordTiming]:
    step = total / len(words)
    return [WordTiming(word=w, start=i * step, end=(i + 1) * step) for i, w in enumerate(words)]


def failed_checks(stats: VideoStats = GOOD, t: list[WordTiming] | None = None,
                  words: list[str] = WORDS) -> set[str]:
    report = qa.evaluate(stats, timings() if t is None else t, words)
    assert report.passed == (not report.failures)
    return {f.check for f in report.failures}


def make_video(path: Path, seconds: float, silent_from: float | None = None, silent_to: float | None = None,
               size: str = f"{constants.WIDTH}x{constants.HEIGHT}", fps: int = constants.FPS) -> Path:
    volume = "volume=1"
    if silent_from is not None:
        volume = f"volume='if(between(t,{silent_from},{silent_to}),0,1)':eval=frame"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=0x336699:s={size}:r={fps}:d={seconds}",
        "-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=pink:a=0.3",
        "-af", volume, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(path)], check=True)
    return path


@pytest.mark.heavy
def test_acceptance(tmp_path: Path) -> None:
    """A clean video passes; one with a 3 s silence fails and names the check."""
    voice = write_wav(tmp_path / "voice.wav", 65.0, constants.VOICE_SAMPLE_RATE)
    good = make_video(tmp_path / "good.mp4", 65.0)
    report = qa.run_qa(good, voice, timings(), WORDS)
    assert report.passed, report.failures
    assert report.measured["width"] == constants.WIDTH

    gap = make_video(tmp_path / "gap.mp4", 65.0, silent_from=10, silent_to=13)
    report = qa.run_qa(gap, voice, timings(), WORDS)
    assert not report.passed
    assert "silence" in {f.check for f in report.failures}


@pytest.mark.heavy
def test_measure_reads_the_video(tmp_path: Path) -> None:
    voice = write_wav(tmp_path / "voice.wav", 12.0, constants.VOICE_SAMPLE_RATE)
    video = make_video(tmp_path / "v.mp4", 12.0, silent_from=4, silent_to=6.5, size="720x1280", fps=25)
    stats = qa.measure(video, voice)
    assert stats.duration_s == pytest.approx(12.0, abs=0.2)
    assert stats.voice_duration_s == pytest.approx(12.0, abs=0.01)
    assert (stats.width, stats.height, stats.fps) == (720, 1280, 25.0)
    assert stats.file_bytes == video.stat().st_size
    assert stats.longest_silence_s == pytest.approx(2.5, abs=0.3)


@pytest.mark.heavy
def test_unreadable_video_gives_failed_report(tmp_path: Path) -> None:
    voice = write_wav(tmp_path / "voice.wav", 40.0, constants.VOICE_SAMPLE_RATE)
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    report = qa.run_qa(bad, voice, timings(), WORDS)
    assert not report.passed
    assert "duration" in {f.check for f in report.failures}


def test_good_stats_pass_and_report_every_measurement() -> None:
    report = qa.evaluate(GOOD, timings(), WORDS)
    assert report.passed and report.failures == []
    for field in dataclasses.fields(VideoStats):
        assert field.name in report.measured


@pytest.mark.parametrize(("change", "check"), [
    ({"duration_s": 20.0, "voice_duration_s": 20.0}, "duration"),
    ({"duration_s": 95.0, "voice_duration_s": 95.0}, "duration"),
    ({"duration_s": 65.0, "voice_duration_s": 64.5}, "duration"),
    ({"longest_silence_s": constants.MAX_SILENCE_S + 0.1}, "silence"),
    ({"width": constants.HEIGHT, "height": constants.WIDTH}, "resolution"),
    ({"fps": 25.0}, "fps"),
    ({"file_bytes": constants.MIN_FILE_BYTES - 1}, "file_size"),
    ({"file_bytes": constants.MAX_FILE_BYTES + 1}, "file_size"),
])
def test_each_bad_measurement_fails_its_check(change: dict[str, float], check: str) -> None:
    assert failed_checks(dataclasses.replace(GOOD, **change), timings(total=19.0)
                         if change.get("voice_duration_s") == 20.0 else None) == {check}


def test_silence_at_the_limit_passes() -> None:
    assert failed_checks(dataclasses.replace(GOOD, longest_silence_s=constants.MAX_SILENCE_S)) == set()


def test_failure_reasons_are_not_empty() -> None:
    report = qa.evaluate(dataclasses.replace(GOOD, fps=25.0, longest_silence_s=3.0), timings(), WORDS)
    assert {f.check for f in report.failures} == {"fps", "silence"}
    assert all(f.reason.strip() for f in report.failures)


@pytest.mark.parametrize("broken", [
    timings()[:-1],
    [*timings()[:5], timings()[5].model_copy(update={"word": "typo"}), *timings()[6:]],
    [timings()[1], timings()[0], *timings()[2:]],
    [*timings()[:-1], timings()[-1].model_copy(update={"end": 65.0 + constants.ALIGNMENT_SLACK_S + 0.5})],
    [],
])
def test_alignment_problems_fail_alignment(broken: list[WordTiming]) -> None:
    assert failed_checks(t=broken) == {"alignment"}


def test_timing_starting_before_previous_fails_alignment() -> None:
    t = timings()
    t[10] = WordTiming(word=WORDS[10], start=t[9].start - 0.1, end=t[10].end)
    assert failed_checks(t=t) == {"alignment"}
