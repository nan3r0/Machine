"""Pick the next approved script to publish (task p4-pick, PRD R14, PLAN.md section 7 Workflow B).

Pure file logic: no network, no secret. Contract written by p4-contracts; p4-pick implements it.
"""

from datetime import date
from pathlib import Path


class PickError(Exception):
    """Nothing may be published this run. The message says why and names the script or file."""


def next_script(queue_dir: Path, records_dir: Path, today: date) -> str:
    """Return the id of the script to publish today, or raise PickError.

    Reads every `queue_dir/approved/*.json` as a Script and every `records_dir/*.json` as a
    PublishRecord (`model_validate_json`). A file that does not parse raises PickError naming the
    file, and so does a record whose file name is not `<script_id>.json`. A missing
    `queue_dir/approved` counts as empty. The rules, in order:

    1. A record with no `youtube_video_id` means an earlier upload may have reached YouTube: raise
       PickError naming its script_id. Nothing is picked that run, even if other scripts are due.
    2. A record with a video id whose script is still in `queue_dir/approved/` is an inconsistent
       ledger: raise PickError naming the script.
    3. Candidates are approved scripts with no record and `publish_after` on or before `today`.
       Return the first by (`publish_after`, `id`). With none, raise PickError whose message starts
       with "queue empty".
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m pipeline.publish.pick QUEUE_DIR RECORDS_DIR`, with today's UTC date.

    On success prints only the script id and a newline to stdout and returns 0, so the workflow can
    regex-check it. On PickError prints the reason to stderr, nothing to stdout, and returns 1: the
    scheduled run goes red and GitHub emails the owner (owner decision O6).
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
