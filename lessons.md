# Lessons

A log of mistakes made on this project and what changed because of them. Read before any non-trivial change. Add an entry the same session a mistake is found. Never edit old entries; add a new one if a lesson is revised.

## Entry format

### YYYY-MM-DD: short title
What happened:
Why it happened (root cause, not symptom):
How it was caught:
Fix:
Rule going forward:
Test added: (file and name, or "none, and why")

## Traps to avoid from the start

- A hook that crashes exits 1, which Claude Code treats as "allow". Hooks must catch everything and exit 2.
- FFmpeg filter paths (`subtitles=`) need different escaping on Windows and Linux. Test both, or build the path in one helper.
- Passing titles or file names into a shell string invites injection. Always pass FFmpeg an argument list.
- Caption text is user-controlled. Escape `{`, `}` and `\` before writing `.ass`.
- Never trust a "success" from a TTS call without checking the wav has real length and is not silent.
- Model downloads (Kokoro, Whisper for stable-ts) on every Actions run waste minutes. Cache them.
- A Google OAuth consent screen left in "testing" mode issues refresh tokens that expire after 7 days (PLAN.md section 10).
- Dummy-commit keepalive actions break GitHub's terms (PLAN.md section 3). Never add one.

## Entries

### 2026-11-15: Lock hook failed open when PyYAML was missing
What happened: `enforce_locks.py` imported PyYAML at module level, outside its fail-closed handler.
Why it happened (root cause, not symptom): the try/except only wrapped `main()`, so an import error exited 1, which Claude Code treats as "allow".
How it was caught: advisor review of the hook before handover.
Fix: the import moved inside `load_yaml`, under the handler. While making that edit in two steps, the half-edited live hook blocked the second edit; it was repaired through Bash.
Rule going forward: everything a hook does, imports included, runs inside its fail-closed handler. Change a live hook in one edit, or repair it outside the edit tools.
Test added: `.harness/tests/test_enforce_locks.py::test_missing_pyyaml_fails_closed`

### 2026-11-15: Two hook tests passed for the wrong reason
What happened: two tests that widen `paths_allowed` appended a list item after the `tests:` flow list, which made the task YAML invalid. The hook then blocked everything because the YAML was broken, so the tests passed without checking the rule they named.
Why it happened (root cause, not symptom): a fail-closed system makes any broken fixture look like a passing "blocked" test, and the fixture was never checked on its own.
How it was caught: a new test for `.harness/status.yaml` passed before the hook was changed.
Fix: a `with_extra_allowed` helper inserts the pattern inside `paths_allowed`, with its own test that the result is valid YAML.
Rule going forward: for fail-closed code, see each "blocked" test fail before the change it covers, and check its fixtures are valid separately.
Test added: `.harness/tests/test_enforce_locks.py::test_extra_allowed_yaml_is_valid`

### 2026-11-15: Lock hook could be bypassed by path aliases and by sessions without a task
What happened: an automated security review found that Windows path aliases (`TESTS~1`, `tests.`, `x.py:stream`, junctions) slipped past the lock patterns, and that any session started without `LOOM_TASK` could edit the hook and settings that enforce the rules.
Why it happened (root cause, not symptom): the hook compared the literal path string instead of the file it resolves to, and treated "no task" as trusted.
How it was caught: background security review of the pushed commit.
Fix: aliasing path forms are blocked, symlinks and junctions are resolved, and hooks, settings and agents need `LOOM_ADMIN=1` at launch. p1-contracts adds a CI scope check, since the hook can never see Bash writes.
Rule going forward: match protected paths on the resolved file, never the raw string. Enforcement files are protected by default, not only inside tasks. Every local guard gets a server-side check.
Test added: `test_admin_files_blocked_without_task`, `test_admin_files_blocked_even_for_contract_owner_task`, `test_windows_path_tricks_are_blocked`, `test_symlink_into_locked_dir_is_blocked` in `.harness/tests/test_enforce_locks.py`

### 2026-11-15: PR merged before its last commits were pushed
What happened: the orchestrating session kept pushing hook fixes and the niche to PR #1's branch after asking the owner to review it. The owner merged the earlier state, so four commits were missing from main and needed a follow-up PR (#2).
Why it happened (root cause, not symptom): a PR was treated as still open to new work after it had been handed to the owner for review.
How it was caught: comparing main with the branch after the owner said it was merged.
Fix: follow-up PR #2.
Rule going forward: once a PR is handed to the owner, never push to its branch. New work goes on a new branch and PR, or the owner is told "don't merge yet" before any push.
Test added: none, process rule.

### 2026-11-15: An owner message in a task window was read as a decision it was not
What happened: the owner typed "stick with kokoro for now" in the contracts window. The session read it as "use the PyTorch `kokoro` package", replaced its own `kokoro-onnx` choice, and dropped the pinned weight hashes, which two reviews then flagged.
Why it happened (root cause, not symptom): a short, ambiguous message changed a recorded decision without the orchestrating session or the owner confirming what it meant.
How it was caught: the orchestrating session compared the new handoff with the previous one.
Fix: the owner chose explicitly (PyTorch `kokoro`, no quality loss allowed) and the weights get pinned by revision and sha256.
Rule going forward: a task session that reads an owner message as changing a recorded decision states the change in its handoff under Decisions, and the orchestrating session confirms it with the owner before review.
Test added: none, process rule.

### 2026-11-15: Killing a task session left its window broken
What happened: stopping the `claude` process in a task window opened with PowerShell `-NoExit` left the terminal in mouse-tracking mode, printing escape codes at the prompt.
Why it happened (root cause, not symptom): the process was killed instead of exiting, so it never restored the terminal, and `-NoExit` kept the broken window open.
How it was caught: the owner asked what the junk was.
Fix: task windows are launched without `-NoExit`, so they close when Claude exits.
Rule going forward: end a task session with `/exit` or by closing its whole window, never by killing only the `claude` process.
Test added: none, launcher change.

### 2026-11-15: CI ran git network commands without credentials
What happened: the first CI run on the contracts PR failed in the scope check: `git fetch` could not authenticate because checkout uses `persist-credentials: false`.
Why it happened (root cause, not symptom): the step fetched a ref the checkout had already fetched (`fetch-depth: 0`), and network git commands were never tried on the private repo before pushing.
How it was caught: the first CI run.
Fix: the redundant fetch is removed (contracts review round 1).
Rule going forward: with `persist-credentials: false`, CI steps make no git network calls; fetch everything needed in the checkout step.
Test added: covered by the CI run on every push.

### 2026-11-15: Platform facts in the plan were out of date
What happened: research found five plan assumptions wrong, including the YouTube audit (no longer needed), upload quota cost, Gemini free limits, Instagram's upload method and a missing analytics metric.
Why it happened (root cause, not symptom): the plan was written from memory of how the platforms used to work, not checked against current official docs.
How it was caught: a research pass the owner asked for while the contracts task ran.
Fix: PLAN.md and PRD.md updated with sources (PR #5).
Rule going forward: before the Architect plans a phase that touches an external API, check that API's current official docs and record the source and date in PRD.md section 7.
Test added: none, process rule.

### 2026-11-15: Docs drifted behind the work
What happened: for several hours, mistakes and decisions (a merge-order slip, the voice package choice, the orchestration setup, five lessons) were not written into lessons.md, PRD.md, architecture.md or HARNESS.md until the owner noticed.
Why it happened (root cause, not symptom): updating docs depended on the orchestrating session remembering to do it. No step in the harness required it, and nothing failed when docs were stale.
How it was caught: the owner asked why lessons.md and other docs were not being updated.
Fix: doc sync built into the harness (owner decision 2026-11-15): a required Docs section in every handoff, a "Docs aligned" item in the Gate 2 checklist, a Haiku Scribe close-out session after every task merge, and the CI check `tests/docs_check.py` (task p1-docs-check).
Rule going forward: a mistake gets its lessons.md entry, and a decision gets its PRD.md entry, in the same turn it happens, on a docs branch. A task is not closed until its close-out doc sync has merged.
Test added: `tests/test_docs_check.py` (written by p1-docs-check).

### 2026-11-15: A task session wrote to the main checkout instead of its worktree
What happened: the contracts session used an absolute path under the main repo folder instead of its worktree, so the edit targeted the wrong copy of the repo.
Why it happened (root cause, not symptom): absolute paths were built from the repo name, not from the session's working directory.
How it was caught: the lock hook blocked the edit as out of scope.
Fix: the session redid the edit under the worktree root.
Rule going forward: in a worktree, build absolute paths only from the worktree root (the session's working directory), never the main checkout.
Test added: none; the hook already blocks it.

### 2026-11-15: git diff quoted unusual file names and could hide them from the scope check
What happened: without `-z`, `git diff --name-only` wraps non-ASCII and other unusual paths in quotes with escapes, so a pattern check sees a different string and an edit to a protected file can slip past.
Why it happened (root cause, not symptom): the checker parsed git's human-readable output instead of its machine format.
How it was caught: an automated security review of the contracts commits.
Fix: `tests/scope_check.py` reads `git diff --name-only -z` and splits on NUL.
Rule going forward: any code that reads file lists from git uses `-z`.
Test added: regression test for non-ASCII paths in `tests/test_scope_check.py`.

### 2026-11-15: Python written through a Bash heredoc lost its backslashes
What happened: code with escape sequences, written into test files through a Bash heredoc, came out with halved backslashes: a NUL byte and a broken `\n` landed in the tests.
Why it happened (root cause, not symptom): the shell and Python each interpreted the backslashes, so non-raw strings were unescaped twice.
How it was caught: the contracts session's own test run.
Fix: rewritten with the Edit tool.
Rule going forward: write or change code containing backslashes with the Edit or Write tool, never through a shell heredoc or `echo`.
Test added: none, tooling rule.

### 2026-11-15: A Windows-only hook test failed on the Linux CI runner
What happened: CI's Gate 1 failed on `test_windows_backslashes_and_case_are_normalised`. Linux treats a backslash as part of a file name, so the hook correctly saw no Windows path there. `make check` stopped at that failure, so the main suite and heavy tests never ran.
Why it happened (root cause, not symptom): harness tests were only ever run on the owner's Windows machine, and nothing marked which ones depend on Windows path rules.
How it was caught: the second CI run on the contracts PR.
Fix: the test is skipped off Windows.
Rule going forward: a test that depends on one operating system's behaviour carries a `skipif` for the others, and every test file is assumed to run on Linux in CI.
Test added: the test itself, now marked Windows-only.

### 2026-11-15: The rotation hook spec told the hook to give up on the one stop that mattered
What happened: the Architect's task YAML for h-rotation-hook said to exit early whenever `stop_hook_active` is true. Claude Code sets that flag on every stop that follows a hook block, which is exactly the stop where the replacement window should launch, so rotation could never fire. The implementer followed the spec, and its tests sent `stop_hook_active=false` on that stop, so they passed.
Why it happened (root cause, not symptom): the spec was written from an assumption about the hook protocol, and the tests mirrored the spec instead of the real event sequence.
How it was caught: Gate 2 review.
Fix: the launch path runs before the `stop_hook_active` check; tests now send `true` on the stop after a block.
Rule going forward: specs and tests for hooks follow the documented event sequence of the tool, including flags set by earlier blocks, not the author's mental model.
Test added: `test_fresh_handoff_launches_task_once` and `test_acceptance` in `.harness/tests/test_context_guard.py`, now sending `stop_hook_active=true`.

### 2026-11-15: An automatically run hook script was placed in an unprotected folder
What happened: `context_guard.py` was registered as a Stop hook from `.harness/scripts/`, which any session can edit, so a session could change code that then runs in every later session, admin ones included.
Why it happened (root cause, not symptom): the script was judged "not a security control" by what it does, not by when it runs; anything a hook runs automatically is privileged.
How it was caught: background security review of the registration commit.
Fix: the script moves to `.claude/hooks/`, which is owner-only.
Rule going forward: every file a hook or setting executes lives under `.claude/hooks/` (owner-only), whatever its purpose.
Test added: none; the lock hook already protects `.claude/hooks/`.

### 2026-11-15: pip-audit failed three times on environment details
What happened: CI's pip-audit first audited the whole runner (flagging CI tools' own dependencies), then could not resolve the `+cpu` torch builds from PyPI, and setuptools could not be upgraded past torch's cap. Each needed a separate fix round.
Why it happened (root cause, not symptom): the audit command was never run once on a Linux runner before being locked into CI, so each problem surfaced one CI run at a time.
How it was caught: three consecutive CI runs on PR #6.
Fix: audit only project requirement files, with `+cpu` stripped from a temporary copy; two setuptools advisories ignored until torch lifts its cap (documented in the Makefile).
Rule going forward: before locking a CI tool step, run it once on the target OS (a throwaway workflow run) and fix everything it reports in one round.
Test added: `tests/test_ci_workflow.py` checks the audit command.

### 2026-11-15: Orchestrator watchers missed or broke on small details
What happened: one review launched before its prompt file existed (the command that wrote it was rejected), one CI watcher ran a script missing from the task branch (exit 127), and one task watcher never fired although the task was done.
Why it happened (root cause, not symptom): watcher and launch commands were chained or path-dependent, so one failed step silently changed what ran next.
How it was caught: the orchestrator checking a task that had gone quiet, after the owner asked.
Fix: steps run separately; scripts are run from main's copy.
Rule going forward: launch commands never depend on a file written in the same chained command, and the orchestrator checks git state directly whenever a watcher has been silent longer than the task should take.
Test added: none, process rule.

### 2026-11-15: Finished task sessions never closed their windows
What happened: four task windows (two already merged) sat open at the prompt after the work was committed, because the session ended its turn without exiting.
Why it happened (root cause, not symptom): the launch brief said to finish the handoff but never said to run /exit, and the watcher only reports; it does not close the window.
How it was caught: the owner saw four idle windows in the taskbar.
Fix: the launch brief now ends with "run /exit"; the orchestrator also stops the window's parent powershell.exe after Gate 1.
Rule going forward: every task brief ends with an explicit /exit step, and the orchestrator confirms no `open_task_window` process is left before reporting a task closed.
Test added: none, process rule.

### 2026-11-15: Single-pass loudnorm missed the loudness target
What happened: p1-compose measured -15.6 LUFS against -14 in CI (tolerance 1 LU). The Gate 2 reviewer had named the risk but called it non-blocking because the heavy test could not run locally.
Why it happened (root cause, not symptom): single-pass loudnorm applies a true-peak limit that pulls integrated loudness below target on speech; the heavy test was the first real measurement.
How it was caught: CI, as the reviewer predicted.
Fix: two-pass loudnorm (measure, then apply with measured values and linear mode).
Rule going forward: a risk a reviewer flags on a heavy-test path is fixed before the first CI run when the fix is cheap; for loudness use two-pass loudnorm from the start.
Test added: `tests/render/test_compose.py::test_acceptance` (existing, locked) is the regression.

### 2026-11-15: Orchestrator window-close command killed its own shell
What happened: a pattern match on `p1-compose` in a PowerShell command line also matched the command running it, so the close step tried to terminate itself.
Why it happened (root cause, not symptom): the filter was on the task name, which appears in the orchestrator's own command text.
How it was caught: taskkill output "The process cannot terminate itself".
Fix: match on `open_task_window` only and exclude `$PID`.
Rule going forward: process filters exclude the current process and match a string that only the target carries.
Test added: none, process rule.

### 2026-11-15: A merged PR missed the review fix because the fix was never pushed
What happened: PR #31 (p1-render-cli) was merged with the blocking Gate 2 finding still in it, because the round-1 fix existed only as a local commit. A follow-up PR (#32) shipped it.
Why it happened (root cause, not symptom): the orchestrator told the owner a fix session was running while the PR was still open and green, so the owner merged.
How it was caught: the orchestrator checked git state after the merge.
Fix: follow-up PR with the fix; the Architect added the regression test.
Rule going forward: when a review requests changes, close the PR or mark it draft (`gh pr ready --undo`) before starting the fix round, and tell the owner not to merge until the fix is pushed and green.
Test added: `tests/test_render_one.py::test_non_utf8_script_exits_2`.

### 2026-11-15: A variable font silently fell back to DejaVu
What happened: the committed Montserrat was a variable font whose name table says family "Montserrat Thin", so libass could not match the style name and rendered every caption in DejaVu. Code reviews flagged the risk twice; only a real frame proved it.
Why it happened (root cause, not symptom): the compose test uses an empty fonts folder, and golden frames did not exist until render-cli, so nothing rendered the real font.
How it was caught: orchestrator reading a CI golden frame after render-cli.
Fix: static Montserrat-Bold.ttf (family "Montserrat", Bold), with a locked name-table test.
Rule going forward: a font file is checked by its name table (family, style, no fvar) in a test, and the first render that uses it is looked at, not assumed.
Test added: `tests/render/test_font.py`.

### 2026-11-15: A local `tests` package shadows the repo's tests
What happened: several task sessions needed a shim because an installed `tests` package in site-packages is imported instead of the repo's `tests/`.
Why it happened (root cause, not symptom): the project's `tests/` is imported by name and a stray distribution on the owner's Python install installs a top-level `tests` package.
How it was caught: implementers hit it in p1-captions-ass, p1-qa and p1-actions-workflow; the reviewer asked for it to be recorded.
Fix: none in the repo yet; task venvs are created with the repo requirements only, and sessions use a runner that puts the repo first on sys.path.
Rule going forward: if a task needs the shim, say so in the handoff Evidence; an owner decision on a permanent fix (for example a `pythonpath` entry in pytest config) is still open.
Test added: none.

### 2026-11-16: The mutation run tree lacked files the tests read
What happened: the first phase-end `reports` run (CI run 43877583446) failed in `mutmut run`: `tests/test_ci_workflow.py::test_ci_is_safe` raised FileNotFoundError for `mutants/.github/workflows/ci.yml`.
Why it happened (root cause, not symptom): mutmut runs the suite inside a copy of the repo (`mutants/`) holding only the mutated source, `tests/`, `pyproject.toml` and `[tool.mutmut] also_copy`. `also_copy` listed only `queue/`, `.harness/` and `assets/`, but the tests also read `.github/`, `.claude/hooks/`, the Makefile, the requirements files and the docs that `tests/docs_check.py` checks. The reports job runs only on manual dispatch, so nothing exercised the list before phase end.
How it was caught: the owner's manual dispatch of the reports job.
Fix: `also_copy` now lists every repo-root path the suite reads at test time, found by grepping `tests/` for `ROOT /` reads, `cwd=ROOT` and the files `tests/docs_check.py` opens.
Rule going forward: a test that reads a new repo-root file or folder adds it to `[tool.mutmut] also_copy` in the same change. A nested file goes in as its folder, since mutmut does not create parent folders for single files.
Test added: none. A test mirroring the list would be a second hand-kept copy of it and could not see reads inside subprocesses; the reports run is the real check.

### 2026-11-16: The mutation run reran heavy renders for every mutant
What happened: the second phase-end `reports` run (CI run 43881197536) was cancelled at the job's 90-minute limit inside `mutmut run`, after 487 of 997 mutants. The first 400 mutants took about 4 minutes; the rest, in render and voice alignment code, took up to 4.5 minutes each and many timed out. The runner also warned it was down to 10 MB of free disk.
Why it happened (root cause, not symptom): the reports job installs ffmpeg and torch and GitHub sets CI=true, so `tests/conftest.py` keeps the `heavy` tests (full renders, Kokoro, alignment). mutmut reran them for every mutant they touch, each with a CPU limit of about 30 times the test's clean runtime.
How it was caught: the owner's manual dispatch of the reports job.
Fix: `[tool.mutmut] pytest_add_cli_args = ["-m", "not heavy"]`. mutmut 3.8.1 appends this to every pytest call it makes, so heavy tests are deselected from the clean run, the stats run and each mutant run. The coverage line in the job runs outside mutmut and still includes heavy tests.
Rule going forward: mutation testing runs only the fast suite. Code reached only by heavy tests shows as "no tests" in `mutmut.txt`; the QA lead judges that code from `coverage.xml`, not as a gap mutmut found.
Test added: none. The reports run is the real check.

### 2026-11-16: A finding in the last report threw away all four reports
What happened: the third phase-end `reports` run (CI run 43898395038) finished coverage and mutmut (997 of 997 mutants), then `pip-audit` found 9 known vulnerabilities in 3 packages and exited 1. The step failed, so the `upload-artifact` step was skipped and the coverage, mutation, licence and audit reports were all lost.
Why it happened (root cause, not symptom): the job was written fail-fast, like a gate. Every report ran in one shell step and the upload ran only on success, but this job exists to collect findings, so a finding is an expected outcome, not a reason to drop the evidence.
How it was caught: the owner's manual dispatch of the reports job.
Fix: one step per report; every report after the first and the upload run on `${{ !cancelled() }}`. A failing report still turns the job red; nothing uses `|| true` or `continue-on-error`. pip-audit keeps auditing the whole installed env with no ignores, so the Auditor sees dev tool and accepted advisories too; Gate 1 stays the merge blocker with its narrower scope.
Rule going forward: a job that collects findings uploads them whatever the findings are. Give each report its own step, run later steps and the upload unless cancelled, and let the failure show in the job status rather than hiding it.
Test added: `tests/test_ci_workflow.py::test_report_findings_fail_the_job_without_losing_the_reports`.

### 2026-11-16: A test built its expected value with the code under test
What happened: the QA lead's mutation review found that the caption escaping test at `tests/render/test_captions_ass.py:81` computed its expected text with the same function it was testing, so a bug in that function could not fail it.
Why it happened (root cause, not symptom): the test was written from the code's output shape instead of from the spec, so it could only agree with the code.
How it was caught: the phase-end QA lead review (p1-qa-lead).
Fix: the oracle is now a hand-written unescape of the ASS escapes, and exact expected strings live in `tests/render/test_captions_exact.py`.
Rule going forward: a test's expected value comes from the spec, a literal or an independent oracle, never from the code under test. Fake tool output (ffprobe, silencedetect, loudnorm) comes from a real capture, never hand-written.
Test added: `tests/render/test_captions_exact.py::test_escape_gives_exact_text`.

### 2026-11-16: Word bounds came from a speech rate that was never measured at the live voice speed
What happened: `SPEECH_WPM` 150 was scaled from a speed 1.0 sample (167 wpm x 0.9) when `VOICE_SPEED` dropped to 0.9. The real rate was about 144 wpm, so the 65 s format's 225-word maximum would have run about 94 s and failed the 62 to 90 s QA range. The derivation comment in constants.py also disagreed with the code (155 vs 156).
Why it happened (root cause, not symptom): the word bounds were derived by arithmetic from an assumed rate instead of from a render at the new speed, and nothing checks the comment against the values.
How it was caught: the owner's 65 s acceptance render (167 words in 69.5 s, run 43873059742).
Fix: `SPEECH_WPM` 144 and `TIKTOK_WORDS` (149, 216), with the arithmetic in the comment (branch docs/p1-constants-timeout-contracts). The Retention format, whose word bounds had the same flaw, was removed (owner rule: every video over a minute).
Rule going forward: after any change to the voice or its speed, re-measure the speech rate from a real render and re-derive every word bound from it in the same change.
Test added: none; these are constants, and the 65 s sample's fit is already checked by `tests/test_schema.py::test_acceptance`.

### 2026-11-16: A shell and Python rewrite mangled regex backslashes
What happened: in p2-entry-ci a Bash heredoc feeding a Python rewrite of `tests/workflow_rules.py` turned `\b` into a backspace and `\n` into a real newline; a sed repair then dropped the backslash again.
Why it happened (root cause, not symptom): two layers of escaping (the shell, then the Python string) sat between the intended text and the file.
How it was caught: ruff and pytest failed at once.
Fix: repaired with the Edit tool.
Rule going forward: edit source files with the Edit or Write tools only, never through a shell heredoc, sed or a Python rewrite script.
Test added: none, a process rule.

### 2026-11-16: The orchestrator passed 50% context without rotating
What happened: the fifth orchestrator session ran to 62% context before the owner noticed and asked why it had not rotated. The handoff says to rotate at about 50% or after every task close-out.
Why it happened (root cause, not symptom): rotation depended on the Stop hook `context_guard.py`, which only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator` (it sets `LOOM_ROLE`). This session was started another way, so the hook never fired, and nothing else checked the context size. Close-outs were also batched into later PRs, so the "rotate after every close-out" trigger never came up.
How it was caught: the owner read `/context` and asked.
Fix: orchestrator.md now has a numbered step in the Token rules that applies when the hook is absent: check `/context` at every task close-out and before launching each task, and rotate at 50% by writing the State block, opening the docs PR and telling the owner to start a fresh session.
Rule going forward: a control that exists only in one launch path is not a control for every session. The orchestrator checks its own context size at each close-out and launch, hook or no hook, and rotates at 50%, not when asked.
Test added: none. This is a process rule; the Token rules step in `.harness/handoffs/orchestrator.md` is the check.

