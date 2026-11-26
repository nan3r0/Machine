"""render_one writes scenes.ass and composes it under the captions (task p3-wiring, milestone M1).

The heavy acceptance renders both demo scripts, checks QA and the render budget, and writes frames
for visual QA to out/frames/: golden frames, a strip of GOLDEN_STRIP_FRAMES frames
GOLDEN_STRIP_STEP_S apart across the host intro's end, and as many consecutive full-resolution
frames from the middle of the first story scene.
"""

import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants, render_one
from pipeline.render import compose
from pipeline.schema import Script, WordTiming
from pipeline.visuals import router
from pipeline.voice import align
from tests.media import FRAMES_DIR, duration, extract_frames
from tests.test_render_one import SAMPLE, Fakes, fakes  # noqa: F401  (fakes is a fixture)

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "fixtures" / "scripts" / "demo-data.json"
SCENES_TEXT = "[Script Info]\n; scenes\n"


def test_writes_scenes_ass_and_passes_it_to_compose(
    fakes: Fakes,  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[Script, list[WordTiming]]] = []

    def build(script: Script, timings: list[WordTiming]) -> str:
        seen.append((script, timings))
        fakes.calls.append(("scenes", (script,)))
        return SCENES_TEXT

    monkeypatch.setattr(router, "build_scenes_ass", build)
    out = tmp_path / "out"
    render_one.render(SAMPLE, out, tmp_path / "cache")
    scenes = out / "scenes.ass"
    assert scenes.read_text(encoding="utf-8") == SCENES_TEXT
    assert fakes.compose_kwargs.get("scenes") == scenes
    steps = fakes.steps()
    assert steps.index("align") < steps.index("scenes") < steps.index("compose")
    assert [t.word for t in seen[0][1]] == seen[0][0].narration_words()


def strip_and_steps(video: Path, prefix: str, scene_change: float) -> None:
    n, step = constants.GOLDEN_STRIP_FRAMES, constants.GOLDEN_STRIP_STEP_S
    start = max(0.0, scene_change - step * n / 2)
    extract_frames(video, f"{prefix}-strip", tuple(round(start + k * step, 2) for k in range(n)))
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{scene_change + 2.0:.2f}",
            "-i",
            str(video),
            "-frames:v",
            str(n),
            str(FRAMES_DIR / f"{prefix}-step-%02d.png"),
        ],
        check=True,
    )


@pytest.mark.heavy
@pytest.mark.parametrize("script_path", [SAMPLE, DEMO], ids=["sample-65s", "demo-data"])
def test_acceptance(script_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_compose, real_align = compose.compose, align.align_words
    spent: list[float] = []
    timings: list[WordTiming] = []

    def timed(*args: Any, **kwargs: Any) -> Path:
        began = time.monotonic()
        result = real_compose(*args, **kwargs)
        spent.append(time.monotonic() - began)
        return result

    def aligned(*args: Any, **kwargs: Any) -> list[WordTiming]:
        timings.extend(real_align(*args, **kwargs))
        return timings

    monkeypatch.setattr(compose, "compose", timed)
    monkeypatch.setattr(align, "align_words", aligned)
    out = tmp_path / "out"
    report = render_one.render(script_path, out, ROOT.parent / render_one.DEFAULT_CACHE_DIR)
    assert report.passed, report.failures
    assert (out / "scenes.ass").is_file()
    assert spent and spent[0] < constants.RENDER_BUDGET_S, f"compose took {spent[0]:.0f} s"
    video = out / "final.mp4"
    prefix = script_path.stem
    end = duration(video) - constants.GOLDEN_END_OFFSET_S
    extract_frames(video, f"{prefix}-golden", (*constants.GOLDEN_FRAME_TIMES_S, end))
    script = Script.model_validate_json(script_path.read_text(encoding="utf-8"))
    strip_and_steps(video, prefix, router.scene_spans(script, timings)[0].end)
