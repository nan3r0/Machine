# p4b-weekly-audit

## Goal
Audit F7: a weekly workflow that runs the shared `make audit` and a GPL/AGPL licence rule over the runtime set. A red run is the alert.

## Status
done, except the Linux proof: the PR's own run of `weekly_audit.yml` (pull_request on the workflow path) must be green before review (lessons.md 2026-11-15). Not run locally; `make audit` and `pip-licenses` were not executed here.

## What changed (and why)
- New `.github/workflows/weekly_audit.yml`, the only file touched.
- Triggers: weekly cron `23 5 * * 1` (off the hour), `workflow_dispatch`, and `pull_request` on `requirements*.txt`, `Makefile` and the workflow file. No push.
- Read-only token, no secret, no environment. Own concurrency group per run id, no cancel, so a run is never cancelled instead of red.
- Job `vulnerabilities`: installs the pinned `pip-audit==2.10.1`, runs `make audit` (ignores live in the Makefile).
- Job `licences`: setuptools first, torch from the CPU index with `--no-deps`, then `requirements.txt` and `requirements-heavy.txt`, then `pip-licenses==5.5.5`. No dev tools, no pip-audit.
- Licence report writes JSON with `--ignore-packages phonemizer-fork:3.3.2`; a following step (`if: !cancelled()`) applies the regex `(?i)\bA?GPL|GNU (Affero )?General Public` to every License field and exits 1 on a match. pip-licenses' own `--fail-on` is not used because it matches substrings, so GPL would also hit LGPL.
- The two jobs have no `needs`, so a red audit does not skip the licence check.

## Decisions made
- JSON output plus a small inline Python step instead of a pipe or `--fail-on`: the locked test forbids a pipe in the report line and both fail-on flags.
- Vulnerability job installs only pip-audit; `make audit` reads requirement files and needs no runtime install.
- The heavy set is installed from `requirements-heavy.txt` as ci.yml does (the test accepts it or the render lock).

## Tried and abandoned
none

## Known risks
- `--ignore-packages name:version` needs pip-licenses 5.5.5 to accept that form; the PR run is the proof.
- pip-licenses installs its own dependencies (prettytable, wcwidth) into the audited env; their licences count. Expected permissive.
- If a new GPL package enters the runtime set the run goes red by design.

## Next step
Open a draft PR so the workflow's own run proves it on Linux. Then the security specialist review (`.github/workflows/**` trigger) and Gate 2. Owner setup for failure emails is in the runbook task.

## Docs
- `docs/runbook.md` (p4b-runbook): mention the weekly audit, that a red run means a new advisory or a GPL/AGPL licence, and that the accepted ignores are in the Makefile and `phonemizer-fork:3.3.2` in the workflow.
- `workflow.md` / status: mark p4b-weekly-audit done at close-out.
- No other doc is made false by this change.

## Evidence
- `pytest -q --tb=short tests/test_weekly_audit_workflow.py`: 10 passed.
- `ruff check .`: all checks passed.
- `mypy --strict pipeline/`: no issues in 25 files.
