# Handoff: orchestrator

Read this first in any session started without `LOOM_TASK`. Then read only the HARNESS.md sections named below, when needed. Keep this file current: rewrite "State" and "Open items" before you stop.

## Role
You are the Stage 0 orchestrator (HARNESS.md section 10, Stage 0). Model: Sonnet. You launch task sessions, verify their work, run reviews, push, open PRs and log outcomes. The owner only approves the contracts PR and merges PRs. Never edit `.claude/` admin files (owner only, `LOOM_ADMIN=1`).

## How to run a task
1. Worktree per task branch `task/<id>` under `.claude/worktrees/`. Python: `.venv/Scripts/python.exe` in that worktree (create with `python -m venv .venv`, install `requirements.txt` and `requirements-dev.txt` only). Before launching, check `.venv/Scripts/python.exe -c "import pydantic"`; an existing venv may be empty.
2. Launch (window closes itself when the session ends):
   `cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 -Task <id> -Model <from .harness/config.yaml> -WorkDir <worktree> -Message "<brief>"`
   From Git Bash use `powershell -NoProfile -Command` with `Start-Process powershell.exe -PassThru -ArgumentList` and wrap the script path, `-WorkDir` and `-Message` in literal double quotes (spaces in "Claude Projects" otherwise split the arguments and the window dies at once). Confirm the window exists before waiting. Without the claude PID, skip the watcher and ask the owner to say when the window closes (process queries via PowerShell can be denied).
   Brief: role, "Follow CLAUDE.md", read the task YAML and handoff, Bash one plain command per call, commit but do not push, finish the handoff including Docs.
