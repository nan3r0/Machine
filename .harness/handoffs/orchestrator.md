# Handoff: orchestrator

Read this first in any session started without `LOOM_TASK`. Then read only the HARNESS.md sections named below, when needed. Keep this file current before you stop: **REPLACE the one State block, never append a new one** (a check in `.harness/tests/test_orchestrator_handoff.py` fails on a second `## State` heading or a file over 12 KB), and edit Open items. Old state goes to `orchestrator-history.md` (append-only, never read at session start) only if it is worth keeping.

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
5. Blocking findings: write `.harness/reviews/<id>-round<N>.md`, relaunch (resume if the session's context is small, else fresh). Non-blocking notes: log them, don't chase them. **At most 2 review rounds per task.** If round 2 still has blocking findings, stop: escalate to Opus for the fix (HARNESS.md section 6) or tell the owner, never start round 3 with the same implementer. Round 2 reruns only the reviewer(s) that blocked in round 1 (Gate 2 only, or security only), unless the fix touches files outside the blocked findings, then rerun both. The round-2 reviewer gets the round-1 findings and the fix diff only (`git diff <round-1-sha>..HEAD`), not the whole task again.
6. Push, open the PR, `sh .harness/scripts/wait_ci.sh <pr>` once. Green: tell the owner it's ready. Close the task window by stopping its parent `powershell.exe`, never only `claude.exe`.
7. Close-out after merge: lessons and decisions yourself; Scribe (Haiku) window for status.yaml, workflow.md status, CLAUDE.md status, outcome log. Docs go on a `docs/*` branch, never a task branch.

## Token rules
- Terse replies; caveman style for chat, normal English for docs, commits and PRs.
- Rotate yourself after every task close-out, or at about 50% context, whichever comes first: rewrite State and Open items here. The Stop hook `context_guard.py` does this automatically at 50%: when it blocks your stop with "Context at N%", update this file and the docs it lists, commit, reply ROTATE, and it opens the replacement window. It only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator` (sets `LOOM_ROLE`). Before the hook is registered, tell the owner to start a fresh session (`claude.cmd --model claude-sonnet-5-5`) and type "continue as orchestrator". Cost per turn grows with context, so earlier is cheaper.
- If the hook is not guarding you (you were not started with `-Task orchestrator`), you must rotate yourself: run `/context` at every task close-out and before launching each task, and at 50% write the State block, open the docs PR and tell the owner to start a fresh session. Do not wait to be asked.
- One watcher per task; no polling loops in your own turns.
- One Gate 2 pass per task; chase only blocking findings (round cap in step 5).
- Phase-end reviews follow HARNESS.md section 6b "Phase-end review policy": launch the full set only at its triggers, and put findings in `.harness/backlog.md`, not straight into new tasks.
- Weekly limit near (the owner says so, or a limit message appears): finish the current task's close-out, then stop. Do not start a new wave or a new review. Write the State block so the next session can resume. HARNESS.md section 10b describes the 5-hour and weekly freeze; this session only does the close-out part by hand.

## State (2026-11-25, 25th session end, replaces all earlier State blocks)
- Phase 4c lock work done (#172, #176, #179). Owner set `lock-resolve` as a required check with "up to date" and #169 is closed. `p4d-gemini-quota-guard` done: contracts #182, code #181 (Gate 2 and security approved). Close-out docs on branch `docs/p4d-closeout` (owner pushes, then PR).
- `weekly-scripts` is ACTIVE (Sunday 06:00 UTC cron), not disabled. It failed on Gemini 503 overload and the 20 requests a day free limit of `gemini-3.8-flash` (per model; the checker `gemini-3.5-flash-lite` has about 500). The client retry is not in the 14-call caps, so real requests can reach 28. Guard now stops early. Owner chose to keep one bulk run for now; if it keeps failing, spread writer calls over days (PLAN.md risk table).
- Owner steps open: first manual weekly-scripts run, R17, threat model v3.1 sign-off, re-enable `daily-publish`. Owner answer open: narrow rfc3986/csvw Dependabot ignores to major-only?
- Non-blocking: ci.yml `check` and `reports` jobs install torch from the CPU index without `--require-hashes` (about lines 90 and 149); `error.read()` in gemini.py has no size cap (negligible, fixed Google host).
- Process: owner pushes (agents have no push). Task order: architect writes task YAML, locked tests and import stubs, that contracts commit merges to main (branch `plan/<id>`) BEFORE the implementer starts; then merge main into the task branch (never rebase). Implementer worktree branches are `worktree-agent-*`: have the implementer `git checkout -B task/<id> <base>`. Never hand the owner a `worktree-agent-*` name. `gh pr create` is allowed; `gh workflow run` is denied. A done task needs a row in a workflow.md status table. Run Gate 2 plus security reviewer in parallel for security-trigger files. Match `^## State \(` by line when scripting edits.
- Launch recipe: `Agent` with `isolation: worktree` and `run_in_background` (implementer type has a shell); architect for tests, task YAMLs and locked files.

## Open items
Owner:
- Push and merge each implementer branch the orchestrator names, dispatch `render.yml` on main after the lock fix merges, answer the Gemini quota question, then R17 by hand, then re-enable `daily-publish`.
- Approve the Phase 4 audit; sign off threat model v3.1 (its section 7 lists the settings, now done). Confirm the credit line text ("Narrated with a synthetic voice." after the sources line).
- Create the reusable harness skill: expand `graph-engineering` or make a new one with `skill-creator` in an owner admin window (`~/.claude/skills` is protected). It bakes in: caveman for chat, ponytail for code, model per role, rotation (orchestrator ~50%, tasks 60%), one watcher per task, one review pass chasing only blocking findings, the round cap and the phase-end review policy; contracts-first locked tests, lock hook plus scope check, `LOOM_ADMIN`, read-only reviewers, clean child environments; handoff Docs section, Scribe close-out, docs check; $0 rule, heavy tests in CI only, limit pause and resume, at most 2 parallel sessions.
- Pin `huggingface_hub` in `requirements-heavy.txt` (outside any task's paths, needs the owner).
- To-do artifact (stale, republish when tasks change): https://claude.ai/artifact/JAc72genBdoDjz2NaWqrpZ.

Orchestrator:
- Save the weekly usage-limit message to `.harness/tests/fixtures/limit_messages/` when it happens (only `session_5h-2026-11-15.txt` exists).
- Clean up stale worktrees under `.claude/worktrees/` (many, including merged task and docs branches). `git worktree remove` fails on path length: retry with `\\?\`.
- Doc follow-ups not applied: architecture.md line 54 and HARNESS.md section 11 tree comment for `docs_check.py` (add handoff Docs sections, lessons entries, required headings).
- Known risk: pip-audit ignores two setuptools 81.0.0 advisories (torch 2.11 caps setuptools below 82) and torch PYSEC-2025-194 (fixed in 2.13, no matching torchaudio, stable-ts imports torchaudio at load); drop the ignores and move the pins when torch or torchaudio ships.
- Older non-blocking follow-ups moved to `.harness/backlog.md` (the owner picks which become tasks).
