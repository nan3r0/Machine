# Build Workflow

The process (roles, lifecycle, gates, escalation, handoffs, learning loop) is defined in HARNESS.md. This file is the Stage 0 how-to and the Phase 1 build record.

## Steps (Stage 0, one task)

1. Pick the next task in `.harness/tasks/phase1/` whose `depends_on` are all done.
2. Start a fresh session with the task id set, from the project root:
   - PowerShell: `$env:LOOM_TASK='p1-align'; claude --model sonnet`
   - Git Bash: `LOOM_TASK=p1-align claude --model sonnet`
   - Use `--model opus` for `test_author`, `architect` and `reviewer` tasks.
3. Tell the session: "Do task p1-align. Follow CLAUDE.md." It reads the task YAML and its `context_files`.
4. Gate 1: `ruff check .`, `mypy --strict pipeline/`, `pytest --cov=pipeline`, and check that changed files stay inside `paths_allowed` (the hook does not see Bash writes). Heavy tests skip locally, so for kokoro, align, compose, qa and render-cli, Gate 1 is a green CI run on the `task/<task-id>` branch. The session hands off as `partial` ("awaiting CI"); you push the branch, and if CI fails you paste the failure into the same session (a resume, not a new attempt) until it is green.
5. The implementer writes `.harness/handoffs/<task-id>.md` from the HARNESS.md section 7 template.
6. Gate 2: save the diff where the reviewer can read it (`git diff main... > .harness/reviews/<task-id>.diff`), then start a fresh read-only Opus session with no task set: `claude --model opus --disallowedTools "Edit,Write,MultiEdit,NotebookEdit,Bash"` and ask it to review the task as the `reviewer` agent (`.claude/agents/reviewer.md`). Blocking issues go back to step 2, at most 2 rounds, then Opus fixes (HARNESS.md section 6). If the task's changed files match `specialist_reviews` in `.harness/config.yaml`, run that specialist too, the same way (`security-reviewer` or `visual-qa` agent). In Phase 1 that means security for p1-contracts (`ci.yml`), p1-compose and p1-actions-workflow, and visual-qa for p1-captions-ass, p1-compose and p1-qa. Visual-qa reads the golden-render frames from the CI artifact, downloaded to `out/frames/`.
7. Gate 3: add the task id to `done` in `.harness/status.yaml`, merge to main, and check that CI is green on main.
8. Log the attempt: `python .harness/log_outcome.py <task-id> --attempt N --result <result> [--failing ...]`.
9. If a mistake was found, add a `lessons.md` entry and a regression test.

Failures repeat step 2 with the failing output in context. Escalation thresholds are in `.harness/config.yaml`.

**Rotation (HARNESS.md section 7a).** Failed tests or review changes: keep the same session. Context above about 50% (`/context`) or `max_turns` hit: ask for a partial handoff, then start a fresh session on the same task from it, and log `--result rotated --rotation-reason context_limit` (or `max_turns`). After 3 rotations on one task, the Architect splits it.

**Who runs the steps (since 2026-11-15).** An orchestrating Claude session drives Stage 0 for the owner: it launches each task as a fresh session with `LOOM_TASK` set (headless, or in a visible PowerShell window the owner can watch and type into), runs the gates and reviews, pushes branches, opens PRs and logs outcomes. The owner approves the contracts PR and merges PRs. Bookkeeping (outcome log, status lines) goes on a separate branch, never on a task branch, so CI's scope check stays clean.

**Changing the harness itself.** Hooks, settings, agents, commands, skills, plugins and `.mcp.json` are blocked in every session unless you launch it with `LOOM_ADMIN=1` (retrospectives that add skills need it too) (PowerShell: `$env:LOOM_ADMIN='1'; claude`). Never set it for an implementer session.

**Pausing (HARNESS.md section 10a).** Press `Esc`, then: "Stop here. Write handoff.md for this task (status: partial) and commit WIP." Next time, start a fresh session from the task YAML and handoff. Use `claude --continue` only if the task was nearly done.

