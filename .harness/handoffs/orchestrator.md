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
- Rotate yourself after every task close-out, or at about 50% context, whichever comes first: rewrite State and Open items here. The Stop hook `context_guard.py` does this automatically at 50%: when it blocks your stop with "Context at N%", update this file and the docs it lists, commit, reply ROTATE, and it opens the replacement window. It only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator` (sets `LOOM_ROLE`). Before the hook is registered, tell the owner to start a fresh session (`claude.cmd --model claude-sonnet-5-5`) and type "continue as orchestrator". Cost per turn grows with context, so earlier is cheaper.
- One watcher per task; no polling loops in your own turns.
- One Gate 2 pass per task; chase only blocking findings.

## State (2026-11-15, second orchestrator session, Phase 1 code complete)
- All Phase 1 code tasks merged: contracts, tts-kokoro, docs-check, align, captions-ass, compose, qa, render-cli (#31, #32), font-fix (#35), actions-workflow (#34). Close-out docs on `docs/p1-closeout-4`.
- First GitHub render run (workflow `render.yml`, run 43784575673 on task/p1-font-fix): QA passed, 35.5 s, 1080x1920, 30 fps, real Montserrat Bold in the golden frames.
- Open: (1) owner manual acceptance of a downloaded `final.mp4` (PLAN.md section 11); (2) phase-end reviews: QA lead (mutmut report), CSO threat model, Auditor, phase review (tasks 11 to 14 in `.harness/tasks/phase1/`); (3) owner decision pending: every video about 65 s once live. Recommended plan given to the owner: one Architect PR changing PLAN.md section 4 (65 s default format, 62 to 90 s QA range already exists, curiosity reset mandatory, replace the 30 to 45 s retention metric), plus `queue/approved/sample-65s.json` (about 175 words) and the workflow default path. Waiting for "go" and a retention target.
- Architect follow-ups: move `_AUDIO_RATE_HZ`, `_STDERR_TAIL_LINES` (compose.py) and `_FPS_TOLERANCE`, `_TOOL_TIMEOUT_S`, `_STDERR_TAIL_LINES` (qa.py) into `pipeline/constants.py` (locked). Non-blocking notes not chased: render.yml log upload gating and `--` guard, composite action for shared CI setup, `FONTS_DIR` relative to cwd, stale `qa.json` on reused out dirs, `render_one` computes narration text twice.
- Launch helper pattern: a small .ps1 taking -Task -Worktree -Brief (Git Bash `cmd //c start` quoting fails). Close windows by stopping the `open_task_window` powershell, excluding your own PID.
- Process rule: when review requests changes, mark the PR draft before starting the fix round and tell the owner not to merge.

## Open items
- Usage-limit fixture saved (`.harness/tests/fixtures/limit_messages/session_5h-2026-11-15.txt`). Add the weekly one when it happens.
- Known risk: pip-audit ignores two setuptools 81.0.0 advisories because torch 2.11 caps setuptools below 82; drop the ignores when torch lifts the cap (Makefile comment). It also ignores torch PYSEC-2025-194 (fixed in 2.13) because no torchaudio for torch 2.13 exists and stable-ts imports torchaudio at load; move both pins when one ships.
- **Owner to-do, remind them after the first implementer task closes out:** create a reusable skill for this setup, or expand the existing `graph-engineering` skill, with `skill-creator` in an owner-launched admin window (`~/.claude/skills` is protected). It packages the HARNESS.md and CLAUDE.md templates, task, handoff and orchestrator files, all `.harness/scripts`, the lock hook and the rotation hook. It must bake in:
  - tokens: caveman for chat, ponytail for code, model per role (Sonnet orchestrates and implements, Opus advises on architecture, contracts and reviews, Haiku does doc sync), rotation (orchestrator per task or ~50%, tasks at 60%) with automatic handover, one watcher per task, one review pass chasing only blocking findings, low effort for mechanical work, small tool output
  - safety: contracts-first locked tests with a task-aware conftest, lock hook plus CI scope check, `LOOM_ADMIN` for config files, read-only reviewers, specialist reviews only when triggered, clean child-session environments, self-closing windows
  - docs: handoff Docs section, Scribe close-out, CI docs check, lessons logged the same turn
  - cost and limits: $0 rule, heavy tests in CI only, usage-limit pause and resume, at most 2 parallel task sessions
- Doc follow-ups not yet applied: architecture.md line 54 and HARNESS.md section 11 tree comment for `docs_check.py` (add handoff Docs sections, lessons entries, required headings); HARNESS.md section 10 close-out should say status.yaml and the workflow.md row change in the same commit. Pin `huggingface_hub` in `requirements-heavy.txt` (needs owner approval, outside any task's paths). Review notes on kokoro.py (streaming hash, NaN guard, `repo_id`) were non-blocking and are not chased.
