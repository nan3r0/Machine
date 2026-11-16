"""Heavy guard and capture for the canned ffprobe and silencedetect output in tests/fixtures/ffmpeg/
(task p1-qa-tests).

Every CI run writes the real output of the commands qa runs to out/frames/ffmpeg-capture/ (uploaded
with the `frames` artifact). The fixtures must be replaced with that capture before the task is done;
until then this test fails if their shape differs from the real tools.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.render import qa
from tests import media
from tests.wavs import write_wav

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ffmpeg"
CAPTURE = media.FRAMES_DIR / "ffmpeg-capture"
SILENCE_LINE = re.compile(r"^\[silencedetect @ 0x[0-9a-f]+\] "
                          r"(silence_start: -?[\d.]+|silence_end: [\d.]+ \| silence_duration: [\d.]+)\s*$")
SECONDS = 12.0


def shape(value: Any) -> Any:
    """Keys and value types of a JSON value, ignoring the values themselves."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(item) for item in value[:1]]
    return type(value).__name__


def silence_lines(log: str) -> list[str]:
    return [line for line in log.splitlines() if "silence_" in line]


def video_with_two_silences(path: Path) -> Path:
    """Two silences, the longer first, so a capture keeps the longest-run check meaningful."""
    size = f"{constants.WIDTH}x{constants.HEIGHT}"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=0x336699:s={size}:r={constants.FPS}:d={SECONDS}",
        "-f", "lavfi", "-i", f"anoisesrc=d={SECONDS}:c=pink:a=0.3:seed=1",
        "-af", "volume='if(between(t,2,5)+between(t,8,9.8),0,1)':eval=frame",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(path)], check=True, timeout=300)
    return path


@pytest.mark.heavy
def test_fixtures_match_real_tool_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    voice = write_wav(tmp_path / "voice.wav", SECONDS, constants.VOICE_SAMPLE_RATE)
    video = video_with_two_silences(tmp_path / "final.mp4")
    outputs: list[tuple[list[str], subprocess.CompletedProcess[str]]] = []
    real_run = subprocess.run

    def spy(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        result: subprocess.CompletedProcess[str] = real_run(args, **kwargs)
        outputs.append((list(args), result))
        return result

    monkeypatch.setattr(subprocess, "run", spy)
    qa.measure(video, voice)
    monkeypatch.undo()

    probes = [r.stdout for args, r in outputs if args[0] == "ffprobe"]
    silence = next(r.stderr for args, r in outputs if args[0] == "ffmpeg")
    CAPTURE.mkdir(parents=True, exist_ok=True)
    for name, text in zip(("ffprobe_video.json", "ffprobe_voice.json", "silencedetect.log"),
                          [*probes, silence], strict=True):
        (CAPTURE / name).write_text(text, encoding="utf-8")

    report = f"real output saved to {CAPTURE}"
    for real, name in zip(probes, ("ffprobe_video.json", "ffprobe_voice.json"), strict=True):
        fixture = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        # Only what qa reads; other top-level keys vary with the FFmpeg version.
        read = ("streams", "format")
        real_read = {k: json.loads(real).get(k) for k in read}
        assert shape(real_read) == shape({k: fixture.get(k) for k in read}), report
    real_lines = silence_lines(silence)
    assert len(real_lines) == 4 and all(SILENCE_LINE.match(line) for line in real_lines), report
    fixture_lines = silence_lines((FIXTURES / "silencedetect.log").read_text(encoding="utf-8"))
    assert fixture_lines and all(SILENCE_LINE.match(line) for line in fixture_lines)
