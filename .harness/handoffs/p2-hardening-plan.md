# p2-hardening-plan (Architect)

## Goal
Turn the owner-approved CSO findings P2-1 to P2-6 (`.harness/handoffs/p2-cso.md`) into tasks with locked tests, make them run before the live Workflow A run and the remaining phase-end reviews, and record D1 as decided.

## Status
done (planning and contracts). Branch `docs/p2-hardening-tasks`, committed, not pushed, no PR.

## What changed (and why)
- New tasks in `.harness/tasks/phase2/`:
  - `14_validate_urls.yaml`, **p2-validate-urls** (P2-3). Only `pipeline/script/validate.py`. The checks normalise with NFKC and treat U+3002 and U+FF61 as dots, then reject domain-like tokens. Decimals and one-letter abbreviations still pass.
  - `15_gemini_redirects.yaml`, **p2-gemini-redirects** (P2-5). Only `pipeline/script/gemini.py`. It uses an opener whose redirect handler returns None, so any 3xx becomes a GeminiError with no retry.
  - `16_weekly_hardening.yaml`, **p2-weekly-hardening** (P2-1, P2-2, P2-4, P2-6), covering `weekly_scripts.yml`, the new `requirements-generate.txt` and `pyproject.toml` (mutmut `also_copy`):
    - the key job installs only hashed packages;
    - open-pr stages only new id-named scripts and fails on any changed tracked or oddly named file;
    - a read-only, keyless `validate` job runs `tests/test_queue_scripts.py` before open-pr;
    - a workflow-level `concurrency` group.
  - The three tasks share no path, so they can run in parallel.
- `10_qa_lead.yaml`, `12_audit.yaml` and `13_phase_review.yaml` now also depend on the three new tasks.
- New locked tests:
  - `tests/script/test_validate_urls.py`;
  - `tests/script/test_gemini_redirect.py`, which uses two real HTTP servers on 127.0.0.1;
  - `tests/test_weekly_hardening.py`. It covers the hash file and workflow structure, and runs open-pr's `run:` steps under bash in a scratch git repo with a bare remote and a fake `gh`.
- Changed locked tests, all still green on current code:
  - `tests/test_weekly_workflow.py::test_two_jobs_split_secret_from_write` now accepts the optional `validate` job and `needs: [generate, validate]`. Without this, p2-weekly-hardening could not pass a done task's test it may not edit.
  - `tests/script/test_gemini.py` `install()` and the `FakeUrlopen` docstring in `tests/script/gemini_fakes.py` now patch `urllib.request.OpenerDirector.open` instead of `urllib.request.urlopen`. The fake then catches both urlopen and the opener P2-5 needs; without this the existing tests would call the real endpoint once gemini.py builds its own opener. All 38 tests pass on the current code.
- D1 recorded as decided (option (c), repo secret, added by the owner 2026-11-18) in:
  - PRD.md section 7, which now has the decision and the P2 approval entry; the D1 open question is removed from section 8;
  - spec.md section 5;
  - architecture.md section 7;
  - the CLAUDE.md Status;
  - `architect-p2-plan.md` D1;
  - docs/threat-model.md, only the lines that said open or not yet added.
- Also recorded with D1: the P2-1 condition (no run of Workflow A until p2-weekly-hardening merges).
- spec.md section 4 (P2-6): the caps count logical calls, a run makes up to 28 HTTP requests per model, and runs never overlap. PRD.md section 8 adds that each model's daily limit must cover 28.
- PRD.md R13.7 is new. workflow.md:
  - the module order and the status rows are updated;
  - the criterion map has an R13.7 row;
  - security review is listed for the new tasks.

## Decisions made
- New tests go in new files, not in `test_weekly_workflow.py`, `test_pins.py`, `test_validate.py` or `test_gemini.py`, which differs from the brief.
  - Those files belong to done tasks or to no task, so they always run. Failing tests there would turn main red.
  - Listing them under a new task would instead skip the existing security tests until it is done (`tests/conftest.py`).
- Three tasks, not six. P2-1, P2-2, P2-4 and P2-6 all edit `weekly_scripts.yml`, so they are one task.
- The P2-6 spec.md wording is written here as contract text, not left to an implementer.
- The optional "fail early if `scripts/<day>` exists" (P2-6) is skipped. The concurrency group and the failing push already stop a second PR.
- p2-weekly-hardening writes `requirements-generate.txt`. This departs from the 2026-11-15 assumption that the contracts task owns all pins. The file is mechanical output, and the locked test pins it: every line hashed, direct pins equal to requirements.txt, and the named transitive packages present.
- The validate job installs pytest in a second, unhashed pip call. That job holds no secret and no write token; the worst case is a false pass, and CI on the owner's edits still runs.
- P2-2 bad names: the task notes say fail on any other untracked file in `queue/approved/`. The test only demands that such a file is never pushed.
- `.harness/locks.yaml` is unchanged, because `tests/**` already covers every new file.

