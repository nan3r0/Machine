"""Exact FFmpeg arguments, filter escaping and the two-pass run with FFmpeg faked.

Task p1-qa-tests, QA lead items 3, 4, 5 and 13. No FFmpeg needed: `subprocess.run` is replaced and
pass 1 returns the real loudnorm log in tests/fixtures/ffmpeg/loudnorm_pass1.log.
"""

import subprocess
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline import constants
from pipeline.render import compose
from pipeline.render.compose import ComposeError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ffmpeg"
PASS1_LOG = (FIXTURES / "loudnorm_pass1.log").read_text(encoding="utf-8")
# The values loudnorm printed in PASS1_LOG, by the loudnorm pass 2 option they feed.
MEASURED = {"measured_I": "-25.38", "measured_TP": "-2.94", "measured_LRA": "2.80",
            "measured_thresh": "-35.89", "offset": "0.94"}
LOUDNORM = f"loudnorm=I={constants.LOUDNESS_LUFS:g}:TP=-1"
TAIL_LINES = 20


def render_args(voice: Path, vf: str, af: str, out: Path) -> list[str]:
    return [
        "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i",
        f"color=c={constants.BACKGROUND_COLOR}:s={constants.WIDTH}x{constants.HEIGHT}:r={constants.FPS}",
        "-i", str(voice),
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(constants.FPS),
        "-c:a", "aac", "-b:a", constants.AUDIO_BITRATE, "-ar", "48000",
        "-shortest",
        str(out),
    ]


def measure_args(voice: Path) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "info", "-i", str(voice),
            "-af", f"{LOUDNORM}:print_format=json", "-f", "null", "-"]


# --- item 3: build_ffmpeg_args -------------------------------------------------------------------

WORK = Path("work")
VF = "subtitles=filename='work/captions.ass':fontsdir='assets/fonts'"


def test_render_args_single_pass() -> None:
    args = compose.build_ffmpeg_args(WORK / "voice.wav", WORK / "captions.ass", WORK / "final.mp4",
                                     Path("assets/fonts"))
    assert args == render_args(WORK / "voice.wav", VF, LOUDNORM, WORK / "final.mp4")


def test_render_args_with_pass_one_measurement() -> None:
    """Pass 2 feeds every measured value back and runs loudnorm in linear mode (lessons.md)."""
    args = compose.build_ffmpeg_args(WORK / "voice.wav", WORK / "captions.ass", WORK / "final.mp4",
                                     Path("assets/fonts"), dict(MEASURED))
    af = (f"{LOUDNORM}:measured_I=-25.38:measured_TP=-2.94:measured_LRA=2.80"
          ":measured_thresh=-35.89:offset=0.94:linear=true")
    assert args == render_args(WORK / "voice.wav", VF, af, WORK / "final.mp4")


# --- item 5: parse_loudnorm_json -----------------------------------------------------------------

def test_parse_real_loudnorm_log() -> None:
    assert compose.parse_loudnorm_json(PASS1_LOG) == MEASURED


@pytest.mark.parametrize("stderr", [
    "",
    PASS1_LOG[:PASS1_LOG.index("{")],
    PASS1_LOG.replace('"target_offset"', '"other_offset"'),
    PASS1_LOG.replace('"input_tp" : "-2.94",', ""),
    PASS1_LOG.replace("}", ""),
])
def test_parse_missing_or_broken_measurement_raises(stderr: str) -> None:
    with pytest.raises(ComposeError):
        compose.parse_loudnorm_json(stderr)


# --- item 4: compose with FFmpeg faked ------------------------------------------------------------

