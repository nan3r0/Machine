"""Visual router: scene spans, per-scene plan and the whole scenes.ass (task p3-router).

Every video (owner 2026-11-26): the host intro (the hook) on the generic HOST_BACKDROP_SET, a
transition into the story scenes, then the host outro (the end of the loop line) on the same
backdrop. Trusts a validated script. The only file reads are art.load_host and art.load_set,
called through the `art` module so tests can replace them.
"""

from dataclasses import dataclass
from typing import Literal

from pipeline.schema import Script, WordTiming

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
    raise NotImplementedError


def scene_plan(script: Script) -> list[ScenePlan]:
    """One plan per scene. Missing keys fall back: set DEFAULT_SET[script.template], pose
    DEFAULT_POSE, camera DEFAULT_CAMERA. Layout: story for a story scene or any scene without
    items; chart with 1 item counter, 2 or more bars; steps with every value a 4-digit year
    timeline, else steps; map place. Data layouts keep their items in order."""
    raise NotImplementedError


def build_scenes_ass(script: Script, timings: list[WordTiming]) -> str:
    """The complete scenes.ass: ass_kit.header() then events, back to front.

    - Intro and outro spans: HOST_BACKDROP_SET (camera still) and the host in HOST_INTRO_POSE
      or HOST_OUTRO_POSE, talking on the words inside the span.
    - Each story-layout scene: its set with its camera and the host in its pose.
    - Each data-layout scene: its set dimmed, the card or chart for its layout, no host.
    - A story scene start fades in over SCENE_FADE_S; the first scene and the outro fade in over
      HOST_TRANSITION_S instead. The outro's events run to timings[-1].end + SCENE_TAIL_S.
    """
    raise NotImplementedError
