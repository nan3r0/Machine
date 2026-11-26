"""PR body shows each scene's visual; exact check on data card values (task p3-batch-visuals).

Each scene line carries its set, pose and items as same-line code spans. An item label or value the
scene's cited facts do not back is flagged and the scene becomes a story scene keeping its set
(p3-plan D4), with no Gemini call.
"""

from pathlib import Path
from typing import Any

import pytest

from pipeline import constants as c
from pipeline.schema import Flag, Script, SourceFile
from pipeline.script import batch, generate
from tests.script.test_batch import capped_script, capped_source, run, setup

LONG_SET = max(c.SET_IDS, key=len)
LONG_POSE = max(c.POSES, key=len)


def visual(script: Script, index: int, kind: str, data: dict[str, Any]) -> Script:
    raw = script.model_dump()
    raw["scenes"][index]["visual"] = {"type": kind, "data": data}
    return Script.model_validate(raw)


def items(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"label": label, "value": value} for label, value in pairs]


def capped_with_visuals(n: int, src: SourceFile) -> Script:
    script = capped_script(n, src)
    for i in range(c.SCENES_MAX):
        script = visual(script, i, "story", {"set": LONG_SET, "pose": LONG_POSE})
    label, value = "L" * c.VISUAL_LABEL_MAX_CHARS, "9" * c.VISUAL_VALUE_MAX_CHARS
    full = items(*[(label, value)] * c.VISUAL_ITEMS_MAX)
    left = c.VISUAL_TEXT_MAX_CHARS - c.VISUAL_ITEMS_MAX * (len(label) + len(value))
    rest = (left // (c.VISUAL_DATA_SCENES_MAX - 1)) // 2
    script = visual(script, 0, "chart", {"set": LONG_SET, "pose": LONG_POSE, "items": full})
    for i in range(1, c.VISUAL_DATA_SCENES_MAX):
        script = visual(script, i, "chart", {"set": LONG_SET, "items": items(("M" * rest, "8" * rest))})
    return script


def test_body_with_visuals_at_every_cap_fits() -> None:
    written = [(capped_with_visuals(n, src), src) for n in range(1, 8) for src in [capped_source(n)]]
    reason = "r" * c.REASON_MAX_CHARS
    flags = [Flag(script_id=s.id, scene=i, reason=reason) for s, _ in written for i in range(c.SCENES_MAX)]
    flags += [Flag(script_id=s.id, scene=None, reason=reason) for s, _ in written]
    flags += [
        Flag(script_id=s.id, scene=i, reason=reason)
        for s, _ in written
        for i in range(c.VISUAL_DATA_SCENES_MAX)
    ]
    body = batch.pr_body(written, flags, [], exhausted=False)
    assert len(body) <= c.PR_BODY_MAX_CHARS


def test_scene_line_shows_set_pose_and_items() -> None:
    src = capped_source(1)
    script = visual(
        capped_script(1, src),
        2,
        "chart",
        {"set": "forest", "pose": "think", "items": items(("Apart, km", "3,219"))},
    )
    body = batch.pr_body([(script, src)], [], [], exhausted=False)
    line = next(ln for ln in body.splitlines() if ln.startswith("Scene 3:"))
    for text in ("forest", "think", "Apart, km", "3,219"):
        assert f" {text} `" in line or f"`{text}`" in line, text
    default = next(ln for ln in body.splitlines() if ln.startswith("Scene 1:"))
    assert default.count("`") >= 4, "the default visual is shown too"


def inject(monkeypatch: pytest.MonkeyPatch, data: dict[str, Any], kind: str) -> None:
    original = generate.write_script

    def write(source: SourceFile, script_id: str, publish_after: Any) -> Script:
        return visual(original(source, script_id, publish_after), 0, kind, data)

    monkeypatch.setattr(generate, "write_script", write)


def test_unbacked_value_is_flagged_and_becomes_story(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = setup(tmp_path, monkeypatch, count=1)
    inject(monkeypatch, {"set": "forest", "items": items(("Harbor Office", "9,999"))}, "chart")
    run(dirs)
    scene = next(iter(dirs.written().values())).scenes[0]
    assert scene.visual.type == "story" and scene.visual.data == {"set": "forest"}
    flag_lines = [ln for ln in dirs.body().splitlines() if "9,999" in ln]
    assert flag_lines and any("1" in ln for ln in flag_lines)
    assert sum(1 for call in fake.calls if call[2] == "rewrite") == 0


def test_backed_items_are_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, _ = setup(tmp_path, monkeypatch, count=1)
    data = {"set": "archive", "items": items(("Harbor Office", "1902"))}
    inject(monkeypatch, data, "steps")
    run(dirs)
    scene = next(iter(dirs.written().values())).scenes[0]
    assert scene.visual.type == "steps" and scene.visual.data == data


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_body_with_visuals_at_every_cap_fits()
    test_scene_line_shows_set_pose_and_items()
    test_unbacked_value_is_flagged_and_becomes_story(tmp_path, monkeypatch)