class FakeFFmpeg:
    """Records each FFmpeg call. Pass 1 prints the real loudnorm log; pass 2 writes `out`."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.render_stderr = "pass 2 warning\n"
        self.render_code = 0
        self.out_bytes = b"mp4 data"
        self.error: Exception | None = None

    def run(self, args: list[str], **kwargs: Any) -> SimpleNamespace:
        self.calls.append((list(args), kwargs))
        if self.error:
            raise self.error
        if len(self.calls) == 1:
            return SimpleNamespace(args=args, returncode=0, stdout="", stderr=PASS1_LOG)
        if self.out_bytes is not None:
            self.out.write_bytes(self.out_bytes)
        return SimpleNamespace(args=args, returncode=self.render_code, stdout="", stderr=self.render_stderr)


@pytest.fixture
def work(tmp_path: Path) -> SimpleNamespace:
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"RIFF")
    captions = tmp_path / "captions.ass"
    captions.write_text("[Script Info]\n", encoding="utf-8")
    return SimpleNamespace(voice=voice, captions=captions, out=tmp_path / "final.mp4",
                           fonts=tmp_path / "fonts", log=tmp_path / "logs" / "deep" / "compose.log")


@pytest.fixture
def ffmpeg(monkeypatch: pytest.MonkeyPatch, work: SimpleNamespace) -> FakeFFmpeg:
    fake = FakeFFmpeg(work.out)
    monkeypatch.setattr(subprocess, "run", fake.run)
    return fake


def run_compose(work: SimpleNamespace) -> Path:
    return compose.compose(work.voice, work.captions, work.out, work.fonts, work.log)


def test_acceptance(work: SimpleNamespace, ffmpeg: FakeFFmpeg) -> None:
    """Two passes in order: measure the voice, then render with the measured values; log both."""
    assert run_compose(work) == work.out
    assert [args for args, _ in ffmpeg.calls] == [
        measure_args(work.voice),
        compose.build_ffmpeg_args(work.voice, work.captions, work.out, work.fonts, dict(MEASURED)),
    ]
    second = ffmpeg.calls[1][0]
    assert second[second.index("-af") + 1].endswith(":offset=0.94:linear=true")
    for _, kwargs in ffmpeg.calls:
        assert not kwargs.get("shell")
    assert work.log.read_text(encoding="utf-8") == PASS1_LOG + "pass 2 warning\n"


def test_log_is_truncated_first(work: SimpleNamespace, ffmpeg: FakeFFmpeg) -> None:
    work.log.parent.mkdir(parents=True)
    work.log.write_text("stale log from the last run\n", encoding="utf-8")
    run_compose(work)
    assert "stale" not in work.log.read_text(encoding="utf-8")


@pytest.mark.parametrize("missing", ["voice", "captions"])
def test_missing_input_is_named(work: SimpleNamespace, ffmpeg: FakeFFmpeg, missing: str) -> None:
    gone, other = (work.voice, work.captions) if missing == "voice" else (work.captions, work.voice)
    gone.unlink()
    with pytest.raises(ComposeError) as exc:
        run_compose(work)
    assert str(gone) in str(exc.value)
    assert str(other) not in str(exc.value)
    assert ffmpeg.calls == []


def test_ffmpeg_failure_carries_exactly_the_stderr_tail(work: SimpleNamespace, ffmpeg: FakeFFmpeg) -> None:
    lines = [f"ffmpeg error line {i:02d}" for i in range(30)]
    ffmpeg.render_stderr = "\n".join(lines) + "\n"
    ffmpeg.render_code = 1
    with pytest.raises(ComposeError) as exc:
        run_compose(work)
    message = str(exc.value)
    assert message.endswith("\n".join(lines[-TAIL_LINES:]))
    assert lines[-TAIL_LINES - 1] not in message
    assert work.log.read_text(encoding="utf-8").endswith(ffmpeg.render_stderr), "a failed pass is logged too"


@pytest.mark.parametrize("out_bytes", [b"", None])
def test_empty_or_missing_output_raises(work: SimpleNamespace, ffmpeg: FakeFFmpeg,
                                        out_bytes: bytes | None) -> None:
    ffmpeg.out_bytes = out_bytes
    with pytest.raises(ComposeError):
        run_compose(work)


def test_ffmpeg_that_cannot_start_raises_compose_error(work: SimpleNamespace, ffmpeg: FakeFFmpeg) -> None:
    ffmpeg.error = FileNotFoundError("ffmpeg not found")
    with pytest.raises(ComposeError):
        run_compose(work)


# --- item 13: filter path escaping ----------------------------------------------------------------

def take(text: str, i: int, terms: str) -> tuple[str, int]:
    """One FFmpeg token from `text[i:]` up to an unquoted, unescaped char of `terms` (av_get_token)."""
    out = []
    while i < len(text) and text[i] not in terms:
        if text[i] == "\\":
            out.append(text[i + 1])
            i += 2
        elif text[i] == "'":
            end = text.index("'", i + 1)
            out.append(text[i + 1:end])
            i = end + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out), i


def subtitles_options(vf: str) -> dict[str, str]:
    """Undo both FFmpeg escaping levels: the filtergraph, then the filter's key=value options."""
    name, i = take(vf, 0, "=,;[")
    assert (name, vf[i]) == ("subtitles", "=")
    args, i = take(vf, i + 1, "[],;")
    assert i == len(vf), f"unescaped graph separator in {vf!r}"
    options, i = {}, 0
    while i < len(args):
        key, i = take(args, i, "=:")
        value, i = take(args, i + 1, ":")
        options[key] = value
        i += 1
    return options


def test_awkward_posix_path_is_escaped_exactly() -> None:
    value = compose.subtitles_filter_value(PurePosixPath("/tmp/a b/it's:x\\y.ass"))
    assert value == r"'/tmp/a b/it\'\''s\:x\\y.ass'"


path_text = st.text(st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=30)


@settings(deadline=None, max_examples=200)
@given(name=path_text, fonts=path_text)
def test_any_path_survives_both_escaping_levels(name: str, fonts: str) -> None:
    """FFmpeg reads back exactly the paths given, whatever characters they hold."""
    captions, fonts_dir = PurePosixPath("/w", name), PurePosixPath("/f", fonts)
    vf = (f"subtitles=filename={compose.subtitles_filter_value(captions)}"
          f":fontsdir={compose.subtitles_filter_value(fonts_dir)}")
    assert subtitles_options(vf) == {"filename": captions.as_posix(), "fontsdir": fonts_dir.as_posix()}