**Usage limits (HARNESS.md section 10b).** Not a failure: log `--result usage_limit`, no attempt counted. Save each real limit message (5-hour and weekly) verbatim to `.harness/tests/fixtures/limit_messages/<type>-<date>.txt`; Stage 1's parser is built from them. After the reset, resume the same session if its context is under about 50%, otherwise rotate.

**ENV_ISSUE.md.** If a session writes it, fix the environment yourself or log `--category env_or_dependency`; don't let the agent loop on installs.

## Rules

- Every task passes all three gates before the next task that depends on it starts.
- A fresh session starts cold. Its context is the task YAML, its `context_files`, CLAUDE.md and lessons.md. Nothing else carries over except handoffs.
- A locked test that seems wrong becomes a `CONTRACT_CHANGE.md` for the Architect, never an edit.
- Stop and ask the owner for: new dependencies, contract changes, any open question in PRD.md section 8, commits and pushes.
- Small requests after a phase still go through the gates. Skipped reviews are where repeat mistakes come from.

## Phase 1 module order

```
p1-contracts -> p1-tts-kokoro, p1-align, p1-captions-ass, p1-compose, p1-qa
all five -> p1-render-cli -> p1-actions-workflow -> p1-qa-lead, p1-cso, p1-audit -> p1-phase-review
p1-captions-ass -> p1-font-fix (added after PR #32: static Montserrat Bold, run before p1-actions-workflow)
p1-actions-workflow -> p1-sample-65s (added 2026-11-16: render workflow defaults to the 65 s sample, run before the phase-end reviews)
p1-qa-lead -> p1-qa-tests (added 2026-11-16: locked tests for QA lead items 1 to 13 and 16, run before p1-phase-review)
p1-qa-tests -> p1-constants-timeout (added 2026-11-16: compose and qa numbers from constants.py, timeout on compose's FFmpeg calls, run before p1-phase-review)
```

Stage 0 runs them one at a time in file-name order (`.harness/tasks/phase1/00_*.yaml` to `14_*.yaml`; gaps in the numbers are tasks dropped with edge-tts). Tasks added later (`15_*.yaml` onward) run where their dependencies and the note above put them. Before p1-qa-lead and p1-audit, run the CI report job and download its reports to `out/reports/`.

### Criterion to test map

Locked by p1-contracts. Every task's acceptance test is `test_acceptance` in its file.

