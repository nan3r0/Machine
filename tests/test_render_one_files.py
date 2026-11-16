"""What render() writes and where (task p1-qa-tests, QA lead item 11). Every step is faked."""

from pathlib import Path

import pytest

from pipeline import constants, render_one
from pipeline.render import captions_ass, compose, qa
from pipeline.schema import WordTiming
from pipeline.voice import align, kokoro
from tests.test_render_one import SAMPLE, Fakes

CAPTIONS = "[Script Info]\nTitle: café «1938» 日本 {\\b1}\n"


class CaptionFakes(Fakes):
    def build_ass(self, timings: list[WordTiming], *args: object, **kwargs: object) -> str:
        super().build_ass(timings)
        return CAPTIONS


@pytest.fixture
def steps(monkeypatch: pytest.MonkeyPatch) -> CaptionFakes:
    f = CaptionFakes()
    monkeypatch.setattr(kokoro, "synthesize", f.synthesize)
    monkeypatch.setattr(align, "align_words", f.align_words)
    monkeypatch.setattr(captions_ass, "build_ass", f.build_ass)
    monkeypatch.setattr(compose, "compose", f.compose)
    monkeypatch.setattr(qa, "run_qa", f.run_qa)
    return f


def test_captions_file_holds_exactly_what_build_ass_returned(tmp_path: Path, steps: CaptionFakes) -> None:
    out = tmp_path / "out"
    render_one.render(SAMPLE, out, tmp_path / "models")
    assert (out / "captions.ass").read_bytes().decode("utf-8").replace("\r\n", "\n") == CAPTIONS


def test_compose_gets_the_committed_fonts(tmp_path: Path, steps: CaptionFakes) -> None:
    render_one.render(SAMPLE, tmp_path / "out", tmp_path / "models")
    assert steps.args("compose")[3] == Path(constants.FONTS_DIR)


def test_nested_out_dir_is_created(tmp_path: Path, steps: CaptionFakes) -> None:
    out = tmp_path / "out" / "a" / "b"
    assert render_one.render(SAMPLE, out, tmp_path / "models").passed
    assert (out / "qa.json").is_file()


def test_rendering_twice_into_one_folder_works(tmp_path: Path, steps: CaptionFakes) -> None:
    out = tmp_path / "out"
    render_one.render(SAMPLE, out, tmp_path / "models")
    assert render_one.render(SAMPLE, out, tmp_path / "models").passed
    assert (out / "captions.ass").read_bytes().decode("utf-8").replace("\r\n", "\n") == CAPTIONS
