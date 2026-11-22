# Handoff: p4b-youtube

## Goal
Send the paid product placement flag on every YouTube insert (audit F1) and refuse an access token with characters outside printable ASCII before the `::add-mask::` print.

## Status
done. Gate 1 locally green; heavy tests do not apply to this task.

## What changed (and why)
`pipeline/publish/youtube.py` only:
- `_start_session`: query `part=snippet,status,paidProductPlacementDetails`; body gains `paidProductPlacementDetails.hasPaidProductPlacement` read from `constants.YOUTUBE_PAID_PRODUCT_PLACEMENT` at call time. Without it an unset flag no longer counts as "no paid placement".
- `_refresh_access_token`: after the scope check and before the mask print, the token must fullmatch `[\x21-\x7e]+` (new module regex `_TOKEN_CHARS`), else `UploadError(sent=False)` with a message that does not hold the token. A newline in the token would end the add-mask line and leave the rest unmasked or inject a workflow command.
- `upload()` docstring steps 1 and 2 updated to match.

## Decisions made
None beyond the task notes. The docstring words the character class in prose, since a backslash escape in a normal docstring would turn into literal characters.

## Tried and abandoned
none

## Known risks
The token check rejects any token with a space or non-ASCII character. Google access tokens are printable ASCII, so a real token should pass; a refusal fails the run with `sent=False` and the claim may be released.

## Next step
Gate 2 review and the security specialist review (`pipeline/publish/**` trigger). Then merge.

## Docs
none. The `upload()` docstring is the only doc this change touches, and it is updated. If PRD R15 or spec.md lists the `part` value, it needs `paidProductPlacementDetails` at close-out; I did not check them, they are outside `paths_allowed`.

## Evidence
- `pytest -q --tb=short tests/publish`: 146 passed (includes `test_youtube_placement.py::test_acceptance`).
- `ruff check .`: all checks passed (after wrapping two docstring lines over 110 chars).
- `mypy --strict pipeline/`: no issues in 25 source files.