| PRD criterion | Test |
|---|---|
| R1.1 to R1.3 | `tests/test_schema.py`; workflow default in `tests/test_render_default.py` (task p1-sample-65s) |
| R2.1 to R2.3 | `tests/voice/test_kokoro.py` (`test_acceptance`, `test_second_run_uses_cache_offline`, `test_unpinned_voice_fails_before_any_download`, `test_tampered_weights_fail_before_kokoro_loads`, `test_kokoro_failure_raises_voice_error`, `check_wav` tests); weight pins in `tests/test_pins.py` |
| R3.1, R3.2 | `tests/voice/test_align.py` (heavy acceptance on the fixture wav, plus a hypothesis property on `to_word_timings`) |
| R4.1 to R4.3 | `tests/render/test_captions_ass.py` (hypothesis property `test_every_word_shown_once_in_order_inside_the_audio`); caption font is static Montserrat Bold in `tests/render/test_font.py` |
| R5.1 to R5.3 | `tests/render/test_compose.py::test_acceptance` (heavy; also writes `out/frames/compose-*.png`) |
| R6.1 | `tests/render/test_qa.py` |
| R6.2 | `tests/test_render_one.py::test_acceptance` (heavy golden render; writes `out/frames/golden-*.png`: every 10 s from 1 s to 60 s plus one frame 0.5 s before the end) |
| R6.3 | `tests/test_render_one.py::test_qa_failure_exits_non_zero_and_names_checks` |
| R7.1 | `tests/test_workflows.py` plus a manual run |
| R7.2 | Manual, owner, on the 65 s sample |
| R7.3 | CI run on push; structure in `tests/test_ci_workflow.py` |
| R7.4 | `tests/test_conftest_selection.py` |
| R7.5 | CI `make check`; scope check in `tests/test_scope_check.py` |
| R7.6 | Handoffs of p1-qa-lead, p1-cso, p1-audit; owner approves |
| QA lead gaps (p1-qa-tests) | `tests/render/test_captions_exact.py`, `tests/render/test_compose_exact.py`, `tests/render/test_qa_exact.py`, `tests/render/test_ffmpeg_fixtures.py` (heavy fixture guard), `tests/voice/test_kokoro_audio.py`, `tests/voice/test_align_model.py`, `tests/test_render_one_files.py` |
| Numbers in constants.py, compose FFmpeg timeout (p1-constants-timeout) | `tests/render/test_render_constants.py` |
| Phase 2 shapes (Fact, SourceFile, Flag, LineVerdict) | `tests/test_schema_sources.py` |
| R8.1 | `tests/test_sources_files.py` |
| R8.2 | Manual, owner, in the p2-seed-sources PR |
| R9.1, R9.2 | `tests/factcheck/test_exact.py` |
| R10.1 to R10.3 | `tests/script/test_generate.py` |
| R10.3 to R10.5 | `tests/script/test_batch.py` |
| R11.1 | `tests/factcheck/test_semantic.py` |
| R11.2, R11.3, R13.1 | `tests/script/test_batch.py` |
| R12.1 | `tests/script/test_validate.py` |
| R12.2 | `tests/test_render_one_validate.py` |
| R12.3 | `tests/test_queue_scripts.py` |
| R13.2 | `tests/test_weekly_workflow.py` |
| R13.3 | `tests/test_workflow_safety.py` |
| R13.4 | PRD.md section 7 entry for owner decision D1 |
| R13.5 | Manual, owner, on the first Workflow A PR |
| R13.6 | Handoffs of p2-qa-lead, p2-cso, p2-audit; owner approves |
| R13.7 | `tests/test_weekly_hardening.py` (P2-1, P2-2, P2-4, P2-6), `tests/script/test_validate_urls.py` (P2-3), `tests/script/test_gemini_redirect.py` (P2-5) |

Phase 2 rows without backticks name test files that do not exist yet; the task that writes each file adds the backticks, so the docs check starts checking them.

`tests/test_ci_workflow.py`, `tests/test_pins.py` and `tests/test_scope_check.py` belong to no task, so they always run. CI uploads `out/frames/` as the `frames` artifact for the visual-qa reviewer.

### Phase 1 status