## Tried and abandoned
- A fake 302 through the patched opener. It would raise GeminiError on today's code too, so it proves nothing. Replaced by real loopback servers.
- Grepping open-pr's `run:` for `git diff --quiet`. It can be passed by pasting the string. Replaced by running the steps in a scratch repo.

## Known risks
- **Blocking, owner action:** the key is a repo secret now, and `weekly_scripts.yml` on main runs on its cron at **Sunday 2026-11-22 06:00 UTC**, with the unhashed install. Unless p2-weekly-hardening merges before then, the owner runs `gh workflow disable weekly-scripts` now and re-enables it after the merge.
- The open-pr shell tests skip on Windows: Python's `bash` resolves to WSL, and Git Bash needs the PATH of the CI runner. The p2-weekly-hardening implementer hands off as partial, awaiting CI, until CI is green.
- The tests were checked against today's workflow with Git Bash, through a throwaway driver. The good case passes. Edit, delete and a bad name fail, as they should until the task lands.
- Dependabot bumps `requirements.txt` but may not regenerate the hashes in `requirements-generate.txt`. The pin test then fails, which forces a regeneration.
- p2-weekly-hardening edits `pyproject.toml`, and so does `fix/mutmut-copy-sources`. Merge that branch first, or rebase.
- R13.4 says to record D1 before the key is added. The owner added it the same day, before this record.

## Next step
- Owner: disable weekly-scripts now, or before Sunday 06:00 UTC.
- Owner: review and merge this branch.
- Orchestrator: launch p2-validate-urls and p2-gemini-redirects in parallel (2 implementers max), then p2-weekly-hardening.
- After p2-weekly-hardening merges, the owner re-enables the workflow and dispatches it. That run is p2-weekly-workflow's manual acceptance (R13.5).

## Docs
- Applied here:
  - PRD.md: R13.7, D1, the P2 approval entry, and section 8;
  - spec.md sections 4 and 5;
  - architecture.md sections 6 and 7;
  - CLAUDE.md Status;
  - workflow.md;
  - architect-p2-plan.md D1;
  - docs/threat-model.md, three D1 lines.
- Left for close-out of the tasks, as listed in `16_weekly_hardening.yaml`:
  - architecture.md section 4 (three jobs, hashed install);
  - spec.md section 7 (`requirements-generate.txt`);
  - the threat-model P-rows (CSO at phase end).
- The p2-cso close-out (status.yaml, its workflow.md row) is the orchestrator's.
- lessons.md: none.

## Evidence
- `ruff check .`: all checks passed.
- `mypy --strict pipeline/`: no issues in 21 files.
- `python tests/docs_check.py`: passed.
- `pytest -q --tb=short`: 724 passed, 184 skipped. The new task files are skipped; the edited `test_weekly_workflow.py` and `test_gemini.py` pass on current code.
- `pytest .harness/tests`: 69 passed.
- With `LOOM_TASK` set, each new acceptance test fails on its own assertion:
  - p2-validate-urls: 85 failed and 63 passed. Every ordinary-text case passes; every bare domain and look-alike fails.
  - p2-gemini-redirects: 4 failed and 3 passed. 301, 302 and 303 are followed today. 307 and 308 on a POST, and the direct control, pass.
  - p2-weekly-hardening: 5 failed (missing file, unhashed install, two jobs, no concurrency) and 10 skipped (the shell tests on Windows).
- `TRANSITIVE` was checked against a real `pip download` of requirements.txt (manylinux_2_28, 2_17 and 2014 x86_64, Python 3.12). The download gave exactly 10 wheels: the 4 direct packages plus pydantic-core, annotated-types, typing-extensions, typing-inspection, cffi and pycparser.
- `--platform manylinux2014_x86_64` alone finds no numpy 2.4.6 wheel, so the task YAML lists all three tags.
- The generate install test now checks every line that holds `pip install`. That way a second, bare install can't slip in beside the hashed one.
- The scratch repo copies the real `.gitignore`. p2-weekly-hardening therefore also adds `.gitignore` to mutmut `also_copy`.
- Venv used: `../p2-weekly-workflow/.venv`.
