"""Data shapes shared by every pipeline step (PLAN.md section 7, spec.md section 3). Locked contract.

Imports nothing from `pipeline` and does no IO. Parse script files with
`Script.model_validate_json(text)`: the models are strict, so JSON strings are accepted for dates
but a wrong JSON type (for example "12" for an int) is rejected with an error naming the field.
"""

from datetime import date, timedelta
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

NonBlank = Annotated[str, Field(pattern=r"\S")]
ScriptId = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
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
    id: ScriptId
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


class Fact(_Strict):
    """One sourced fact. Ids are unique across all source files; scripts cite them by id."""

    id: Annotated[int, Field(ge=1)]
    text: NonBlank
    url: Annotated[str, Field(pattern=r"^https://[^\s/]+\.[^\s/]+(/\S*)?$")]


class SourceFile(_Strict):
    """One solved mystery, as stored in sources/<slug>.yaml. Parse with
    `SourceFile.model_validate(yaml.safe_load(text))`. Fact ids are unique within the file."""

    topic: NonBlank
    facts: Annotated[list[Fact], Field(min_length=1)]

    @model_validator(mode="after")
    def _unique_fact_ids(self) -> "SourceFile":
        ids = [fact.id for fact in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError(f"fact ids repeat within the file: {sorted(ids)}")
        return self


class Flag(_Strict):
    """A problem the owner must see in the approval PR body; never written into a script file.
    `scene` is the scene index, or None when the flag is about the whole script."""

    script_id: NonBlank
    scene: Annotated[int, Field(ge=0)] | None
    reason: NonBlank


class LineVerdict(_Strict):
    """The meaning check's answer for one scene (PLAN.md section 5). `fact_ids` are the facts the
    checker says support the line: SUPPORTED and PARTIAL must name at least one, so a verdict that
    cites no fact can only be UNSUPPORTED."""

    index: Annotated[int, Field(ge=0)]
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "PARTIAL"]
    reason: NonBlank
    fact_ids: list[int]

    @model_validator(mode="after")
    def _support_names_a_fact(self) -> "LineVerdict":
        if self.verdict != "UNSUPPORTED" and not self.fact_ids:
            raise ValueError(f"a {self.verdict} verdict must name at least one fact id")
        return self


class PublishRecord(_Strict):
    """One video in the publish ledger, stored as data/published/<script_id>.json on the orphan
    `ledger` branch (PRD R16.3); the script itself stays in queue/approved/ unchanged.
    Parse with `PublishRecord.model_validate_json(text)`; every field must be present, nulls included.

    The claim job writes it with no video id before the upload: such a record means an upload may
    have reached YouTube unrecorded, so nothing is published until the owner resolves it. The
    record job then sets `youtube_video_id` and `published_at` together. `script_sha` is the git
    blob SHA of the approved script file. `run_id` and `run_attempt` are the GITHUB_RUN_ID and
    GITHUB_RUN_ATTEMPT of the run that wrote the claim, so a later run or attempt cannot upload
    against it. Times are UTC.
    """

    script_id: ScriptId
    script_sha: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    claimed_at: AwareDatetime
    youtube_video_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{11}$")] | None
    published_at: AwareDatetime | None
    run_id: Annotated[int, Field(gt=0)]
    run_attempt: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def _utc_and_complete(self) -> "PublishRecord":
        for moment in (self.claimed_at, self.published_at):
            if moment is not None and moment.utcoffset() != timedelta(0):
                raise ValueError(f"{moment.isoformat()} is not UTC")
        if (self.youtube_video_id is None) != (self.published_at is None):
            raise ValueError("youtube_video_id and published_at are set together or not at all")
        return self
