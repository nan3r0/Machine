# Handoff: p4b-ledger-contracts (test_author)

## Goal
Contract change for the bot-only `ledger` branch (CSO P1-2 and P4-1, phase review T3 to T5 and N1): `PublishRecord` binds a claim to its run, pick rule 2 skips instead of raising, and `main` no longer holds `data/published/`. Design: `.harness/handoffs/p4b-plan.md`, "P1-2 design".

## Status
partial. All edits are in and committed except the two deletions: `git rm` needs approval this session (see `ENV_ISSUE.md`). After the orchestrator runs the two `git rm` commands, the task is done pending the Linux CI run of the `docs/*` PR (the shell tests in `tests/test_daily_publish_workflow.py` skip on Windows).

## What changed (and why)
- `pipeline/schema.py`: `PublishRecord` gains `run_id` (int > 0) and `run_attempt` (int >= 1), both required and strict (no bool, string, float or null). Docstring: records live on the orphan `ledger` branch, the script stays in `queue/approved/`; the "moves unchanged to queue/published/" sentence is gone.
- `tests/test_schema_publish.py`: `record()` carries both fields (run id 45037285671, a real id past 2**32). New `BAD_RUN` cases (zero, negative, bool, string, float, null for each field) assert the single error is on that field and is not `extra_forbidden`; the required-field test covers both fields and asserts exactly one `missing` error. Plain `ValidationError` would have passed before the change for the wrong reason (extra="forbid").
- `tests/publish/test_pick.py`: deleted `test_published_script_still_approved_is_inconsistent` (old rule 2); `add_record` writes both run fields. Every remaining test passes against today's pick and holds after p4b-pick-ledger.
- New `tests/publish/test_pick_ledger.py` (owned by p4b-pick-ledger): published record whose script is still approved is skipped, then "queue empty"; record with no script anywhere is ignored; a claim-only record stops the run first with "Check the channel" (with other due scripts, only future scripts, or none); records missing `run_id`, `run_attempt` or both (claim or published; both missing is what today's claim job writes) raise PickError naming the file; `.gitkeep` and `README.md` in both folders are ignored; `main()` with `sys.argv` patched and a faked clock (UTC 2026-11-25 00:30, local 2026-11-24) prints `utc-case\n` and exits 0, and with nothing due prints nothing and exits 1; `test_acceptance`.
- `tests/test_daily_publish_workflow.py`: removed the imports of `PublishRecord`, `datetime` and `record_problems`, the `old_record` helper, and the tests that build or parse records (`test_claim_commits_a_record_before_the_upload`, `test_record_publishes_the_video_id_and_moves_the_script`, `test_record_keeps_the_claim_when_the_script_changed`). Structure tests and `test_acceptance` unchanged.
- `pyproject.toml`: `"data/"` left `[tool.mutmut] also_copy` (lessons.md 2026-11-16, 2026-11-22).
- `workflow.md`: R14 row adds tests/publish/test_pick_ledger.py in plain text; R16 row drops `tests/test_published_records.py`.
- Pending (ENV_ISSUE.md): delete `tests/test_published_records.py` and `data/published/.gitkeep`.

## Decisions made
- Kept the record-free cases of two old tests instead of deleting them whole, to keep coverage in the window before p4b-ledger-workflow-tests: `test_claim_never_rewrites_or_claims_what_main_does_not_offer` became `test_claim_never_claims_what_main_does_not_offer` (only the "no approved script" case); `test_record_needs_a_claim_only_record` became `test_record_needs_a_claim` (only the "no record" case). The claim-only and published-record cases needed `old_record`. p4b-ledger-workflow-tests removes these with the rest of the main-ledger tests.
- `test_pick_ledger.py` imports `TODAY`, `add_script` and `add_record` from `tests/publish/test_pick.py` (one record fixture), but defines its own `dirs` fixture (an imported fixture used as a parameter trips ruff F811).
- The UTC test fakes `pick.datetime.now(tz)`, `now()`, `utcnow()` and `pick.date.today()`, with local one day behind UTC and the only script due on the UTC date, so a local-date implementation returns "queue empty" (exit 1) instead of the id, on any runner timezone. It relies on pick using module-level `datetime`/`date` names, as today.
- Deviation from the plan: none.

## Tried and abandoned
- Removing one run field per pick case only: on the old schema the other field is rejected as an extra, so pick raised anyway and the case could not go red. Added the both-missing case.
- Matching the run-field errors with `pytest.raises(..., match="^run_id$")`: the pydantic message for an extra field also has the field name on its own line, so it passed before the change. Switched to asserting `errors()` loc and type.

## Known risks
- With `data/published/.gitkeep` gone, today's `daily_publish.yml` render job (`pick queue data/published`) fails with "ledger folder missing". It fails closed and the workflow is disabled until p4b-ledger-workflow; do not enable it before then.
- Coverage window (accepted in the plan): the claim-writes-record, record-fills-video-id and changed-script shell tests are gone until p4b-ledger-workflow-tests.
- The UTC test patches `pick.datetime` and `pick.date`; an implementation that imports the clock another way (for example `time.gmtime`) would not be steered by the fake.

## Next step
Orchestrator: run the two `git rm` commands from ENV_ISSUE.md, delete ENV_ISSUE.md, commit, open the `docs/*` PR and wait for Linux CI green (shell tests). Then p4b-pick-ledger.

## Docs
- PRD.md R14.1, R16.3, R17 and R18: the wording in p4b-plan.md "Proposed PRD wording" (p4b-docs).
- spec.md data model: `PublishRecord` gains `run_id` and `run_attempt`; records live on the `ledger` branch, not on `main` (p4b-docs).
- docs/threat-model.md :25 and :40: the ledger moves to the `ledger` branch and records carry the run binding (p4b-cso).
- CLAUDE.md Status: p4b-ledger-contracts done (close-out).
- workflow.md: done in this task.

## Evidence
- `pytest -q tests/test_schema_publish.py` before the schema change: 20 failed, 19 passed (the good-parse test, every run-field case and every required case red). After: 39 passed.
- `pytest -q --noconftest tests/publish/test_pick_ledger.py tests/publish/test_pick.py` against today's pick (rule 2 still raises): 2 failed, 25 passed. The failures are `test_published_script_still_approved_is_skipped` and `test_acceptance`, both "done-case is published but still in queue/approved/": exactly the rule p4b-pick-ledger changes. `--noconftest` was needed because conftest skips a file whose owner task is not done.
- The run-field refusal shown red: with the two schema fields temporarily removed, `--noconftest tests/publish/test_pick_ledger.py` gave 8 failed, 7 passed, including both "both fields missing" cases and `test_acceptance` (the one-field-missing cases pass on the old schema through extra="forbid", which is why the both-missing case exists). Schema restored, `git diff --stat` showed only the test file changed; pick, pick ledger and schema tests: 66 passed, 2 failed (the rule 2 cases above).
- `tests/docs_check.py` only checks backticked `tests/...` paths, so docs naming `data/published/` do not break it after the `.gitkeep` deletion. `data/` holds nothing but `published/.gitkeep`, so dropping it from `also_copy` loses nothing.
- `pytest -q tests .harness/tests`: 1538 passed, 96 skipped, 9 failed, all 9 in `tests/test_published_records.py` (pending deletion).
- `ruff check .`: all checks passed. `mypy --strict pipeline/`: no issues in 25 files.
- Not run locally: the shell tests (skip on Windows). Linux CI pending.
