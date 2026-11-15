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