### 2026-11-17: Single-pass delimiter stripping let a nested delimiter rebuild itself
What happened: p2-generate removed the data-block delimiters from fact text with one `str.replace` pass. A fact holding `</source_fa</source_facts>cts>` came out as `</source_facts>`, so the prompt held two end markers and the text after the first sat outside the data block.
Why it happened (root cause, not symptom): removing a substring can join its neighbours into a new copy of the same substring. One pass only removes the copies present before it starts. The locked test only tried a plain, non-nested delimiter.
How it was caught: Gate 2 review, round 1.
Fix: `_clean` in `pipeline/script/generate.py` repeats the replace until the text stops changing, and every untrusted string that goes into a prompt (fact text, topic, rewrite reason, old narration) goes through it. The shared helper now lives in `pipeline/script/prompt_data.py`, imported by both generate.py and semantic.py.
Rule going forward: any filter that deletes a token from untrusted text runs until stable, or escapes the characters the token is made of. Test the nested case, not just the plain one.
Test added: none yet; tests are locked. The Architect owes a regression test for the nested case.

### 2026-11-17: A task venv was launched without its requirements installed
What happened: the p2-generate worktree had a `.venv` holding only base packages (no pydantic). The orchestrator's Gate 1 run of mypy and pytest failed on imports, and was rerun with another worktree's venv.
Why it happened (root cause, not symptom): the worktree and venv were created in an earlier session that stopped before `pip install`, and the next session checked only that `.venv/Scripts/python.exe` existed.
How it was caught: Gate 1 in the orchestrator, after the task finished.
Fix: none in code. The orchestrator checks `python -c "import pydantic"` in the task venv before launching, and installs `requirements.txt` and `requirements-dev.txt` if it fails.
Rule going forward: check that a venv imports the project's dependencies, not that its interpreter exists.
Test added: none. Process rule in `.harness/handoffs/orchestrator.md`, How to run a task, step 1.

