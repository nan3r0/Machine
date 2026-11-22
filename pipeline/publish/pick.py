"""Pick the next approved script to publish (task p4-pick, PRD R14, PLAN.md section 7 Workflow B).

Pure file logic: no network, no secret. Contract written by p4-contracts; p4-pick implements it.
The publish records come from the ledger branch's `data/published/`; a script that has one is skipped.
"""

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.schema import PublishRecord, Script


class PickError(Exception):
    """Nothing may be published this run. The message says why and names the script or file."""


def next_script(queue_dir: Path, records_dir: Path, today: date) -> str:
    """Return the id of the script to publish today, or raise PickError.

    Reads every `queue_dir/approved/*.json` as a Script and every `records_dir/*.json` as a
    PublishRecord (`model_validate_json`). A file that does not parse raises PickError naming the
    file, and so does a record whose file name is not `<script_id>.json`. A missing
    `queue_dir/approved` counts as empty. A missing `records_dir` raises PickError naming it: the
    folder always exists (`.gitkeep`), and a wrong path would hide an unconfirmed claim. The records
    folder is the ledger branch's `data/published/`, checked out by the workflow. The rules, in
    order:

    1. A record with no `youtube_video_id` means an earlier upload may have reached YouTube: raise
       PickError naming its script_id. Nothing is picked that run, even if other scripts are due.
    2. A script with a record is already published and is left out, even while it is still in
       `queue_dir/approved/`.
    3. Candidates are approved scripts with no record and `publish_after` on or before `today`.
       Return the first by (`publish_after`, `id`). With none, raise PickError whose message starts
       with "queue empty".
    """
    if not records_dir.is_dir():
        raise PickError(f"ledger folder missing: {records_dir}")
    records = _load_records(records_dir)
    for record in records:
        if record.youtube_video_id is None:
            raise PickError(
                f"unconfirmed claim for {record.script_id}: an upload may have reached YouTube. "
                "Check the channel, then fill in or delete its record"
            )
    approved = _load_approved(queue_dir / "approved")
    recorded = {record.script_id for record in records}
    due = [s for s in approved if s.id not in recorded and s.publish_after <= today]
    if not due:
        raise PickError("queue empty: no approved script is due")
    return min(due, key=lambda s: (s.publish_after, s.id)).id


def _load_records(records_dir: Path) -> list[PublishRecord]:
    records = []
    for path in sorted(records_dir.glob("*.json")):
        try:
            record = PublishRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise PickError(f"cannot read record {path.name}: {error}") from error
        if path.name != f"{record.script_id}.json":
            raise PickError(f"record {path.name} does not match its script_id {record.script_id}")
        records.append(record)
    return records


def _load_approved(approved_dir: Path) -> list[Script]:
    scripts = []
    for path in sorted(approved_dir.glob("*.json")):
        try:
            scripts.append(Script.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error:
            raise PickError(f"cannot read script {path.name}: {error}") from error
    return scripts


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m pipeline.publish.pick QUEUE_DIR RECORDS_DIR`, with today's UTC date.

    On success prints only the script id and a newline to stdout and returns 0, so the workflow can
    regex-check it. On PickError prints the reason to stderr, nothing to stdout, and returns 1: the
    scheduled run goes red and GitHub emails the owner (owner decision O6).
    """
    parser = argparse.ArgumentParser(prog="pipeline.publish.pick")
    parser.add_argument("queue_dir", type=Path)
    parser.add_argument("records_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        script_id = next_script(args.queue_dir, args.records_dir, datetime.now(timezone.utc).date())
    except PickError as error:
        print(error, file=sys.stderr)
        return 1
    print(script_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
