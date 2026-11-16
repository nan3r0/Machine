# Handoff: p2-contracts

## Goal
Phase 2 contracts (shapes, constants, module stubs with docstring contracts) and the locked tests for every Phase 2 build task, plus the close-out docs for p2-entry-ci and p2-factcheck-exact.

## Status
done (Test Author). Branch `docs/p2-contracts` from origin/main 0ab46e2, committed, not pushed. Owner reviews and merges (HARNESS.md section 5).

## What changed (and why)
- `pipeline/schema.py`: `Fact` (id >= 1, non-blank text, https url with a host), `SourceFile` (topic, at least one fact, ids unique in the file), `Flag`, `LineVerdict` (with `fact_ids`; SUPPORTED and PARTIAL must name one, owner decision D5). Script unchanged.
- `pipeline/constants.py`: Phase 2 numbers (D5, D6): models `gemini-3.8-flash` / `gemini-3.5-flash-lite`, checker temperature 0, endpoint and `Api-Revision 2026-05-20`, budgets 14 and 14, `SCRIPT_ATTEMPTS` 2, timeout 120 s, retry wait 10 s, field caps, `TARGET_WORDS` 156, and new size caps (`SCENES_MAX` 10, `NARRATION_MAX_CHARS` 1500, `FACTS_PER_SOURCE_MAX` 10, fact text 160, url 100, `REASON_MAX_CHARS` 120) that keep a 7-script PR body at every cap under 60000. Phase review N7 comment fixed.
- Stubs with docstring contracts: `pipeline/script/{__init__,validate,gemini,sources,generate,batch}.py`, `pipeline/factcheck/semantic.py`.
- `queue/approved/sample-65s.json`: NOAA URL removed from the description (D6).
- Locked tests (one file per task, each with `test_acceptance`): `tests/test_schema_sources.py` (this task), `tests/script/test_validate.py`, `tests/test_render_one_validate.py`, `tests/test_queue_scripts.py` (p2-validate), `tests/script/test_gemini.py` (p2-gemini), `tests/test_sources_files.py` (p2-seed-sources), `tests/script/test_generate.py` (p2-generate), `tests/factcheck/test_semantic.py` (p2-semantic), `tests/script/test_batch.py` (p2-batch), `tests/test_weekly_workflow.py` (p2-weekly-workflow). Helpers (not collected): `tests/script/scripts.py`, `tests/script/gemini_fakes.py` (the reference interactions.create example copied verbatim, source and date in its docstring).
- Opus advice folded in: unique normalised topic and queue fact ids resolving to one source (`test_sources_files.py`); the picker reads `queue/published/` too, a short batch says "N of 7: sources exhausted", zero unused sources means exit 1, no body, no call (`test_batch.py`, `test_generate.py`); Gemini 404 fails at once naming the model, 429 gets one retry only (`test_gemini.py`); `test_weekly_workflow.py` calls `rules.assert_safe(wf, "weekly_scripts.yml")`.
- Coordinator's security addition: model-derived strings in the PR body stay inside code (fence longer than any backtick run), so no link, image, HTML, comment or @mention renders. Test `test_model_text_cannot_escape_its_code_span` in `test_batch.py`, with a self-test of its Markdown code detector.
- Task YAMLs 03 to 08: notes aligned with the contracts (see Decisions).
- Close-out: `.harness/status.yaml` adds p2-entry-ci and p2-factcheck-exact; workflow.md Phase 2 rows and criterion map; `docs/threat-model.md` P1-6 closed and section 4.2/4.3 line references refreshed; lessons.md entry (shell plus Python rewrite mangled backslashes); architecture.md section 7 (sources exhaustion, Phase 4 upload-then-commit gap, model deprecations, p2-entry-ci reviewer notes); p2-entry-ci handoff Status corrected to `task/p2-entry-ci`.
- PRD.md: R8.1, R10.3, R10.5 (new), R11.1, R12.1, R13.1 extended; D2 to D8 recorded in section 7 with D1 open; Interactions API research; open questions updated. spec.md: data model, numbers, security lines.

