"""compose and qa take every number from pipeline.constants, and compose cannot hang on FFmpeg.

Task p1-constants-timeout. FFmpeg and ffprobe are faked. Each constant is patched to an odd value and
the behaviour must follow it, so a module-private copy of the number fails the test.
"""

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pipeline import constants
from pipeline.render import compose, qa
from pipeline.render.compose import ComposeError
from pipeline.render.qa import VideoStats

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ffmpeg"
PASS1_LOG = (FIXTURES / "loudnorm_pass1.log").read_text(encoding="utf-8")
PROBE_VIDEO = (FIXTURES / "ffprobe_video.json").read_text(encoding="utf-8")
PROBE_VOICE = (FIXTURES / "ffprobe_voice.json").read_text(encoding="utf-8")
SILENCE_LOG = (FIXTURES / "silencedetect.log").read_text(encoding="utf-8")
WORK = Path("work")


class FakeFFmpeg:
    """Pass 1 prints the real loudnorm log, pass 2 writes `out`. Can fail or time out on one call."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.calls: list[dict[str, Any]] = []
        self.render_stderr = ""
        self.render_code = 0
        self.timeout_on_call: int | None = None
        self.timeout_stderr: bytes | None = None

    def run(self, args: list[str], **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.timeout_on_call == len(self.calls):
            raise subprocess.TimeoutExpired(args, kwargs.get("timeout") or 0, stderr=self.timeout_stderr)
        if len(self.calls) == 1:
            return SimpleNamespace(args=args, returncode=0, stdout="", stderr=PASS1_LOG)
        self.out.write_bytes(b"mp4 data")
        return SimpleNamespace(args=args, returncode=self.render_code, stdout="", stderr=self.render_stderr)


@pytest.fixture
def work(tmp_path: Path) -> SimpleNamespace:
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"RIFF")
    captions = tmp_path / "captions.ass"
    captions.write_text("[Script Info]\n", encoding="utf-8")
    return SimpleNamespace(voice=voice, captions=captions, out=tmp_path / "final.mp4",
                           fonts=tmp_path / "fonts", log=tmp_path / "logs" / "compose.log")


@pytest.fixture
def ffmpeg(monkeypatch: pytest.MonkeyPatch, work: SimpleNamespace) -> FakeFFmpeg:
    fake = FakeFFmpeg(work.out)
    monkeypatch.setattr(subprocess, "run", fake.run)
    return fake


def run_compose(work: SimpleNamespace) -> Path:
    return compose.compose(work.voice, work.captions, work.out, work.fonts, work.log)


# --- compose timeout --------------------------------------------------------------------------------

def test_acceptance(work: SimpleNamespace, ffmpeg: FakeFFmpeg, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both FFmpeg calls get COMPOSE_TIMEOUT_S, and a hung FFmpeg ends as a ComposeError."""
    monkeypatch.setattr(constants, "COMPOSE_TIMEOUT_S", 7)
    assert run_compose(work) == work.out
    assert [call.get("timeout") for call in ffmpeg.calls] == [7, 7]

    ffmpeg.calls.clear()
    ffmpeg.timeout_on_call = 2
    with pytest.raises(ComposeError) as exc:
        run_compose(work)
    assert isinstance(exc.value.__cause__, subprocess.TimeoutExpired)


@pytest.mark.parametrize("call", [1, 2])
@pytest.mark.parametrize("partial_stderr", [None, b"frame=  100 fps=12\n"])
def test_timeout_on_either_pass_raises_compose_error(work: SimpleNamespace, ffmpeg: FakeFFmpeg, call: int,
                                                     partial_stderr: bytes | None) -> None:
    """TimeoutExpired carries bytes or None as stderr even with text=True; neither may escape."""
    ffmpeg.timeout_on_call = call
    ffmpeg.timeout_stderr = partial_stderr
    with pytest.raises(ComposeError):
        run_compose(work)
    assert len(ffmpeg.calls) == call


