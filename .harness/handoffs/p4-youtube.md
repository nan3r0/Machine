# Handoff: p4-youtube (implementer)

## Goal
Implement `pipeline/publish/youtube.py` (PRD R15): token refresh, resumable `videos.insert` over the standard library, CLI that writes one output line.

## Status
done. Gate 1 locally green. Security review applies (`pipeline/publish/**`). No heavy tests involved, so no "awaiting CI" caveat.

## What changed (and why)
- `pipeline/publish/youtube.py` only. `upload` runs checks (script via `validate.problems`, file size bounds, three env credentials), then three steps: token refresh, init, one PUT.
- A `_NoRedirect` opener (same pattern as `gemini.py`) turns every 3xx into an HTTPError, so the token and secrets never follow a redirect.
- Token step checks `access_token` is a non-empty string and `scope` split on spaces equals exactly `{YOUTUBE_SCOPE}`. A broader or missing scope fails with `sent=False`. After a good answer it prints `::add-mask::<token>` to stdout before the init request, as the brief asked.
- Session URL (`Location` header) must be `https` and its whole netloc must equal `YOUTUBE_UPLOAD_HOST` or `host:443`. Comparing the whole netloc rejects user info, other ports, suffix and parent hosts, and relative URLs.
- Errors name the step and HTTP status plus a 200-char body excerpt, redacted before clipping (client secret, refresh token, access token, and the session URL for the PUT step). Messages never contain the session URL, only the step name. Logs hold status codes and the video id only.
- `invalid_grant` in an error body adds "the refresh token was revoked or expired, make it again".
- `main` appends exactly one line: `video_id=<id>` (exit 0), or `sent=true|false` (exit 1, reason on stderr). An unreadable or invalid script counts as `sent=false`.

## Decisions made
- The brief's three extra checks, all done: mask after refresh (done in `_refresh_access_token`, covered by `test_access_token_is_masked_before_init`); errors name the host only, never the session URL (the init refusal message names the allowed host, the PUT messages name the step only); token `scope` exactness and `Location` / `X-Upload-*` header shapes follow the contract text and are covered by locked tests.
- The `sent` flag flips to True only inside `_send_video`'s `_call`, so a failed local `read_bytes` still counts as `sent=False`. The contract says "no byte went out", which this matches.
- Reads the whole mp4 into memory (max 100 MB, `MAX_FILE_BYTES`). Streaming would add code for no gain on a runner.

## Tried and abandoned
none

## Known risks
- The API shapes (`Location` header, token answer, `videos` resource) are from the contract and hand-built fakes. No live call has been made. The owner's first live run (R17) is the first real check.
- No retry: a transient failure costs a day, by design (plan).
- A record failure after a good upload leaves the claim in place; that is the plan's accepted trade-off, not this module.

## Next step
p4-daily-workflow (wave 4) wires `python -m pipeline.publish.youtube SCRIPT MP4 "$GITHUB_OUTPUT"` into the upload job. The job must not echo the output of this CLI anywhere except the job log, where the mask line already applies.

## Docs
- Applied here: none (paths_allowed is the one source file).
- Owed at Phase 4 close-out: spec.md section 7 and architecture.md section 1b should note that `youtube.py` prints a `::add-mask::` workflow command to stdout, so the upload job's stdout must stay in the job log. The threat model (p4-cso) should list the scope check (`scope` must equal the upload scope only) as a control against a wrongly consented token.
- lessons.md: no new entry; nothing went wrong.

## Evidence
Run with `../p2b-qa-tests-batch/.venv/Scripts/python.exe`.
- `LOOM_TASK=p4-youtube pytest tests/publish/test_youtube.py`: 122 passed.
- Full `pytest -q`: 1441 passed, 78 skipped. `ruff check .`: passed. `mypy --strict pipeline/`: no issues in 25 files. `tests/docs_check.py`: passed.
- `git status`: only `pipeline/publish/youtube.py` and this handoff changed.
