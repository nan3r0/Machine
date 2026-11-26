"""Scenes layer under the captions (task p3-compose, method A).

compose.build_ffmpeg_args and compose.compose gain a keyword-only `scenes` path (default None,
which keeps today's arguments). With it the filtergraph is `subtitles=<scenes>,subtitles=<captions>`
with the same fontsdir. Captions move to CAPTION_POS_Y.
"""

import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pytest

from pipeline import constants
from pipeline.render import captions_ass, compose
from pipeline.render.compose import ComposeError, subtitles_filter_value
from pipeline.schema import WordTiming
from tests.media import write_captions
from tests.wavs import write_wav

PASS1_LOG = (Path(__file__).resolve().parent.parent / "fixtures" / "ffmpeg" / "loudnorm_pass1.log").read_text(
    encoding="utf-8"
)
RED_FRAME = (
    "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
    "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
    "MarginL, MarginR, MarginV, Encoding\n"
    "Style: Shape,Arial,20,&H000000FF,&H000000FF,&H00000000,&H00000000,"
    "0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:00.00,0:00:05.00,Shape,,0,0,0,,"
    "{\\pos(0,0)\\p1}m 0 0 l 1080 0 l 1080 1920 l 0 1920{\\p0}\n"
)


def vf(args: list[str]) -> str:
    return args[args.index("-vf") + 1]


@pytest.mark.parametrize("root", [PurePosixPath("/w o'rk/a,b"), PureWindowsPath("C:/work")])
def test_scenes_burn_under_the_captions(root: Any) -> None:
    voice, captions, scenes, out, fonts = (root / n for n in ("v.wav", "c.ass", "s.ass", "o.mp4", "fonts"))
    args = compose.build_ffmpeg_args(voice, captions, out, fonts, None, scenes=scenes)
    font = f":fontsdir={subtitles_filter_value(fonts)}"
    assert vf(args) == (
        f"subtitles=filename={subtitles_filter_value(scenes)}{font},"
        f"subtitles=filename={subtitles_filter_value(captions)}{font}"
    )
    assert args[0] == "ffmpeg" and args[-1] == str(out)


def test_no_scenes_keeps_todays_arguments(tmp_path: Path) -> None:
    names = (tmp_path / "v.wav", tmp_path / "c.ass", tmp_path / "o.mp4", tmp_path / "fonts")
    assert compose.build_ffmpeg_args(*names, None, scenes=None) == compose.build_ffmpeg_args(*names, None)


def test_scenes_is_keyword_only(tmp_path: Path) -> None:
    names = (tmp_path / "v.wav", tmp_path / "c.ass", tmp_path / "o.mp4", tmp_path / "fonts")
    with pytest.raises(TypeError):
        compose.build_ffmpeg_args(*names, None, tmp_path / "s.ass")  # type: ignore[misc]


def inputs(tmp_path: Path) -> tuple[Path, Path]:
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"RIFF")
    return voice, write_captions(tmp_path / "captions.ass")


def test_missing_scenes_file_raises(tmp_path: Path) -> None:
    voice, captions = inputs(tmp_path)
    with pytest.raises(ComposeError):
        compose.compose(
            voice,
            captions,
            tmp_path / "o.mp4",
            tmp_path,
            tmp_path / "log.txt",
            scenes=tmp_path / "missing.ass",
        )


def test_compose_passes_scenes_to_the_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    voice, captions = inputs(tmp_path)
    scenes = tmp_path / "scenes.ass"
    scenes.write_text(RED_FRAME, encoding="utf-8")
    out = tmp_path / "o.mp4"
    calls: list[list[str]] = []

    def fake_run(args: list[str], *a: Any, **k: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        out.write_bytes(b"mp4")
        return subprocess.CompletedProcess(args, 0, "", PASS1_LOG)

    monkeypatch.setattr(subprocess, "run", fake_run)
    compose.compose(voice, captions, out, tmp_path, tmp_path / "log.txt", scenes=scenes)
    assert subtitles_filter_value(scenes) in vf(calls[-1])


def test_captions_sit_at_caption_pos_y() -> None:
    text = captions_ass.build_ass([WordTiming(word="Bloop", start=0.0, end=0.5)])
    x = (constants.SAFE_LEFT_PX + constants.SAFE_RIGHT_PX) / 2
    assert f"\\pos({x:g},{constants.CAPTION_POS_Y})" in text


@pytest.mark.heavy
def test_scenes_layer_shows_in_the_video(tmp_path: Path) -> None:
    voice = write_wav(tmp_path / "voice.wav", 2.0, constants.VOICE_SAMPLE_RATE)
    captions = write_captions(tmp_path / "captions.ass")
    scenes = tmp_path / "scenes.ass"
    scenes.write_text(RED_FRAME, encoding="utf-8")
    out = compose.compose(
        voice, captions, tmp_path / "o.mp4", Path(constants.FONTS_DIR), tmp_path / "log.txt", scenes=scenes
    )
    raw = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "1",
            "-i",
            str(out),
            "-frames:v",
            "1",
            "-vf",
            "crop=2:2:100:100",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    red, green, blue = raw[0], raw[1], raw[2]
    assert red > 200 and green < 60 and blue < 60, (red, green, blue)


def test_acceptance() -> None:
    test_scenes_burn_under_the_captions(PurePosixPath("/w o'rk/a,b"))
    test_captions_sit_at_caption_pos_y()
