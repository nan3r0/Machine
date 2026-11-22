# Handoff: p4b-plan (Architect)

## Goal
Plan Phase 4b: the follow-up work from the Phase 4 phase-end reviews (`p4-phase-review.md` T1 to T11, `p4-cso.md`, `p4-audit.md`, `p4-qa-lead.md`) with the owner's decisions of 2026-11-22, up to go-live (PRD R18).

## Status
done (plan and task YAMLs only). Task files: `.harness/tasks/phase4b/00_*.yaml` to `14_*.yaml`. Nothing else changed. The orchestrator commits and opens the PR.

## What changed (and why)
Plan and task YAMLs only: `.harness/tasks/phase4b/` (15 tasks) and this handoff.

## Owner first (before wave 1)
1. **Disable `daily-publish` now:** `gh workflow disable daily-publish`. It fires at 14:07 UTC on 2026-11-23, when `sample-65s` becomes due. It stays disabled until R18.
2. **Hold R17 (the first live run) until wave 4 has merged.** A disabled workflow cannot be dispatched, so R17 is: `gh workflow enable daily-publish`, dispatch at once (well away from 14:07 UTC), and `gh workflow disable daily-publish` right after it finishes. The phase review said to run it now. New finding, not in any review: on the current design the record job moves `queue/approved/sample-65s.json` to `queue/published/`. `tests/test_render_one.py:21-22` reads that file at import, so main's CI would fail at collection on the next run, and `render.yml`'s default input (`render.yml:8`) would point at a missing file. Under the ledger design (below) scripts never move, so this goes away. It also avoids migrating an R17 record from main to the ledger branch.

