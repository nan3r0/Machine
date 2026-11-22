"""R14 on the ledger branch: a published record takes its script out of the candidates (task
p4b-pick-ledger, design in .harness/handoffs/p4b-plan.md, "P1-2 design").

The records folder is the `ledger` branch's data/published/, and a published script stays in
queue/approved/. Expected ids come from the pick rules and literals, never from pick itself.
"""

import json
import sys
from datetime import date, datetime, timezone, tzinfo
from pathlib import Path

import pytest

from pipeline.publish import pick
from pipeline.publish.pick import PickError
from tests.publish.test_pick import TODAY, add_record, add_script

VIDEO = "dQw4w9WgXcQ"


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    queue, records = tmp_path / "queue", tmp_path / "ledger" / "data" / "published"
    (queue / "approved").mkdir(parents=True)
    records.mkdir(parents=True)
    return queue, records


def test_published_script_still_approved_is_skipped(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_script(queue, "done-case", date(2026, 11, 20))
    add_record(records, "done-case", VIDEO)
    add_script(queue, "next-case", date(2026, 11, 21))
    assert pick.next_script(queue, records, TODAY) == "next-case"
    (queue / "approved" / "next-case.json").unlink()
    with pytest.raises(PickError, match="^queue empty"):
        pick.next_script(queue, records, TODAY)


def test_record_whose_script_is_in_no_folder_is_ignored(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    add_record(records, "gone-case", VIDEO)
    add_script(queue, "due-case", date(2026, 11, 21))
    assert pick.next_script(queue, records, TODAY) == "due-case"


@pytest.mark.parametrize("queue_holds", ["other-due", "only-future", "nothing"])
def test_claim_only_record_stops_the_run_first(dirs: tuple[Path, Path], queue_holds: str) -> None:
    """Rule 1 before anything else: published records and an empty queue do not hide a claim."""
    queue, records = dirs
    add_script(queue, "done-case", date(2026, 11, 19))
    add_record(records, "done-case", VIDEO)
    add_record(records, "claimed-case", None)
    if queue_holds == "other-due":
        add_script(queue, "claimed-case", date(2026, 11, 20))
        add_script(queue, "other-case", date(2026, 11, 18))
    if queue_holds == "only-future":
        add_script(queue, "later-case", date(2026, 11, 26))
    with pytest.raises(PickError, match="claimed-case") as caught:
        pick.next_script(queue, records, TODAY)
    assert "Check the channel" in str(caught.value)
    assert not str(caught.value).startswith("queue empty")


@pytest.mark.parametrize("field", ["run_id", "run_attempt"])
@pytest.mark.parametrize("video_id", [VIDEO, None])
def test_record_without_run_fields_fails(dirs: tuple[Path, Path], field: str, video_id: str | None) -> None:
    queue, records = dirs
    add_script(queue, "due-case", date(2026, 11, 21))
    add_record(records, "old-case", video_id)
    path = records / "old-case.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    del data[field]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PickError, match="old-case.json"):
        pick.next_script(queue, records, TODAY)


def test_gitkeep_and_readme_are_ignored(dirs: tuple[Path, Path]) -> None:
    queue, records = dirs
    for folder in (queue / "approved", records):
        (folder / ".gitkeep").write_bytes(b"")
        (folder / "README.md").write_text("# Notes\n", encoding="utf-8")
    add_script(queue, "due-case", date(2026, 11, 21))
    assert pick.next_script(queue, records, TODAY) == "due-case"


UTC_NOW = datetime(2026, 11, 25, 0, 30, tzinfo=timezone.utc)
LOCAL_NOW = datetime(2026, 11, 24, 19, 30)  # the day before: a local-date pick finds nothing due


class FakeDatetime(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = None) -> "FakeDatetime":
        if tz is None:
            return cls(*LOCAL_NOW.timetuple()[:6])
        return cls.fromtimestamp(UTC_NOW.timestamp(), tz)

    @classmethod
    def utcnow(cls) -> "FakeDatetime":
        return cls(*UTC_NOW.timetuple()[:6])


class FakeDate(date):
    @classmethod
    def today(cls) -> "FakeDate":
        return cls(2026, 11, 24)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pick, "datetime", FakeDatetime)
    monkeypatch.setattr(pick, "date", FakeDate)


@pytest.mark.parametrize(("due", "code", "out"), [(date(2026, 11, 25), 0, "utc-case\n"),
                                                  (date(2026, 11, 26), 1, "")])
def test_main_uses_argv_and_the_utc_date(dirs: tuple[Path, Path], clock: None,
                                         monkeypatch: pytest.MonkeyPatch,
                                         capsys: pytest.CaptureFixture[str], due: date, code: int,
                                         out: str) -> None:
    queue, records = dirs
    add_script(queue, "utc-case", due)
    monkeypatch.setattr(sys, "argv", ["pick", str(queue), str(records)])
    assert pick.main() == code
    assert capsys.readouterr().out == out


def test_acceptance(tmp_path: Path) -> None:
    """R14.1 to R14.3 on the ledger: a published script left in queue/approved/ is skipped, a claim
    still stops the run and names the script, and a record without its run fields fails."""
    queue, records = tmp_path / "queue", tmp_path / "records"
    (queue / "approved").mkdir(parents=True)
    records.mkdir()
    test_published_script_still_approved_is_skipped((queue, records))
    add_record(records, "claimed-case", None)
    with pytest.raises(PickError, match="claimed-case"):
        pick.next_script(queue, records, TODAY)
    (records / "claimed-case.json").unlink()
    add_script(queue, "due-case", date(2026, 11, 21))
    assert pick.next_script(queue, records, TODAY) == "due-case"
    (records / "bad-case.json").write_text('{"script_id": "bad-case"}', encoding="utf-8")
    with pytest.raises(PickError, match="bad-case.json"):
        pick.next_script(queue, records, TODAY)