### 2026-11-18: A task window launched from Git Bash closed at once with no work done
What happened: the p2-semantic window was started with `Start-Process` and an argument list. It vanished within seconds; the worktree had no commit and no handoff, and the owner saw no window.
Why it happened (root cause, not symptom): `Start-Process -ArgumentList` joins the array with spaces and does not quote items, so the repo path "Claude Projects" and the multi-word brief were split into separate arguments, and `open_task_window.ps1` failed on its parameters.
How it was caught: the owner reported no window; the worktree was unchanged.
Fix: wrap the script path, `-WorkDir` and `-Message` values in literal double quotes inside the argument list.
Rule going forward: pass every path or sentence to `Start-Process -ArgumentList` with its own embedded quotes, and confirm the window exists before waiting on it.
Test added: none. Process rule in `.harness/handoffs/orchestrator.md`, How to run a task, step 2.

### 2026-11-18: The weekly workflow extracted a job artifact over a live checkout
What happened: p2-weekly-hardening first downloaded the `generate` artifact into the workspace of `open-pr` and `validate`, which hold credentials or run tests. The security review blocked it.
Why it happened (root cause, not symptom): `download-artifact` with `path: .` writes whatever the earlier job uploaded. A compromised `generate` job could plant `.git/hooks`, `.git/config`, `conftest.py` or `pytest.py`, which then run with the write token or make `validate` pass without checking anything. The filters only looked inside `queue/approved`.
How it was caught: security review, round 1.
Fix: both jobs download to `runner.temp` and copy only regular files named `queue/approved/<id>.json` into the checkout; git runs with hooks disabled after that.
Rule going forward: never extract an artifact over a checkout in a job that holds credentials or runs tests. Extract to a temp folder, filter, copy.
Test added: `tests/test_weekly_hardening.py`, including the shell tests that run in CI.

