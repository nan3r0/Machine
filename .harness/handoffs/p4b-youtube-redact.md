# Handoff: p4b-youtube-redact

## Goal
Redact every echoed form of a stored secret, longest form first, so a shorter form inside a longer one cannot leave part of the secret in an error message.

## Status
done

## What changed (and why)
`_http_message` in `pipeline/publish/youtube.py` (the task YAML calls it `_error_message`) now collects the plain, URL-encoded and JSON-escaped forms of all stored secrets into a set, drops empty forms, and replaces them longest first. Before, forms were replaced per secret in a fixed order, so a client secret of 12 backslashes plus `x` had its JSON-escaped form cut by the plain form and a prefix leaked.

## Decisions made
A set dedupes equal forms. Sorting by length alone is enough; ties cannot contain each other unless equal.

## Tried and abandoned
none

## Known risks
Only these three forms are covered, as before. A secret echoed in another encoding is not redacted.

## Next step
Gate 2 and the security review (pipeline/publish/** trigger). Then close p4b-youtube-survivors and this task in status.yaml.

## Docs
none

## Evidence
- `pytest -q tests/publish/test_youtube_survivors.py`: 87 passed
- `pytest -q tests/publish`: 223 passed, 24 skipped (tests owned by other tasks)
- `ruff check .`: clean
- `mypy --strict pipeline/`: no issues in 25 files
