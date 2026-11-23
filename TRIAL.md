# Routing trial: trial-lean

**Status: closed 2026-11-23. The active profile is `baseline`.**

## Result

- Almost every Phase 4 task touched a security path (`pipeline/publish/**`, `.github/workflows/**`), so the safety rules kept Gate 2 on Opus. No review ran on Sonnet and no shadow check was produced (`compare_profiles.py`: 0 reviews by model, 0 shadow checks). The trial saved almost nothing.
- Implementation outcomes: baseline 23 tasks, 87% first-pass, 1.09 attempts per task; trial-lean 3 tasks, 67%, 1.67 attempts. Three tasks are too few to read anything from.
- The real usage savings come from fewer repeated reviews and proportionate phase-end reviews, not from the review model (HARNESS.md sections 6a and 6b).
- The profile code (`profile:` in config.yaml, `.harness/model_for.py`, `compare_profiles.py`, the shadow re-run in `run_review.sh`) stays, as the mechanism for any future routing change. A new trial would have to pick tasks that stay off the security paths.

## Original description

A reversible test of cheaper review routing. The current routing is kept as the `baseline` profile and is
untouched; the trial is a second profile in `.harness/config.yaml`. Owner-only: config.yaml is a harness
file, so only a `LOOM_ADMIN=1` session or the owner can switch profiles.

## What changes in trial-lean

| Role | Baseline | trial-lean |
|---|---|---|
| Gate 2 reviewer, ordinary implementation tasks | Opus | **Sonnet** |
| Visual QA (rendered frames) | Opus | **Sonnet** |
| Everything else (architect, test author, escalation, security reviewer, CSO, auditor, QA lead, retrospective, implementer, scribe, orchestrator) | unchanged | unchanged |

Safety rules built into `.harness/model_for.py` (tested in `.harness/tests/test_model_for.py`):
- Gate 2 stays on **Opus** when the task is a tests/contracts task (`test_author` or `architect` role), when its
  diff touches any `specialist_reviews.security` path, or when no saved diff is found.
- If the profile lookup fails for any reason, `run_review.sh` runs the review on Opus, as before.
- **Shadow checks:** about 1 in 3 downgraded reviews is also run on Opus and saved as `<name>-shadow.json`.

## Orchestrator rule during the trial

If a `<review>-shadow.json` exists next to a review, act on the blocking findings of **both**. A task merges
only when neither has a blocking finding. So the trial cannot let a bug through that the Opus review
would have stopped, on the tasks it samples.

## Start, check, roll back

1. **Install:** commit these files to main yourself (one commit, so `git revert` undoes it). New worktrees pick
   up the new `run_review.sh`. Do it between tasks, not while a review is running.
2. **Start:** set `profile: trial-lean` at the top of `.harness/config.yaml` in the main checkout. Every
   worktree reads the profile from there, so one line switches everything.
3. **Check** after 8 to 10 tasks (or any time): `python .harness/compare_profiles.py`. Compare against the
   baseline numbers it prints:
   - first-pass rate and attempts per task (baseline at install: 87%, 1.09)
   - changes-requested rate per review model (baseline Opus: 14%)
   - shadow checks: how often Opus found blocking issues the Sonnet review missed
   - weekly usage % on claude.ai, Settings, Usage, against the week before
4. **Roll back:** set `profile: baseline`. That is the whole rollback: no files to restore, and logs and
   reviews from the trial stay for comparison. To remove the trial code too: `git revert <commit>`.

## When to keep or drop it

- Keep it if shadow checks show no (or only trivial) missed blocking issues and first-pass rate holds.
- Drop it if Opus shadow reviews catch real blocking issues that Sonnet missed more than once, or if
  attempts per task rise (rework eats the savings).
- Partial: if only one kind of task goes wrong (for example render tasks), add its paths to the keep-Opus
  rule instead of dropping the whole trial.
