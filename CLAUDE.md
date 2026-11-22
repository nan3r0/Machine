# Shorts Pipeline

A $0, cloud-only pipeline that scripts, voices, renders and publishes faceless short videos, built by Claude Code agents under the Loom harness. Everything runs on GitHub Actions and free tiers; nothing depends on a local PC.

## Where things are

| File | What it holds |
|---|---|
| `PLAN.md` | The product design. Source of truth for what the pipeline does |
| `HARNESS.md` | How it is built: roles, gates, escalation, handoffs. Detail for every rule below |
| `PRD.md` | Checkable acceptance criteria per phase, decisions, open questions |
| `spec.md` | Stack, data model, numbers, security, gates, approved dependencies |
| `architecture.md` | Layers, flows, decisions, testing map, known weak points |
| `workflow.md` | Stage 0 how-to, module order, criterion to test map, status |
| `docs/threat-model.md` | STRIDE threat model of the pipeline (CSO). Read before adding an integration or secret |
| `lessons.md` | Mistakes and the rule each produced. Read before changing code |
| `.harness/tasks/` | Task YAMLs. Your task is the one named in `LOOM_TASK`. No `LOOM_TASK` means you are the orchestrator: read `.harness/handoffs/orchestrator.md` first |

## Status

Pipeline Phase 2 in progress (Phase 1 closed), Harness Stage 0. Phase 2 task graph in `.harness/tasks/phase2/`, decisions D1 to D8 in the Architect's Phase 2 plan handoff (D1 decided 2026-11-18: option (c), `GEMINI_API_KEY` is a repo secret). Done in Phase 2: entry CI, exact fact-check, contracts, script validation, Gemini client, seeded sources (15 files), script writer, meaning fact-check, weekly batch, weekly scripts workflow, CSO threat model v2, URL check hardening, hashed weekly workflow with validate job, Gemini redirect refusal. Phase-end reviews p2-qa-lead, p2-audit and p2-phase-review are done; Phase 2 code can close. Owner approved the Auditor report and signed off the threat model (2026-11-21). Owner gate left: re-enable weekly-scripts and run it once (R13.5). Phase 2b (phase review N1 to N5 and the QA lead's locked tests, plan in `.harness/handoffs/p2b-plan.md`) is built and merged: all six tasks done; its CI reports re-run is pending. Phase 2c is done (Gemini exceptions fixed, survivor tests added). Done too: p2d-ci-triggers, p4-licences and p4-contracts. Next: p4-pick and p4-youtube, then Phase 4, YouTube publishing (the Architect's Phase 4 plan handoff in `.harness/handoffs/`, tasks in `.harness/tasks/phase2d/` and `.harness/tasks/phase4/`; owner decisions O1 to O8 are made, the repo is public for now). The free Actions allowance ran out on 2026-11-21; public repos are not metered. Workflow A (weekly-scripts) stays disabled until the owner's first manual run. Harness set up; Phase 1 task graph approved (Kokoro-only voice). Repo: private `nan3r0/Machine`. Niche: Solved Internet & Everyday Mysteries (content rules in PLAN.md section 4). Done: all Phase 1 code tasks and the owner manual acceptance (69.6 s video, slower suspense pacing, VOICE_SPEED 0.9; every video targets about 65 s). Done too: the phase-end reviews (QA lead, CSO, Auditor) and the high-risk QA tests (p1-qa-tests). Done too: the speech-rate constants fix (144 wpm, 62 to 90 s over-a-minute rule, Retention format removed) and the compose FFmpeg timeout. Done too: golden frames across the full video (visual QA approved). The phase review and the owner approval of the Auditor report. Phase 1 is closed; next is Phase 2 (scripts and fact-check), planned by the Architect. Harness: automatic rotation hook live (`.claude/hooks/context_guard.py`); orchestrator state in `.harness/handoffs/orchestrator.md`. Voice: PyTorch `kokoro`, weights pinned. Everything must stay $0: free tiers only, no payment method on any account. Done tasks: `.harness/status.yaml`. Weak points: architecture.md section 7.

## Commands

- Gate 1: CI runs `make check` (adds the docs check, bandit, semgrep, gitleaks, pip-audit, actionlint). Locally: `ruff check .`, `mypy --strict pipeline/`, `pytest --cov=pipeline`, `python tests/docs_check.py`. Tests marked `heavy` run in CI only; never install ffmpeg or torch locally to run them. A skipped heavy test is not a pass: hand off as `partial`, "awaiting CI", until CI is green (CI starts from a PR, a draft is enough).
- Harness tests: `pytest .harness/tests`
- Log an attempt: `python .harness/log_outcome.py <task-id> --attempt N --result <result>`

## Rules every session follows

**One task, one fresh session.**
- Work on exactly the task in `LOOM_TASK`. Read its YAML, its `context_files`, this file and lessons.md first.
- Nothing carries over from earlier sessions except the repo and `.harness/handoffs/`.

**Locked files are off-limits.**
- Paths in `.harness/locks.yaml` (contracts and tests) are never edited by implementers. The PreToolUse hook blocks it.
- If a locked test looks wrong, write `CONTRACT_CHANGE.md` (which test, why it contradicts PLAN.md, what it should say) and stop.
- Never write files through Bash to get around the hook. CI diffs every task branch against `paths_allowed`, so it gets caught anyway.
- Claude Code config and execution files (hooks, settings, agents, commands, skills, plugins, `.mcp.json`), anywhere, are owner-only (`LOOM_ADMIN=1`). Outside the repo, only memory and job scratch folders are writable.

**Stay inside `paths_allowed`.**
- Edit only files that match your task's `paths_allowed`, plus your own `.harness/handoffs/<task-id>.md`, `CONTRACT_CHANGE.md` and `ENV_ISSUE.md`.
- Need a file outside it? Say so in the handoff and stop. Don't widen the scope yourself.

**Write the handoff before finishing.** `.harness/handoffs/<task-id>.md`, from HARNESS.md section 7: Goal, Status, What changed (and why), Decisions made, Tried and abandoned (required, "none" if none), Known risks, Next step, Docs (required, "none" if none: every doc change this work needs), Evidence (test counts, commands run). A task without a complete handoff is not done. Edit the docs inside your `paths_allowed`; the rest is applied at close-out (HARNESS.md section 10).

**Rotate before the context fills** (HARNESS.md section 7a). Check `/context`; above about 50% on an unfinished task, write a partial handoff and stop, so a fresh session continues from it. To pause, write the handoff with status `partial` and commit WIP. Rotations and usage limits are not failed attempts.

**Spend few tokens** (HARNESS.md section 7b). Chat replies terse (caveman style); code minimal (ponytail: simplest thing that works); docs, commits and PRs in normal English. Tool output small:
- `pytest -q --tb=short`, single files or test IDs while iterating, full suite only before finishing.
- FFmpeg and subprocess: `-hide_banner -loglevel error`; long logs go to `out/logs/<step>.log`, then grep them.
- Search first (`grep -n`), then read only the line ranges you need. Use a subagent for wide searches.
- Never print JSON queues, `.ass` files, transcripts, media or install logs (`pip -q`). `git diff --stat` before full diffs.
- An install or environment problem not fixed in 2 tries: write `ENV_ISSUE.md` and stop.

**Pass the gates in order** (HARNESS.md section 6a): Gate 1 automated checks, then Gate 2 Opus review, then Gate 3 merge plus full suite.

**Gate 2 review checklist** (reviewer is read-only and returns JSON):
1. Contract: does what the task and PLAN.md say, not just what the tests check
2. Test integrity: no special-casing of test inputs
3. Edge cases: empty or long input, unicode in captions, odd audio lengths, API errors, timeouts
4. Failure handling: errors caught, logged, surfaced; nothing silently swallowed
5. Security: no secrets in code or logs, no shell injection in FFmpeg or subprocess, pinned dependencies
6. Fit: existing interfaces, no duplicate helpers, nothing outside `paths_allowed`
7. Maintainability: clear names, no dead code, docstrings on public interfaces
8. Docs aligned: handoff Docs section complete; no doc made false by the diff

Every blocking finding from any reviewer needs file:line, severity, a concrete failure scenario and a fix hint; otherwise it is a note. Specialist reviews (security, visual QA, phase-end QA Lead, CSO, Auditor) follow HARNESS.md section 6b and the triggers in `.harness/config.yaml`.

## Project rules

- Tests before code. Every fixed bug gets a regression test that fails without the fix.
- No new dependency outside spec.md section 7 without owner approval.
- Numbers (resolution, loudness, durations, thresholds) live only in `pipeline/constants.py`.
- Subprocess calls take argument lists, never `shell=True`.
- No secrets and no personal details in code, config, logs or commits.
- Work on a branch. Commit or push only when the owner asks.
- If PLAN.md or HARNESS.md looks wrong, tell the owner before working around it.
- End of session: update Status here if the project changed shape; add a lessons.md entry for any mistake found.
