"""Heavy guard: the canned ffprobe and silencedetect output in tests/fixtures/ffmpeg/ still has the
shape the real tools print, so the fast fakes in test_qa_exact.py cannot drift (task p1-qa-tests).

On a mismatch the failure message holds the real output; replace the fixture with it.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.render import qa
from tests.render.test_qa import make_video
from tests.wavs import write_wav

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "ffmpeg"
SILENCE_LINE = re.compile(r"^\[silencedetect @ 0x[0-9a-f]+\] "
                          r"(silence_start: -?[\d.]+|silence_end: [\d.]+ \| silence_duration: [\d.]+)\s*$")


def shape(value: Any) -> Any:
    """Keys and value types of a JSON value, ignoring the values themselves."""
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(item) for item in value[:1]]
    return type(value).__name__


def silence_lines(log: str) -> list[str]:
    return [line for line in log.splitlines() if "silence_" in line]


@pytest.mark.heavy
def test_fixtures_match_real_tool_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    voice = write_wav(tmp_path / "voice.wav", 12.0, constants.VOICE_SAMPLE_RATE)
    video = make_video(tmp_path / "v.mp4", 12.0, silent_from=4, silent_to=6.5)
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
    report = f"real ffprobe output:\n{probes}\nreal silencedetect output:\n{silence}"
    for real, name in zip(probes, ("ffprobe_video.json", "ffprobe_voice.json"), strict=True):
        fixture = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        # Only what qa reads; other top-level keys vary with the FFmpeg version.
        read = ("streams", "format")
        real_read = {k: json.loads(real).get(k) for k in read}
        assert shape(real_read) == shape({k: fixture.get(k) for k in read}), report
    real_lines = silence_lines(silence)
    assert real_lines and all(SILENCE_LINE.match(line) for line in real_lines), report
    fixture_lines = silence_lines((FIXTURES / "silencedetect.log").read_text(encoding="utf-8"))
    assert all(SILENCE_LINE.match(line) for line in fixture_lines)
