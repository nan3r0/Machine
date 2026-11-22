"""Phase 4 contracts: PublishRecord and the YouTube constants (task p4-contracts, PRD R14 to R16).

Expected values come from the plan (.harness/handoffs/p4-plan.md, Contracts and O1 to O3) and
YouTube's documented limits, never from the code under test (lessons.md 2026-11-16).
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from pipeline import constants
from pipeline.schema import PublishRecord
from pipeline.script import validate
from tests.script.scripts import make_script

SHA = "0123456789abcdef0123456789abcdef01234567"
CLAIMED = "2026-11-23T14:09:12Z"  # what `date -u +%Y-%m-%dT%H:%M:%SZ` prints in the claim job
RUN_ID = 45037285671  # a real GITHUB_RUN_ID: past 2**32, so the field must not be a 32-bit int


def record(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"script_id": "sample-65s", "script_sha": SHA, "claimed_at": CLAIMED,
                            "youtube_video_id": None, "published_at": None, "run_id": RUN_ID,
                            "run_attempt": 1}
    data.update(overrides)
    return data


def parse(data: dict[str, Any]) -> PublishRecord:
    return PublishRecord.model_validate_json(json.dumps(data))


def test_claim_and_published_records_parse() -> None:
    claim = parse(record())
    assert claim.youtube_video_id is None and claim.published_at is None
    done = parse(record(youtube_video_id="dQw4w9WgXcQ", published_at="2026-11-23T14:11:40Z"))
    assert done.youtube_video_id == "dQw4w9WgXcQ"
    assert done.published_at is not None and done.published_at.utcoffset() is not None
    parse(record(youtube_video_id="a-b_C9d-E_f", published_at="2026-11-23T14:11:40+00:00"))
    rerun = parse(record(run_id=1, run_attempt=3))
    assert (claim.run_id, claim.run_attempt, rerun.run_id, rerun.run_attempt) == (RUN_ID, 1, 1, 3)


BAD = [
    pytest.param({"script_id": "Sample_65s"}, id="script-id-pattern"),
    pytest.param({"script_id": "../x"}, id="script-id-path"),
    pytest.param({"script_sha": SHA.upper()}, id="sha-uppercase"),
    pytest.param({"script_sha": SHA[:39]}, id="sha-short"),
    pytest.param({"script_sha": SHA + "0"}, id="sha-long"),
    pytest.param({"claimed_at": "2026-11-23T14:09:12"}, id="claimed-naive"),
    pytest.param({"claimed_at": "2026-11-23T15:09:12+01:00"}, id="claimed-not-utc"),
    pytest.param({"claimed_at": "2026-11-23"}, id="claimed-date-only"),
    pytest.param({"youtube_video_id": "dQw4w9WgXc", "published_at": CLAIMED}, id="id-10-chars"),
    pytest.param({"youtube_video_id": "dQw4w9WgXcQQ", "published_at": CLAIMED}, id="id-12-chars"),
    pytest.param({"youtube_video_id": "dQw4w9WgX;Q", "published_at": CLAIMED}, id="id-bad-char"),
    pytest.param({"youtube_video_id": "dQw4w9WgXcQ"}, id="id-without-published-at"),
    pytest.param({"published_at": CLAIMED}, id="published-at-without-id"),
    pytest.param({"youtube_video_id": "dQw4w9WgXcQ", "published_at": "2026-11-23T14:11:40"},
                 id="published-naive"),
    pytest.param({"youtube_video_id": "dQw4w9WgXcQ", "published_at": "2026-11-23T16:11:40+02:00"},
                 id="published-not-utc"),
    pytest.param({"extra": 1}, id="extra-field"),
]

# The run fields are checked by name: before they existed, extra="forbid" rejected any record
# holding them, so a bare ValidationError would pass for the wrong reason.
BAD_RUN = [
    pytest.param({"run_id": 0}, id="run-id-zero"),
    pytest.param({"run_id": -1}, id="run-id-negative"),
    pytest.param({"run_id": True}, id="run-id-bool"),
    pytest.param({"run_id": "45037285671"}, id="run-id-string"),
    pytest.param({"run_id": 1.0}, id="run-id-float"),
    pytest.param({"run_id": None}, id="run-id-null"),
    pytest.param({"run_attempt": 0}, id="attempt-zero"),
    pytest.param({"run_attempt": True}, id="attempt-bool"),
    pytest.param({"run_attempt": "1"}, id="attempt-string"),
    pytest.param({"run_attempt": 1.0}, id="attempt-float"),
    pytest.param({"run_attempt": None}, id="attempt-null"),
]


@pytest.mark.parametrize("overrides", BAD)
def test_bad_record_is_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse(record(**overrides))


@pytest.mark.parametrize("overrides", BAD_RUN)
def test_bad_run_field_is_rejected(overrides: dict[str, Any]) -> None:
    [field] = overrides
    with pytest.raises(ValidationError) as caught:
        parse(record(**overrides))
    assert [(e["loc"], e["type"] == "extra_forbidden") for e in caught.value.errors()] == [((field,), False)]


@pytest.mark.parametrize("field", ["script_id", "script_sha", "claimed_at", "youtube_video_id",
                                   "published_at", "run_id", "run_attempt"])
def test_every_field_is_required(field: str) -> None:
    data = record()
    del data[field]
    with pytest.raises(ValidationError) as caught:
        parse(data)
    assert [(e["loc"], e["type"]) for e in caught.value.errors()] == [((field,), "missing")]


def test_youtube_constants() -> None:
    assert constants.YOUTUBE_TOKEN_ENDPOINT == "https://oauth2.googleapis.com/token"
    assert constants.YOUTUBE_UPLOAD_ENDPOINT == "https://www.googleapis.com/upload/youtube/v3/videos"
    assert constants.YOUTUBE_UPLOAD_HOST == "www.googleapis.com"
    assert constants.YOUTUBE_SCOPE == "https://www.googleapis.com/auth/youtube.upload"
    assert constants.YOUTUBE_CATEGORY_ID == "27"
    assert constants.YOUTUBE_PRIVACY == "public"
    assert constants.YOUTUBE_MADE_FOR_KIDS is False
    assert constants.YOUTUBE_SYNTHETIC_MEDIA is True  # owner decision O2
    assert constants.YOUTUBE_PAID_PRODUCT_PLACEMENT is False  # audit F1
    assert constants.YOUTUBE_CREDIT_LINE == ("Sources: Wikipedia (CC BY-SA 4.0) or public records. "
                                             "Narrated with a synthetic voice.")  # O3, reworded by F4
    assert constants.YOUTUBE_DESCRIPTION_MAX_BYTES == 5000
    for timeout in (constants.YOUTUBE_CONNECT_TIMEOUT_S, constants.YOUTUBE_UPLOAD_TIMEOUT_S):
        assert isinstance(timeout, int) and 0 < timeout
    assert constants.YOUTUBE_CONNECT_TIMEOUT_S <= constants.YOUTUBE_UPLOAD_TIMEOUT_S


def test_credit_line_passes_the_published_field_rules() -> None:
    assert validate.problems(make_script(description=constants.YOUTUBE_CREDIT_LINE)) == []
    # The same check catches a link, so the pass above is not vacuous.
    linked = constants.YOUTUBE_CREDIT_LINE.replace("Wikipedia", "wikipedia.org")
    assert validate.problems(make_script(description=linked)) == ["description: contains a URL"]


def test_description_with_credit_fits_youtube_bytes() -> None:
    """Every character of a valid description can take up to 4 UTF-8 bytes."""
    tail = (constants.YOUTUBE_CREDIT_SEPARATOR + constants.YOUTUBE_CREDIT_LINE).encode("utf-8")
    assert constants.DESCRIPTION_MAX_CHARS * 4 + len(tail) < constants.YOUTUBE_DESCRIPTION_MAX_BYTES
    assert constants.YOUTUBE_CREDIT_SEPARATOR == "\n\n"


def test_acceptance() -> None:
    """PublishRecord parses a claim and a published record and rejects every bad shape; the YouTube
    constants hold the plan's values; the credit line is publishable and fits the byte limit."""
    test_claim_and_published_records_parse()
    for param in BAD:
        test_bad_record_is_rejected(*param.values)
    for param in BAD_RUN:
        test_bad_run_field_is_rejected(*param.values)
    test_youtube_constants()
    test_credit_line_passes_the_published_field_rules()
    test_description_with_credit_fits_youtube_bytes()