def test_timeout_is_finite_and_positive() -> None:
    assert 0 < constants.COMPOSE_TIMEOUT_S < float("inf")


# --- compose numbers from constants -----------------------------------------------------------------

def render_args() -> list[str]:
    return compose.build_ffmpeg_args(WORK / "voice.wav", WORK / "captions.ass", WORK / "final.mp4",
                                     Path("assets/fonts"))


def test_audio_rate_comes_from_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "AUDIO_SAMPLE_RATE_HZ", 44_100)
    args = render_args()
    assert args[args.index("-ar") + 1] == "44100"


def test_true_peak_comes_from_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "TRUE_PEAK_DBTP", -2.5)
    args = render_args()
    assert ":TP=-2.5" in args[args.index("-af") + 1]
    measure = compose.build_measure_args(WORK / "voice.wav")
    assert ":TP=-2.5:" in measure[measure.index("-af") + 1]


def test_compose_error_tail_length_comes_from_constants(work: SimpleNamespace, ffmpeg: FakeFFmpeg,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "COMPOSE_STDERR_TAIL_LINES", 3)
    lines = [f"render line {i:02d}" for i in range(10)]
    ffmpeg.render_stderr = "\n".join(lines) + "\n"
    ffmpeg.render_code = 1
    with pytest.raises(ComposeError) as exc:
        run_compose(work)
    message = str(exc.value)
    assert message.endswith("\n".join(lines[-3:]))
    assert lines[-4] not in message


# --- qa numbers from constants ----------------------------------------------------------------------

class FakeTools:
    """ffprobe returns the real fixture JSON; FFmpeg prints the real silencedetect log, or fails."""

    def __init__(self, video: Path) -> None:
        self.video = video
        self.calls: list[dict[str, Any]] = []
        self.fail_with: str | None = None

    def run(self, args: list[str], **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.fail_with is not None:
            return SimpleNamespace(args=args, returncode=1, stdout="", stderr=self.fail_with)
        if args[0] == "ffprobe":
            stdout = PROBE_VIDEO if args[-1] == str(self.video) else PROBE_VOICE
            return SimpleNamespace(args=args, returncode=0, stdout=stdout, stderr="")
        return SimpleNamespace(args=args, returncode=0, stdout="", stderr=SILENCE_LOG)


@pytest.fixture
def media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    video = tmp_path / "final.mp4"
    video.write_bytes(b"x" * 1234)
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"RIFF")
    tools = FakeTools(video)
    monkeypatch.setattr(subprocess, "run", tools.run)
    return SimpleNamespace(video=video, voice=voice, tools=tools)


def test_qa_tool_timeout_comes_from_constants(media: SimpleNamespace,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "QA_TOOL_TIMEOUT_S", 11)
    qa.measure(media.video, media.voice)
    assert media.tools.calls and all(call.get("timeout") == 11 for call in media.tools.calls)


def test_qa_tool_error_tail_length_comes_from_constants(media: SimpleNamespace,
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "QA_STDERR_TAIL_LINES", 2)
    lines = [f"ffprobe complaint {i:02d}" for i in range(10)]
    media.tools.fail_with = "\n".join(lines) + "\n"
    with pytest.raises(RuntimeError) as exc:
        qa.measure(media.video, media.voice)
    message = str(exc.value)
    assert message.endswith("\n".join(lines[-2:]))
    assert lines[-3] not in message


def fps_failed(fps: float) -> bool:
    stats = VideoStats(duration_s=65.0, voice_duration_s=65.0, width=constants.WIDTH,
                       height=constants.HEIGHT, fps=fps, file_bytes=5_000_000, longest_silence_s=0.5)
    script = [f"w{i}" for i in range(constants.TIKTOK_WORDS[0])]
    report = qa.evaluate(stats, [], script)
    return "fps" in {failure.check for failure in report.failures}


def test_fps_tolerance_comes_from_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "QA_FPS_TOLERANCE", 0.5)
    assert not fps_failed(constants.FPS + 0.4)
    assert fps_failed(constants.FPS + 0.6)
