# Handoff: p4c-lock-pin-2-contracts (test_author)

## Goal
Locked test and task YAML for the second lock break. Dependabot merged three bumps that leave pins pip cannot resolve (Requires-Dist in each wheel's METADATA):
- #151 pydantic 2.14.4 into requirements.txt and both hashed locks. It needs exactly pydantic-core 2.50.5, but both locks pin 2.50.4 because p4c-lock-pin's `ignore: pydantic-core` blocked the matching bump. `pip install --require-hashes -r requirements-generate.txt` fails with ResolutionImpossible (weekly-scripts run 45253643834).
- #150 thinc 8.3.14 to 10.0.0 in requirements-render.txt. spacy 3.8.18 needs thinc>=8.3.12,<8.4.0.
- #152 curated-transformers 0.1.1 to 2.0.1 in requirements-render.txt. spacy-curated-transformers 0.3.1 needs curated-transformers>=0.1.0,<0.2.0.

## Status
done

## What changed (and why)
- `tests/test_lock_consistency.py` (locked, edited as test author):
  - Kept: the hashed-lock discovery, the cross-file one-version check and its tmp_path guard.
  - New `CONSTRAINTS` table of (package, version, dependency, specifier) rows, each citing the wheel METADATA it comes from: pydantic 2.14.3 and 2.14.4 to their exact pydantic-core, spacy 3.8.18 to thinc, spacy-curated-transformers 0.3.1 to curated-transformers. `constraint_problems` checks every hashed lock offline with `packaging.specifiers.SpecifierSet`. If a lock pins a listed package at a version with no row, it fails with "add one from that wheel's METADATA Requires-Dist", so a future bump cannot pass unchecked.
  - A tmp_path guard covers a good lock, a stale core pin, a thinc pin outside the cap, a missing dependency pin, an unknown pydantic version and an unrelated lock.
  - Guards against vacuous passes: both locks still pin pydantic and pydantic-core; the render lock still pins spacy, spacy-curated-transformers, thinc and curated-transformers.
  - Dependabot: the "ignores pydantic-core" check is replaced. Now no pip entry may ignore pydantic-core, and each needs a group whose patterns include both pydantic and pydantic-core. Each pip entry must also ignore semver-major updates of thinc and curated-transformers (an ignore with no `update-types` also counts).
  - `test_acceptance` runs the seven contract checks.
- New `.harness/tasks/phase4c/01_lock_pin_2.yaml` (p4c-lock-pin-2, implementer). paths_allowed: requirements-generate.txt, requirements-render.txt and .github/dependabot.yml. Its notes name the exact commits to copy hash blocks from: `ba7bbd0` for pydantic-core 2.50.5 (140 lines), `9aca65d^` for thinc 8.3.14 and `e2f92bb^` for curated-transformers 0.1.1.
- Locks: `tests/**` in `.harness/locks.yaml` already covers the test. No change.

## Decisions made
- One `CONSTRAINTS` table replaces a pydantic-only map. Rows are keyed by the requiring package's version, so bumping spacy or pydantic forces a fresh row read from METADATA.
- `packaging` is not in any requirements file CI installs directly. It comes in through pytest (and is pinned in requirements-render.txt), so it is always present where tests run. No new dependency.
- Conftest ownership: `tests/conftest.py` maps a test file to the last task YAML listing it. `01_lock_pin_2.yaml` sorts after `00_lock_pin.yaml`, so the file now belongs to p4c-lock-pin-2. That does not break the p4b-plan.md "Contract change rule": p4c-lock-pin was never marked done, so the file already skipped on main and keeps skipping until p4c-lock-pin-2 is done. A new file was not needed for that reason, and the old Dependabot check had to change anyway.
- `depends_on: []`. p4c-lock-pin is superseded and should be marked done together with p4c-lock-pin-2.
- semver-major ignores for thinc and curated-transformers, as the coordinator asked. See Known risks.

## Tried and abandoned
- Running the simulation through a Bash heredoc and a `python -c` with quoted arguments. The worktree guard refused the first, and PowerShell 5.1 stripped the quotes from the second. Piping a here-string into `python -` worked.

## Known risks
- The semver-major ignore does not stop minor bumps that still break the caps: thinc 8.4.x, and curated-transformers 0.2.x (a 0.x minor). Dependabot would open such a PR. The CONSTRAINTS check would make it red in Gate 1 once p4c-lock-pin-2 is done and the file stops skipping, but only if the PR is not merged with failing checks. A plain ignore (all update types) would be stricter. That is an owner or orchestrator choice.
- CONSTRAINTS only covers known pairs. transformers 5.23.0 (#153) and ruff 0.17.6 (#154) were merged too and are not checked here. Any other transitive cap in the render lock is unchecked as well. A render.yml dispatch on main is the real proof.
- The test does not prove that the whole set resolves. That still needs the Linux installs listed in the task notes.
- Local runs on the owner's Python need the `tests` shim (lessons.md 2026-11-15).

## Next step
Merge this docs branch, then run p4c-lock-pin-2 (implementer). After it is pushed, the owner dispatches weekly-scripts and render.yml. When both install, mark p4c-lock-pin and p4c-lock-pin-2 done.

## Docs
- lessons.md (orchestrator at close-out): Dependabot bumps one package at a time. When another pin requires an exact or capped version of it (pydantic to pydantic-core, spacy to thinc and curated-transformers), the lock becomes unresolvable. CI never installs these locks, so nothing goes red. Packages that must move together belong in a Dependabot group, never in an ignore, and the locked CONSTRAINTS table needs a row for each new version. The p4c-lock-pin entry owed earlier should be folded into this one, since its ignore rule was wrong.
- CLAUDE.md Status and workflow.md status: add p4c-lock-pin-2 at close-out.
- No other doc changes.

## Evidence
- `LOOM_TASK=p4c-lock-pin-2` on today's main (via the `tests` shim): 4 failed, 6 passed. Failures: `test_pins_satisfy_the_known_requirements` (pydantic-core 2.50.4 in both locks, thinc 10.0.0, curated-transformers 2.0.1), both Dependabot checks and `test_acceptance`. With only the pydantic fix simulated, the CONSTRAINTS check and the new Dependabot capped-pins check still failed.
- Full fix simulated (pydantic-core 2.50.5 copied from ba7bbd0 into both locks, thinc and curated-transformers blocks copied from 9aca65d^ and e2f92bb^, the Dependabot group and ignores): test_lock_consistency, test_render_lock and test_weekly_hardening gave 25 passed, 16 skipped. Reverted with `git restore`.
- Without LOOM_TASK (with the `tests` shim): full suite 1601 passed, 102 skipped (test_lock_consistency now has 10 tests, all skipping on main). `pytest .harness/tests`: 90 passed. `ruff check .`: clean. `python tests/docs_check.py`: passed.
