# Handoff: p4b-youtube-survivors (test_author)

## Goal
Locked tests for the YouTube client's mutation survivors, QA lead ranks 1, 2 and 4 to 9 from `.harness/handoffs/p4-qa-lead.md` "Next step". Tests only.

## Status
done. One new file, `tests/publish/test_youtube_survivors.py`, 87 tests, all pass on current code. No test failed on current code, so no bug to report. No shell tests in this task. The file is locked by the `tests/**` glob in `.harness/locks.yaml`.

## What changed (and why)
- New `tests/publish/test_youtube_survivors.py`, same fixtures and fakes as `test_youtube.py`:
  - Rank 1: the PUT error echoes the session URL, the upload_id, the upload_id inside a query, and the URL-encoded and JSON-escaped session URL; none survives, `[redacted]` is present, `sent is True`. A session URL without `upload_id` uploads (PUT goes to it) and is still redacted on failure.
  - Rank 2: a client secret with a backslash, a quote and a slash, echoed raw, URL-encoded and JSON-escaped (forms written as literals) at each of the three steps; the token endpoint echoing the real form body it was sent; a hypothesis property (200 examples) over the secret, the filler length before it (0 to 260, so the 200-character cut lands everywhere) and the form.
  - Rank 4: `Path.read_bytes` raising PermissionError after a good stat gives `sent is False`, two requests, the type named and no file path.
  - Rank 5: BadStatusLine at each step (PUT gives `sent=True`), IncompleteRead after the PUT, an error body whose read raises (OSError and IncompleteRead) at each step, a non-UTF-8 error body with a secret inside, a JSON answer nested 100,000 deep at the token and PUT steps.
  - Rank 6: `"<step> failed: HTTP <code>"` for the three steps and three codes, the 200-character excerpt (and a short body kept whole), the invalid_grant hint only with invalid_grant at every step, `"<step> failed: <Type>"` exactly for URLError and OSError forms, exact log records for a good upload and for a failed init.
  - Rank 7: PUT redirect for 301, 302, 303, 307, 308 through the real `OpenerDirector.open` to a local server; `sent is True`, one hit on the redirecting server, none on the target.
  - Rank 8: `youtube.main()` with no argv reads `sys.argv` and writes exactly one line for success, token failure and PUT failure.
  - Rank 9: session URL edges refused (`https://[www.googleapis.com/x`, port 80, empty port, `HTTP://`) and allowed (`:443`, uppercase host); 12-character, newline-carrying and empty video ids give `sent=True`; ids of each allowed character class pass; unicode title, description and tags reach the init body unchanged.

## Decisions made
- Rank 7: the task note says to patch the upload host constant, but the host check also requires `https`, so a local plain-HTTP server can never pass it, and an HTTPS server with a self-signed cert would fail on verification and pass for the wrong reason. Instead the token and init answers stay faked, the Location is the real `SESSION`, and the PUT (asserted to target `SESSION`) is re-pointed at the local server before calling the real `OpenerDirector.open`. No constant or code is patched; the client's own `_OPENER` and redirect handler run.
- The step names "token refresh", "upload init", "video upload" and the log record texts are pinned as the QA lead listed them; the contract does not spell them out.
- Uppercase host and `:443` are treated as allowed (host names are case-insensitive; the contract allows port 443).
- The property uses printable ASCII without space for secrets and a space filler, so a correct message can never hold 12 secret characters in a row (`[redacted]` is 10).

## Tried and abandoned
- Running read-failure mid-acceptance with `monkeypatch.undo()` to restore `Path.read_bytes`: undo also drops the env fixture. Moved that call to the end of `test_acceptance` instead.

## Known risks
- Rank 7 has limited mutant-killing power: Python's default `HTTPRedirectHandler` does not follow a redirect of a PUT for any of the five codes either, so a regression to plain `urlopen` would still pass this test. It still guards against a handler that follows every method. The token and init redirect tests in `test_youtube.py` remain the real guard.
- Contract gap, for the owner or Architect, not a test failure: the token request body is built with `urllib.parse.urlencode`, which uses `quote_plus` (space becomes `+`), while `_http_message` redacts `quote(secret, safe="")` (space becomes `%20`). A secret containing a space and echoed back in form encoding would not be redacted. Google client secrets and refresh tokens hold no spaces, so the property excludes space; no test locks this either way.
- The hypothesis property runs 200 examples with no fixed seed; it took under a few seconds locally.

## Next step
Gate 2 review, then merge. Ranks 3 (upload job shell guards) and 10 (pick messages) are outside this task.

## Docs
- `workflow.md` line 96, the R15.1 to R15.4 row of the criterion-to-test map: append "tests/publish/test_youtube_survivors.py (redaction forms, crash paths, pinned messages and logs, PUT redirect, CLI argv, host and id edges)". Outside this task's `paths_allowed`; apply at close-out.

## Evidence
- `.venv/Scripts/python.exe -m pytest -q --tb=short tests/publish/test_youtube_survivors.py`: 87 passed.
- `.venv/Scripts/python.exe -m pytest -q --tb=short tests/publish/`: 223 passed, 24 skipped (Windows shell skips).
- `.venv/Scripts/python.exe -m ruff check .`: all checks passed.
- `.venv/Scripts/python.exe -m mypy --strict pipeline/`: no issues in 25 source files.
- No local mutmut run exists, so mutant ids were not confirmed; tests target behaviour.
