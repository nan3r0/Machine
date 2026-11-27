"""Visual router: scene spans, per-scene plan and the whole scenes.ass (task p3-router).

Every video (owner 2026-11-26): the host intro (the hook) on the generic HOST_BACKDROP_SET, a
transition into the story scenes, then the host outro (the end of the loop line) on the same
backdrop. Trusts a validated script. The only file reads are art.load_host and art.load_set,
called through the `art` module so tests can replace them.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pipeline import constants as c
from pipeline.schema import Script, WordTiming
from pipeline.visuals import art, cards, charts
from pipeline.visuals.ass_kit import header
from pipeline.visuals.character import host_events
from pipeline.visuals.sets import set_events

Layout = Literal["story", "counter", "bars", "steps", "timeline", "place"]


@dataclass(frozen=True)
class Span:
    """A stretch of the video: the host intro, story scene `index` (0-based) or the host outro."""

    kind: Literal["intro", "scene", "outro"]
    index: int | None
    start: float
    end: float


@dataclass(frozen=True)
class ScenePlan:
    """How one scene is drawn, after the fallbacks."""

    set_id: str
    pose: str
    camera: str
    layout: Layout
    items: tuple[tuple[str, str], ...]


def scene_spans(script: Script, timings: list[WordTiming]) -> list[Span]:
    """Intro, one span per scene in order, outro. Contiguous: each span ends where the next starts.

    Word counts of the hook, each scene and the loop line (split as Script.narration_words
    splits them) map onto `timings`. Scene k starts at its first word's start, except scene 0,
    which starts where the intro ends. The intro runs from 0 to min(scene 0's first word start,
    HOST_INTRO_MAX_S). The outro runs from max(the loop line's first word start,
    timings[-1].end - HOST_OUTRO_MAX_S) to timings[-1].end. So a long hook or loop line keeps
    its words; the story scene next to it shows for the rest.
    Raises ValueError if len(timings) differs from the script's word count.
    """
    counts = [len(script.hook.split()), *(len(sc.narration.split()) for sc in script.scenes),
              len(script.loop_line.split())]
    if sum(counts) != len(timings):
        raise ValueError(f"script has {sum(counts)} words, timings has {len(timings)}")
    hook, loop = counts[0], counts[-1]
    intro_end = min(timings[hook].start, c.HOST_INTRO_MAX_S)
    outro_start = max(timings[len(timings) - loop].start, timings[-1].end - c.HOST_OUTRO_MAX_S)
    starts = [intro_end]
    first = hook
    for n in counts[1:-2]:
        first += n
        starts.append(timings[first].start)
    starts.append(outro_start)
    spans = [Span("intro", None, 0.0, intro_end)]
    for k, (a, b) in enumerate(zip(starts, starts[1:], strict=False)):
        spans.append(Span("scene", k, a, b))
    spans.append(Span("outro", None, outro_start, timings[-1].end))
    return spans



def scene_plan(script: Script) -> list[ScenePlan]:
    """One plan per scene. Missing keys fall back: set DEFAULT_SET[script.template], pose
    DEFAULT_POSE, camera DEFAULT_CAMERA. Layout: story for a story scene or any scene without
    items; chart with 1 item counter, 2 or more bars; steps with every value a 4-digit year
    timeline, else steps; map place. Data layouts keep their items in order."""
    plans = []
    for scene in script.scenes:
        data = scene.visual.data
        items = tuple((str(i["label"]), str(i["value"])) for i in data.get("items", []))
        plans.append(ScenePlan(
            data.get("set", c.DEFAULT_SET[script.template]),
            data.get("pose", c.DEFAULT_POSE),
            data.get("camera", c.DEFAULT_CAMERA),
            _layout(scene.visual.type, items),
            items,
        ))
    return plans


def _layout(kind: str, items: tuple[tuple[str, str], ...]) -> Layout:
    if kind == "story" or not items:
        return "story"
    if kind == "map":
        return "place"
    if kind == "chart":
        return "counter" if len(items) == 1 else "bars"
    return "timeline" if all(re.fullmatch(r"\d{4}", v) for _, v in items) else "steps"


_CARDS = {
    "counter": charts.counter_events, "bars": charts.bars_events, "steps": cards.steps_events,
    "timeline": cards.timeline_events, "place": cards.place_events,
}



def build_scenes_ass(script: Script, timings: list[WordTiming], *,
                     levels: Sequence[float] | None = None) -> str:
    """The complete scenes.ass: ass_kit.header() then events, back to front.

    `levels` (voice_levels of voice.wav) goes unchanged to every host_events call as `levels`.

    - Intro and outro spans: HOST_BACKDROP_SET (camera still) and the host in HOST_INTRO_POSE
      or HOST_OUTRO_POSE, talking on the words inside the span.
    - Each story-layout scene: its set with its camera and the host in its pose.
    - Each data-layout scene: its set dimmed, the card or chart for its layout, no host.
    - A story scene start fades in over SCENE_FADE_S; the first scene and the outro fade in over
      HOST_TRANSITION_S instead. The outro's events run to timings[-1].end + SCENE_TAIL_S.
    """
    host = art.load_host()
    sets: dict[str, art.SetArt] = {}

    def load(set_id: str) -> art.SetArt:
        if set_id not in sets:
            sets[set_id] = art.load_set(set_id)
        return sets[set_id]

    plans = scene_plan(script)
    lines: list[str] = []
    for sp in scene_spans(script, timings):
        end = sp.end + c.SCENE_TAIL_S if sp.kind == "outro" else sp.end
        if sp.index is None:
            fade = c.HOST_TRANSITION_S if sp.kind == "outro" else 0.0
            lines += set_events(load(c.HOST_BACKDROP_SET), sp.start, end, "still", fade_in=fade)
            pose = c.HOST_INTRO_POSE if sp.kind == "intro" else c.HOST_OUTRO_POSE
            lines += host_events(host, sp.start, end, pose, timings)
            continue
        plan = plans[sp.index]
        fade = c.HOST_TRANSITION_S if sp.index == 0 else c.SCENE_FADE_S
        data = plan.layout != "story"
        lines += set_events(load(plan.set_id), sp.start, end, plan.camera, dim=data, fade_in=fade)
        if data:
            lines += _CARDS[plan.layout](list(plan.items), sp.start, end)
        else:
            lines += host_events(host, sp.start, end, plan.pose, timings)
    return header() + "\n".join(lines) + "\n"
