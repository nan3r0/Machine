"""The writer picks each scene's visual in the same Gemini call (task p3-writer-visuals).

Each writer scene adds flat fields `visual_type`, `set`, `pose`, `camera` (enums from constants)
and `items` ({label, value} strings). A story scene becomes `{"type": "story", "data": {set, pose,
camera}}`; a data scene adds `items`. A scene whose visual breaks a validate rule becomes
`{"type": "story", "data": {}}` in code, with no error and no extra call.
"""

import json
from typing import Any

import pytest

from pipeline import constants as c
from pipeline.script import generate
from tests.script.scripts import FILLER
from tests.script.test_generate import PUBLISH, SOURCE, answer, install

STORY = {"visual_type": "story", "set": "forest", "pose": "think", "camera": "still", "items": []}
CHART = {
    "visual_type": "chart",
    "set": "archive",
    "pose": "talk",
    "camera": "push_in",
    "items": [{"label": "Apart, km", "value": "3,219"}],
}


def with_visuals(*visuals: dict[str, Any]) -> dict[str, Any]:
    scenes = answer()["scenes"]
    return answer(scenes=[{**s, **visuals[i % len(visuals)]} for i, s in enumerate(scenes)])


def scene_schema() -> dict[str, Any]:
    schema = generate._WRITER_SCHEMA
    return schema["properties"]["scenes"]["items"]  # type: ignore[no-any-return]


def test_schema_has_flat_visual_enums_and_no_anyof() -> None:
    props = scene_schema()["properties"]
    assert props["visual_type"]["enum"] == ["chart", "map", "steps", "story"] or sorted(
        props["visual_type"]["enum"]
    ) == ["chart", "map", "steps", "story"]
    assert sorted(props["set"]["enum"]) == sorted(c.SET_IDS)
    assert sorted(props["pose"]["enum"]) == sorted(c.POSES)
    assert sorted(props["camera"]["enum"]) == sorted(c.CAMERA_MOVES)
    assert set(props["items"]["items"]["properties"]) == {"label", "value"}
    assert "anyOf" not in json.dumps(generate._WRITER_SCHEMA)


def test_visuals_map_to_scene_data_in_one_call(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, with_visuals(STORY, CHART))
    script = generate.write_script(SOURCE, "the-bloop", PUBLISH)
    assert len(fake.calls) == 1
    first, second = script.scenes[0].visual, script.scenes[1].visual
    assert first.type == "story" and first.data == {"set": "forest", "pose": "think", "camera": "still"}
    assert second.type == "chart"
    assert second.data == {
        "set": "archive",
        "pose": "talk",
        "camera": "push_in",
        "items": [{"label": "Apart, km", "value": "3,219"}],
    }


@pytest.mark.parametrize(
    "bad",
    [
        {**STORY, "set": "moon"},
        {**STORY, "set": c.HOST_BACKDROP_SET},
        {**STORY, "pose": "dance"},
        {**CHART, "items": [{"label": "A", "value": "1"}] * (c.VISUAL_ITEMS_MAX + 1)},
        {**CHART, "items": [{"label": "see www.evil.example", "value": "1"}]},
        {**CHART, "visual_type": "map", "items": []},
    ],
    ids=["set", "backdrop", "pose", "too many items", "url label", "map without items"],
)
def test_broken_visual_falls_back_without_a_retry(
    bad: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = install(monkeypatch, with_visuals(bad, STORY))
    script = generate.write_script(SOURCE, "the-bloop", PUBLISH)
    assert len(fake.calls) == 1
    assert script.scenes[0].visual.type == "story" and script.scenes[0].visual.data == {}
    assert script.scenes[1].visual.data == {"set": "forest", "pose": "think", "camera": "still"}


def test_too_many_data_scenes_fall_back_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, with_visuals(CHART))
    script = generate.write_script(SOURCE, "the-bloop", PUBLISH)
    kinds = [s.visual.type for s in script.scenes]
    assert kinds.count("chart") == c.VISUAL_DATA_SCENES_MAX
    assert kinds[: c.VISUAL_DATA_SCENES_MAX] == ["chart"] * c.VISUAL_DATA_SCENES_MAX


def test_rewrite_line_keeps_the_visual(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, with_visuals(CHART, STORY), {"narration": FILLER})
    script = generate.write_script(SOURCE, "the-bloop", PUBLISH)
    rewritten = generate.rewrite_line(script, 0, SOURCE, "a number is not in the facts")
    assert rewritten.scenes[0].visual == script.scenes[0].visual


def test_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    test_schema_has_flat_visual_enums_and_no_anyof()
    test_visuals_map_to_scene_data_in_one_call(monkeypatch)
    test_broken_visual_falls_back_without_a_retry({**STORY, "set": "moon"}, monkeypatch)
