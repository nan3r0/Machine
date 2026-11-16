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
| R6.2 | `tests/test_render_one.py::test_acceptance` (heavy golden render; writes `out/frames/golden-*.png`) |
| R6.3 | `tests/test_render_one.py::test_qa_failure_exits_non_zero_and_names_checks` |
| R7.1 | `tests/test_workflows.py` plus a manual run |
| R7.2 | Manual, owner, on the 65 s sample |
| R7.3 | CI run on push; structure in `tests/test_ci_workflow.py` |
| R7.4 | `tests/test_conftest_selection.py` |
| R7.5 | CI `make check`; scope check in `tests/test_scope_check.py` |
| R7.6 | Handoffs of p1-qa-lead, p1-cso, p1-audit; owner approves |

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
| p1-sample-65s | not started | |
| QA lead, CSO, Auditor, phase review | not started | |