| Task | Status | Review |
|---|---|---|
| Harness setup (hook, config, agents, logger, status file) | done, 25 harness tests pass, hook confirmed live | none yet |
| p1-contracts | done, merged 2026-11-15 (PR #6), 100 passed, 110 skipped, CI green | Gate 2 and security approved after 5 fix rounds |
| p1-tts-kokoro | done, merged 2026-11-15 (PR #22), heavy tests passed in CI | Gate 2 approved |
| p1-docs-check | done, merged 2026-11-15 (PR #23), 127 passed, 110 skipped | Gate 2 and security approved |
| p1-align | done, merged 2026-11-15 (PR #26), heavy tests passed in CI | Gate 2 approved |
| p1-captions-ass | done, merged 2026-11-15 (PR #27), 127 passed, 83 skipped | Gate 2 and visual QA approved (code only, no frames yet) |
| p1-compose | done, merged 2026-11-15 (PR #28), heavy tests passed in CI after one fix round (two-pass loudnorm) | Gate 2, security and visual QA approved; Montserrat bold unverified on a real render |
| p1-qa | done, merged 2026-11-15 (PR #30), heavy tests passed in CI | Gate 2 and visual QA approved (code only) |
| p1-render-cli | done, merged (PRs #31 and #32), heavy tests passed in CI | Gate 2: one blocking finding (exit codes), fixed in #32; regression test added by the Architect in #33 |
| p1-font-fix | done, merged (PR #35); render run shows real Montserrat Bold | Locked name-table test; golden frame checked by the orchestrator |
| p1-actions-workflow | done, merged (PR #34); first render run on GitHub passed QA (35.5 s) | Gate 2 and security approved. Owner manual acceptance still open |
| p1-sample-65s | done, merged (PR #38); default render is the 65 s sample | Diff read by the orchestrator; no separate review (one default path) |
| Owner manual acceptance | done 2026-11-16: 69.6 s video from run 43873059742 approved (voice pacing and tone) | Owner |
| p1-qa-lead | reviewed 2026-11-16 (QA lead; read-only role, so not in status.yaml) | |
| p1-cso | reviewed 2026-11-16 (CSO; read-only role, so not in status.yaml) | |
| p1-audit | reviewed 2026-11-16 (Auditor; read-only role, so not in status.yaml) | |
| p1-phase-review | reviewed by the Architect (read-only role, so not in status.yaml), findings in .harness/handoffs/p1-phase-review.md; Phase 1 closes when the owner approves the Auditor report (R7.6) and main CI is green | |
| p1-qa-tests | done 2026-11-16: PRs #47 and #48 merged; real FFmpeg fixtures from CI run 43917100099; CI green with LOOM_TASK (run 43918370324) | |
| p1-constants-timeout | done 2026-11-16: PR #50 (contracts) and #51 merged; CI green incl. heavy tests; Gate 2 and security review approved | |
| p1-golden-65s | done 2026-11-16: PRs #53 (contracts) and #54 merged; render.yml uses the shared frame helper; visual QA approved the 65 s frames | Gate 2, security review and visual QA approved |

## Phase 2 module order

Planned 2026-11-16 by the Architect (`.harness/handoffs/architect-p2-plan.md`). Owner decisions D2 to D8 taken with the defaults (PRD.md section 7); D1 decided 2026-11-18 as option (c), repo secret. Stage 0 (D7). Task files: `.harness/tasks/phase2/00_*.yaml` to `16_*.yaml`, run in dependency order. Tasks 14 to 16 (2026-11-18, `.harness/handoffs/p2-hardening-plan.md`) close CSO P2-1 to P2-6; they touch no common file, so they can run in parallel, and they come before the live run of Workflow A and before the remaining phase-end reviews.

```
p2-entry-ci, p2-factcheck-exact            (no owner decision needed; can start at once)
p2-entry-ci -> p2-contracts                (after owner decisions D2 to D6)
p2-contracts -> p2-validate, p2-gemini, p2-seed-sources
p2-validate, p2-gemini -> p2-generate
p2-gemini -> p2-semantic
p2-factcheck-exact, p2-generate, p2-semantic -> p2-batch
p2-batch, p2-seed-sources, p2-entry-ci -> p2-weekly-workflow
p2-weekly-workflow -> p2-cso
p2-validate -> p2-validate-urls; p2-gemini -> p2-gemini-redirects; p2-weekly-workflow -> p2-weekly-hardening
p2-weekly-hardening -> live run of Workflow A   (key is a repo secret; workflow disabled until then)
p2-validate-urls, p2-gemini-redirects, p2-weekly-hardening -> p2-qa-lead, p2-audit
p2-qa-lead, p2-cso, p2-audit -> p2-phase-review
```

Specialist reviews: security for p2-validate, p2-gemini, p2-batch, p2-weekly-workflow and the three hardening tasks (`specialist_reviews` in `.harness/config.yaml`). No visual QA: Phase 2 changes no render code.

### Phase 2 status

| Task | Status | Review |
|---|---|---|
| p2-entry-ci | done, merged 2026-11-16 (PR #60) | Gate 2 approved; non-blocking notes in architecture.md section 7 |
| p2-factcheck-exact | done, merged 2026-11-16 (PR #59) | Gate 2 approved |
| p2-contracts | done, merged 2026-11-16 (PR #62) | Owner approved |
| p2-validate | done, merged 2026-11-16 (PR #64) | Gate 2 and security approved; non-blocking notes in the orchestrator handoff |
| p2-gemini | done, merged 2026-11-16 (PR #63) | Gate 2 and security approved; non-blocking notes in the orchestrator handoff |
| p2-seed-sources | done, merged 2026-11-16 (PR #65) | Gate 2 approved after round 1; owner reviewed the facts |
| p2-generate | done, merged 2026-11-17 (PR #67) | Gate 2 approved after round 1 (nested delimiter fix) |
| p2-semantic | done, merged 2026-11-18 (PR #69) | Gate 2 approved round 1; non-blocking notes in the orchestrator handoff |
| p2-batch | done, merged 2026-11-18 (PR #71) | Gate 2 and security review approved round 1; non-blocking notes in the orchestrator handoff |
| p2-weekly-workflow | done, merged 2026-11-18 (PR #73); manual acceptance waits for p2-weekly-hardening (D1 decided, repo secret added) | Gate 2 and security review approved round 1; non-blocking notes in the orchestrator handoff |
| p2-qa-lead | done | proposed tests await owner decision |
| p2-cso | done, merged 2026-11-18 (PR #75); threat model version 2 | Owner signed off the threat model 2026-11-21 |
| p2-audit | done | report awaits owner approval |
| p2-phase-review | done | Phase 2 code can close; owner gates R13.5 and R13.6 remain |
| p2-validate-urls | done, merged 2026-11-18 (PR #81); closes CSO P2-3 | See the handoff for review rounds |
| p2-gemini-redirects | done, merged 2026-11-18 (PR #83); closes CSO P2-5 | See the handoff |
| p2-weekly-hardening | done, merged 2026-11-18 (PR #82); closes CSO P2-1, P2-2, P2-4, P2-6 | Gate 2 approved; security review round 1 fixed (see handoff). Workflow A stays disabled until the owner's first manual run |
| p2b-prompt-data | done, merged 2026-11-21 (PR #86) | Gate 2 approved; tests in the task YAML |
| p2b-gemini-shapes | done, merged 2026-11-21 (PR #87) | Gate 2 approved; tests in the task YAML |
| p2b-unicode-digits | done, merged 2026-11-21 (PR #88) | Gate 2 approved; tests in the task YAML |
| p2b-hook-check | done, merged 2026-11-21 (PR #89) | Gate 2 approved; tests in the task YAML |
| p2b-qa-tests-batch | done, merged 2026-11-21 (PR #91) | Gate 2 approved; tests in the task YAML |
| p2b-qa-tests-factcheck | done, merged 2026-11-21 (PR #92) | Gate 2 approved; tests in the task YAML |

## Phase 2b module order

Planned 2026-11-21 by the Architect (`.harness/handoffs/p2b-plan.md`): phase review N1 to N5 and the QA lead's ranked tests, before Phase 4. Task files: `.harness/tasks/phase2b/00_*.yaml` to `05_*.yaml`. At most two at once; no two tasks in a wave share a path.

```
wave 1: p2b-prompt-data, p2b-gemini-shapes          (no owner decision needed)
wave 2: p2b-unicode-digits, p2b-hook-check          (after owner decisions O2 and O1)
owner dispatches the CI reports job on main
wave 3: p2b-qa-tests-batch, p2b-qa-tests-factcheck  (scope: owner decision O3)
```

Specialist reviews: security for p2b-gemini-shapes, p2b-unicode-digits and p2b-hook-check.
