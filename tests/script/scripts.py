"""Hand-built scripts and sources for the Phase 2 tests. Expected values come from PLAN.md and
pipeline/constants.py, never from the code under test (lessons.md 2026-11-16)."""

from datetime import date
from typing import Any

from pipeline.schema import Script, SourceFile

# 22 plain words: no number, no proper noun, nothing a check could object to.
FILLER = ("the sound came back again and again across the cold dark water "
          "and nobody on the ships could say what made it")


def scene(narration: str, fact_ids: list[int], template: str = "steps") -> dict[str, Any]:
    return {"narration": narration, "on_screen_text": "the sound",
            "visual": {"type": template, "data": {}}, "source_fact_ids": fact_ids}


def script_dict(**overrides: Any) -> dict[str, Any]:
    """A valid script of 2 + 7 * 22 + 2 = 158 words that passes every validate rule."""
    data: dict[str, Any] = {
        "id": "the-bloop", "topic": "The Bloop", "template": "steps",
        "hook": "Listen closely.",
        "scenes": [scene(FILLER, [101 + i]) for i in range(7)],
        "loop_line": "Still listening.",
        "title": "The ocean sound nobody could explain, solved",
        "description": "Source: NOAA National Ocean Service, Ocean Facts.\n#mystery #ocean",
        "tags": ["ocean mysteries", "solved mysteries", "science"],
        "platforms": ["youtube", "instagram", "tiktok"],
        "publish_after": date(2026, 11, 23),  # strict models take a date object outside JSON
    }
    data.update(overrides)
    return data


def make_script(**overrides: Any) -> Script:
    return Script.model_validate(script_dict(**overrides))


def script_with_words(count: int, scenes: int = 7) -> Script:
    """A script whose narration_words() has exactly `count` words (hook and loop line one each)."""
    body = count - 2
    sizes = [body // scenes + (1 if i < body % scenes else 0) for i in range(scenes)]
    return make_script(hook="Listen.", loop_line="Gone.",
                       scenes=[scene(" ".join(["word"] * size), [101]) for size in sizes])


def source_dict(base: int, topic: str, count: int = 7) -> dict[str, Any]:
    """A source whose fact ids are base + 1 .. base + count; each fact has a name and a year."""
    return {"topic": topic, "facts": [
        {"id": base + k,
         "text": f"Records kept by Harbor Office show case {k} closed in {1900 + base // 100 + k}.",
         "url": f"https://example.org/{base}/{k}"} for k in range(1, count + 1)]}


def make_source(base: int, topic: str, count: int = 7) -> SourceFile:
    return SourceFile.model_validate(source_dict(base, topic, count))
