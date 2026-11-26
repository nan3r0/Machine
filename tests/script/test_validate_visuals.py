"""Scene visual data rules (task p3-validate-visuals, .harness/handoffs/p3-plan.md "Scene format").

Every key of `visual.data` is optional; only set, pose, camera and items are allowed. Messages name
the scene (1-based) and the field. Caps come from pipeline/constants.py.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants as c
from pipeline.schema import Script
from pipeline.script import validate

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE = json.loads((ROOT / "queue" / "approved" / "sample-65s.json").read_text(encoding="utf-8"))
DEMO = ROOT / "tests" / "fixtures" / "scripts" / "demo-data.json"


def with_visual(index: int, kind: str, data: dict[str, Any]) -> Script:
    scenes = [dict(s) for s in SAMPLE["scenes"]]
    scenes[index] = {**scenes[index], "visual": {"type": kind, "data": data}}
    return Script.model_validate({**SAMPLE, "scenes": scenes})


def items(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in pairs]


def problems_for(script: Script, scene: int, field: str) -> list[str]:
    return [p for p in validate.problems(script) if f"scene {scene}" in p and field in p]


def test_phase2_empty_data_stays_valid() -> None:
    scenes = [{**s, "visual": {"type": "story", "data": {}}} for s in SAMPLE["scenes"]]
    assert validate.problems(Script.model_validate({**SAMPLE, "scenes": scenes})) == []


@pytest.mark.parametrize(
    "data",
    [{"set": s} for s in c.SET_IDS]
    + [{"pose": p} for p in c.POSES]
    + [{"camera": m} for m in c.CAMERA_MOVES],
)
def test_every_allowed_value_passes(data: dict[str, Any]) -> None:
    assert validate.problems(with_visual(1, "story", data)) == []


@pytest.mark.parametrize(
    ("kind", "data", "field"),
    [
        ("story", {"mood": "dark"}, "mood"),
        ("story", {"set": c.HOST_BACKDROP_SET}, "set"),
        ("story", {"set": "moon"}, "set"),
        ("story", {"set": 3}, "set"),
        ("story", {"pose": "dance"}, "pose"),
        ("story", {"camera": "zoom"}, "camera"),
        ("story", {"items": items(("Heard", "1997"))}, "items"),
        ("chart", {"items": []}, "items"),
        ("chart", {"items": items(*[("A", "1")] * (c.VISUAL_ITEMS_MAX + 1))}, "items"),
        ("chart", {"items": "1997"}, "items"),
        ("chart", {"items": [{"label": "A"}]}, "items"),
        ("chart", {"items": [{"label": "A", "value": "1", "colour": "red"}]}, "items"),
        ("chart", {"items": [{"label": "A", "value": 1}]}, "items"),
        ("chart", {"items": items(("  ", "1"))}, "label"),
        ("chart", {"items": items(("x" * (c.VISUAL_LABEL_MAX_CHARS + 1), "1"))}, "label"),
        ("chart", {"items": items(("A", "1" * (c.VISUAL_VALUE_MAX_CHARS + 1)))}, "value"),
        ("chart", {"items": items(("A", "1"), ("B", "lots"))}, "value"),
        ("steps", {"items": items(("A", "1997"), ("B", ""))}, "value"),
        ("map", {"items": items(("Pacific", ""), ("Antarctica", ""))}, "items"),
        ("chart", {"items": items(("see www.evil.example", "1"))}, "URL"),
        ("chart", {"items": items(("A", "<b>1"))}, "<"),
        ("chart", {"items": items(("A", "١٢"))}, "number"),
        ("chart", {"items": items(("A​", "1"))}, "invisible"),
    ],
)
def test_bad_visual_named_by_scene_and_field(kind: str, data: dict[str, Any], field: str) -> None:
    assert problems_for(with_visual(1, kind, data), 2, field), validate.problems(with_visual(1, kind, data))


def test_one_number_or_text_counter_and_year_steps_pass() -> None:
    assert validate.problems(with_visual(1, "chart", {"items": items(("Apart, km", "3,219"))})) == []
    assert validate.problems(with_visual(1, "chart", {"items": items(("Time", "eight years"))})) == []
    assert validate.problems(with_visual(1, "steps", {"items": items(("Listen", ""), ("Find", ""))})) == []
    assert validate.problems(with_visual(1, "map", {"items": items(("Antarctica", "far south"))})) == []


def test_data_scene_and_text_totals_are_capped() -> None:
    scenes = [dict(s) for s in SAMPLE["scenes"]]
    for i in range(c.VISUAL_DATA_SCENES_MAX + 1):
        scenes[i] = {**scenes[i], "visual": {"type": "chart", "data": {"items": items(("A", "1"))}}}
    too_many = Script.model_validate({**SAMPLE, "scenes": scenes})
    assert any("data scenes" in p for p in validate.problems(too_many))
    label = "x" * c.VISUAL_LABEL_MAX_CHARS
    value = "1" * c.VISUAL_VALUE_MAX_CHARS
    scenes = [dict(s) for s in SAMPLE["scenes"]]
    for i in range(2):
        scenes[i] = {
            **scenes[i],
            "visual": {"type": "chart", "data": {"items": items(*[(label, value)] * 4)}},
        }
    long_text = Script.model_validate({**SAMPLE, "scenes": scenes})
    assert 2 * 4 * (len(label) + len(value)) > c.VISUAL_TEXT_MAX_CHARS
    assert any("items" in p and str(c.VISUAL_TEXT_MAX_CHARS) in p for p in validate.problems(long_text))


def test_demo_fixture_is_valid() -> None:
    assert validate.problems(Script.model_validate_json(DEMO.read_text(encoding="utf-8"))) == []


def test_acceptance() -> None:
    test_phase2_empty_data_stays_valid()
    assert validate.problems(Script.model_validate(SAMPLE)) == []
    test_demo_fixture_is_valid()
    test_bad_visual_named_by_scene_and_field("story", {"set": c.HOST_BACKDROP_SET}, "set")
    test_data_scene_and_text_totals_are_capped()
