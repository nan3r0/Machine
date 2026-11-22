# Contract change request: p4-daily-workflow

Tests: every claim shell test in `tests/test_daily_publish_workflow.py` that expects the claim to succeed (`test_claim_commits_a_record_before_the_upload`, `test_claim_retries_once_after_a_rejected_push`, and the `claimed()` helper used by the record tests).

Why: review round 1 (`.harness/reviews/p4-daily-workflow-round1.md`) requires the claim to take the script's blob hash from the render job (`needs.render.outputs.script_blob`) and refuse when main's copy differs. The tests call `run_job(..., {"render.script_id": ID})` with no `render.script_blob`, and `run_job` resolves a missing output to an empty string. The claim now refuses an empty or malformed blob, so those tests fail in CI. Accepting an empty blob would reopen the defect, so the workflow stays strict.

What the tests should say:
- Pass `"render.script_blob": git(repo, "hash-object", SCRIPT).strip()` in the outputs of every successful claim run.
- Add a test: a claim run with a blob that differs from main's script exits non-zero and pushes nothing (also after the rebase retry, when main's script changes between the first push and the retry).
- Add a test: record refuses to move a script whose hash differs from the record's `script_sha`.
