"""R12.2: render_one stops before the voice step for a script outside TIKTOK_WORDS (task p2-validate,
phase review N5). A 45 minute render of an oversized script is what this avoids."""

from pathlib import Path
from typing import Any

import pytest

from pipeline import constants, render_one
from pipeline.voice import kokoro
from tests.script.scripts import make_script, script_with_words


def voice_calls(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    calls: list[Any] = []

    def synthesize(*args: Any, **kwargs: Any) -> None:
        calls.append(args)
        raise RuntimeError("stop after the voice step")

    monkeypatch.setattr(kokoro, "synthesize", synthesize)
    return calls


@pytest.mark.parametrize("count", [constants.TIKTOK_WORDS[0] - 1, constants.TIKTOK_WORDS[1] + 1])
def test_word_count_outside_bounds_exits_2_before_voice(
        count: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    calls = voice_calls(monkeypatch)
    path = tmp_path / "script.json"
    path.write_text(script_with_words(count).model_dump_json(), encoding="utf-8")
    assert render_one.main([str(path), str(tmp_path / "out")]) == 2
    assert calls == []
    out = capsys.readouterr()
    assert "word" in out.out + out.err


def test_publishable_problem_exits_2_before_voice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = voice_calls(monkeypatch)
    path = tmp_path / "script.json"
    path.write_text(make_script(title="see www.evil.example").model_dump_json(), encoding="utf-8")
    assert render_one.main([str(path), str(tmp_path / "out")]) == 2
    assert calls == []


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A short script never reaches the voice step; a good one does."""
    calls = voice_calls(monkeypatch)
    short = tmp_path / "short.json"
    short.write_text(script_with_words(40).model_dump_json(), encoding="utf-8")
    assert render_one.main([str(short), str(tmp_path / "a")]) == 2
    assert calls == []
    good = tmp_path / "good.json"
    good.write_text(make_script().model_dump_json(), encoding="utf-8")
    assert render_one.main([str(good), str(tmp_path / "b")]) == 2  # the fake voice step raises
    assert len(calls) == 1