## Owner decisions (2026-11-22, final)
- **F1 accepted.** Send `paidProductPlacementDetails.hasPaidProductPlacement = false` on every insert, from a constant. Bundled with the access-token character check (refuse anything outside `^[\x21-\x7e]+$` with `sent=False`, before `::add-mask::`).
- **Cadence stays 7 videos a week.** T7 and N2 are dropped. The runbook gets a short refill note (below).
- **P1-2: CSO recommendation.** No ruleset bypass for the bot; the ledger moves to a bot-only branch. Design below.
- **Upload guards keep failing without writing `sent=false`.**
- **F3** accepted; the channel never links the repo. **F4**: credit constant reworded (folded into T1). **F6**: drop Cottingley (T9). **F7**: build the weekly audit (T8). **F9** accepted. **F10** accepted as a personal tool, recorded in PRD section 7, no task.
- **P1-4 lock tool** (not decided by the owner, so the review's default): no new tool. `pip download` plus `pip hash`, as `requirements-generate.txt` already does.

## F1 evidence (checked 2026-11-22)
- [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert): `paidProductPlacementDetails` is in the list of `part` names the parameter accepts. The page's "you can set values for these properties" list does not name it. That is the caveat.
- [Revision history](https://developers.google.com/youtube/v3/revision_history), 2026-11-16: `hasPaidProductPlacement` "no longer defaults to false". If a `videos.insert` or `videos.update` request does not set it, "the video isn't declared as free of paid product placement". To declare no paid placement, set it to `false` explicitly.
- So the part is settable on insert per Google's own change note. R17 is the live confirmation: if the insert is refused for that part, the error names it, `sent=false` releases the claim, and the Architect revisits.
- Also confirmed: [`github.run_attempt`](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts) "begins at 1 for the workflow run's first attempt, and increments with each re-run". `github.run_id` "does not change if you re-run the workflow run". Live confirmation that "re-run failed jobs" counts as a re-run: the first time it happens (the runbook says not to do it on purpose).

## P1-2 design: the bot-only ledger branch

**Why.** The CSO rates P1-2 critical: anything pushed to `main` reaches the YouTube token at the next run. The fix is a ruleset on `main` that requires a PR and the `check` job, with no bypass. Then `github-actions[bot]` cannot push to `main`, so the claim and the record must live somewhere else.

**Layout.**
- An orphan branch `ledger`. It holds only `data/published/.gitkeep` and `data/published/<script_id>.json` (one `PublishRecord` each). It has no code and no workflow files.
- `main` no longer holds `data/published/`. Approved scripts stay in `queue/approved/` unchanged forever. The ledger, not the folder, says what was published. Nothing new goes to `queue/published/`. It stays append-only (D3) for anything already there, and the owner may move published scripts there by PR as housekeeping, but nothing depends on it.
- `pick` already takes the records folder as an argument, so its CLI does not change. Only rule 2 changes.

**`PublishRecord` gains** `run_id` (int > 0) and `run_attempt` (int >= 1). Both are required: they are the `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` of the run that wrote the claim. No record exists yet anywhere (`data/published/` holds only `.gitkeep`, and R17 waits), so nothing needs migrating.

**Pick rules.**
1. A claim-only record stops the run and names the script. Unchanged.
2. A record with a video id takes its script out of the candidates. It used to raise; the script now stays in `queue/approved/` by design.
3. The oldest due approved script with no record, or "queue empty". Unchanged.

**Jobs** (`daily_publish.yml`). Every value still reaches `run:` through env, and hooks stay off in write jobs. `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` come from the runner's default environment.

| Job | Checkouts | Does |
|---|---|---|
| render | `main` at the root, no credentials; `ref: ledger`, `path: ledger`, no credentials | `python -m pipeline.publish.pick queue ledger/data/published`, render as today |
| claim | `main` at the root, no credentials (blob check); `ledger` at `ledger` with credentials | Refuses if the ledger already holds the record, or main's script is missing or differs from the rendered blob. Writes the record with `run_id` and `run_attempt` (regex `^[0-9]+$`, then jq `--argjson`), commits inside `ledger/`, pushes to `ledger`. One rejected push: one `pull --rebase`, one retry |
| upload | `main` (`ref: main`) at the root and `ledger` at `ledger`, both without credentials | The claim check step, before the only step holding the secrets (P4-2), refuses a missing or symlinked record and anything but: video id null, `script_sha` equal to the rendered blob, `run_id` and `run_attempt` equal to its own (P4-1). The ledger is untrusted data here: jq on one regex-checked path, nothing executed or extracted from it. Then the main blob check and the CLI as today. Still no `sent=false` from the guards |
| record | `ledger` only, with credentials | Requires a claim-only record whose `run_id` equals this run's. Video id: fill it in, one commit, push to `ledger`. `sent=false`: delete the claim. Anything else: keep the claim and fail |

**Why record checks `run_id` but not `run_attempt`** (a change from the phase review's "upload and record refuse unless both match"): if the upload succeeded and only record failed (say a push race), a re-run of failed jobs re-runs only record, with the upload's outputs from the earlier attempt. Requiring the attempt to match would turn that safe recovery into a manual one. The duplicate-upload risk is in upload, and upload checks both.

**Why not a ruleset bypass:** the CSO advises against it. A bot bypass on `main` would also let any workflow with `contents: write` push code to `main`, which is the attack P1-2 closes.

**Ledger branch threats** (for the CSO, T11). A push to `ledger` needs repo write access, the same as today's push to `main`, but it can only change data. A forged published record skips a script; a forged claim stops publishing until the owner checks. Neither reaches the token or runs code: no job runs anything from `ledger`, and workflows always come from `main`. A workflow file pushed to `ledger` could run on its push event, but the YouTube secrets sit behind the main-only environment rule, and the Gemini key is already a repo secret any branch can read (D1, accepted).

**Bootstrap** (owner, or the orchestrator with the owner's OK, once, before p4b-ledger-workflow merges). In a fresh clone, not a worktree:
```
git switch --orphan ledger      # empty index and tree
mkdir -p data/published
touch data/published/.gitkeep
git add data/published/.gitkeep
git commit -m "Start the publish ledger"
git push origin ledger
```
A missing `ledger` branch makes the render job's checkout fail, so the run goes red (fails closed).

**Owner settings** (Settings, Rules, Rulesets), turned on **after** p4b-ledger-workflow merges, not before, or the old claim job's pushes to `main` would fail:
- `main`: restrict deletions, block force pushes, require a pull request (0 approvals, the owner is the only reviewer), require the status check `check`. No bypass list. Effect: Workflow A's PR is opened with `GITHUB_TOKEN`, so its `pull_request` run waits for approval. The owner approves that run on the PR page (or pushes an edit, which triggers `scripts/**` push CI) before merging.
- `ledger`: restrict deletions, block force pushes. No bypass needed, because the bot only fast-forwards. Do not add "restrict updates": it would block the bot too.
- Agent deny rules (owner-only settings): `git push` to `main` and to `ledger`, `gh pr merge`, `gh run rerun`, `gh workflow run daily-publish`.

**Test changes** (the conftest rule below decides the shape):
- `tests/test_published_records.py` and `data/published/.gitkeep` are deleted. The ledger is not on `main`, so the test would check an empty folder. Every run's `pick` validates every record anyway and fails closed on a bad one.
- `"data/"` leaves `[tool.mutmut] also_copy` in the same change. A listed path that does not exist breaks the reports job (lessons.md 2026-11-16 and 2026-11-22).
- The old main-ledger shell tests in `tests/test_daily_publish_workflow.py` are deleted. The rewritten ones go in `tests/test_daily_publish_ledger.py`.

**Proposed PRD wording** (applied by p4b-docs):
- R14.1: "The next script is the oldest in `queue/approved/` whose `publish_after` is on or before today (UTC) and that has no record on the `ledger` branch (`data/published/`)."
- R16.3: "The claim is committed to the bot-only `ledger` branch before the upload and names the run id and attempt; the upload refuses a claim from another run or attempt. After the upload the record holds the video id; the script stays in `queue/approved/` unchanged and is never picked again. A claim whose upload sent nothing is released. A record with a video id is never changed or deleted by the workflow. Nothing in Workflow B pushes to `main`."
- R17: "... and the record is on the `ledger` branch."
- R18 gates: threat model v3.1 signed off; the Phase 4 Auditor report approved; O1 implemented; the `main` and `ledger` rulesets and the agent deny rules in place (P1-2); P1-4 heavy half, P4-1, F1 and F7 merged; F8 retention set; cadence decided (done: 7 a week, refill every two weeks).

## P1-4 heavy half
- Two hashed files, made with `pip download` (manylinux tags, CPython 3.12) and `pip hash`:
  - `requirements-render-torch.txt`: torch +cpu and torchaudio from the PyTorch CPU index.
  - `requirements-render.txt`: everything else.
- Both render paths install only from them with `--require-hashes`: the daily render job and `render.yml`. `ci.yml` keeps its unhashed install (it holds no secret and publishes nothing).
- `render.yml` takes the lock too, for one reason: it is dispatch-only and has no secret, so `gh workflow run render.yml --ref <task branch>` proves the hashed install and a full render on Linux before merge. Gate 1 cannot.
- Risk: openai-whisper is sdist-only, and hash mode may reject its build dependencies. The task says how to handle that, and to stop with ENV_ISSUE.md after two tries.

## Weekly audit (F7)
- New `weekly_audit.yml`. Triggers: a weekly schedule, dispatch, and `pull_request` on `requirements*.txt`, `Makefile` and the workflow file. The PR trigger checks dependency bumps on their PR and gives the Linux proof before merge.
- Read-only token, no secret.
- It runs `make audit` (a new Makefile target that `check` also calls, so the accepted ignores live in one place), then pip-licenses over the runtime set with one rule: GPL or AGPL fails, LGPL passes.
- actionlint is left out on purpose. It is pinned, so its result changes only when a workflow changes, and every such PR already runs it.
- A red run is the alert, so the rules must pass on today's main.

## Runbook content (p4b-runbook, `docs/runbook.md`)
1. **One-time setup:**
   - the `youtube` environment, its three secrets and the main-only deployment rule
   - the ledger bootstrap above
   - the two rulesets and the deny rules
   - failure emails (Settings, Notifications, Actions)
   - artifact and log retention of 30 days or less (F8)
   - the consent screen "In production"
2. **A red daily run:** which job failed and what it means.
   - render or pick: nothing claimed. Fix the script or the queue; the next day retries.
   - claim: nothing claimed.
   - upload: check whether the upload step ran.
   - record: an upload outcome is unknown.
3. **A kept claim:** check the channel first. Then, on the `ledger` branch, fill in `youtube_video_id` and `published_at`, or delete the record. Never re-run failed jobs while a claim is kept. With the run binding a re-run of upload refuses anyway; a re-run of only record is safe.
4. **Token revoke and rotate:** revoke at myaccount.google.com, Third-party access. Make a new refresh token in the OAuth Playground (p4-plan Phase 0 step 5), replace the environment secret, and delete the Playground redirect URI again.
5. **Refill at 7 a week:** the sources last about two weeks. Every second weekend, add about 14 new `sources/*.yaml` by PR (PLAN.md section 4 content rules, the owner reviews the facts) before the Sunday Workflow A run. When the batch PR body says "sources exhausted" or a daily run fails with "queue empty", refill first. A red "queue empty" run publishes nothing, so it is safe.

## Contract change rule (conftest ownership)
- `tests/conftest.py` maps each test file to the last task YAML that lists it (`phase4b` sorts after `phase4`). If a phase4b task listed an existing Phase 4 test file under `tests:`, that file would skip on main as soon as this plan merged.
- So every phase4b `tests:` names only new files.
- Edits to existing locked files (`test_youtube.py`, `test_pick.py`, `test_daily_publish_workflow.py`, `test_schema_publish.py`, `test_workflows.py`, `workflow_rules.py`, `test_ci_workflow.py`, `test_sources_files.py`) must hold before and after the implementer merges.
- The new behaviour goes in the new file owned by the implementer.
- Contract tasks therefore have `tests: []`, and their `acceptance` names an existing test that must still pass.
- **Coverage window:** from p4b-ledger-contracts (wave 2) to p4b-ledger-workflow (wave 4), the main-ledger shell tests are gone and the ledger tests skip. They must go in wave 2: they build and parse `PublishRecord` without the new run fields, so they would fail on Linux CI as soon as the schema changes. Local Windows runs skip them, so each contract PR's Linux CI must be green before merge. The workflow on `main` is unchanged in that window, `daily-publish` is disabled, and `tests/test_workflow_safety.py` (owned by no task) still guards the secret and write split. Accepted.
- Locked tests merge on a `docs/*` branch before the implementer starts (lessons.md 2026-11-18).

## Task graph

| File | Task | Role | Paths | Depends on |
|---|---|---|---|---|
| 00 | p4b-youtube-contracts | test_author | constants.py, test_schema_publish.py, test_youtube.py, new test_youtube_placement.py, workflow.md | none |
| 01 | p4b-drop-cottingley | test_author | sources/cottingley-fairies.yaml, test_sources_files.py | none |
| 02 | p4b-youtube | implementer | pipeline/publish/youtube.py | 00 |
| 03 | p4b-ledger-contracts | test_author | schema.py, test_schema_publish.py, test_pick.py, new test_pick_ledger.py, test_daily_publish_workflow.py (drops the shell tests that parse records), test_published_records.py (delete), data/published/.gitkeep (delete), pyproject.toml, workflow.md | 00 |
| 04 | p4b-pick-ledger | implementer | pipeline/publish/pick.py | 03 |
| 05 | p4b-ledger-workflow-tests | test_author | new test_daily_publish_ledger.py, test_daily_publish_workflow.py, workflow_rules.py, workflow.md | 03 |
| 06 | p4b-ledger-workflow | implementer | daily_publish.yml | 05, 04 |
| 07 | p4b-youtube-survivors | test_author | new test_youtube_survivors.py | 02 |
| 08 | p4b-render-lock-tests | test_author | new test_render_lock.py, workflow_rules.py, test_daily_publish_workflow.py, test_workflows.py | 06 |
| 09 | p4b-audit-tests | test_author | Makefile, test_ci_workflow.py, new test_weekly_audit_workflow.py | none |
| 10 | p4b-render-lock | implementer | requirements-render*.txt, daily_publish.yml, render.yml, pyproject.toml | 08 |
| 11 | p4b-weekly-audit | implementer | weekly_audit.yml | 09 |
| 12 | p4b-runbook | scribe | docs/runbook.md | 06 |
| 13 | p4b-docs | architect | PRD, PLAN, spec, architecture, CLAUDE.md, workflow.md | 06, 02, 11, 10, 12 |
| 14 | p4b-cso | cso | docs/threat-model.md | 06, 10, 02, 11 |

QA rank 3 and P4-2 are in 05. T3 (pick tests) is folded into 03, because rank 10 tested the rule 2 message the redesign removes. T4 and T5 are one design (05 and 06). T7 is dropped.

Security review (config triggers): p4b-youtube, p4b-pick-ledger, p4b-ledger-workflow, p4b-render-lock, p4b-weekly-audit. No visual QA: no render code changes, only how it is installed.

## Waves (at most two at once, no shared path within a wave)
1. p4b-youtube-contracts, p4b-drop-cottingley. Drop-cottingley must merge before the owner's first weekly-scripts run.
2. p4b-youtube, p4b-ledger-contracts.
3. p4b-pick-ledger, p4b-ledger-workflow-tests.
4. p4b-ledger-workflow, p4b-youtube-survivors.
   - Then the owner: ledger bootstrap (before 4 merges), rulesets and deny rules (after 4 merges), R17 by hand.
5. p4b-render-lock-tests, p4b-audit-tests.
6. p4b-render-lock (owner dispatches render.yml on its branch as the proof), p4b-weekly-audit.
7. p4b-runbook, p4b-cso.
8. p4b-docs. Then the close-outs merge, the owner dispatches the CI reports job (lessons.md 2026-11-21), and R18 is the owner's call.

Status rows for these tasks go in workflow.md's `### Phase 4 status` table. A `### Phase 4b status` heading does not match the docs check's rule.

## Docs owed (p4b-docs applies these; the CSO's own item goes to p4b-cso)
- **CLAUDE.md:**
  - Status: the repo is public; the threat model sign-off refers to v2, and v3.1 is pending.
  - R17 not run; `daily-publish` disabled until go-live.
  - The ledger is on the `ledger` branch.
  - "Where things are" gains `docs/runbook.md`.
- **architecture.md:**
  - :123 and :134 are stale (public repo).
  - :64 and :66 (alerts, "skip, try next") were dropped by O6.
  - :141 says 14 sources; there are 14 again after Cottingley.
  - :144: the gap is closed by the claim design.
  - New section for Workflow B: four jobs, claim before upload on the `ledger` branch, run binding, blob binding, upload checks out `main` and verifies the claim before the secret step, hashed render install.
- **PRD.md:**
  - :24 current phase; :167 private repo; :218 sources count and refill; :220 decisions made.
  - R14.1, R16.3, R17 and R18 as proposed above.
  - Section 7 gets:
    - the audit approval and O1 to O8 as decided
    - O3 consent and the F4 rewording
    - F1 (with the evidence above, dated 2026-11-22)
    - F3, F6, F7, F9 and F10 (personal tool)
    - cadence 7 a week with a refill every two weeks (T7 and N2 dropped)
    - the ledger branch decision (P1-2, no bypass)
    - the record-checks-run-id-only choice
    - the 2026-11-02 and 2026-11-16 API facts with source and date
    - the P1-4 lock method (no new tool)
  - :207 the weekly audit is built.
- **PLAN.md:**
  - :35, :89, :279 private repo.
  - :74, :112, :257: the ledger branch replaces the move to `queue/published/`.
  - :211 cadence (7 a week, refill).
  - :246 "exit cleanly" becomes a red run (O6); :252 drop "skip, try next".
  - :311 cite the 2026-11-02 revision and the creator-settings caveat.
  - :335 the narrowed Phase 4 done-when (O5).
  - Section 6: note which mitigations are built.
  - Section 9: the `ledger` branch.
- **spec.md:**
  - :56: scripts stay in `queue/approved/`; the ledger branch.
  - :122 semgrep 1.186.0.
  - :126: reword the GPL note (no GPL files are tracked or distributed; the repo is public).
  - Add the layout, `PublishRecord` with the run fields, the YouTube secrets, the upload job's light install, and the render lock files.
- **workflow.md:**
  - a "Phase 4b module order" section with the waves above (no `### Phase 4b status` heading)
  - backticks on criterion-map files that now exist
- **docs/threat-model.md** (p4b-cso): section 2, "re-check on Google's pages at audit" becomes "confirmed 2026-11-22 (p4-audit)"; v3.1 rows.

## Decisions made
- **P4-1 and P1-2 share one contract task.** P1-2 was decided first, so the run binding is designed on the ledger branch from the start.
- **Record checks `run_id` only; upload checks both.** Reason above.
- **The ledger branch is orphan and data only,** at the same `data/published/` path, so pick's records argument and the record format carry over.
- **Scripts no longer move to `queue/published/`.** The bot cannot write `main`. This also removes the `sample-65s` breakage.
- **`test_published_records.py` is deleted, not rewritten.** CI on `main` cannot see the ledger branch, and pick validates every record on each run.
- **render.yml shares the render lock,** for the Linux proof. ci.yml does not.
- **The weekly audit leaves actionlint out** (pinned, already run on every workflow PR) and adds a `pull_request` path trigger, which also proves it on Linux before merge.
- **T9 is a test_author task,** because `MIN_FILES` (15) is locked. PRD R8.2's "at least 14" still holds.
- **The credit line keeps its second sentence:** "Sources: Wikipedia (CC BY-SA 4.0) or public records. Narrated with a synthetic voice."
- **workflow.md and PRD.md are not changed by this plan.** docs_check passes without them; p4b-docs applies them.

## Tried and abandoned
- A ruleset bypass for `github-actions[bot]`: rejected by the owner per the CSO.
- Moving published scripts to `queue/published/` through Workflow A's weekly PR: more write-token code in Workflow A for a cosmetic folder. Dropped (YAGNI).
- Proving the render lock through a daily-publish dispatch: it publishes, its render job runs only on `main`, and agents may not dispatch it.

## Known risks
- **`hasPaidProductPlacement` on insert** is backed by the revision note, not the insert page's settable list. R17 confirms it.
- **Requiring the `check` status on `main`** means Workflow A's bot-opened PR needs the owner to approve its CI run before merging. That is one more tap per week.
- **openai-whisper's sdist under hash mode** may need pinned build dependencies (p4b-render-lock).
- **The coverage window** between waves 3 and 4 (above).
- **Workflow B is unproven live.** R17 is the first live run of the ledger design and of the paid-placement part.
- **Policy facts change often.** Two relevant API changes came this month.

## Next step
1. Owner:
   - disable `daily-publish` now
   - hold R17 until wave 4
   - confirm the full credit line. The owner gave "Sources: Wikipedia (CC BY-SA 4.0) or public records"; keeping "Narrated with a synthetic voice." after it is the Architect's reading (lessons.md 2026-11-15).
2. Orchestrator: merge this plan, then run wave 1 (p4b-youtube-contracts and p4b-drop-cottingley, both Opus test_author).

## Docs
- Applied: none. The task YAMLs and this handoff only.
- Owed: the "Docs owed" list above, as task p4b-docs (and p4b-cso for the threat model). lessons.md: no new mistake in this session. The R17 and `sample-65s` interaction was a planning gap in Phase 4, which the phase review did not catch. The orchestrator may log it as a lesson ("check what a bot commit removes against every test that reads it").

## Evidence
- Read: CLAUDE.md, lessons.md, HARNESS.md sections 5, 6, 6a and 6b, p4-phase-review, p4-cso, p4-audit, p4-qa-lead and p4-plan handoffs, phase4 task YAMLs, locks.yaml, config.yaml, conftest.py, docs_check.py, `daily_publish.yml`, `pick.py`, `youtube.py:50-146`, workflow.md :85-246, the Makefile, and pyproject `also_copy`.
- Greps: `sample-65s`, `data/published`, `queue/published`, R14 to R18, credit line.
- Web, 2026-11-22: the videos.insert reference, the videos resource, the revision history, and the GitHub contexts reference (run_id, run_attempt).
- Checks, with `../p2b-qa-tests-batch/.venv`:
  - `python tests/docs_check.py`: passed.
  - `ruff check .`: passed.
  - `pytest` without LOOM_TASK: 1465 passed, 63 skipped.
  - `pytest .harness/tests`: 88 passed.
  - A YAML sanity script: all 15 phase4b tasks have every field, and every `depends_on` resolves.
