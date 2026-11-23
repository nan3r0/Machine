# Handoff: p4c-lock-pin-contracts (test_author)

## Goal
Locked test and task YAML for the pydantic-core lock bug. Dependabot bumped pydantic-core alone in requirements-generate.txt (commit ba7bbd0) to 2.50.5, but pydantic 2.14.3 needs exactly 2.50.4, so the hashed install fails with ResolutionImpossible (weekly-scripts run 45232745791, "Install light requirements"; the daily_publish upload job uses the same file).

## Status
done

## What changed (and why)
- New `tests/test_lock_consistency.py`, owned by p4c-lock-pin, so it skips on main until that task is done:
  - Every root `requirements*.txt` holding `--hash=` is a hashed lock (today requirements-generate.txt, requirements-render.txt, requirements-render-torch.txt). A package pinned in more than one of them must have one version in all. Names are normalised (`Pydantic_Core` equals `pydantic-core`).
  - Guards against a vacuous pass: generate and render are both found as hashed locks, and both still pin pydantic-core.
  - `test_the_check_flags_a_package_bumped_in_one_lock_only` runs the check on a `tmp_path` pair split on pydantic-core, plus an unhashed file that must be left out.
  - `.github/dependabot.yml`: every pip update entry ignores pydantic-core.
  - `test_acceptance` runs the four contract checks.
- New `.harness/tasks/phase4c/00_lock_pin.yaml` (p4c-lock-pin, implementer): paths_allowed requirements-generate.txt and .github/dependabot.yml. The notes say to copy the 2.50.4 hash lines from requirements-render.txt, not invent them.
- Locks: `tests/**` in `.harness/locks.yaml` already covers the new test file. No change.

## Decisions made
- Cross-file equality only. Which pydantic-core a pydantic release needs lives in its wheel METADATA, which an offline test cannot read. Equality with requirements-render.txt (which installs fine on Linux) catches the failure we hit, and any later one-sided bump of a shared package.
- The lock parser is reused from `tests/test_render_lock.py` (`requirements`, `normalise`). It accepts the en_core_web_sm direct URL line; `test_weekly_hardening.pins` would cut it at `#`.
- New test file, not an edit to `test_weekly_hardening.py` or `test_render_lock.py`, per the conftest ownership rule (p4b-plan.md "Contract change rule"): an existing file listed under a new task would skip on main.
- The Dependabot ignore has no `update-types`, so it drops all pydantic-core bumps. pydantic decides its version, and a pydantic bump means regenerating the locks anyway.

## Tried and abandoned
none

## Known risks
- The test does not prove that the pinned set resolves. A pydantic bump that pins a new pydantic-core in both locks at the same wrong version would pass here and fail on install. Linux install proof stays in the implementer's notes.
- Dependabot can still bump pydantic in requirements.txt without touching the locks. test_weekly_hardening and test_render_lock catch the drift between requirements.txt and the locks, so that PR goes red.
- Local runs on the owner's Python need the `tests` shim (lessons.md 2026-11-15).

## Next step
Merge on this docs branch, then run p4c-lock-pin (implementer). The orchestrator owes a lessons.md entry: a Dependabot bump of one package in a hashed lock can split pins that must move together; locks must agree, and pydantic-core is ignored.

## Docs
- lessons.md: entry above, by the orchestrator at close-out.
- CLAUDE.md Status and workflow.md status: add Phase 4c (p4c-lock-pin) at close-out.
- No other doc changes.

## Evidence
- Without LOOM_TASK: `tests/test_lock_consistency.py` 6 skipped.
- `LOOM_TASK=p4c-lock-pin` on today's main: 3 failed (shared versions, dependabot ignore, acceptance), 3 passed. Failure text: `{'pydantic-core': {'requirements-generate.txt': '2.50.5', 'requirements-render.txt': '2.50.4'}}`.
- Simulated fix (pydantic-core 2.50.4 with render's hash lines in generate, ignore entry in dependabot.yml): 6 passed. Reverted; the implementer makes the change.
- Full suite without LOOM_TASK (with the `tests` shim): 1601 passed, 98 skipped. `pytest .harness/tests`: 90 passed. `ruff check .`: clean. `python tests/docs_check.py`: passed.
- Mutation tree: `[tool.mutmut] also_copy` already lists `.github/` and every requirements file, so the test runs there unchanged.
