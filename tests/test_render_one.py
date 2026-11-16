"""R6.2, R6.3 and the golden render: one script JSON to final.mp4 (task p1-render-cli)."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants, render_one
from pipeline.render import captions_ass, compose, qa
from pipeline.render.compose import ComposeError
from pipeline.schema import QAFailure, QAReport, Script, WordTiming
from pipeline.voice import align, kokoro
from pipeline.voice.kokoro import VoiceError
from tests import media
from tests.wavs import write_wav

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "queue" / "approved" / "sample-40s.json"
SCRIPT = Script.model_validate_json(SAMPLE.read_text(encoding="utf-8"))
PASS = QAReport(passed=True, failures=[], measured={"duration_s": 40.0})
FAIL = QAReport(passed=False, failures=[QAFailure(check="silence", reason="2.4 s silence > 1.5 s")],
                measured={"longest_silence_s": 2.4})


class Fakes:
    """Stand-ins for every step, recording the order and arguments of each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.report = PASS
        self.voice_error: Exception | None = None
        self.compose_error: Exception | None = None

    def synthesize(self, text: str, out_path: Path, cache_dir: Path, *args: Any, **kwargs: Any) -> Path:
        self.calls.append(("voice", (text, out_path, cache_dir)))
        if self.voice_error:
            raise self.voice_error
        return write_wav(out_path, 1.0, constants.VOICE_SAMPLE_RATE)

    def align_words(self, audio: Path, text: str, cache_dir: Path) -> list[WordTiming]:
        self.calls.append(("align", (audio, text, cache_dir)))
        return [WordTiming(word=w, start=i * 0.3, end=i * 0.3 + 0.25) for i, w in enumerate(text.split())]

    def build_ass(self, timings: list[WordTiming], *args: Any, **kwargs: Any) -> str:
        self.calls.append(("captions", (timings,)))
        return "[Script Info]\n"

    def compose(self, voice: Path, captions: Path, out: Path, fonts_dir: Path, log_path: Path) -> Path:
        self.calls.append(("compose", (voice, captions, out, fonts_dir, log_path)))
        if self.compose_error:
            raise self.compose_error
        out.write_bytes(b"mp4")
        return out

    def run_qa(self, video: Path, voice: Path, timings: list[WordTiming],
               script_words: list[str]) -> QAReport:
        self.calls.append(("qa", (video, voice, timings, script_words)))
        return self.report

    def steps(self) -> list[str]:
        return [name for name, _ in self.calls]

    def args(self, step: str) -> tuple[Any, ...]:
        return next(args for name, args in self.calls if name == step)


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> Fakes:
    f = Fakes()
    monkeypatch.setattr(kokoro, "synthesize", f.synthesize)
    monkeypatch.setattr(align, "align_words", f.align_words)
    monkeypatch.setattr(captions_ass, "build_ass", f.build_ass)
    monkeypatch.setattr(compose, "compose", f.compose)
    monkeypatch.setattr(qa, "run_qa", f.run_qa)
    return f


def write_script(tmp_path: Path, **changes: Any) -> Path:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is None:
            del data[key]
        else:
            data[key] = value
    path = tmp_path / "script.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.heavy
def test_acceptance(tmp_path: Path) -> None:
    """R6.2: the sample renders, passes QA and the CLI exits 0. Also the golden render checks."""
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, "-m", "pipeline.render_one", str(SAMPLE), str(out),
                             "--cache-dir", str(ROOT / render_one.DEFAULT_CACHE_DIR)],
                            cwd=ROOT, capture_output=True, text=True, timeout=1200)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    for name in ("voice.wav", "captions.ass", "final.mp4", "qa.json"):
        assert (out / name).exists(), name
    report = QAReport.model_validate_json((out / "qa.json").read_text(encoding="utf-8"))
    assert report.passed

    final = out / "final.mp4"
    video = media.stream(media.probe(final), "video")
    assert (video["width"], video["height"]) == (constants.WIDTH, constants.HEIGHT)
    low, high = constants.RETENTION_SECONDS
    assert low <= media.duration(final) <= high
    drift = abs(media.duration(final) - media.duration(out / "voice.wav"))
    assert drift <= constants.DURATION_MATCH_TOLERANCE_S

    ass = (out / "captions.ass").read_text(encoding="utf-8")
    dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) == len(SCRIPT.narration_words())
    for line in dialogues:
        positions = media.ASS_POS.findall("".join(media.ASS_OVERRIDE.findall(line)))
        assert len(positions) == 1, line
        x, y = map(float, positions[0])
        assert constants.SAFE_LEFT_PX <= x <= constants.SAFE_RIGHT_PX
        assert constants.SAFE_TOP_PX <= y <= constants.SAFE_BOTTOM_PX

    assert max(constants.GOLDEN_FRAME_TIMES_S) < media.duration(final)
    frames = media.extract_frames(final, "golden", constants.GOLDEN_FRAME_TIMES_S)
    assert all(f.stat().st_size > 0 for f in frames)