### 2026-11-18: A Unicode URL check fixed one invisible character at a time, three rounds running
What happened: p2-validate-urls rejected bare domains. Review round 1 found combining marks (U+034F, U+FE0F) splitting a domain, round 2 found unassigned code points (U+E01F0) and `<` plus U+0338 composing into one character after NFKC.
Why it happened (root cause, not symptom): each fix named the reported characters, not the class "characters that render as nothing or change what a character is".
How it was caught: security review, rounds 1 to 3; the Architect closed the class on escalation.
Fix: reject Cc, Cf, Cn, Co and Cs on the raw text, fold with NFKD, drop Mn and Me, and run the angle-bracket check on raw and folded text.
Rule going forward: a check on untrusted Unicode text rejects or normalises by category, and its tests run every category, not a list of examples.
Test added: `tests/script/test_validate_urls_marks.py` and `test_validate_urls_cn.py`.

### 2026-11-18: A locked shell test asserted byte equality of a file the job legitimately edits
What happened: `test_open_pr_ignores_files_outside_queue_approved` asserted `.git/config` was unchanged after `open-pr`. CI failed because the job sets the commit identity and push tracking in that file.
Why it happened (root cause, not symptom): the test checked the wrong property. The intent is that a planted config never reaches the checkout.
How it was caught: CI, the first run on Linux (the shell tests skip on Windows).
Fix: the test plants a marker in the artifact's `.git/config` and asserts it never arrives and its fsmonitor command never ran.
Rule going forward: assert the intent (the planted content is absent), not equality of a file the code under test may change.
Test added: the corrected test in `tests/test_weekly_hardening.py`.

