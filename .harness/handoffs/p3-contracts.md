# Handoff: p3-contracts (Architect, test_author)

## Goal
Phase 3 slice 1 contracts per `.harness/tasks/phase3/02_contracts.yaml`, plus the owner addendum of 2026-11-26: the host is the channel mascot. Every video is a host intro (the hook) on one generic backdrop, a transition into the story scenes, then a short host outro.

## Status
done (session 2 finished the list session 1 left). Branch `plan/p3-contracts`, committed, not pushed (agents cannot push).

## What changed
- **`pipeline/constants.py`**: the Phase 3 block. It holds:
  - set ids (D13), `HOST_BACKDROP_SET`, poses, camera moves, the default set per template, the host intro and outro poses;
  - `HOST_INTRO_MAX_S` and `HOST_OUTRO_MAX_S` (5 s each), `HOST_TRANSITION_S` 0.5, `SCENE_FADE_S` 0.3, `SCENE_TAIL_S`;
  - drift and pan speeds per depth, the 120 px margin, push-in 1.08, the layer and shape caps, the ASS layer bands;
  - blink, bob and swing timings, `CAPTION_POS_Y` 1240, `CAPTION_BAND_TOP_PX`, the host placement, `DATA_PANEL`, card fonts and colours, the counter;
  - the item caps, `RENDER_BUDGET_S`, and the golden strip numbers.
- **`pipeline/visuals/art.py`** (contract, now in `.harness/locks.yaml`): the models and loaders. `host.yaml` validates.
- **Stubs with docstring contracts**: `pipeline/visuals/__init__.py`, `ass_kit.py`, `character.py`, `sets.py`, `cards.py`, `charts.py` and `router.py` (with the `Span` and `ScenePlan` types).
- **New locked tests**, each owned by one task:
  - `tests/test_render_constants_visuals.py` (this task);
  - `tests/visuals/ass_parse.py` (helper);
  - `tests/visuals/test_ass_kit.py`, `test_character.py`, `test_sets.py`, `test_sets_art.py`, `test_cards.py`, `test_charts.py`, `test_router.py`;
  - `tests/script/test_validate_visuals.py`, `tests/render/test_compose_layers.py`, `tests/test_render_one_visuals.py`, `tests/script/test_generate_visuals.py`, `tests/script/test_batch_visuals.py`.
- **Existing locked tests**, which hold before and after the change:
  - `tests/script/test_generate.py`: dropped `visual.data == {}`.
  - `tests/test_render_one.py`: the fake compose takes `**kwargs` and stores them in `compose_kwargs`.
  - `tests/script/test_batch.py`: the docstring points to the new arithmetic.
  - `tests/render/test_captions_exact.py`: accepts the caption y at either `HEIGHT / 2` or `CAPTION_POS_Y`, so it holds before and after p3-compose.
- **Fixtures**:
  - `queue/approved/sample-65s.json`: scenes now carry sets, poses and cameras. Scene 4 is a `steps` timeline (1997, 2005), and the old `step` and `label` keys are gone. `origin/ledger` holds only `data/published/.gitkeep`, checked 2026-11-26.
  - `tests/fixtures/scripts/demo-data.json`: a `chart` template script about the Death Valley sailing stones, 163 words, with counter, place card and bars scenes.
- **Docs**:
  - PRD.md: section 3 phase line, section 4 R19 to R22, and the section 7 entries of 2026-11-25 and 2026-11-26.
  - workflow.md: the criterion map rows, `## Phase 3 module order` and `### Phase 3 status`.

## Decisions made
- **No schema.py change.** The intro is the hook and the outro is the loop line.
- **The host backdrop** is set art (`assets/sets/host_backdrop.yaml`, drawn by p3-sets-art) outside `SET_IDS`, so neither the writer nor validate can pick it.
- **Spans are exact and contiguous.**
  - Intro = [0, min(scene 0's first word, 5 s)].
  - Outro = [max(the loop line's first word, last end - 5 s), last end].
  - A long hook or loop line keeps its words, and no validate cap is added. This replaces p3-plan's "the hook uses the first scene's set".
- **The transition is a fade effect, not a span.**
- **Host size.** The host is drawn at scale 0.85 with its ground at (540, 1020), to clear two caption lines at y 1240. The owner's sheet showed scale 1.0; visual QA checks it.
- **PR body.** Same-line set, pose and item spans, at most 3 data scenes and 160 characters of item text a script. The arithmetic gives at most 60000; the real body check is in `test_batch_visuals.py`.
- **Writer fallback.** A broken visual becomes `{"type": "story", "data": {}}`. Data scenes past the cap fall back in scene order.
- **D4.** An unbacked item makes the scene a story scene with `data == {"set": <its set>}`, and adds a flag.
- **Router tests** swap `art.load_set` for a fixture set, so p3-router does not wait for p3-sets-art.

## Tried and abandoned
- A validate word cap on the hook and loop line: it would make the approved `sample-65s` invalid.
- Captions at y 1230 with the host at scale 1.0: the host overlapped two caption lines.

## Known risks
- No implementation has run the tests yet. A test that turns out wrong comes back as `CONTRACT_CHANGE.md`.
- **`test_batch_visuals` assumes batch calls `generate.write_script` through the module.** It does today.
- **The caption y check is loose until p3-compose merges.** After p3-compose merges, narrow `test_captions_exact.py` to `CAPTION_POS_Y`, as an Architect task.
- **The demo fixture's facts are for rendering only.** They are not in `sources/` and are not fact-checked.

## Next step
1. Owner:
   - `git push -u origin plan/p3-contracts`
   - Open a PR to main titled "p3-contracts: Phase 3 slice 1 contracts and locked tests". Wait for CI (`check`) to go green, then merge.
2. Orchestrator, at close-out:
   - add p3-spike, p3-character-art and p3-contracts to `.harness/status.yaml` and set their workflow.md rows to done;
   - then launch wave 4: p3-validate-visuals and p3-ass-kit.

## Docs
- Done here: PRD.md (sections 3, 4 and 7) and workflow.md (map, order, status).
- Owed at close-out, outside this task's paths:
  - `.harness/tasks/phase3/03_validate_visuals.yaml` notes: add the `VISUAL_DATA_SCENES_MAX` cap (3 data scenes a script), the `VISUAL_TEXT_MAX_CHARS` total, and the rejection of `HOST_BACKDROP_SET` as a scene set.
  - `11_router.yaml`: the host intro and outro spans, and the `art.load_set` fake.
  - `07_sets_art.yaml`: add `assets/sets/host_backdrop.yaml`.
  - `13_writer_visuals.yaml`: the story fallback and the data scene cap.
  - `14_batch_visuals.yaml`: D4 keeps `{"set": ...}`.
  - p3-plan.md: the hook and loop line deviation (mascot addendum).
  - spec.md file tree: `assets/character/host.yaml`, `assets/sets/`, `pipeline/visuals/`.
  - CLAUDE.md Status: p3-contracts done.
- lessons.md: none.

## Evidence
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues in 33 files.
- `pytest -q tests` without `LOOM_TASK`: 1656 passed, 258 skipped. The new task-owned tests skip on main.
- `LOOM_TASK=p3-contracts pytest tests/test_render_constants_visuals.py`: 13 passed.
- With each implementer's `LOOM_TASK`, its new tests collect and fail on the stubs, as they should.
- `pytest .harness/tests`: 90 passed. `python tests/docs_check.py`: passed.
- Validating `sample-65s` (167 words) and `demo-data` (163 words) with the current validate: no problems.
- Run with the sibling venv `agent-a84cab27280eafe81` (lessons.md 2026-11-15).
