# Contract change: tests/script/test_validate_visuals.py

Test: every test that builds a `Script` (`with_visual`, `test_phase2_empty_data_stays_valid`, `test_data_scene_and_text_totals_are_capped`, `test_acceptance`, via `Script.model_validate(...)`).

Why: `Script` is strict (`pipeline/schema.py` line 20, and its docstring says to use `model_validate_json`). `SAMPLE` is a JSON-loaded dict, so `publish_after` is the string "2026-11-23" and `Script.model_validate` raises `ValidationError: publish_after Input should be a valid date`. 43 of 44 tests in the file fail at construction, before `validate.problems` runs. The validate.py change is done and mypy/ruff clean.

Fix: build scripts with `Script.model_validate(..., strict=False)` or `Script.model_validate_json(json.dumps(...))`. With `strict=False` on every `model_validate` call in the file (copy in a temp dir), 42 of 44 pass; the other 2 are the two calls my rewrite missed, which have the same cause. The demo fixture test already uses `model_validate_json` and passes.
