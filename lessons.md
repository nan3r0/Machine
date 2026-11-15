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
