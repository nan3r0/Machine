# Handoff: p3-contracts (Architect, test_author)

## Goal
Phase 3 slice 1 contracts per `.harness/tasks/phase3/02_contracts.yaml`, plus the owner addendum of 2026-11-26: the host is the channel mascot. Every video is a host intro (the hook) on one generic backdrop, a transition into the story scenes, then a short host outro.

## Status
partial. This session hit its turn budget. Branch `plan/p3-contracts`, two local commits, not pushed. A fresh p3-contracts session continues from "Next step". Do not merge to main until that list is done, because `test_queue_scripts` and the visual tests depend on the remaining items.

## What changed
- `pipeline/constants.py`: the Phase 3 block. It holds:
  - set ids (D13), `HOST_BACKDROP_SET`, poses, camera moves, the default set per template, the host intro and outro poses;
  - `HOST_INTRO_MAX_S` and `HOST_OUTRO_MAX_S` (5 s each), `HOST_TRANSITION_S` 0.5, `SCENE_FADE_S` 0.3, `SCENE_TAIL_S`;
  - drift and pan speeds per depth, `SET_LAYER_MARGIN_PX` 120, `PUSH_IN_SCALE` 1.08, the layer and shape caps, the ASS layer bands;
  - blink, bob and arm swing timings, `CAPTION_POS_Y` 1240, `CAPTION_BAND_TOP_PX`, host placement (scale 0.85, ground at 540, 1020), `DATA_PANEL`, card fonts and colours, the counter steps;
  - the item caps (`VISUAL_ITEMS_MAX` 4, `VISUAL_DATA_SCENES_MAX` 3, label 24, value 12, `VISUAL_TEXT_MAX_CHARS` 160 a script), `RENDER_BUDGET_S`, and the golden strip numbers.
