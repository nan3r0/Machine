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

## State (2026-11-26, 28th session, replaces all earlier State blocks)
- Phase 4c and `p4d-gemini-quota-guard` are done and merged (#181, #182, #183). Required checks on main: `check` and `lock-resolve`, up to date.
- Phase 3 (visuals) is planned and owner-approved, merged in #184 and #185. Plan: `.harness/handoffs/p3-plan.md`. Task YAMLs: `.harness/tasks/phase3/`. Look: an original round-head host character on flat parallax sets, bold captions, Flux paintings later (slice 2). Reference style: the owner's screenshots and the browser mock at https://claude.ai/artifact/DqwmzkpCP8LrNSyCZ3xToN. Do not copy any creator's character.
- Method A (all libass), owner 2026-11-25: 64 s vs 140 s for PNG layers. p3-background is deferred to slice 2 (Flux image layers). M0 is satisfied.
- Merged on 2026-11-26: p3-spike handoff (#186), p3-character-art (#187), p3-contracts (#188, main at `fbec8b0`). Owner approved the host still sheet. All spike branches are deleted everywhere.
- Mascot direction (owner 2026-11-26): the host is the channel mascot. Every video is host intro (hook, max 5 s, one generic backdrop, no house set), a 0.5 s transition, the story scenes, then a short host outro. Already in constants, the router contract and PRD R19 to R22.
- p3-contracts decisions (handoff `.harness/handoffs/p3-contracts.md`):
  - The host is drawn at 0.85 of the approved size to clear the captions. Visual QA must check it.
  - New cap of 3 data scenes per script. The p3-validate-visuals YAML does not say so yet.
  - `test_captions_exact.py` now accepts the frame centre or `CAPTION_POS_Y`. An Architect task narrows it after p3-compose merges.
  - YAML notes owed at close-out: 03, 07, 11, 13, 14 (handoff Docs section).
- Next:
  1. Close-out done on branch `docs/p3-closeout` (status.yaml, workflow.md, CLAUDE.md, YAML notes 03/07/11/13/14, p3-plan line). Owner pushes and merges it. Outcome log not written (no result data yet).
  2. Wave 4 built and reviewed 2026-11-26 (Gate 2 plus security approve, both with only non-blocking notes). Owner merge order: `plan/p3-validate-visuals-tests` (Architect fix of a locked-test strict-date bug, commit 453aacb), then `task/p3-validate-visuals` (already merged with the plan branch), then `task/p3-ass-kit`, then `docs/p3-closeout`. After that: scope check passes, then wave 5 (p3-character, p3-sets), then the rest. Non-blocking notes to carry: ass_kit text_event does not reject newlines (check in cards/charts review); validate.py does not reject `{}\` in item text (the renderer must escape); chart value regex accepts `1,`; U+2028/2029 not in bad categories.
- `weekly-scripts` is ACTIVE (Sunday cron). The 2026-11-25 manual run failed on Gemini 503 overload; the quota guard stopped it after 3 errors (6 requests). Owner decided (D6): do not run it again for real until M2, because sources are single-use. Free limit: 20 requests a day for `gemini-3.8-flash` per model. If 503s persist later: longer retry wait, or spread writes over days.
- Owner steps open: R17, threat model v3.1 sign-off, re-enable `daily-publish` (go-live waits for Phase 3 slice 1, D7). Dependabot rfc3986/csvw ignores stay bare (narrowing gains nothing).
- Non-blocking: ci.yml `check` and `reports` jobs install torch without `--require-hashes` (about lines 90 and 149); `error.read()` in gemini.py has no size cap (negligible).
- Process: owner pushes (agents have no push). Contracts commit (task YAML, locked tests, import stubs) merges to main on a `plan/<id>` branch BEFORE the implementer starts; then merge main into the task branch, never rebase (lessons.md). Implementers: `git checkout -B task/<id> <base>`. Never hand the owner a `worktree-agent-*` name. `gh pr create` is allowed; `gh workflow run` is denied (give Actions page steps). Agents cannot watch video: visual QA reads still frames and an 8-frame strip; the owner watches M1. Gate 2 plus security reviewer in parallel for security-trigger files. A done task needs a row in a workflow.md status table. Match `^## State \(` by line when scripting edits.
- Launch recipe: `Agent` with `isolation: worktree` and `run_in_background` (implementer has a shell); architect for tests, task YAMLs and locked files. A subagent that runs out of turns can be resumed with SendMessage (its worktree holds the branch). Agents cannot delete remote branches; give the owner the command.

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
