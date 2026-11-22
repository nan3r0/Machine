# Handoff: p4-phase-review

## Goal
Phase-end architecture check of Phase 4 (HARNESS.md 6a): how `pick`, `youtube` and `daily_publish.yml` fit together and with `render_one` and Workflow A; contradictions with PLAN.md, PRD.md, spec.md, architecture.md; the CSO, Auditor and QA lead handoffs.

## Status
done (read-only). Phase 4 code can close. Phase 4 cannot close yet: R17 (first live run) has not run, and go-live (R18) waits on the gates below.

## What changed (and why)
none

## Decisions made
- Upload guards do not write `sent=false` for now (revisit after P4-1 binds the claim to the run).
- Add the token whitespace check (`^[\x21-\x7e]+$`, sent=False, before `::add-mask::`), bundled with F1.
- P4-2 and QA rank 3 become one test_author task (same guards, same locked file).
- PRD R18 gains P1-2, P1-4 heavy half, P4-1, F1 and F7 as go-live gates unless the owner defers one formally in PRD section 7.

## Tried and abandoned
Checking whether `daily-publish` is disabled in repo settings (needs `gh`; the orchestrator checked: it is active).

## Known risks
- Blocker before the secrets are added: `daily_publish.yml:6` runs `7 14 * * *` and `sample-65s` is due 2026-11-23. Without secrets each run is red (two bot commits, a failure email). With the secrets added, the next run publishes unattended before any gate closes. Disable `daily-publish` now, dispatch R17 by hand, re-enable only at R18.
- P4-1 (re-running failed jobs after an unknown upload outcome duplicates the upload) is live today; the control is the runbook rule.
- If the `youtube` environment does not exist GitHub creates it unprotected; the main-only deployment rule is an owner setting.
- A failure in the upload job before the CLI writes its line keeps the claim; the owner reconciles by hand. Safe by design.

## Findings
Interfaces pass: render to pick, claim to upload to record (all bound to the rendered blob), upload to record (one `video_id=` or `sent=` line), Workflow A to Workflow B (`unused_sources` counts `queue/**`; bot pushes touch only `data/published` and the queue move). The p4-daily-workflow contract patch is applied (PR #117).
- N1 high: the P1-2 bot-only ledger branch contradicts PRD R16.3 and pick rule 2 (`pick.py:47-49`): if the bot cannot push to main the script stays in `queue/approved/` and every later pick raises. It is an Architect redesign. The owner first chooses a ruleset bypass for the bot (the CSO advises against it) or the ledger branch.
- N2 high: 3 to 4 scripts a week (F2) leaves red "queue empty" runs on off days. Whoever changes `SCRIPTS_PER_BATCH` and the spacing must also restrict the cron days (`daily_publish.yml:6`).
- N3 medium: PRD R18 lists only threat model v3, the audit, O1 and O4. Add the gates above.
- N4 low: the record job does no hash re-check after `pull --rebase`; a changed script conflicts, the push fails and the claim is kept. Fails closed.
- N5 note: `youtube.main` catches only UploadError; the token whitespace check removes the realistic other exception. No catch-all.
PRD R14 to R16.4 met in code; R17 not run; R18 open.

## Next step
Owner first: disable `daily-publish` (`gh workflow disable daily-publish`), add the YOUTUBE_* environment secrets on `youtube` with the main-only deployment rule, dispatch R17 by hand and check the video is public and labelled and the record is on main. Then decide F1, F2/O4, F3, F4, F6, F7, F9, F10, P1-2 and the P1-4 lock tool; set F8; approve the audit; sign off threat model v3; add the agent deny rules (`git push` to main, `gh pr merge`, `gh run rerun`, `gh workflow run daily-publish`).

Follow-up tasks (a contract change takes two steps: locked tests merge on a `docs/*` branch, then the implementer):
- T1 F1 `paidProductPlacementDetails` plus the token whitespace refusal; test_author then implementer; security review; go-live gate.
- T2 QA ranks 1, 2, 4, 5, 6, 7, 8 (youtube CLI), 9; tests only, new `tests/publish/test_youtube_survivors.py`.
- T3 QA rank 8 (pick CLI) and 10; tests only, `tests/publish/test_pick.py`.
- T4 P4-1: claim records `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` (a `PublishRecord` field), upload and record refuse unless both match; fold in P4-2 and QA rank 3; confirm live that the attempt number increments on a failed-jobs re-run; security review; go-live gate.
- T5 P1-2 per the owner's choice (ledger branch needs an Architect redesign, N1); the owner's ruleset on main; go-live gate. If decided before T4, merge T4 and T5 design.
- T6 P1-4 heavy half: hash-checked lock for the render installs (owner-approved lock tool, or `pip install --dry-run --report` into a `--require-hashes` file); go-live gate.
- T7 F2 cadence, only if 3 to 4 a week: constants, batch tests, cron days (N2).
- T8 F7 weekly audit workflow (pip-audit, pip-licenses, actionlint; a red run is the alert) unless formally deferred.
- T9 F6: remove `sources/cottingley-fairies.yaml` if dropped; must land before the next Workflow A run.
- T10 Runbook (CSO item 5): kept claim, never re-run failed jobs, token revoke and rotate, environment setup; scribe or orchestrator.
- T11 CSO v3.1 re-check after T4 to T6, and a reports re-dispatch after their close-outs merge.

Waves (max two tasks at once, no shared path): 1 T1 test_author and T3; 2 T1 implementer and T2; 3 T4 contract and T8 test_author; 4 T4 implementer and T8 implementer; 5 T5 design and tests, T7 test_author once T1 has merged; 6 T5 implementers, then T6, then T7 implementer (all touch `daily_publish.yml`, one at a time); 7 T11, then R18. T9 and T10 any wave.

## Docs
Owed at close-out:
- CLAUDE.md Status: repo is public; threat model sign-off refers to v2, v3 pending; add R17 and "daily-publish disabled until go-live".
- architecture.md: :123 and :134 stale (public repo); :64 and :66 (alerts, "skip, try next") dropped by O6; :141 says 14 sources, there are 15; :144 gap closed by the claim design; add a section for Workflow B (four jobs, claim before upload, blob binding, upload checks out main and verifies the claim before the secret step).
- PRD.md: :24 current phase; :167 private repo; :218 sources count; :220 decisions made; R18 gates; section 7 gets the audit approval, O1 to O8, O3 consent, F1 to F10 decisions, the 2026-11-02 and 2026-11-16 API facts with source and date, and the F7 decision (:207).
- PLAN.md: :35, :89, :279 private repo; :211 cadence (O4); :246 "exit cleanly" becomes a red run (O6); :252 drop "skip, try next"; :311 cite the 2026-11-02 revision; :335 narrow Phase 4 done-when (O5); section 6 note built mitigations; section 9 add `data/published/`.
- spec.md: :122 semgrep 1.186.0; :126 reword the GPL note; add layout, `PublishRecord`, YouTube secrets, the upload job's light install.
- docs/threat-model.md section 2: replace "re-check on Google's pages at audit" with "confirmed 2026-11-22 (p4-audit)" (CSO).

## Evidence
Read-only; nothing run. Read the task YAML, p4-plan and the phase-end handoffs, `daily_publish.yml`, `weekly_scripts.yml:20-79`, `pick.py`, `youtube.py:100-285`, `schema.py:149-172`, `sources.py:28-37`, `render_one.py` CLI lines, greps of PLAN, PRD, spec, architecture, HARNESS 6b, status.yaml, lessons.md entries 2026-11-18 to 2026-11-22.
