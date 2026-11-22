"""The committed publish ledger is consistent (PRD R16.3, task p4-contracts). Owned by no task: it
always runs, so a bad record or a half-done queue move on main turns CI red.

Each rule is shown failing on a bad ledger in tmp_path first (lessons.md 2026-11-15).
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from pipeline.schema import PublishRecord

ROOT = Path(__file__).resolve().parent.parent
VIDEO = "dQw4w9WgXcQ"
SCRIPT = b'{"id": "old-case"}\n'


def blob_sha(path: Path) -> str:
    """The git blob SHA the file has (or would have) in the repo, line-ending filters applied."""
    result = subprocess.run(["git", "hash-object", "--", str(path)], cwd=path.parent, check=True,
                            capture_output=True, text=True, timeout=60)
    return result.stdout.strip()


def record_problems(root: Path) -> list[str]:
    """Every problem with `root/data/published/*.json`: each parses as a PublishRecord and is named
    `<script_id>.json`; a record with a video id has its script, unchanged (same blob SHA), under
    queue/published/ and none under queue/approved/."""
    found = []
    for path in sorted((root / "data" / "published").glob("*.json")):
        name = path.relative_to(root).as_posix()
        try:
            record = PublishRecord.model_validate_json(path.read_bytes())
        except ValidationError as error:
            found.append(f"{name}: not a PublishRecord ({error.error_count()} errors)")
            continue
        if path.name != f"{record.script_id}.json":
            found.append(f"{name}: file name is not {record.script_id}.json")
        if record.youtube_video_id is None:
            continue
        published = root / "queue" / "published" / f"{record.script_id}.json"
        if not published.is_file():
            found.append(f"{name}: published, but queue/published/{record.script_id}.json is missing")
        elif blob_sha(published) != record.script_sha:
            found.append(f"{name}: queue/published/{record.script_id}.json is not the claimed version")
        if (root / "queue" / "approved" / f"{record.script_id}.json").exists():
            found.append(f"{name}: published, but the script is still in queue/approved/")
    return found


def put(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def ledger(tmp_path: Path, **overrides: Any) -> Path:
    """A consistent ledger: old-case published, new-case claimed and still approved."""
    put(tmp_path / "queue" / "published" / "old-case.json", SCRIPT)
    put(tmp_path / "queue" / "approved" / "new-case.json", b'{"id": "new-case"}\n')
    sha = blob_sha(tmp_path / "queue" / "published" / "old-case.json")
    done = {"script_id": "old-case", "script_sha": sha, "claimed_at": "2026-11-23T14:09:12Z",
            "youtube_video_id": VIDEO, "published_at": "2026-11-23T14:11:40Z", **overrides}
    claim = {"script_id": "new-case", "script_sha": "0" * 40, "claimed_at": "2026-11-24T14:09:12Z",
             "youtube_video_id": None, "published_at": None}
    put(tmp_path / "data" / "published" / "old-case.json", json.dumps(done).encode("utf-8"))
    put(tmp_path / "data" / "published" / "new-case.json", json.dumps(claim).encode("utf-8"))
    return tmp_path


def test_consistent_ledger_passes(tmp_path: Path) -> None:
    assert record_problems(ledger(tmp_path)) == []


def test_unparseable_record_fails(tmp_path: Path) -> None:
    put(ledger(tmp_path) / "data" / "published" / "broken.json", b"{not json")
    assert record_problems(tmp_path) == ["data/published/broken.json: not a PublishRecord (1 errors)"]


def test_record_named_for_another_script_fails(tmp_path: Path) -> None:
    root = ledger(tmp_path)
    (root / "data" / "published" / "new-case.json").rename(root / "data" / "published" / "other.json")
    assert record_problems(root) == ["data/published/other.json: file name is not new-case.json"]


def test_published_script_missing_fails(tmp_path: Path) -> None:
    (ledger(tmp_path) / "queue" / "published" / "old-case.json").unlink()
    assert record_problems(tmp_path) == [
        "data/published/old-case.json: published, but queue/published/old-case.json is missing"]


def test_edited_published_script_fails(tmp_path: Path) -> None:
    put(ledger(tmp_path) / "queue" / "published" / "old-case.json", b'{"id": "old-case", "x": 1}\n')
    assert record_problems(tmp_path) == [
        "data/published/old-case.json: queue/published/old-case.json is not the claimed version"]


def test_published_script_left_in_approved_fails(tmp_path: Path) -> None:
    put(ledger(tmp_path) / "queue" / "approved" / "old-case.json", SCRIPT)
    assert record_problems(tmp_path) == [
        "data/published/old-case.json: published, but the script is still in queue/approved/"]


@pytest.mark.parametrize("overrides", [{"youtube_video_id": "short"}, {"published_at": None},
                                       {"script_sha": "X" * 40}])
def test_bad_field_fails(tmp_path: Path, overrides: dict[str, Any]) -> None:
    [problem] = record_problems(ledger(tmp_path, **overrides))
    assert problem.startswith("data/published/old-case.json: not a PublishRecord")


def test_acceptance() -> None:
    """The ledger committed in this repo is consistent."""
    assert (ROOT / "data" / "published").is_dir(), "data/published/ is the ledger folder (keep .gitkeep)"
    assert record_problems(ROOT) == []