- `pipeline/visuals/art.py` (contract): the `Shape`, `Pose`, `HostArt`, `SetLayer` and `SetArt` models, `path_points`, `load_host` and `load_set`. `assets/character/host.yaml` validates (108 shapes).
- Stubs with docstring contracts: `pipeline/visuals/__init__.py`, `ass_kit.py`, `character.py`, `sets.py`, `cards.py`, `charts.py` and `router.py`. `router.py` defines the `Span` and `ScenePlan` dataclasses.
- Locked tests:
  - `tests/test_render_constants_visuals.py` (this task's own; 13 pass with `LOOM_TASK=p3-contracts`);
  - `tests/visuals/ass_parse.py` (an independent Dialogue reader and ASS unescape oracle);
  - `tests/visuals/test_ass_kit.py`, `test_character.py`, `test_sets.py`, `test_sets_art.py`, `test_cards.py`, `test_charts.py` and `test_router.py`.

## Decisions made
- **No schema.py change.** The intro is the hook and the outro is the loop line, both already in `Script`.
- **The host backdrop** is drawn like a set (`assets/sets/host_backdrop.yaml`, drawn by p3-sets-art). It is not in `SET_IDS`, so neither the writer nor validate can pick it as a scene's set. `test_sets_art.py` requires its asset.
- **Spans are exact and contiguous**: intro, scenes, outro.
  - Intro = [0, min(scene 0's first word, `HOST_INTRO_MAX_S`)].
  - Outro = [max(the loop line's first word, last end - `HOST_OUTRO_MAX_S`), last end].
  - A longer hook or loop line keeps its words, and the neighbouring story scene shows for the rest. No validate rule is added, so `sample-65s` (a 20 word loop line, about 8 s) stays valid.
  - This replaces p3-plan's "the hook uses the first scene's set".
- **The transition is an effect, not a span**: a fade over `HOST_TRANSITION_S` into the first scene and into the outro.
- **Host placement.** Scale 0.85 with the ground anchor at (540, 1020), so the art box spans x 303 to 821 and y 338 to 1037. That clears `CAPTION_BAND_TOP_PX` (1048, two caption lines over y 1240) and the right UI zone. The owner's sheet showed scale 1.0; visual QA checks the smaller host.
- **PR body.** Same-line set and pose spans per scene, at most 3 data scenes a script, and 160 characters of item text a script. The arithmetic in `test_render_constants_visuals.py` starts from the measured Phase 2 body (51441 characters for 7 scripts at every cap) and gives at most 60000. `VISUAL_DATA_SCENES_MAX` is a new validate rule that p3-validate-visuals' notes do not yet name.
- **The host.yaml hash** is checked on LF-normalised bytes.
- **Router tests** swap `art.load_set` for a fixture set, so p3-router does not wait for p3-sets-art.

## Tried and abandoned
- Clamping the intro and outro through a validate word cap: it would make the approved `sample-65s` invalid.
- Captions at y 1230 with the host at scale 1.0 and feet at 1150: the host overlaps two caption lines.

## Known risks
- The visual tests are written but no implementation has run them yet. An implementer who finds one wrong writes `CONTRACT_CHANGE.md`.
- The `test_charts.py` bar case `"2,5"[:1]` is just `"2"`. It is harmless but odd; tidy it in the next session.
- `ass_kit.header` ends with the events `Format:` line, and `test_ass_kit` checks that.

## Next step (fresh p3-contracts session, same branch)
1. `queue/approved/sample-65s.json`: give its scenes `set` and `pose`, and replace the `step` and `label` keys, which validate will reject. Add one `steps` timeline scene with items 1997 and 2005. `origin/ledger` was checked on 2026-11-26 and holds only `data/published/.gitkeep`, so the file can change.
2. `tests/fixtures/scripts/demo-data.json`: a valid 65 s `chart` template script with counter, bars and place scenes. Add a test that validates it.
3. Locked tests still to write:
   - `tests/script/test_validate_visuals.py` (including `VISUAL_DATA_SCENES_MAX` and rejecting `HOST_BACKDROP_SET` as a set);
   - `tests/render/test_compose_layers.py`: the keyword-only `scenes`, the filter chain, `CAPTION_POS_Y`, and a heavy render;
   - `tests/test_render_one_visuals.py`: the wiring through fakes, plus the heavy acceptance with the render budget, golden frames, the 8-frame strip across the intro end, and 8 consecutive frames;
   - `tests/script/test_generate_visuals.py`;
   - `tests/script/test_batch_visuals.py`: the body at every cap with visuals, and the D4 replacement through a wrapped `generate.write_script`.
4. Edit the locked tests:
   - `tests/script/test_generate.py:112`: drop `scene.visual.data == {}`;
   - `tests/test_render_one.py`: the fake compose takes `**kwargs` and stores them;
   - the `tests/script/test_batch.py` docstring: point to the new arithmetic.
5. `.harness/locks.yaml`: add `pipeline/visuals/art.py`. `pyproject.toml` `also_copy` needs no new root folder so far; check again after step 3.
6. Docs:
   - PRD.md R19 to R22, section 3 phase line, section 7 owner answers (p3-plan D1 to D7 and D10 to D13, method A, and the mascot addendum of 2026-11-26);
   - workflow.md `## Phase 3 module order`, a `### Phase 3 status` table, and criterion map rows.
7. Run ruff, `mypy --strict pipeline/`, pytest without `LOOM_TASK` and with `LOOM_TASK=p3-contracts`, and `python tests/docs_check.py`. Then commit.
8. Owner: `git push -u origin plan/p3-contracts`, open a PR to main, and merge once CI is green. Implementers start only after that merge (lessons.md 2026-11-25).

## Docs
- Owed in this task: PRD.md and workflow.md (step 6).
- Owed at close-out:
  - task YAML notes. 03 names `VISUAL_DATA_SCENES_MAX` and the backdrop rule. 11 names the host intro and outro and the `art.load_set` fake. 07 adds `host_backdrop.yaml`.
  - p3-plan.md: the hook and loop line deviation.
  - spec.md file tree: `assets/character/host.yaml` and `pipeline/visuals/`.
- lessons.md: none.

## Evidence
- `ruff check .`: clean after the last edit (the earlier run flagged 1 B007, fixed).
- `mypy --strict pipeline/`: no issues in 33 files.
- `pytest -q tests` without `LOOM_TASK`: 1656 passed, 186 skipped. The new task-owned tests skip on main, as conftest intends.
- `LOOM_TASK=p3-contracts pytest tests/test_render_constants_visuals.py`: 13 passed.
- `python tests/docs_check.py`: passed.
- Run with the sibling venv `agent-a84cab27280eafe81` (lessons.md 2026-11-15).
