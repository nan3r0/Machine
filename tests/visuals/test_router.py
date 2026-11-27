"""Visual router (task p3-router): host intro first, story scenes in order, host outro last,
contiguous spans; fallbacks; the whole scenes.ass."""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pipeline import constants as c
from pipeline.schema import Script, WordTiming
from pipeline.visuals import art, router
from tests.visuals.ass_parse import drawing, events, shown_text, visible

ROOT = Path(__file__).resolve().parent.parent.parent
BASE = json.loads((ROOT / "queue" / "approved" / "sample-65s.json").read_text(encoding="utf-8"))


def from_json(data: dict[str, Any]) -> Script:
    """Script is strict, so dates must come through JSON, as script files are parsed."""
    return Script.model_validate_json(json.dumps(data))


def fake_set(name: str) -> art.SetArt:
    """A two-layer set whose far path has a height unique to `name`, so tests can tell sets apart."""
    height = 100 + sum(map(ord, name)) % 1500
    return art.SetArt.model_validate(
        {
            "name": name,
            "outline_colour": "ink",
            "palette": {"ink": "000000"},
            "layers": [
                {
                    "depth": "far",
                    "shapes": [
                        {"layer": 0, "fill": "ink", "outline": 0, "path": f"m 0 0 l 1080 0 l 1080 {height}"}
                    ],
                },
                {
                    "depth": "near",
                    "shapes": [
                        {"layer": 1, "fill": "ink", "outline": 0, "path": "m 0 1000 l 900 1000 l 900 1900"}
                    ],
                },
            ],
        }
    )


SET = art.SetArt.model_validate(
    {
        "name": "fixture",
        "outline_colour": "ink",
        "palette": {"ink": "000000"},
        "layers": [
            {
                "depth": "far",
                "shapes": [{"layer": 0, "fill": "ink", "outline": 0, "path": "m 0 0 l 1080 0 l 1080 900"}],
            },
            {
                "depth": "near",
                "shapes": [
                    {"layer": 1, "fill": "ink", "outline": 0, "path": "m 0 1000 l 900 1000 l 900 1900"}
                ],
            },
        ],
    }
)


def script(
    hook: int,
    scenes: list[int],
    loop: int,
    data: list[dict[str, Any]] | None = None,
    types: list[str] | None = None,
) -> Script:
    word = "word"
    return from_json(
        {
            **BASE,
            "hook": " ".join([word] * hook),
            "loop_line": " ".join([word] * loop),
            "scenes": [
                {
                    "narration": " ".join([word] * n),
                    "on_screen_text": "",
                    "visual": {
                        "type": (types or ["story"] * len(scenes))[i],
                        "data": (data or [{}] * len(scenes))[i],
                    },
                    "source_fact_ids": [1],
                }
                for i, n in enumerate(scenes)
            ],
        }
    )


def timings_for(s: Script, step: float = 0.4, gap: float = 0.0) -> list[WordTiming]:
    return [
        WordTiming(word=w, start=i * (step + gap), end=i * (step + gap) + step)
        for i, w in enumerate(s.narration_words())
    ]


@given(
    st.integers(1, 20),
    st.lists(st.integers(1, 30), min_size=1, max_size=10),
    st.integers(1, 30),
    st.floats(0.1, 0.8),
    st.floats(0.0, 0.5),
)
def test_spans_intro_scenes_outro_contiguous(
    hook: int, scenes: list[int], loop: int, step: float, gap: float
) -> None:
    s = script(hook, scenes, loop)
    timings = timings_for(s, step, gap)
    spans = router.scene_spans(s, timings)
    assert [sp.kind for sp in spans] == ["intro", *["scene"] * len(scenes), "outro"]
    assert [sp.index for sp in spans[1:-1]] == list(range(len(scenes)))
    assert spans[0].start == 0 and spans[-1].end == timings[-1].end
    assert all(sp.start <= sp.end for sp in spans)
    assert all(a.end == b.start for a, b in zip(spans, spans[1:], strict=False)), (
        "ordered, no gap, no overlap"
    )
    scene0 = timings[hook].start
    assert spans[0].end == pytest.approx(min(scene0, c.HOST_INTRO_MAX_S))
    loop_start = timings[len(timings) - loop].start
    assert spans[-1].start == pytest.approx(max(loop_start, timings[-1].end - c.HOST_OUTRO_MAX_S))
    first = hook
    for k in range(1, len(scenes)):
        first += scenes[k - 1]
        assert spans[1 + k].start == pytest.approx(timings[first].start)


def test_word_count_mismatch_raises() -> None:
    s = script(3, [5, 5], 4)
    with pytest.raises(ValueError):
        router.scene_spans(s, timings_for(s)[:-1])


def test_empty_data_falls_back_to_defaults() -> None:
    s = script(3, [5, 5], 4)
    plans = router.scene_plan(s)
    assert [(p.set_id, p.pose, p.camera, p.layout) for p in plans] == [
        (c.DEFAULT_SET[s.template], c.DEFAULT_POSE, c.DEFAULT_CAMERA, "story")
    ] * 2


