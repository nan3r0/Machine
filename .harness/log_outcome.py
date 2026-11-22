"""Append one task-attempt record to .harness/log/outcomes.jsonl (HARNESS.md section 9).

Run from the project root, e.g.:
    python .harness/log_outcome.py p1-align --attempt 1 --result passed --turns 23 --duration 412
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from model_for import active_profile, load_config, main_root, model_for

RESULTS = ["passed", "tests_failed", "review_changes", "escalated", "blocked", "rotated", "usage_limit"]
CATEGORIES = ["wrong_api_usage", "env_or_dependency", "spec_misread", "flaky_test",
              "ffmpeg_syntax", "contract_wrong", "other"]
ROTATION_REASONS = ["task_done", "context_limit", "max_turns", "escalation", "pause"]

parser = argparse.ArgumentParser()
parser.add_argument("task_id")
parser.add_argument("--result", required=True, choices=RESULTS)
parser.add_argument("--attempt", type=int, default=1)
parser.add_argument("--role", default="implementer")
parser.add_argument("--failing", nargs="*", default=[], help="failing test names")
parser.add_argument("--turns", type=int)
parser.add_argument("--duration", type=int, help="seconds")
parser.add_argument("--escalated", action="store_true")
parser.add_argument("--lock-violations", type=int, default=0)
parser.add_argument("--category", choices=CATEGORIES)
parser.add_argument("--review-findings", nargs="*", default=[])
parser.add_argument("--rotation-reason", choices=ROTATION_REASONS)
parser.add_argument("--context-pct", type=int, help="context used at rotation, percent")
parser.add_argument("--handoff-quality", choices=["agent", "fallback"], default="agent")
parser.add_argument("--auto-compacted", action="store_true")
args = parser.parse_args()

root = main_root()  # the owner flips the profile in the main checkout, so a worktree must read it there
cfg = load_config(root)
record = {
    "task_id": args.task_id, "attempt": args.attempt, "role": args.role,
    "model": model_for(args.role, root=root), "profile": active_profile(cfg),
    "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "duration_s": args.duration, "turns": args.turns,
    "result": args.result, "failing_tests": args.failing, "escalated": args.escalated,
    "review_findings": args.review_findings, "lock_violations": args.lock_violations,
    "failure_category": args.category,
    "rotation_reason": args.rotation_reason, "context_pct": args.context_pct,
    "handoff_quality": args.handoff_quality, "auto_compacted": args.auto_compacted,
}
log = Path(".harness/log/outcomes.jsonl")
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record) + "\n")