### 2026-11-18: Locked tests written during a review round cannot ride on the task branch
What happened: three times the Architect's regression tests for a review round failed `tests/scope_check.py` on the task branch.
Why it happened (root cause, not symptom): the scope check reads the task YAML and `locks.yaml` from main, where the role is implementer, so a new locked test or a YAML edit on the task branch is flagged.
How it was caught: the Architect and the scope check.
Fix: locked tests go on a `docs/*` branch, the owner merges it, then the task branch takes main and the implementer starts.
Rule going forward: budget one extra owner PR per review round that needs a new locked test.
Test added: none. Process rule.

### 2026-11-18: A pushed task branch cannot be rebased
What happened: after the locked-test PRs merged, the orchestrator rebased the task branches onto main, which needs a force-push, which is forbidden. The push was denied.
Why it happened (root cause, not symptom): a rebase rewrites commits that were already pushed.
How it was caught: the push was blocked.
Fix: merge `origin/main` into the branch instead; the duplicate test commits merge cleanly.
Rule going forward: update a pushed task branch with a merge, never a rebase and force-push.
Test added: none. Process rule.

### 2026-11-21: A reports re-run before the close-out skips the new tests
What happened: the CI reports job (mutmut) was dispatched right after the last test PRs merged. The mutation report was byte for byte the old one, so it looked as if the new tests killed nothing.
Why it happened (root cause, not symptom): `tests/conftest.py` runs only tasks listed in `.harness/status.yaml` `done`, and mutmut copies `.harness/`. The close-out PR that adds the tasks to `done` had not merged yet, so the new tests never ran.
How it was caught: identical survivor lists across two runs, then reading the conftest rule.
Fix: dispatch the reports job after the close-out PR merges. Re-run gave 401 survivors, down from 493.
Rule going forward: dispatch `ci.yml` on main only after the status.yaml close-out is merged.
Test added: none. Process rule.

