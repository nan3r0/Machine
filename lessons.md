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