3. One background watcher: `sh .harness/scripts/wait_task.sh <worktree> <id> <start-sha> <claude-pid>`.
4. On TASK_DONE: run ruff, `mypy --strict pipeline/`, pytest (with `LOOM_TASK=<id>`), `tests/scope_check.py task/<id> origin/main`. Then one Gate 2 review with `.harness/scripts/run_review.sh` (prompt: read `.claude/agents/reviewer.md`, the task YAML, the handoff, the diff saved to `.harness/reviews/<id>.diff`). Add a specialist review only if `specialist_reviews` paths in config.yaml match.
5. Blocking findings: write `.harness/reviews/<id>-round<N>.md`, relaunch (resume if the session's context is small, else fresh). Non-blocking notes: log them, don't chase them.
6. Push, open the PR, `sh .harness/scripts/wait_ci.sh <pr>` once. Green: tell the owner it's ready. Close the task window by stopping its parent `powershell.exe`, never only `claude.exe`.
7. Close-out after merge: lessons and decisions yourself; Scribe (Haiku) window for status.yaml, workflow.md status, CLAUDE.md status, outcome log. Docs go on a `docs/*` branch, never a task branch.

## Token rules
- Terse replies; caveman style for chat, normal English for docs, commits and PRs.
- Rotate yourself after every task close-out, or at about 50% context, whichever comes first: rewrite State and Open items here. The Stop hook `context_guard.py` does this automatically at 50%: when it blocks your stop with "Context at N%", update this file and the docs it lists, commit, reply ROTATE, and it opens the replacement window. It only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator` (sets `LOOM_ROLE`). Before the hook is registered, tell the owner to start a fresh session (`claude.cmd --model claude-sonnet-5-5`) and type "continue as orchestrator". Cost per turn grows with context, so earlier is cheaper.
- If the hook is not guarding you (you were not started with `-Task orchestrator`), you must rotate yourself: run `/context` at every task close-out and before launching each task, and at 50% write the State block, open the docs PR and tell the owner to start a fresh session. Do not wait to be asked.
- One watcher per task; no polling loops in your own turns.
- One Gate 2 pass per task; chase only blocking findings.

## State (2026-11-22, end of twentieth orchestrator session)
- Phase 4 code done and merged: p4-daily-workflow (#114, #118), phase-end reviews p4-cso (#120), p4-audit and p4-qa-lead (#122), p4-phase-review (this close-out, `docs/p4-closeout-2`). Reports CI re-run done (run 45037285671, `data/` added to mutmut also_copy in #121).
- The follow-up task list T1 to T11, waves and docs owed are in `.harness/handoffs/p4-phase-review.md`. Start with wave 1 (T1 test_author, T3) once the owner has decided F1 and F2/O4; T1 needs an Architect contract round. Phase review says PRD R18 gates are not yet in PRD: apply the docs list at the next docs branch.
- URGENT owner items: `gh workflow disable daily-publish` (cron live, sample-65s due 2026-11-23), then R17 by hand; approve the audit; sign off threat model v3; decide F1, F2, F3, F4, F6, F7, F9, F10, P1-2 and the P1-4 lock tool; F8 retention; agent deny rules. Remind: `trial-lean` back to `baseline`.
- Process: a PR under review stays draft; check `gh pr view <n> --json state` before pushing. Read-only agents cannot write handoffs, so the orchestrator saves their reports (done this session for cso, audit, qa-lead, phase-review). The auditor agent has no web tools; use general-purpose for audits that need them.

## State (2026-11-22, end of nineteenth orchestrator session)
- Merged: p4-daily-workflow (#114 early, fixes in #118, test patch #117). Close-out on `docs/p4-daily-closeout-1`. Gate 2 and security approved on round 3.
- Next: Phase 4 phase-end reviews: CSO (threat model v3, close P1-5), QA lead and audit (need the CI `reports` job output), then phase review. Owner items: runbook R17 (YOUTUBE_* environment secrets on `youtube`, main-only rule; never re-run failed jobs while a claim is kept, check the channel first), `trial-lean` back to `baseline`, first manual weekly-scripts run.
- Lessons: keep a PR under review in draft and check `gh pr view <n> --json state` before pushing; the implementer brief says to stop after writing `CONTRACT_CHANGE.md`.

## State (2026-11-22, end of eighteenth orchestrator session)
- Merged: p4-pick, p4-youtube and their close-out #113 (see the seventeenth block). Trial `trial-lean` still ACTIVE: remind the owner to switch `profile:` back to `baseline` after p4-daily-workflow if the numbers stay flat (every Phase 4 review so far stayed on Opus, no Sonnet saving).
- IN FLIGHT: p4-daily-workflow, draft PR #114, worktree `.claude/worktrees/p4-daily-workflow`, branch `task/p4-daily-workflow`. Gate 1 green, Gate 2 and security (Opus) both blocked in round 1 on one defect (script blob skew between render, claim, upload, record). Round file `.harness/reviews/p4-daily-workflow-round1.md` (gitignored, in that worktree). A round-1 Sonnet window was launched at about 13:40 UTC; the watcher belonged to the old orchestrator, so check the worktree (`git log`, handoff mtime) and whether the window is still open.
- When it finishes: Gate 1 (ruff, mypy, pytest with LOOM_TASK, scope_check, docs_check), save `.harness/reviews/p4-daily-workflow.diff`, Gate 2 and security via `run_review.sh` (prompt files in the old job tmp are gone; prompt: read `.claude/agents/reviewer.md` or `security-reviewer.md`, the task YAML `.harness/tasks/phase4/03_daily_workflow.yaml`, the handoff, the diff). Handoff status is `partial, awaiting CI`: wait for green CI on PR #114 (shell tests and actionlint run there only) before approving. Then tell the owner to merge.
- After merge: close-out (status.yaml, workflow.md row, CLAUDE.md status, outcome log), then CSO (close P1-5), QA lead, audit, phase review. Owner notes for the runbook (R17): YOUTUBE_* must be environment secrets on `youtube` with a main-only deployment rule; a stuck claim with no upload step log means nothing was sent.

## State (2026-11-22, end of seventeenth orchestrator session)
- Merged: p4-pick #107, p4-youtube #106 (Opus Gate 2 and security approved, CI green), Dependabot #108 to #112 (the pydantic-core bump was needed: pydantic 2.14.3 pins it exactly). Close-out on `docs/p4-pick-youtube-closeout-1`.
- Routing trial `trial-lean` is ACTIVE (owner edited `profile:` in the main checkout, uncommitted). Remind the owner to switch back to `baseline` after 8 to 10 tasks or at the end of Phase 4, with `python .harness/compare_profiles.py` numbers. Phase 4 tasks mostly touch `pipeline/publish/**` or `.github/workflows/**` (security paths) so Gate 2 stays on Opus; the trial saves little here. Save `.harness/reviews/<id>.diff` before each review or `model_for` falls back to Opus.
- Next: p4-daily-workflow (Sonnet implementer, security review), then CSO (close P1-5), QA lead, audit, phase review. Carry into p4-daily-workflow: no `actions/cache` step in the upload job; the record job treats a missing `video_id` and `sent` line as sent=true and keeps the claim; add a token-character check before `::add-mask::` only via an Architect task if wanted.
- Follow-ups for the Architect (non-blocking): locked test for the encoded and JSON-escaped secret redaction in youtube.py; file name equals id check in pick.py `_load_approved`; duplicate approved ids; log real HTTP status (201 vs 200); docstring of `_send_video` vs read_bytes sent flag.
- Usage limit hit once (5-hour, resets 3:10am London) mid-review; a retry after the reset worked.
- Harness fix: `log_outcome.py` now reads the profile from the main checkout (lessons 2026-11-22).

## State (2026-11-22, end of sixteenth orchestrator session)
- Merged: p4-contracts #104 (round 1 blocked on a missing claim-refusal test, round 2 and security approved, CI green). Close-out on `docs/p4-contracts-closeout-1`.
- Next: wave 3, p4-pick and p4-youtube in parallel (Sonnet implementers, worktrees `task/p4-pick`, `task/p4-youtube`; security review for p4-youtube). Then p4-daily-workflow, CSO (close P1-5), QA lead, audit, phase review.
- Carry into the p4-youtube brief: mask the derived access token with `::add-mask::` after the refresh, error messages name the host only and never the full session URL, check the token `scope` field and the `Location` and `X-Upload-*` shapes against Google's docs (the contract came from recall; use an agent with web tools if the implementer has none). Carry into p4-daily-workflow: no `actions/cache` step in the upload job.
- A commit can be blocked by the owner's global secret scan (false positives on token constants and fake tokens). The owner approves `SKIP_SECRET_SCAN=1` by running the commit with `!`. Task sessions must stop and say so, not bypass.
- `.harness/reviews/` is gitignored: round files stay in the worktree only.
- Rotate now: fresh session, "continue as orchestrator".

## State (2026-11-22, end of fifteenth orchestrator session)
- Merged: p2d-ci-triggers #102 (Gate 2 and security approved, CI green), p4-licences #101, Phase 2c close-out #100. Close-out for p2d and p4-licences is on `docs/p2d-closeout-1`.
- CI now starts from a PR (a draft is enough), not from a branch push. Open a draft PR right after pushing a task branch. Step 4 and 6 of "How to run a task" read that way.
- Next: p4-contracts (test_author, Opus), then p4-pick and p4-youtube, p4-daily-workflow, CSO (close P1-5), QA lead, audit, phase review. Plan: `.harness/handoffs/p4-plan.md`.
- Owner still to do: branch protection on `main` requiring the `check` job, fork-run approval for all outside collaborators, YouTube Cloud setup, first manual weekly-scripts run. To-do artifact https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ is stale, refresh.
- The fourteenth-session block below is history; its in-flight items are done.

## State (2026-11-22, end of fourteenth orchestrator session)
- Merged: p2c-gemini-escapes #97, p2c-survivor-tests #98, Phase 4 plan #99. Close-out on `docs/p2c-closeout-1`. The repo is PUBLIC (owner decision O1 b, 2026-11-21); the free Actions allowance ($12) had run out, public repos are unmetered, CI works again.
- After p2d merges: close-out for p2d and p4-licences (status.yaml, workflow.md rows into the Phase 2 table, outcome log), then p4-contracts (test_author, Opus). Refresh the to-do artifact.
- Next waves (see `.harness/handoffs/p4-plan.md`): wave 1 p2d-ci-triggers (test_author, Opus; ci.yml is locked, security review applies) and p4-licences (architect agent with web tools, audit A1 and A3); then p4-contracts (test_author), p4-pick and p4-youtube, p4-daily-workflow, CSO, QA lead, audit, phase review. Owner decisions O1 to O8 are made (defaults, repo public).
- Owner still to do: branch protection on `main` and fork-run approval, YouTube Cloud setup (8 steps in the plan, no code), first manual weekly-scripts run, descriptions credit F2 decided (O3). Refresh the to-do artifact https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ.
- Process: a worktree-isolated session refuses `git -C`, `..` paths and chained git; EnterWorktree then ExitWorktree to get back to the main checkout before creating task worktrees. Dispatch `ci.yml` for mutmut only after a close-out merges (lessons 2026-11-21).

## State (2026-11-21, end of thirteenth orchestrator session)
- Phase 2b done: wave 3 merged (p2b-qa-tests-batch #91, p2b-qa-tests-factcheck #92, Opus test authors, Gate 2 approved, CI green, no pipeline bug found). Close-out docs on `docs/p2b-closeout-1` (status.yaml, workflow.md, CLAUDE.md, outcome log, lessons, spec, PRD R12.1, architecture weak points).
- CI reports re-run done after the close-out merged (run 44942078820): survivors 493 down to 401. batch.x_run 30 to 21, x__check_and_repair 19 to 12, x_pr_body 14 to 10, semantic.x__verdict_for 14 to 0, normalise.x__year 15 to 3; gemini.x__parse_answer still 32 (the QA lead's ranks 1 to 7 did not cover it). Remaining batch survivors need a look for equivalents before more tests. An earlier run before the close-out showed no change (see lessons.md 2026-11-21). pip-audit step fails by design (known findings).
- Next: ask the Architect for the follow-up tasks below, then Phase 4 planning. Owner items are in the to-do artifact https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ.
- Architect follow-ups from wave 3 reviews: semantic.py reason strings ("(no verdict)" etc.) are now locked by tests, so treat them as contract; tighten the `check_script` docstring on unlinked fact ids (only SUPPORTED and PARTIAL convert); the batch QA tests match the `_code` inline span layout, loosen if it changes; plus the follow-ups listed in the twelfth-session block below.
- Process: git commands with chained `&&` or loops are refused in a worktree-isolated session, run them one per call. `gh run download` of the reports artifact puts files in a `phase-reports/` subfolder; copy them up.

## State (2026-11-21, end of twelfth orchestrator session)
- Phase 2b plan (PR #85) merged; owner accepted O1 to O3 defaults. Waves 1 and 2 merged: p2b-prompt-data #86, p2b-gemini-shapes #87, p2b-unicode-digits #88, p2b-hook-check #89 (all Gate 2 and security approved, CI green). Main was at f35c97c after #89.
- Wave 3 next: p2b-qa-tests-batch and p2b-qa-tests-factcheck (Opus test_author, `.harness/tasks/phase2b/04_*.yaml`, `05_*.yaml`). They need fresh `out/reports/` (mutmut.txt, coverage). The old files there date from 2026-11-18. I dispatched `ci.yml` on main: run 44933489872 (check it finished, then `gh run download 44933489872 -D out/reports` or the reports artifact; the job can fail, earlier dispatch runs failed, read the log). Launch wave 3 with `.harness/scripts/open_task_window.ps1` (helper pattern in job tmp launch.ps1: Start-Process with quoted args, then watcher with the cmd.exe pid under the window).
- Docs close-out owed (docs/* branch, Scribe for status): status.yaml done += the four tasks, workflow.md Phase 2b rows, CLAUDE.md status, outcome log. Plus: lessons.md line 272 note (clean now in prompt_data), spec.md layout add pipeline/script/prompt_data.py, PRD R12.1 add non-ASCII number rule, architecture.md line 139 (hook and loop line now exact-checked, no meaning check) and line 140 (validate refuses non-ASCII digits).
- Follow-ups for the Architect: regression test for `_hides_ascii_digit` (NFKD-fold symbols, e.g. U+32C0), no locked test covers it; gemini.py `error.read()` inside the HTTPError handler and RecursionError on nested JSON still escape; CJK numerals (Lo) and homoglyph number words pass validate (script allowlist idea); title, description, tags unchecked; no meaning check on the hook.
- Process notes: reviews run from the worktree via run_review.sh with prompt files in job tmp, one after another; Python reading review JSON needs PYTHONIOENCODING=utf-8. Stale worktrees under `.claude/worktrees/` (about 70 now, incl. agent-a850c4d6600968dc6 and the four p2b-* task ones) still need cleanup.

## State (2026-11-18, end of eleventh orchestrator session)
- Phase 2 tasks all done: hardening tasks merged (p2-cso #75, p2-validate-urls #81, p2-weekly-hardening #82, p2-gemini-redirects #83) and the phase-end reports are in `.harness/handoffs/` (p2-qa-lead, p2-audit, p2-phase-review). Close-out is PR #84 (`docs/p2-closeout-6`); merge it first.
- D1 decided option (c): `GEMINI_API_KEY` is a repo secret (AI Studio project, no billing, key restricted to the Gemini API). `weekly-scripts` is still DISABLED: the owner runs `gh workflow enable weekly-scripts`, then one manual workflow_dispatch, and watches the logs (R13.5). The first run also proves the hashed install.
- Owner items: approve the Auditor report (R13.6) and decide F1 cadence (7 vs 3 to 4 a week), F2 source credit, F3 three sources; confirm F4 to F6; sign off the threat model; the repo setting for Actions-created PRs; both Gemini models allow at least 14 calls a day; YouTube Google Cloud setup (Phase 0); decide the QA lead's rank 1 contract change (non-ASCII digits).
- Next for the orchestrator after #84 merges: ask the Architect to turn phase review N1 to N5 and the QA lead's ranked tests into tasks (N1 hook and loop line unchecked and N2 non-ASCII digits need contract changes, N3 shared prompt-data module, N5 GeminiError for odd response shapes); re-run the CI reports job after they land. Then Phase 4 planning (publishing), with the posting slot 14:00 UTC reviewed after 30 days.
- Process notes: a pushed task branch is updated by merging origin/main, never rebase plus force-push (denied, and forbidden). Locked tests for a review round go on a `docs/*` branch first. Use `gh run watch <id> --exit-status`, not `wait_ci.sh`, for a run id. Launch windows with the helper pattern in `.harness/handoffs/orchestrator.md` step 2 (a small .ps1 taking -Task). Reviews and Architect work ran as read-only agents, which cannot run shell or write handoffs: the orchestrator saves their reports.
- To-do artifact refreshed: https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ (static status, republish when tasks change).
- Stale worktrees under `.claude/worktrees/` (now about 60) still need cleanup.

## State (2026-11-18, end of tenth orchestrator session)
- p2-weekly-workflow merged (PR #73), one attempt, Gate 2 and security review approved with no blocking findings, CI green. Close-out on `docs/p2-closeout-5`: outcome logged, status.yaml, workflow.md row, CLAUDE.md status, PLAN.md wording (scripts land in `queue/approved/`, D2; no `workflow_dispatch` count input, D8). Next: phase-end tasks 10 p2-qa-lead, 11 p2-cso, 12 p2-audit (max 2 at once), then 13 p2-phase-review. The QA lead and Auditor need the CI `workflow_dispatch` reports job output in `out/reports/` first.
- Before the manual acceptance run: owner decides D1, threat-model P1-4 is closed, then the `GEMINI_API_KEY` secret is added, and the repo setting "Allow GitHub Actions to create and approve pull requests" is on.
- Non-blocking notes for the phase-end reviews: `generate` and `open-pr` check out the ref separately, so a merge between them cuts the PR branch from a newer commit; a second run on the same UTC day fails at `git push` (date branch name); the artifact carries all of `queue/approved/`, so a bad `generate` job could alter already-approved scripts, visible only in the PR diff (hardening: fail `open-pr` if a tracked file under `queue/approved/` changed). The CSO should record the `actions/download-artifact` v8.0.2 pin (9000827c, checked against the tag).
- Low memory on the owner's PC killed one background watcher; run reviews one after another, not in parallel.

## State (2026-11-18, end of ninth orchestrator session)
- p2-batch merged (PR #71), built in one attempt with no blocking review findings. Close-out on `docs/p2-closeout-4`: outcome logged, status.yaml, workflow.md row, CLAUDE.md status, architecture.md weak point on the budget reservation and logical-call caps. Next: task 09 p2-weekly-workflow (security review triggers on `.github/workflows/**`), then phase-end 10 to 13.
- Non-blocking notes for the phase-end reviews: a left-out script leaves an empty publish day; budgets count logical calls, and one call can be 2 HTTP requests with the retry (spec and threat model should say which the caps mean); fact text renders as plain markdown, safe only while sources stay owner-reviewed; the CSO should add threat-model rows for PR body injection and Gemini quota exhaustion; an oversized PR body aborts the whole batch (fails closed).
- `log_outcome.py --result` takes `passed`, not `pass`. A background orchestrator session must edit inside a worktree (EnterWorktree), never the shared checkout.

## State (2026-11-18, end of eighth orchestrator session)
- p2-semantic merged (PR #69). Close-out on `docs/p2-closeout-3`: status.yaml, workflow.md row, CLAUDE.md status, one lessons entry (launch quoting). Next: task 08 p2-batch, then 09 p2-weekly-workflow, then phase-end 10 to 13.
- p2-batch brief: bound-check verdict indexes before `rewrite_line` (it raises `IndexError`); `check_script` never raises on a bad verdict, only `GeminiError` propagates and the batch decides; same "Edit and Write only" line.
- Non-blocking p2-semantic notes for the Architect: `semantic.py` imports the private `_clean` from `generate.py` (move `_clean`, `DATA_START`, `DATA_END` to a shared public module); fact ids are checked against scene links, not the facts rendered into the prompt; locked test needed for a nested delimiter in the checker prompt (exactly one `DATA_END`), same owed test as p2-generate.
- Orchestrator rotated at close-out; context was small, no hook was guarding.

## State (2026-11-17, end of seventh orchestrator session)
- p2-generate merged (PR #67). Close-out on `docs/p2-closeout-2`: status.yaml, workflow.md row, CLAUDE.md status, PLAN.md D3 ledger wording (lines 39, 74, 220, 299), two lessons entries. Next: task 07 p2-semantic, then 08 p2-batch, 09 p2-weekly-workflow.
- p2-semantic brief: its scene facts also go in a delimited data block; point the implementer at `_clean` in `pipeline/script/generate.py` and the 2026-11-17 delimiter lesson (strip until stable).
- Follow-ups for the Architect: locked regression test for the nested delimiter case in `tests/script/test_generate.py`. Non-blocking p2-generate notes: extra keys inside a scene object are rejected (docstring says ignored only at top level); `rewrite_line` raises `IndexError` on a bad index, so p2-batch must bound-check verdict indexes.
- Stale worktrees under `.claude/worktrees/` (about 46) still need cleanup; many have merged branches.

## State (2026-11-16, end of sixth orchestrator session)
- p2-contracts merged (PR #62); added to status.yaml `done` on branch `docs/p2-closeout-1` (this branch).
- Owner merged #63 to #65; their close-out (status.yaml, workflow.md, architecture.md, CLAUDE.md) is on this branch too. Next: task 06 p2-generate. The details below are history.
- Tasks 03 to 05 built, Gate 1 and Gate 2 passed:
  - p2-gemini PR #63: CI green. Gate 2 and security approve.
  - p2-validate PR #64: CI green. Gate 2 and security approve.
  - p2-seed-sources PR #65 (Opus architect agent with web tools, since `open_task_window.ps1` disallows WebFetch and WebSearch): Gate 2 round 1 blocked on Bloop fact 6 abbreviating PMEL, fixed in 1d64fa9. CI was still pending when this session stopped; check `gh pr checks 65`. Owner must review every fact (PR body lists the open questions: BLC1 "unlikely", Cottingley names, Piltdown fact 409 wording).
- After the owner merges 63 to 65: close-out on a new `docs/*` branch (status.yaml `done` += p2-validate, p2-gemini, p2-seed-sources; workflow.md rows; architecture.md render_one flow notes the pre-voice rejection, exit 2; CLAUDE.md status). Then task 06 p2-generate.
- Follow-ups for the Architect (non-blocking review notes):
  - validate.py URL check: bare domains and full-width forms closed by p2-validate-urls (2026-11-18); unassigned code points are now rejected too. U+2028/2029 still pass. `topic` and `visual.data` unchecked until they reach a published surface.
  - gemini.py: some failures escape as raw exceptions (connection reset, RecursionError, null steps); urllib's redirect handler would forward the key header on a 3xx.
  - Queue-side: sample scene 4 ("eight years ... not alive") should also cite Bloop facts 7 and 8.
- Both Sonnet implementers this session rewrote source files with a Python script instead of Edit or Write (lessons.md rule). Add a line to the task brief: "Edit and Write only, never a Python or heredoc rewrite".
- Stale worktrees under `.claude/worktrees/` still need cleanup.

## State (2026-11-16, end of fifth orchestrator session)
- Phase 1 closed (owner approved the Auditor report, PR #57). Phase 2 planned (PR #58): 14 tasks in `.harness/tasks/phase2/`, decisions D1 to D8 in `architect-p2-plan.md`.
- Phase 2 done so far: p2-factcheck-exact (PR #59), p2-entry-ci (PR #60). Both merged; their status.yaml and workflow.md close-out is in the p2-contracts branch (see below).
- In flight: task 02 p2-contracts, a Test Author agent on branch `docs/p2-contracts` (agent was spawned from the orchestrator session; if its result never arrived, check the branch `docs/p2-contracts` in `.claude/worktrees/` and `.harness/handoffs/p2-contracts.md`). It also carries the close-out docs and the Opus plan changes. When it is done: verify (ruff, mypy --strict, pytest with and without LOOM_TASK=p2-contracts, docs check), push, open the PR, owner merges, then run tasks 03, 04 and 05 (03 and 04 can run in parallel, max 2 sessions), then 06, 07, 08, 09, then phase-end 10 to 13.
- Owner decisions: D2, D3, D4, D6, D7, D8 default yes; D5 writer `gemini-3.8-flash`, checker `gemini-3.5-flash-lite` (Opus advice 2026-11-16; owner must confirm both allow at least 14 calls a day on the AI Studio dashboard before the first live run; `gemini-2.5-*` retires 2026-12-01, `gemini-3.1-flash-lite` 2027-05-07). D1 (where the Gemini key lives) is still open and blocks only the live Workflow A run: recommended option (c) with a restricted key. Owner admin: enable "Allow GitHub Actions to create and approve pull requests"; start the Google Cloud YouTube setup (Phase 0) in parallel.
- Opus advice folded into the plan: no `story` field (filename is the slug); unique normalised topic test; queue fact ids must resolve to sources; queue/published append-only; picker never reuses a source, short batch says "N of 7: sources exhausted", zero gives no PR; Gemini client fails loudly on 429 and model-not-found. Phase 4 idempotency gap: commit the video id and the queue move right after upload. NotebookLM (Gemini Notebook) is only a manual aid for refilling sources.
- Effort estimate given to the owner: about 30 sessions for Phase 2, 3 to 5 weeks to the first automatic YouTube upload; Phase 3 skipped for the first upload.
- Lesson for the orchestrator: the automatic rotation hook only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator`. A session started any other way must rotate itself at about 50% context.
- PLAN.md lines 127 to 128 (NotebookLM wording) are the owner's edit; the p2-contracts handoff lists the proposed text.
- Non-blocking items for later: phase review N1 to N10 (N4: move the `tests.media` import out of render.yml before Phase 4; N5 runtime word-count check is in p2-validate). To-do artifact: https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ (it is stale; refresh it).
- Stale worktrees under `.claude/worktrees/` need cleanup.

## State (2026-11-16, end of second orchestrator session)
- Phase 1 code complete and owner manual acceptance done: run 43873059742 produced a 69.6 s video (QA passed, no silence), the owner approved the voice, pacing and tone. Decisions in force: every video about 65 s on every platform (62 to 90 s QA range), `VOICE_SPEED` 0.9, tone rules in PLAN.md section 4. Measured speech rate is about 144 wpm (167 words in 69.5 s), `SPEECH_WPM` was 150; now 144 (p1-constants-timeout). Owner still has to set the 65 s average view duration target (PLAN.md section 12 placeholder, after 30 days of data).
- Next: the four phase-end tasks in `.harness/tasks/phase1/` (11 QA lead, 12 CSO, 13 Auditor, 14 phase review; 14 runs last). QA lead and Auditor first need the owner to run the CI `workflow_dispatch` reports job (mutmut and coverage, pip-licenses and pip-audit) and download the output to `out/reports/`: check ci.yml for the job, tell the owner the exact steps. CSO writes `docs/threat-model.md`. These are read-only or docs-only roles on Opus, run each in a fresh visible window or as the matching agent; max 2 at once.
- Usage limit: a 5-hour limit hit once mid-session (Architect agent failed with HTTP 429); resuming it with SendMessage after the reset worked. Add the weekly limit fixture when it happens.
- Launch helper pattern: a small .ps1 taking -Task -Worktree -Brief (Git Bash `cmd //c start` quoting fails). Close windows by stopping the `open_task_window` powershell, excluding your own PID. Process rule: when review requests changes, mark the PR draft before the fix round and tell the owner not to merge.
- Phase 2 (scripts + fact-check) has no task graph yet; the Architect plans it after the phase-end reviews. Darker Kokoro voice and music are deferred (voice needs its own sha256 weights entry; music is Phase 3).

## Open items
- Usage-limit fixture saved (`.harness/tests/fixtures/limit_messages/session_5h-2026-11-15.txt`). Add the weekly one when it happens.
- Known risk: pip-audit ignores two setuptools 81.0.0 advisories because torch 2.11 caps setuptools below 82; drop the ignores when torch lifts the cap (Makefile comment). It also ignores torch PYSEC-2025-194 (fixed in 2.13) because no torchaudio for torch 2.13 exists and stable-ts imports torchaudio at load; move both pins when one ships.
- **Owner to-do, remind them after the first implementer task closes out:** create a reusable skill for this setup, or expand the existing `graph-engineering` skill, with `skill-creator` in an owner-launched admin window (`~/.claude/skills` is protected). It packages the HARNESS.md and CLAUDE.md templates, task, handoff and orchestrator files, all `.harness/scripts`, the lock hook and the rotation hook. It must bake in:
  - tokens: caveman for chat, ponytail for code, model per role (Sonnet orchestrates and implements, Opus advises on architecture, contracts and reviews, Haiku does doc sync), rotation (orchestrator per task or ~50%, tasks at 60%) with automatic handover, one watcher per task, one review pass chasing only blocking findings, low effort for mechanical work, small tool output
  - safety: contracts-first locked tests with a task-aware conftest, lock hook plus CI scope check, `LOOM_ADMIN` for config files, read-only reviewers, specialist reviews only when triggered, clean child-session environments, self-closing windows
  - docs: handoff Docs section, Scribe close-out, CI docs check, lessons logged the same turn
  - cost and limits: $0 rule, heavy tests in CI only, usage-limit pause and resume, at most 2 parallel task sessions
- Doc follow-ups not yet applied: architecture.md line 54 and HARNESS.md section 11 tree comment for `docs_check.py` (add handoff Docs sections, lessons entries, required headings); HARNESS.md section 10 close-out should say status.yaml and the workflow.md row change in the same commit. Pin `huggingface_hub` in `requirements-heavy.txt` (needs owner approval, outside any task's paths). Review notes on kokoro.py (streaming hash, NaN guard, `repo_id`) were non-blocking and are not chased.
