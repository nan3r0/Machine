"""R5: FFmpeg render to final.mp4 (task p1-compose)."""

import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from pipeline import constants
from pipeline.render import compose
from pipeline.render.compose import ComposeError
from tests import media

VOICE = Path(__file__).resolve().parent.parent / "fixtures" / "align_sample.wav"


def args_for(tmp_path: Path) -> list[str]:
    return compose.build_ffmpeg_args(tmp_path / "voice.wav", tmp_path / "captions.ass",
                                     tmp_path / "final.mp4", tmp_path / "fonts")


def render(tmp_path: Path, folder: str = "work") -> Path:
    work = tmp_path / folder
    work.mkdir()
    fonts = work / "fonts"
    fonts.mkdir()
    captions = media.write_captions(work / "captions.ass")
    return compose.compose(VOICE, captions, work / "final.mp4", fonts, work / "logs" / "compose.log")


@pytest.mark.heavy
def test_acceptance(tmp_path: Path) -> None:
    """R5.1 to R5.3, plus frames for the visual-qa reviewer."""
    out = render(tmp_path)
    info = media.probe(out)
    video, audio = media.stream(info, "video"), media.stream(info, "audio")
    assert (video["width"], video["height"]) == (constants.WIDTH, constants.HEIGHT)
    assert video["codec_name"] == "h264"
    assert video["pix_fmt"] == "yuv420p"
    assert video["r_frame_rate"] == f"{constants.FPS}/1"
    assert audio["codec_name"] == "aac"
    assert abs(media.integrated_loudness(out) - constants.LOUDNESS_LUFS) <= constants.LOUDNESS_TOLERANCE_LU
    assert abs(media.duration(out) - media.duration(VOICE)) <= constants.DURATION_MATCH_TOLERANCE_S
    assert (tmp_path / "work" / "logs" / "compose.log").exists()
    media.extract_frames(out, "compose", (1.0, 4.0, 8.0))


@pytest.mark.heavy
def test_awkward_paths_render(tmp_path: Path) -> None:
    """The subtitles filter path survives spaces, quotes, commas, brackets and semicolons."""
    out = render(tmp_path, "a b's, [x]; y")
    assert media.duration(out) > 1.0


@pytest.mark.heavy
def test_corrupt_voice_raises_with_ffmpeg_output(tmp_path: Path) -> None:
    bad = tmp_path / "voice.wav"
    bad.write_bytes(os.urandom(2048))
    captions = media.write_captions(tmp_path / "captions.ass")
    log = tmp_path / "logs" / "compose.log"
    with pytest.raises(ComposeError) as exc:
        compose.compose(bad, captions, tmp_path / "final.mp4", tmp_path, log)
    assert str(exc.value).strip()
    assert log.exists()


def test_missing_input_raises(tmp_path: Path) -> None:
    captions = media.write_captions(tmp_path / "captions.ass")
    with pytest.raises(ComposeError):
        compose.compose(tmp_path / "missing.wav", captions, tmp_path / "final.mp4", tmp_path,
                        tmp_path / "compose.log")
    with pytest.raises(ComposeError):
        compose.compose(VOICE, tmp_path / "missing.ass", tmp_path / "final.mp4", tmp_path,
                        tmp_path / "compose.log")


def test_args_are_a_list_of_strings_ending_with_out(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    assert isinstance(args, list) and all(isinstance(a, str) for a in args)
    assert args[0] == "ffmpeg"
    assert args[-1] == str(tmp_path / "final.mp4")
    assert str(tmp_path / "voice.wav") in args


def test_args_quiet_ffmpeg(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    assert "-hide_banner" in args
    assert args[args.index("-loglevel") + 1] == "error"


def test_args_set_format_codecs_and_loudness(tmp_path: Path) -> None:
    args = args_for(tmp_path)
    joined = " ".join(args)
    assert f"{constants.WIDTH}x{constants.HEIGHT}" in joined
    assert constants.BACKGROUND_COLOR in joined
    assert re.search(rf"(r={constants.FPS}\b|-r {constants.FPS}\b)", joined)
    assert "libx264" in args
    assert "yuv420p" in args
    assert "aac" in args
    assert "loudnorm" in joined
    assert re.search(rf"\bI={constants.LOUDNESS_LUFS:g}\b", joined)
    assert "subtitles=" in joined


def test_windows_subtitles_path_is_escaped() -> None:
    value = compose.subtitles_filter_value(PureWindowsPath(r"C:\work\out\captions.ass"))
    assert r"C\:/work/out/captions.ass" in value
    assert "\\w" not in value and "\\o" not in value and "\\c" not in value


def test_linux_subtitles_path_keeps_its_folders() -> None:
    value = compose.subtitles_filter_value(PurePosixPath("/tmp/run/captions.ass"))
    assert "/tmp/run/captions.ass" in value


def test_no_shell_strings() -> None:
    source = Path(compose.__file__).read_text(encoding="utf-8")
    assert "shell=True" not in source
    assert "os.system" not in source
    assert "os.popen" not in source