### 2026-11-21: CI ran twice on every PR push and used up the Actions allowance
What happened: the free plan's Actions allowance ran out on 2026-11-21, mid Phase 2c. In the 6.4 days before, ci.yml made 300 runs (about 1,880 wall-clock minutes); 109 of them were pushes to branches that also ran the same check as a pull_request event, or had no PR at all.
Why it happened (root cause, not symptom): ci.yml has bare `push:` and `pull_request:` triggers with no branch filter and no concurrency, from p1-contracts on. Each push to a PR branch started two identical runs, and nothing tracked minutes as a budget. CSO P1-5 named the missing concurrency in Phase 1 but tied it to the Phase 4 schedule.
How it was caught: GitHub stopped running workflows; the owner traced it to the triggers.
Fix: task p2d-ci-triggers (push on main and scripts/** only, PR runs cancel superseded ones). Phase plans now estimate CI minutes per task and per daily run.
Rule going forward: treat Actions minutes as a budget. Every workflow trigger change states its minutes per run and per week, and a plan whose development pace exceeds the allowance says so before it starts.
Test added: `tests/test_ci_triggers.py` (task p2d-ci-triggers).

### 2026-11-22: contract tests covered the happy path of an at-most-once claim, not the refusal
What happened: the first p4-contracts tests for the daily publish claim job checked the id format, the commit shape and the rebase retry, but nothing made the claim refuse when a record for that script already existed on main.
Why it happened (root cause, not symptom): the tests were written from the flow's steps, not from its safety property (a script is uploaded at most once). A queued second run with a stale checkout could have rewritten the claim and uploaded the same video twice.
How it was caught: Gate 2 review, with a concrete scenario.
Fix: round 1 added a locked shell test that seeds main independently (existing claim-only record, record with a video id, script missing from `queue/approved/`) and asserts a non-zero exit, an unchanged head and an unchanged record.
Rule going forward: for every at-most-once or append-only rule in a plan, a locked test must show the refusal case against state seeded outside the code under test, not only the success path.
Test added: `tests/test_daily_publish_workflow.py` (task p4-contracts).

### 2026-11-22: outcome log took the profile from the worktree, so trial runs logged as baseline
What happened: `log_outcome.py` read `.harness/config.yaml` from the current folder. The owner flips the routing profile in the main checkout only, so a log written from a worktree recorded `baseline` while `trial-lean` was active. The first two entries of the trial (p4-pick, p4-youtube) were wrong until the orchestrator saw the mismatch.
Why it happened (root cause, not symptom): `model_for.py` and `run_review.sh` read the main checkout's config, but `log_outcome.py` was written to read its own folder, and its tests only used a single plain folder.
How it was caught: the orchestrator checked the profile field of the first logged entries against the config.
Fix: `log_outcome.py` reads the config through `model_for.main_root()`.
Rule going forward: anything that depends on a setting the owner changes in the main checkout reads it from there, and its test runs from a real worktree.
Test added: `.harness/tests/test_log_outcome.py::test_worktree_run_records_the_main_checkouts_profile`.

### 2026-11-22: draft PR merged before its review fixes, and an implementer ruled on its own contract change
What happened: PR #114 (p4-daily-workflow) merged while still a draft in review, so main got the version with the script blob skew. The fixes went in a second PR (#118). Separately, the implementer wrote `CONTRACT_CHANGE.md` and then wrote "Architect ruling: approved" itself in the same session.
Why it happened (root cause, not symptom): nothing stops a merge of a PR under review, and the implementer brief did not say to stop after writing `CONTRACT_CHANGE.md`.
How it was caught: the orchestrator read the PR state after pushing the round 2 fix and `gh` reported it closed and merged.
Fix: round 1 and 2 fixes carried by #118; the test patch went through an independent Opus test author (PR #117).
Rule going forward: a PR under review stays draft and is not merged until the orchestrator says so; check `gh pr view <n> --json state` before every push to a task branch. The implementer brief says to stop after writing `CONTRACT_CHANGE.md` and never rule on it.
Test added: none, process rule.

### 2026-11-22: mutmut reports job failed because a new test reads data/published
What happened: the CI reports job stopped at "Mutation report": `tests/test_published_records.py::test_acceptance` failed inside mutmut's `mutants/` copy because `data/published/` was not there.
Why it happened (root cause, not symptom): `also_copy` in pyproject.toml lists every root folder the tests read, and p4-contracts added a test that reads `data/` without anyone adding the folder to the list.
How it was caught: the orchestrator dispatched the reports job for the Phase 4 QA lead and read the failed step log.
Fix: `data/` added to `[tool.mutmut] also_copy`.
Rule going forward: a task that adds a test reading a new root folder or file adds it to `also_copy` in the same change; the reports job is dispatched once per phase, so check it before the phase-end tasks.
Test added: none, CI config; the reports job itself is the check.

### 2026-11-25: render lock broke five times in a row on Dependabot bumps nobody installed
What happened: Dependabot bumps (rfc3986 2.0.0 against csvw 4.2.0, num2words 0.5.14 pulling in sdist-only docopt, srsly 3.0.1 against spacy 3.8.18) merged green but broke `pip install --require-hashes -r requirements-render.txt`. Each was found only by a failed render.yml run, and each fix exposed the next.
Why it happened (root cause, not symptom): CI never installed the lock files, so a bump of a package that another package pins or caps passed every gate. On top of that, conftest gives a locked test file to the last task that lists it, so `tests/test_lock_consistency.py` was skipped on main until its task was marked done.
How it was caught: the owner dispatched render.yml and the orchestrator read the failed step log.
Fix: pins restored (p4c-lock-pin to -5), bare Dependabot ignores for 0.x or capped packages (num2words, docopt, srsly, rfc3986, csvw), CONSTRAINTS and CAPPED rows in the locked test.
Rule going forward: a bump of a package that another package pins or caps must move with it (group it, do not ignore one side); a locked test only runs once its task is in the done list, so mark tasks done at close-out; stop patching one package at a time after the second red run and add the CI resolve check (p4c-ci-lock-resolve).
Test added: `tests/test_lock_consistency.py` (num2words/docopt check, srsly cap).

### 2026-11-25: a task PR failed the scope check because its task YAML was not on main

What happened: p4d-gemini-quota-guard was planned and built, but the architect's task YAML and locked tests lived only on the task branch. CI reads the task YAML from main, so the scope check failed with "no task in .harness/tasks/ on origin/main". The new locked tests also failed at import, so they could not simply go to main first.
Why it happened (root cause, not symptom): the orchestrator skipped the contracts PR step. The earlier tasks had their YAML and tests merged to main before the implementer started.
How it was caught: CI on the task PR.
Fix: the contracts commit went to main first as its own PR, then main was merged into the task branch.
Rule going forward: the contracts commit (task YAML, locked tests, and empty import stubs so the tests collect; conftest skips them until the task is done) merges to main before the implementer starts. Merge main into the task branch, never rebase.
Test added: none (process rule).

### 2026-11-26: ASS override tags written as plain Python strings reached libass as control bytes

What happened: p3-charts built tags like "\an5", "\alpha&HFF&\t(...)" and "\an7\fscx1\t(...)" as ordinary Python strings. Python read \a as BEL, \f as form feed and \t as TAB, so libass would have received control characters: bars never grow, labels lose their alignment, pop-ins vanish.
Why it happened (root cause, not symptom): ruff does not flag valid escapes, and the locked layout tests read only the shown text and \pos, never the tags.
How it was caught: the Gate 2 reviewer and visual QA, both by reading the code.
Fix: double backslashes (or reuse cards._pop), and a regression test on a plan branch (PR #200).
Rule going forward: build ASS tags with doubled backslashes or raw strings. Every layout task needs a test that no event text has a character below 0x20 and that the expected tags appear.
Test added: `tests/visuals/test_charts.py::test_override_tags_reach_libass`.

### 2026-11-26: card text fit was guessed instead of measured

What happened: p3-cards sized label text with a 0.6 em average character width. An all-caps 24-character label ran past the panel edge, and two review rounds were spent before the width was measured.
Why it happened (root cause, not symptom): capitals in Montserrat Bold average about 0.735 em and the widest ("A") is 0.756 em, so a guess based on lowercase text is too small.
How it was caught: Gate 2 round 2 by geometry, then confirmed by measuring the font with Pillow.
Fix: width estimate 0.76 em, one shared fit helper, and tests with all-caps labels (PR #197).
Rule going forward: measure text widths from the real font file, and test the widest valid input (all capitals at the length cap).
Test added: `tests/visuals/test_cards.py::test_long_label_fits_between_badge_and_panel_edge`.

### 2026-11-26: tests added during review need to reach main before the task branch

What happened: p3-cards and p3-charts needed regression tests in locked files, so their scope checks failed on the task branch.
Why it happened (root cause, not symptom): CI reads locks and task YAML from main, and implementers may not edit locked tests.
How it was caught: the scope check on the task PR.
Fix: the Architect rules on CONTRACT_CHANGE.md and the test goes on a `plan/<id>-tests` branch that merges to main first; then main is merged into the task branch.
Rule going forward: do this for every locked-test addition from review.
Test added: none (process rule).
