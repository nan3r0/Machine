"""voice.wav's levels reach the host (task p3b-lipsync-wiring).

render_one calls `levels.voice_levels(voice.wav)` through its module after the voice is written
and passes the result to `router.build_scenes_ass(..., levels=...)`, which hands it unchanged to
every host_events call.
"""

from pathlib import Path
from typing import Any

import pytest

from pipeline import render_one
from pipeline.schema import Script, WordTiming
from pipeline.visuals import art, router
from pipeline.voice import levels
from tests.test_render_one import SAMPLE, Fakes, fakes  # noqa: F401  (fakes is a fixture)
from tests.visuals.test_router import BASE, SET, from_json, timings_for

LEVELS = [0.0, 0.5, 1.0, 0.25]


def test_render_one_passes_the_voice_levels_to_the_scenes(
    fakes: Fakes,  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read: list[Path] = []
    built: list[dict[str, Any]] = []

    def voice_levels(wav: Path) -> list[float]:
        read.append(wav)
        assert wav.is_file(), "levels are read after the voice is written"
        return LEVELS

    def build(script: Script, timings: list[WordTiming], **kwargs: Any) -> str:
        built.append(kwargs)
        return "[Script Info]\n"

    monkeypatch.setattr(levels, "voice_levels", voice_levels)
    monkeypatch.setattr(router, "build_scenes_ass", build)
    out = tmp_path / "out"
    render_one.render(SAMPLE, out, tmp_path / "cache")
    assert read == [out / "voice.wav"]
    assert len(built) == 1 and built[0].get("levels") is LEVELS


def test_router_hands_the_levels_to_every_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(art, "load_set", lambda set_id, *a, **k: SET)
    got: list[Any] = []

    def host_events(*args: Any, **kwargs: Any) -> list[str]:
        got.append(kwargs.get("levels"))
        return []

    monkeypatch.setattr(router, "host_events", host_events)
    s = from_json(BASE)
    router.build_scenes_ass(s, timings_for(s), levels=LEVELS)
    assert len(got) >= 2 and all(g is LEVELS for g in got), got


def test_acceptance(fakes: Fakes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    # Separate scopes: the render half fakes router.build_scenes_ass, which the router half needs real.
    with monkeypatch.context() as m:
        test_render_one_passes_the_voice_levels_to_the_scenes(fakes, tmp_path, m)
    with monkeypatch.context() as m:
        test_router_hands_the_levels_to_every_host(m)