## Decisions made
- **write_script makes exactly one call; the batch owns the retry.** The task YAML had write_script retry internally, but then the batch could not count writer calls, and charging 2 per script up front would leave no budget for any rewrite in a 7-script batch. Budgets are counted as made, and rewrites never spend what the remaining scripts need for their own write and check.
- Script id = source slug; the PR heading shows the id, never the model's title.
- New `<` and `>` ban in spoken and published fields (YouTube rejects them in titles and descriptions, and they could hide text in the PR body).
- Size caps added (scenes, narration characters, facts per source, fact text and url, reason length) so the "at every cap" body test is defined. Facts per source cut from the planned 6 to 12 to 6 to 10.
- Sample fact ids 1 to 9 resolve through a new `sources/bloop.yaml` that p2-seed-sources writes (brief updated), so the resolution test needs no exemption. That is why `test_sources_files.py` asks for 15 files.
- `generation_config.temperature` follows the overview page; the API reference does not list it (recorded in PRD.md section 7). A wrong field would show as HTTP 400 on the first live call.
- A lone surrogate is already rejected by `Script` in non-blank fields, so validate's Cs rule is tested on description, tags and on_screen_text only.
- `TAGS_TOTAL_MAX_CHARS` 500 cannot be reached with 10 tags of 30; kept as the owner set it, no test.
- `.harness/locks.yaml` unchanged: `tests/**`, `schema.py` and `constants.py` already cover every contract and test.

## Tried and abandoned
- `make_script` with a date string: strict models reject strings outside JSON; helpers use `date` objects.
- Throwaway implementations of validate, gemini, sources, generate, semantic, batch, the render_one check and a weekly workflow were written to prove every locked test passable, then discarded (`git checkout -- pipeline/`, workflow file deleted). They found three test bugs (flag-line layout, budget charging, surrogates), fixed before locking.

## Known risks
- The PR body tests use a simplified Markdown code detector; an implementation using fences inside blockquotes or lists fails them (on purpose: fail safe). p2-batch should use top-level fences.
- The Interactions API response and error shapes come from docs only, no live call (D1 open).
- The writer and checker free daily limits are still unconfirmed (PRD open question).
- 14 seeded sources last two batches (architecture.md section 7).

## Next step
Owner reviews and merges this branch. Then p2-validate, p2-gemini and p2-seed-sources can start (in parallel; disjoint paths). p2-generate after p2-validate and p2-gemini; p2-semantic after p2-gemini.

## Docs
- Done on this branch: PRD.md, spec.md, architecture.md, workflow.md, lessons.md, docs/threat-model.md, .harness/status.yaml, task YAMLs 03 to 08, p2-entry-ci handoff.
- PLAN.md lines 127 to 128, section 3 table (owner's; not edited). Proposed wording:
  - Research row: "Hand-curated `sources/*.yaml`, one solved mystery each (D4) | NotebookLM or a Gemini notebook may help refill sources by hand; no API, no ingest task".
  - Script row: "Gemini API free tier, structured JSON output | Writer `gemini-3.8-flash`, checker `gemini-3.5-flash-lite` at temperature 0 (ids only in `pipeline/constants.py`; never `gemini-2.5-*` or preview). At most 14 writer and 14 checker calls per weekly batch. Model ids retire: check the deprecations page every few months. Fallback provider deferred (D8)."
  - Also PLAN.md sections 2, 7, 9 per the architect-p2-plan handoff Docs list.
- CLAUDE.md Status line (owner or orchestrator): "Phase 2 contracts on `docs/p2-contracts`; p2-entry-ci and p2-factcheck-exact done."
- `.harness/handoffs/p1-phase-review.md` N7 fixed here (constants comment), N9 fixed by p2-entry-ci.

## Evidence
Worktree venv, requirements.txt and requirements-dev.txt only (Windows):
- `ruff check .`: all checks passed. `mypy --strict pipeline/`: no issues, 21 files. `python tests/docs_check.py`: passed. `pytest .harness/tests`: 69 passed.
- `pytest -q`: 426 passed, 312 skipped. `LOOM_TASK=p2-contracts pytest -q`: 457 passed, 281 skipped (31 own tests pass).
- Red first against the stubs (whole suite per LOOM_TASK): p2-validate 159 failed, p2-gemini 32, p2-seed-sources 3 (the topic-normaliser self-test and two vacuous checks pass with no files), p2-generate 22, p2-semantic 19, p2-batch 21 (the detector self-test passes), p2-weekly-workflow 6.
- Passable: with throwaway implementations, p2-validate 159, p2-gemini 32, p2-generate 22, p2-semantic 19, p2-batch 22 and p2-weekly-workflow 6 passed, 0 failed. test_sources_files.py was not run against real files (the seeding task writes them).
- Sources read 2026-11-16: aistudio.google.com/docs/interactions-overview, docs/structured-output, api-reference/interactions-api.
