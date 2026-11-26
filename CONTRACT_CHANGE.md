# CONTRACT_CHANGE: tests/visuals/test_router.py

Which test: every test that builds a script through the `script()` helper or the inline
`Script.model_validate({**BASE, ...})` (lines 48 and 163), so all 7 tests in the file.

Why: `BASE` is read with `json.loads`, so `publish_after` is the string `"2026-11-23"`.
`Script` is strict (`ConfigDict(strict=True)`), and `model_validate` on a python dict rejects a
str for a `date` field (pydantic 2.14.4, the pinned version):
`publish_after: Input should be a valid date [type=date_type]`. schema.py's own docstring says to
parse script files with `Script.model_validate_json(text)`. So the tests fail at fixture
construction, before reaching router code, locally and in CI.

What it should say: build the model from JSON, for example in both places

    Script.model_validate_json(json.dumps({...}))

(or `Script.model_validate({...}, strict=False)`).

Evidence the router is correct: with `Script.model_validate` patched in memory to go through
`model_validate_json` (no file change), all 7 tests in test_router.py pass.
