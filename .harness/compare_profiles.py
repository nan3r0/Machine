"""Compare routing profiles from the harness's own records (TRIAL.md). Read-only; prints a report.

    python .harness/compare_profiles.py

Uses .harness/log/outcomes.jsonl (records with no `profile` are baseline) and the review JSONs in
.harness/reviews/ (model and cost from the Claude Code JSON output). Costs are Claude Code's list-price
estimate: on a plan they are a relative measure of usage, not money spent.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path.cwd()


def parse_review(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    models = list((data.get("modelUsage") or {}).keys())
    text = str(data.get("result") or "")
    verdict_match = re.search(r'"verdict"\s*:\s*"(\w+)"', text)
    blocking: list[Any] = []
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            blocking = json.loads(text[start:end + 1]).get("blocking") or []
        except (json.JSONDecodeError, AttributeError):
            blocking = []
    return {"model": models[0] if models else "unknown", "cost": float(data.get("total_cost_usd") or 0),
            "verdict": verdict_match.group(1) if verdict_match else "unparsed", "blocking": blocking,
            "turns": data.get("num_turns")}


def outcomes_report() -> None:
    log = ROOT / ".harness" / "log" / "outcomes.jsonl"
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if log.is_file() else []
    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("role") in ("implementer", "escalation"):
            by_profile[row.get("profile") or "baseline"].append(row)
    print("== Implementation outcomes (implementer and escalation attempts)")
    for profile, recs in sorted(by_profile.items()):
        tasks = {r["task_id"] for r in recs}
        first_pass = {r["task_id"] for r in recs if r.get("attempt", 1) == 1 and r["result"] == "passed"}
        review_changes = sum(r["result"] == "review_changes" for r in recs)
        escalated = sum(bool(r.get("escalated")) or r["result"] == "escalated" for r in recs)
        print(f"  {profile:12} tasks={len(tasks):3}  first-pass={len(first_pass) / max(len(tasks), 1):5.0%}"
              f"  attempts/task={len(recs) / max(len(tasks), 1):.2f}  review-changes={review_changes}"
              f"  escalations={escalated}")


def reviews_report() -> None:
    folder = ROOT / ".harness" / "reviews"
    reviews = {p.stem: r for p in sorted(folder.glob("*.json")) if (r := parse_review(p))}
    print("\n== Reviews by model (excluding shadow re-runs)")
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, r in reviews.items():
        if not name.endswith("-shadow"):
            by_model[r["model"]].append(r)
    for model, recs in sorted(by_model.items()):
        changes = sum(r["verdict"] == "changes_requested" for r in recs)
        cost = sum(r["cost"] for r in recs)
        print(f"  {model:20} reviews={len(recs):3}  changes-requested={changes / len(recs):5.0%}"
              f"  avg-cost=${cost / len(recs):.2f}  total=${cost:.2f}")

    pairs = [(n[: -len("-shadow")], r) for n, r in reviews.items() if n.endswith("-shadow")]
    print(f"\n== Shadow checks: same task reviewed by the trial model and the baseline model ({len(pairs)})")
    missed = 0
    for name, shadow in pairs:
        real = reviews.get(name)
        if not real:
            continue
        gap = len(shadow["blocking"]) - len(real["blocking"])
        flag = "  <-- baseline found more blocking issues" if gap > 0 else ""
        missed += gap > 0
        print(f"  {name:32} trial {real['verdict']:17} {len(real['blocking'])} blocking | "
              f"baseline {shadow['verdict']:17} {len(shadow['blocking'])} blocking{flag}")
    if pairs:
        print(f"  Trial reviewer missed blocking issues in {missed} of {len(pairs)} shadow checks.")


if __name__ == "__main__":
    outcomes_report()
    reviews_report()
