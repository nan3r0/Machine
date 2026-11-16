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

## State (2026-11-16, end of fourth orchestrator session)
- p1-qa-tests done: PRs #47 (contracts) and #48 (real FFmpeg fixtures, handoff) merged. Scope was QA lead items 1 to 13 plus 16 (owner rule: high risk means anything that could break the pipeline logic; 14 and 15 skipped). Opus advisor reviewed the scope. Close-out docs are on branch `docs/p1-qa-tests-closeout` (lessons, architecture section 7, status.yaml, workflow.md, CLAUDE.md status, spec.md fixes); the owner merges it.
- CSO P1-1, P1-3 and P1-6 move to Phase 2 entry (Workflow A needs the first repo secret, the approval PR and write permissions). CSO P1-2, P1-4, P1-5 and Auditor A1 to A3 stay in Phase 4 pre-go-live. Owner still has to check whether free private repos allow environment secrets with branch rules, and approve the Auditor report.
- Done since: p1-constants-timeout (PRs #50, #51) and p1-golden-65s (PRs #53, #54): speech rate 144 wpm, Retention format removed (every video over a minute, QA range 62 to 90 s), numbers moved to constants.py, compose FFmpeg timeout, golden frames across the full video, visual QA approved (open notes: end frame at 69.1 s is empty background, a two-line caption near 34 to 38 s was not sampled). Next: task 14 phase review, then plan Phase 2 (Architect) with CSO P1-1, P1-3, P1-6 at its entry. Owner starts Phase 0 admin (YouTube first) in parallel.
- Gate 2 non-blocking test notes on p1-qa-tests are logged in its handoff, not chased.
- To-do artifact: https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ
- Stale worktrees under `.claude/worktrees/` still need cleanup.

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
