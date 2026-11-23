# Handoff: p4b-audit-tests (test_author)

## Goal
Locked tests for the weekly audit workflow (Audit F7, p4b-plan.md "Weekly audit"), and one shared pip-audit command in the Makefile so Gate 1 and the weekly run use the same ignores.

## Status
done

## What changed (and why)
- `Makefile`: the pip-audit line moved into a new `audit` target (listed in `.PHONY`). `check` runs `$(MAKE) audit` in the old place, between gitleaks and actionlint. The three `--ignore-vuln` entries now exist once.
- `tests/test_ci_workflow.py`: a small `makefile_recipes()` parser. The three Makefile tests now read from the right recipe:
  - `check` plus `audit` cover every gate tool.
  - `pip-audit` is not in `check`'s own recipe.
  - `$(MAKE) audit` comes right after gitleaks, and actionlint stays last.
  - The ignores come from `audit`, and the whole file has exactly three.
- New `tests/test_weekly_audit_workflow.py` (owned by p4b-weekly-audit, so it skips until that task is done). It pins:
  - Triggers: exactly schedule, workflow_dispatch and pull_request. The cron runs weekly off the full hour (minute 1 to 59, one weekday). The PR paths are exactly `requirements*.txt`, `Makefile` and the workflow file. No push.
  - Safety: `assert_safe` with the file name, and the file has no allowlist entry. The token is read-only, with no job permissions, no environment, no `secrets` and no `github.token`.
  - Concurrency: the group contains `github.run_id` and `cancel-in-progress` is never true. GitHub cancels a pending run in a shared group (ci.yml comment), and a cancelled run is not red.
  - Exactly one job runs `make audit`. It installs pip-audit at its requirements-dev.txt pin and does not call `pip-audit -r` itself.
  - Exactly one job runs pip-licenses:
    - Install: setuptools first, then torch from the CPU index (`assert_torch_from_cpu_index_first`), then `-r requirements.txt` and pip-licenses at its pin. No requirements-dev and no pip-audit.
    - The pinned `RULE` regex is in its run text.
    - The `pip-licenses` line has no pipe, no `--fail-on` and no `--allow-only`, and `--ignore-packages` names exactly `phonemizer-fork:3.3.2`.
  - Steps: in every job, each step after the first report step has `!cancelled()`. No step has `continue-on-error` or `|| true`.
  - `test_rule_fails_gpl_and_agpl_only` checks the regex against the licenses.md strings and SPDX forms. GPL and AGPL fail; LGPL, `UNKNOWN` (espeakng-loader), MIT and similar pass.

## Decisions made
- **The licence rule is a regex, not pip-licenses `--fail-on`.** `--partial-match` is a case-insensitive substring match, so no token separates `GPL-3.0` from `LGPL-3.0-only`. An exact list breaks on free-text licence fields. The rule is `(?i)\bA?GPL|GNU (Affero )?General Public`, applied by the workflow to every row's `License` field of pip-licenses JSON output. It should print every offender before exiting 1.
- **phonemizer-fork 3.3.2 is an accepted exception.** The last reports artifact's licenses.md (semgrep 1.186.0 run) lists it as "GNU General Public License v3 or later (GPLv3+)". It is runtime, pulled in by `misaki[en]`. Without the exception the rule is red on today's main, and the task requires green. p1-audit accepted runtime GPL ("obligations apply to distribution"). The ignore is pinned to the version, so a bump alerts again. **Needs Architect or owner confirmation:** p1-audit said "re-check if the repo goes public", and the repo is now public. p4b-plan's spec.md :126 rewording ("no GPL files are tracked or distributed") supports keeping it.
- The pip-licenses output goes to a file (`--output-file`), not a pipe. Steps without `shell: bash` run without pipefail.
- The licence job must not install pip-audit or the dev set, so only the runtime set plus pip-licenses is reported. In practice that means two jobs.

## Tried and abandoned
- A scratch test file in `out/` to prove the new tests are satisfiable: the lock hook blocks it (outside paths_allowed). Instead I added a temporary sample workflow and 17 mutation cases to `tests/test_ci_workflow.py`, ran them (all passed: the sample passes, and each mutation fails `test_acceptance`), then removed them. The sample shape is in Next step.

## Known risks
- The regex also flags a dual licence such as "MIT OR GPL-3.0" and phrases like "Lesser GPL". Either would be a red run for the owner to look at, not a silent pass. No such string is in today's licenses.md.
- The tests cannot prove the inline Python applies the rule to every row and exits 1 on any offender; only the regex literal and the step shape are pinned. Gate 2 should read that step, and the Linux PR run is the proof (p4b-weekly-audit).

## Next step
- Architect or owner: confirm the phonemizer-fork exception now that the repo is public.
- p4b-weekly-audit. A shape that passes every test here:
  - job `audit`: checkout (no credentials), `pip install pip-audit==2.10.1`, then `make audit`.
  - job `licences`: checkout, then one install step: setuptools, torch `--no-deps` from the CPU index, then `-r requirements.txt -r requirements-heavy.txt pip-licenses==5.5.5`.
  - `pip-licenses --format=json --ignore-packages phonemizer-fork:3.3.2 --output-file "$RUNNER_TEMP/licenses.json"`.
  - A rule step with `if: ${{ !cancelled() }}` running a Python heredoc with the pinned regex, printing all offenders.
  - Concurrency group `weekly-audit-${{ github.event.pull_request.number || github.run_id }}`.

## Docs
- spec.md licence note (:126): add phonemizer-fork 3.3.2 (GPLv3+, via `misaki[en]`) as the one accepted GPL package, ignored by version in weekly_audit.yml.
- spec.md / architecture.md: the Makefile now has an `audit` target that `check` calls and weekly_audit.yml runs.
- PRD.md :207: the weekly audit is built (after p4b-weekly-audit).
- workflow.md Phase 4 status table: p4b-audit-tests done.
- All for p4b-docs; none are inside this task's paths_allowed.

## Evidence
- `pytest -q --tb=short tests .harness/tests`: 1537 passed, 243 skipped (the new file collects and its 9 tests skip until p4b-weekly-audit is done).
- `pytest tests/test_ci_workflow.py` before the Makefile change: 3 failed (KeyError 'audit'); after: all pass.
- Temporary sample and mutation run (removed): 17 passed. The cases were: a clean sample; cron on the hour; push trigger; missing PR path; cancel-in-progress; a constant group; a missing `!cancelled()`; `|| true`; an extra ignore; an unpinned ignore; a weakened regex; the dev set; an unpinned pip-audit; `--fail-on`; a pipe; an install before setuptools; `continue-on-error`.
- `ruff check .`: all passed. `mypy --strict pipeline/`: no issues.
