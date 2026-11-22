# Handoff: p4-qa-lead

## Goal
Phase 4 test quality review (HARNESS.md 6b) of `pipeline/publish/` (`pick.py`, `youtube.py`), `tests/publish/` and `tests/test_daily_publish_workflow.py`, from the CI reports run 45037285671. Focus: the sent flag, claim rules in pick, host and redirect refusals, token redaction.

## Status
done (read-only). The owner decides whether the proposed tests become a locked-test task.

## What changed (and why)
none

## Decisions made
- Reports match current code. Zero-hit lines: youtube.py 187-188, 197-198, 236-237, 284 and pick.py 100.
- `mutmut.txt` lists ids only, so survivors are mapped by function and line order. The test author confirms the top ids with `mutmut show <id>` before writing tests.
- In scope: pick 11 survivors; youtube 117 survivors and 1 timeout. Coverage pick 98%, youtube 95%. Most youtube survivors are message and log text, which the owner reads in the failure email, so they are not cosmetic.

## Tried and abandoned
none

## Known risks
- MED, contract question: the upload job's "Require this run's claim" step and the blob check (`daily_publish.yml:177-205`) refuse without writing `sent=false`. Record then keeps the claim and every later pick stops until the owner clears it. Safe but manual. Owner decides whether those guards write `sent=false` first.
- MED: `youtube.main` catches only UploadError. Other exceptions (UnicodeDecodeError if `errors="replace"` is dropped, ValueError on a token with a newline) leave no output line and a stuck claim. Fails closed.
- LOW, contract change candidate: the access token is only checked as a non-empty str. A newline in it would inject a log line after `::add-mask::`. Refuse whitespace with sent=False.
- LOW: redaction misses lowercase percent-encoding. pick does not require the file name to equal the script id (fails safe at claim).

## Next step
Test author writes a tests-only task from the ranked list below. Ranks 1 to 3 need no code change.

1. HIGH: session URL and upload_id redaction never exercised (`youtube.py:98-99`, upload survivors 34-41). Echo SESSION, UPLOAD_ID and the quoted session at the PUT; assert all absent, `[redacted]` present, `sent is True`. Plus a test that a session URL without upload_id still uploads.
2. HIGH: URL-encoded and JSON-escaped secret forms never exercised (`youtube.py:243`, `_http_message` 14-26). Echo the form body and a secret containing a backslash and a quote; add a hypothesis property over secret, prefix length and form.
3. HIGH/MED: the upload job's shell guards are only grep-checked (`test_daily_publish_workflow.py:137-163`). Run the job with fake `python` and `pip` on PATH: no record, published record, other `script_sha` and blob mismatch must exit non-zero with python never called; a good claim calls exactly the CLI; a bad `SCRIPT_ID` (`../x`, `x;touch pwned`) is refused.
4. MED: read failure after a good stat (`youtube.py:197-198`): `sent is False`, two requests, message names PermissionError.
5. MED: crash paths (`youtube.py:226-227`, `236-237`): `BadStatusLine` at each step (PUT gives sent=True), `IncompleteRead` after PUT gives sent=True, unreadable error body, non-UTF-8 error body, deeply nested JSON answer.
6. MED: pin messages: `"<step> failed: HTTP <code>"` for the three steps, the 200-character excerpt, the invalid_grant hint only with invalid_grant, URLError and OSError messages name the type, and the log records equal `["token refresh: HTTP 200", "upload init: HTTP 200", "video upload: HTTP 200", "uploaded video <id>"]`.
7. MED: the PUT redirect against a real local server for 301, 302, 303, 307, 308 (the fake opener patches `OpenerDirector.open`, so a plain `urlopen` regression would pass). Assert `sent is True` and no hit on the target.
8. MED-LOW: CLI entry paths (`youtube.main` reading `sys.argv`, `pick` using UTC today).
9. LOW: host-check edges (`https://[www.googleapis.com/x`, `:443`, uppercase host), 12-character and newline video ids, unicode metadata.
10. LOW: pick messages ("Check the channel", "still in queue/approved"), `.gitkeep` and `README.md` ignored, rule order.

Equivalent or note only: encoding mutants in `_load_records` and `_load_approved` (equivalent on Linux), argparse `prog`, the `safe=","` query mutant, `flush=True` on `::add-mask::`. No flaky tests found.

## Docs
none. The two contract questions under Known risks are for the owner.

## Evidence
Read-only. Files read: the task YAML, `p2-qa-lead.md`, `pick.py`, `youtube.py`, `tests/publish/*`, `tests/test_daily_publish_workflow.py`, `daily_publish.yml:140-259`, and the publish lines of `mutmut.txt`, `coverage.txt` and `coverage.xml`. `YOUTUBE_DESCRIPTION_MAX_BYTES` is pinned by `tests/test_schema_publish.py:106`.
