# Handoff: orchestrator

Read this first in any session started without `LOOM_TASK`. Then read only the HARNESS.md sections named below, when needed. Keep this file current: rewrite "State" and "Open items" before you stop.

## Role
You are the Stage 0 orchestrator (HARNESS.md section 10, Stage 0). Model: Sonnet. You launch task sessions, verify their work, run reviews, push, open PRs and log outcomes. The owner only approves the contracts PR and merges PRs. Never edit `.claude/` admin files (owner only, `LOOM_ADMIN=1`).

## How to run a task
1. Worktree per task branch `task/<id>` under `.claude/worktrees/`. Python: `.venv/Scripts/python.exe` in that worktree (create with `python -m venv .venv`, install `requirements.txt` and `requirements-dev.txt` only).
2. Launch (window closes itself when the session ends):
   `cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 -Task <id> -Model <from .harness/config.yaml> -WorkDir <worktree> -Message "<brief>"`
   Brief: role, "Follow CLAUDE.md", read the task YAML and handoff, Bash one plain command per call, commit but do not push, finish the handoff including Docs.
3. One background watcher: `sh .harness/scripts/wait_task.sh <worktree> <id> <start-sha> <claude-pid>`.
4. On TASK_DONE: run ruff, `mypy --strict pipeline/`, pytest (with `LOOM_TASK=<id>`), `tests/scope_check.py task/<id> origin/main`. Then one Gate 2 review with `.harness/scripts/run_review.sh` (prompt: read `.claude/agents/reviewer.md`, the task YAML, the handoff, the diff saved to `.harness/reviews/<id>.diff`). Add a specialist review only if `specialist_reviews` paths in config.yaml match.
5. Blocking findings: write `.harness/reviews/<id>-round<N>.md`, relaunch (resume if the session's context is small, else fresh). Non-blocking notes: log them, don't chase them.
6. Push, open the PR, `sh .harness/scripts/wait_ci.sh <pr>` once. Green: tell the owner it's ready. Close the task window by stopping its parent `powershell.exe`, never only `claude.exe`.
7. Close-out after merge: lessons and decisions yourself; Scribe (Haiku) window for status.yaml, workflow.md status, CLAUDE.md status, outcome log. Docs go on a `docs/*` branch, never a task branch.

## Token rules
- Terse replies; caveman style for chat, normal English for docs, commits and PRs.
- Rotate yourself after every task close-out, or at about 50% context, whichever comes first: rewrite State and Open items here, then tell the owner to start a fresh session (`claude.cmd --model claude-sonnet-5-5`) and type "continue as orchestrator". Cost per turn grows with context, so earlier is cheaper.
- One watcher per task; no polling loops in your own turns.
- One Gate 2 pass per task; chase only blocking findings.

## State (2026-11-15, end of first orchestrator session)
- Merged to main: harness, hook hardening, plan research, doc sync (PRs #1 to #5, #7 to #9).
- **p1-contracts:** draft PR #6, branch `task/p1-contracts`, worktree `.claude/worktrees/hook-hardening`. Review rounds 1 and 2 done; Gate 2 and security both approve. CI after round 2: all tests, ruff, mypy, bandit, semgrep, gitleaks pass; only pip-audit fails, because it audits the whole runner environment (semgrep's `mcp` and `opentelemetry-api`, and `setuptools`). Round 3 (`.harness/reviews/p1-contracts-round3.md`): audit only the project requirement files and upgrade setuptools. Next: when CI is green, mark PR #6 ready and tell the owner it is the main checkpoint (locked tests).
- After PR #6 merges: close-out (add `p1-contracts` to `.harness/status.yaml`, etc.), then `p1-docs-check` (test_author) and the five implementer tasks (`p1-tts-kokoro`, `p1-align`, `p1-captions-ass`, `p1-compose`, `p1-qa`; Sonnet, at most 2 at once, separate worktrees), then `p1-render-cli`, `p1-actions-workflow`, phase-end reviews.

## Open items
- Owner decision pending: alignment model `base.en` vs `small.en` (orchestrator recommends `small.en` for tighter caption timing).
- Save the first real usage-limit message to `.harness/tests/fixtures/limit_messages/` (HARNESS.md section 10b). Today's 5-hour message: "You've hit your 5-hour limit · resets 5:20pm (Europe/London)".
