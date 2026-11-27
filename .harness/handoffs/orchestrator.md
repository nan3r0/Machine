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

## State (2026-11-26, 29th session, replaces all earlier State blocks)
- Phase 3 waves 1 to 7 merged: p3-spike, p3-character-art, p3-contracts, p3-validate-visuals, p3-ass-kit, p3-character, p3-sets, p3-sets-art (owner approved stills), p3-cards, p3-charts, p3-compose. Close-out docs for waves 4 to 7 are on `docs/p3-wave7` (not pushed).
- Wave 8: p3-router is built and approved (Gate 2 and visual QA, no blockers) on `task/p3-router` (main merged in, CONTRACT_CHANGE removed). Its locked test fixture was fixed by the Architect on `plan/p3-router-tests` (PR #204, merge first), then main is merged into the task branch and the owner pushes it and opens the PR. Docs PR is #203. Owner paused for the weekly usage limit (2026-11-27): no wave 9 started.
- First action next session: check #203, #204 and the router PR are merged; then launch p3-wiring (M1). Owner wants one real animated video from sample-65s as soon as wiring merges: owner dispatches render.yml, downloads the artifact, and judges quality. M1 rendered checks to carry into the wiring brief: hard cut to black then 0.5 s fade at the intro and outro (constants say fade through black), data-scene card contrast over the dimmed set, captions over black during fades, push-in anchor point (libass scales about the pos point, not \org), and the timed render against RENDER_BUDGET_S (router emits about 8100 Dialogue lines for sample-65s versus 2564 in the spike; if too slow, emit only the face group on word and blink cuts in character.py). Also owed: strip { } and backslash from Gemini text before it enters ASS events (p3-wiring or the scenes writer), and correct the p3-router YAML note about the hook set (the mascot addendum replaced it).
- Next: wave 9 p3-wiring is M1 (render.yml on sample-65s and demo-data; owner watches). Then wave 10 p3-writer-visuals and p3-batch-visuals (M2, first Workflow A run), wave 11 p3-cso and p3-qa-lead, wave 12 p3-phase-review.
- Mascot direction (owner 2026-11-26): the host is the channel mascot. Every video is host intro (hook, max 5 s, one generic backdrop, no house set), 0.5 s transition, story scenes, short host outro. In constants, the router contract and PRD R19 to R22.
- Method A (all libass), owner 2026-11-25: 64 s vs 140 s for PNG layers. p3-background deferred to slice 2 (Flux image layers).
- p3-contracts decisions (`.harness/handoffs/p3-contracts.md`): the host is drawn at 0.85 of the approved size to clear the captions (visual QA checks it); cap of 3 data scenes per script.
- Owner steps open: R17, threat model v3.1 sign-off, re-enable `daily-publish` (go-live waits for Phase 3 slice 1, D7). `weekly-scripts` is active (Sunday cron); owner decided (D6) no real run until M2.
- Non-blocking: ci.yml `check` and `reports` install torch without `--require-hashes`; `error.read()` in gemini.py has no size cap.
- Process: owner pushes (agents have no push). Owner has pushed everything with `git push` and `gh pr create` as one-line `!` commands. Paths in `git -C` are absolute and typed on one line (pasted text adds a hidden leading space). Contracts commit merges to main on `plan/<id>` BEFORE the implementer starts. Locked-test fixes from review go on `plan/<id>-tests`, merged to main first, then main is merged into the task branch (never rebase). Review round cap hit on p3-cards; the Architect fixed it. Implementers: `git checkout -B task/<id> <base>`. Never hand the owner a `worktree-agent-*` name. `gh workflow run` is denied (give Actions page steps). Agents cannot watch video: visual QA reads still frames and an 8-frame strip. Gate 2 plus security reviewer in parallel for security-trigger files. A done task needs a row in a workflow.md status table. Match `^## State \(` by line when scripting edits.
- Owner is considering removing `git push` from the global deny list, and later `gh pr merge` once main has a ruleset requiring `check`. Not done; do not assume it.
- Launch recipe: `Agent` with `isolation: worktree` and `run_in_background` (implementer has a shell); architect for tests, task YAMLs and locked files. A subagent out of turns can be resumed with SendMessage. Agents cannot delete remote branches; give the owner the command.

## Open items
Owner:
- Push and merge each branch the orchestrator names, including `docs/p3-wave7`. Dispatch `render.yml` for M1 (sample-65s and demo-data) from the Actions page. Then R17 by hand, then re-enable `daily-publish`.
- Sign off threat model v3.1. Approve the Phase 4 audit. Confirm the credit line text ("Narrated with a synthetic voice." after the sources line).
- Create the reusable harness skill: expand `graph-engineering` or make a new one with `skill-creator` in an owner admin window (`~/.claude/skills` is protected). It bakes in: caveman for chat, ponytail for code, model per role, rotation (orchestrator ~50%, tasks 60%), one watcher per task, one review pass chasing only blocking findings, the round cap and the phase-end review policy; contracts-first locked tests, lock hook plus scope check, `LOOM_ADMIN`, read-only reviewers, clean child environments; handoff Docs section, Scribe close-out, docs check; $0 rule, heavy tests in CI only, limit pause and resume, at most 2 parallel sessions.
- Pin `huggingface_hub` in `requirements-heavy.txt` (outside any task's paths).
- Decide on `git push` in the global deny list (see State).
- Uninstall the stray `tests` package in global site-packages (backlog).
- To-do artifact (stale, republish when tasks change): https://claude.ai/artifact/JAc72genBdoDjz2NaWqrpZ.

Orchestrator:
- Architect task owed: `test_captions_exact.py` accepts the frame centre or `CAPTION_POS_Y`; narrow it now that p3-compose is merged.
- lessons.md entries for waves 4 to 7 were not written by the Scribe (its rules forbid it). Write them: p3-charts (plain-string ASS tags), p3-cards (measure real font widths), and the `plan/<id>-tests` branch rule.
- Save the weekly usage-limit message to `.harness/tests/fixtures/limit_messages/` when it happens (only `session_5h-2026-11-15.txt` exists).
- Clean up stale worktrees under `.claude/worktrees/`. `git worktree remove` fails on path length: retry with `\\?\`.
- Doc follow-ups not applied: architecture.md line 54 and HARNESS.md section 11 tree comment for `docs_check.py` (add handoff Docs sections, lessons entries, required headings).
- Known risk: pip-audit ignores two setuptools 81.0.0 advisories and torch PYSEC-2025-194; drop the ignores when torch or torchaudio ships.
- Non-blocking follow-ups live in `.harness/backlog.md` (the owner picks which become tasks).