def test_steps_run_in_order_and_files_are_written(tmp_path: Path, fakes: Fakes) -> None:
    out = tmp_path / "out"
    assert render_one.main([str(SAMPLE), str(out)]) == 0
    assert fakes.steps() == ["voice", "align", "captions", "compose", "qa"]
    for name in ("voice.wav", "captions.ass", "final.mp4", "qa.json"):
        assert (out / name).exists(), name
    assert QAReport.model_validate_json((out / "qa.json").read_text(encoding="utf-8")).passed


def test_steps_get_the_script_text_and_paths(tmp_path: Path, fakes: Fakes) -> None:
    out = tmp_path / "out"
    render_one.main([str(SAMPLE), str(out), "--cache-dir", str(tmp_path / "models")])
    text, voice_path, cache_dir = fakes.args("voice")
    assert text == SCRIPT.narration_text()
    assert voice_path == out / "voice.wav"
    assert cache_dir == tmp_path / "models"
    assert fakes.args("align") == (out / "voice.wav", SCRIPT.narration_text(), tmp_path / "models")
    _, captions, final, _, log = fakes.args("compose")
    assert (captions, final, log) == (out / "captions.ass", out / "final.mp4", out / "logs" / "compose.log")
    video, voice, timings, words = fakes.args("qa")
    assert (video, voice, words) == (out / "final.mp4", out / "voice.wav", SCRIPT.narration_words())
    assert [t.word for t in timings] == SCRIPT.narration_words()


def test_default_cache_dir(tmp_path: Path, fakes: Fakes) -> None:
    render_one.main([str(SAMPLE), str(tmp_path / "out")])
    assert fakes.args("voice")[2] == render_one.DEFAULT_CACHE_DIR
    assert fakes.args("align")[2] == render_one.DEFAULT_CACHE_DIR


def test_qa_failure_exits_non_zero_and_names_checks(tmp_path: Path, fakes: Fakes,
                                                    capsys: pytest.CaptureFixture[str]) -> None:
    """R6.3."""
    fakes.report = FAIL
    out = tmp_path / "out"
    assert render_one.main([str(SAMPLE), str(out)]) == 1
    printed = capsys.readouterr()
    assert "silence" in printed.out + printed.err
    assert "2.4 s silence" in printed.out + printed.err
    assert not QAReport.model_validate_json((out / "qa.json").read_text(encoding="utf-8")).passed
    assert (out / "final.mp4").exists()


@pytest.mark.parametrize("changes", [{"hook": None}, {"scenes": "nope"}, {"publish_after": "soon"}])
def test_invalid_script_exits_2_before_any_step(tmp_path: Path, fakes: Fakes, changes: dict[str, Any],
                                                capsys: pytest.CaptureFixture[str]) -> None:
    script = write_script(tmp_path, **changes)
    assert render_one.main([str(script), str(tmp_path / "out")]) == 2
    assert fakes.calls == []
    assert next(iter(changes)) in capsys.readouterr().err


def test_missing_script_file_exits_2(tmp_path: Path, fakes: Fakes) -> None:
    assert render_one.main([str(tmp_path / "missing.json"), str(tmp_path / "out")]) == 2
    assert fakes.calls == []


def test_non_utf8_script_exits_2(tmp_path: Path, fakes: Fakes) -> None:
    """Regression: UnicodeDecodeError escaped main() when only named step errors were caught."""
    script = tmp_path / "script.json"
    script.write_bytes(b"\xff\xfe\x00")
    assert render_one.main([str(script), str(tmp_path / "out")]) == 2
    assert fakes.calls == []


def test_voice_failure_stops_the_run(tmp_path: Path, fakes: Fakes,
                                     capsys: pytest.CaptureFixture[str]) -> None:
    fakes.voice_error = VoiceError("kokoro exploded")
    out = tmp_path / "out"
    assert render_one.main([str(SAMPLE), str(out)]) == 2
    assert fakes.steps() == ["voice"]
    assert "kokoro exploded" in capsys.readouterr().err
    assert not (out / "final.mp4").exists()


def test_compose_failure_exits_2(tmp_path: Path, fakes: Fakes, capsys: pytest.CaptureFixture[str]) -> None:
    fakes.compose_error = ComposeError("ffmpeg said no")
    assert render_one.main([str(SAMPLE), str(tmp_path / "out")]) == 2
    assert "qa" not in fakes.steps()
    assert "ffmpeg said no" in capsys.readouterr().err


def test_render_returns_the_report(tmp_path: Path, fakes: Fakes) -> None:
    fakes.report = FAIL
    assert render_one.render(SAMPLE, tmp_path / "out", tmp_path / "models") == FAIL
