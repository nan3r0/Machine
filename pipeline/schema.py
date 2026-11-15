"""Data shapes shared by every pipeline step (PLAN.md section 7, spec.md section 3). Locked contract.

Imports nothing from `pipeline` and does no IO. Parse script files with
`Script.model_validate_json(text)`: the models are strict, so JSON strings are accepted for dates
but a wrong JSON type (for example "12" for an int) is rejected with an error naming the field.
"""

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonBlank = Annotated[str, Field(pattern=r"\S")]
Template = Literal["chart", "map", "steps", "story"]
Platform = Literal["youtube", "instagram", "tiktok"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Visual(_Strict):
    """What a scene shows. Validated in Phase 1, rendered from Phase 3."""

    type: Template
    data: dict[str, Any]


class Scene(_Strict):
    """One narration line with its on-screen text, visual and the facts it rests on."""

    narration: NonBlank
    on_screen_text: str
    visual: Visual
    source_fact_ids: list[int]


class Script(_Strict):
    """One video script, as written to queue/approved/<id>.json."""

    schema_version: Literal[1] = 1
    id: Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
    topic: NonBlank
    template: Template
    hook: NonBlank
    scenes: Annotated[list[Scene], Field(min_length=1)]
    loop_line: NonBlank
    title: NonBlank
    description: str
    tags: list[str]
    platforms: Annotated[list[Platform], Field(min_length=1)]
    publish_after: date

    def narration_text(self) -> str:
        """Text for voice and alignment: hook, each scene's narration, loop_line, single-spaced."""
        parts = [self.hook, *(scene.narration for scene in self.scenes), self.loop_line]
        return " ".join(" ".join(part.split()) for part in parts)

    def narration_words(self) -> list[str]:
        """The script's words: narration_text split on whitespace, punctuation kept."""
        return self.narration_text().split()


class WordTiming(_Strict):
    """When one script word is spoken, in seconds from the start of voice.wav."""

    word: NonBlank
    start: Annotated[float, Field(ge=0)]
    end: float

    @model_validator(mode="after")
    def _end_not_before_start(self) -> "WordTiming":
        if self.end < self.start:
            raise ValueError(f"end {self.end} is before start {self.start}")
        return self


class QAFailure(_Strict):
    """One failed QA check: `check` is its name, `reason` says what was measured and expected."""

    check: Literal["duration", "silence", "alignment", "resolution", "fps", "file_size"]
    reason: NonBlank


class QAReport(_Strict):
    """Result of the QA gate. `passed` is true exactly when there are no failures."""

    passed: bool
    failures: list[QAFailure]
    measured: dict[str, float | int | str | bool]

    @model_validator(mode="after")
    def _passed_matches_failures(self) -> "QAReport":
        if self.passed == bool(self.failures):
            raise ValueError("passed must be true exactly when failures is empty")
        return self
