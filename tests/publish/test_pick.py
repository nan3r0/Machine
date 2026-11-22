"""R14: pick the next approved script (task p4-pick, contract in pipeline/publish/pick.py).

Scripts come from tests/script/scripts.py; expected ids come from the rules in PRD R14, never
from the code under test.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from pipeline.publish import pick
from pipeline.publish.pick import PickError
from tests.script.scripts import make_script

TODAY = date(2026, 11, 25)
SHA = "0123456789abcdef0123456789abcdef01234567"


def add_script(queue: Path, script_id: str, publish_after: date, folder: str = "approved") -> None:
    path = queue / folder / f"{script_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(make_script(id=script_id, publish_after=publish_after).model_dump_json(),
                    encoding="utf-8")


def add_record(records: Path, script_id: str, video_id: str | None, name: str = "") -> None:
    data: dict[str, Any] = {"script_id": script_id, "script_sha": SHA, "claimed_at": "2026-11-23T14:09:12Z",
                            "youtube_video_id": video_id,
                            "published_at": "2026-11-23T14:11:40Z" if video_id else None}
    records.mkdir(parents=True, exist_ok=True)
    (records / (name or f"{script_id}.json")).write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    queue, records = tmp_path / "queue", tmp_path / "data" / "published"
    (queue / "approved").mkdir(parents=True)
    records.mkdir(parents=True)
    return queue, records


def test_oldest_due_script_by_date_then_id(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "c-case", date(2026, 11, 24))
    add_script(queue, "b-case", date(2026, 11, 23))
    add_script(queue, "a-case", date(2026, 11, 23))
    add_script(queue, "z-case", date(2026, 11, 20))
    add_script(queue, "early-case", date(2026, 11, 26))
    assert pick.next_script(queue, records, TODAY) == "z-case"
    (queue / "approved" / "z-case.json").unlink()
    assert pick.next_script(queue, records, TODAY) == "a-case"


def test_publish_after_today_counts_as_due(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "due-today", TODAY)
    assert pick.next_script(queue, records, TODAY) == "due-today"


def test_script_with_a_record_is_skipped(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "old-case", date(2026, 11, 20), folder="published")
    add_record(records, "old-case", "dQw4w9WgXcQ")
    add_script(queue, "next-case", date(2026, 11, 21))
    assert pick.next_script(queue, records, TODAY) == "next-case"


@pytest.mark.parametrize("setup", ["nothing", "only-future", "no-approved-folder"])
def test_queue_empty(tmp_path: Path, dirs: tuple[Path, Path], setup: str) -> None:
    queue, records = dirs
    if setup == "only-future":
        add_script(queue, "later-case", date(2026, 11, 26))
    if setup == "no-approved-folder":
        queue = tmp_path / "other-queue"
    with pytest.raises(PickError, match="^queue empty"):
        pick.next_script(queue, records, TODAY)


def test_missing_records_dir_fails(tmp_path: Path, dirs: tuple[Path, Path]) -> None:
    queue, _ = dirs
    add_script(queue, "due-case", date(2026, 11, 20))
    with pytest.raises(PickError, match="no-ledger"):
        pick.next_script(queue, tmp_path / "no-ledger", TODAY)


def test_unconfirmed_claim_blocks_every_pick(dirs: tuple[Path, Path]) -> None:
    """At most once: a claim with no video id may be a video already on YouTube (R14.3)."""
    queue, records = dirs
    add_script(queue, "claimed-case", date(2026, 11, 20))
    add_record(records, "claimed-case", None)
    add_script(queue, "other-case", date(2026, 11, 19))
    with pytest.raises(PickError, match="claimed-case"):
        pick.next_script(queue, records, TODAY)


def test_published_script_still_approved_is_inconsistent(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "stuck-case", date(2026, 11, 20))
    add_record(records, "stuck-case", "dQw4w9WgXcQ")
    add_script(queue, "other-case", date(2026, 11, 21))
    with pytest.raises(PickError, match="stuck-case"):
        pick.next_script(queue, records, TODAY)


def test_unparseable_record_fails(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "a-case", date(2026, 11, 20))
    (records / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(PickError, match="broken.json"):
        pick.next_script(queue, records, TODAY)


def test_misnamed_record_fails(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "a-case", date(2026, 11, 20))
    add_record(records, "gone-case", "dQw4w9WgXcQ", name="renamed.json")
    with pytest.raises(PickError, match="renamed.json"):
        pick.next_script(queue, records, TODAY)


def test_unparseable_script_fails(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "a-case", date(2026, 11, 20))
    (queue / "approved" / "bad-case.json").write_text('{"id": "bad-case"}', encoding="utf-8")
    with pytest.raises(PickError, match="bad-case.json"):
        pick.next_script(queue, records, TODAY)


def test_cli_prints_only_the_id(dirs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    queue, records = dirs
    add_script(queue, "past-case", date(2020, 1, 1))
    add_script(queue, "future-case", date(2099, 1, 1))
    assert pick.main([str(queue), str(records)]) == 0
    out = capsys.readouterr().out
    assert out == "past-case\n"


def test_cli_fails_with_the_reason(dirs: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    queue, records = dirs
    add_script(queue, "future-case", date(2099, 1, 1))
    assert pick.main([str(queue), str(records)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "queue empty" in captured.err


def test_acceptance(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """R14.1 to R14.3: oldest due script without a record; queue empty fails; an unconfirmed claim
    stops the run and names the script; the CLI prints only the id."""
    queue, records = tmp_path / "queue", tmp_path / "records"
    records.mkdir()
    add_script(queue, "first-case", date(2026, 11, 22))
    add_script(queue, "second-case", date(2026, 11, 23))
    assert pick.next_script(queue, records, TODAY) == "first-case"
    add_record(records, "first-case", None)
    with pytest.raises(PickError, match="first-case"):
        pick.next_script(queue, records, TODAY)
    (records / "first-case.json").unlink()
    (queue / "approved" / "first-case.json").unlink()
    (queue / "approved" / "second-case.json").unlink()
    with pytest.raises(PickError, match="^queue empty"):
        pick.next_script(queue, records, TODAY)
    add_script(queue, "past-case", date(2020, 1, 1))
    assert pick.main([str(queue), str(records)]) == 0
    assert capsys.readouterr().out == "past-case\n"