def test_layouts_and_explicit_choices() -> None:
    data = [
        {"set": "forest", "pose": "think", "camera": "still"},
        {"items": [{"label": "Apart", "value": "3,219"}]},
        {"items": [{"label": "A", "value": "1"}, {"label": "B", "value": "2"}]},
        {"items": [{"label": "Heard", "value": "1997"}, {"label": "Found", "value": "2005"}]},
        {"items": [{"label": "Listen", "value": ""}, {"label": "Find", "value": ""}]},
        {"items": [{"label": "Antarctica", "value": ""}]},
        {"set": "archive"},
    ]
    types = ["story", "chart", "chart", "steps", "steps", "map", "chart"]
    plans = router.scene_plan(script(3, [4] * 7, 4, data, types))
    assert (plans[0].set_id, plans[0].pose, plans[0].camera) == ("forest", "think", "still")
    assert [p.layout for p in plans] == ["story", "counter", "bars", "timeline", "steps", "place", "story"]
    assert plans[3].items == (("Heard", "1997"), ("Found", "2005"))


def test_scenes_ass_host_intro_and_outro_on_the_backdrop(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded: list[str] = []
    monkeypatch.setattr(art, "load_set", lambda set_id, *a, **k: loaded.append(set_id) or fake_set(set_id))
    tagged = r"{\an1}Bloop\N"
    data = [
        {"set": "forest"},
        {"items": [{"label": "Apart", "value": "3,219"}]},
        {},
        {"items": [{"label": tagged, "value": "3,219"}, {"label": "Whale", "value": "0"}]},
    ]
    s = script(4, [10, 10, 10, 10], 12, data, ["story", "chart", "story", "chart"])
    timings = timings_for(s)
    text = router.build_scenes_ass(s, timings)
    assert text.startswith("[Script Info]")
    assert not any(ord(ch) < 0x20 and ch not in "\r\n" for ch in text), "control byte in scenes.ass"
    assert c.HOST_BACKDROP_SET in loaded and "forest" in loaded and c.DEFAULT_SET[s.template] in loaded
    evs = events(text)
    body = {sh.path for sh in art.load_host().body}
    spans = router.scene_spans(s, timings)

    def drawn(t: float) -> set[str | None]:
        return {drawing(e.text) for e in visible(evs, t)}

    def far(set_id: str) -> str:
        return fake_set(set_id).layers[0].shapes[0].path

    def layer_at(layer: int, t: float) -> list[str]:
        return [e.text for e in visible(evs, t) if e.layer == layer]

    for sp in spans:
        mid = (sp.start + sp.end) / 2
        data_scene = sp.index in (1, 3)
        assert (body <= drawn(mid)) == (not data_scene), sp
        assert bool(layer_at(c.ASS_LAYER_DIM, mid)) == data_scene, f"only data scenes dim the set: {sp}"
    intro, first, outro = spans[0], spans[1], spans[-1]
    for sp in (intro, outro):
        mid = (sp.start + sp.end) / 2
        assert far(c.HOST_BACKDROP_SET) in drawn(mid) and far("forest") not in drawn(mid), sp
    first_mid = (first.start + first.end) / 2
    assert far("forest") in drawn(first_mid) and far(c.HOST_BACKDROP_SET) not in drawn(first_mid)
    transition = rf"\fad(0,{round(c.HOST_TRANSITION_S * 1000)})"
    for sp in (first, outro):
        fades = layer_at(c.ASS_LAYER_FADE, sp.start)
        assert any(transition in f for f in fades), f"{c.HOST_TRANSITION_S} s transition at {sp}"
    story = spans[3]
    scene_fade = rf"\fad(0,{round(c.SCENE_FADE_S * 1000)})"
    assert any(scene_fade in f for f in layer_at(c.ASS_LAYER_FADE, story.start)), "story scene fade-in"
    chart = spans[2]
    assert any("3,219" in shown_text(e.text) for e in visible(evs, chart.end - 0.05))
    bars = [shown_text(e.text) for e in visible(evs, spans[4].end - 0.05)]
    assert any(tagged in t for t in bars), "an override tag in a label is shown, not applied"
    assert max(e.end for e in evs) >= timings[-1].end + c.SCENE_TAIL_S - 0.01


def test_empty_data_still_has_intro_and_outro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(art, "load_set", lambda set_id, *a, **k: SET)
    s = from_json(
        {**BASE, "scenes": [{**sc, "visual": {"type": "story", "data": {}}} for sc in BASE["scenes"]]}
    )
    spans = router.scene_spans(s, timings_for(s))
    assert spans[0].kind == "intro" and spans[-1].kind == "outro" and len(spans) == len(s.scenes) + 2
    assert events(router.build_scenes_ass(s, timings_for(s)))


def test_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    test_spans_intro_scenes_outro_contiguous()
    test_word_count_mismatch_raises()
    test_empty_data_falls_back_to_defaults()
    test_layouts_and_explicit_choices()
    test_scenes_ass_host_intro_and_outro_on_the_backdrop(monkeypatch)
