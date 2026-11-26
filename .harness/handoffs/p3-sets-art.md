# Handoff: p3-sets-art (Architect)

## Goal
Draw the six starting sets (D13) and the generic host backdrop as flat layered art in `assets/sets/`, log them in `assets/LICENSES.md`, and get the owner's approval from stills rendered with the host on the runner (p3-plan "Sets", owner mascot addendum 2026-11-26).

## Status
partial, awaiting the owner's approval of the runner stills. The assets pass `tests/visuals/test_sets_art.py` locally; nobody has seen them in libass yet.
- Task branch `task/p3-sets-art`: `9d3d477` has the 7 YAMLs and the licence rows. This handoff is the commit after it. Committed, not pushed.
- Throwaway branch `spike/p3-sets-stills` at `84ffb9f` (task commit `9d3d477` plus the stills script and a `render.yml` override). Committed, not pushed, never merged.

## What changed
- `assets/sets/night_street.yaml`, `desert_rail.yaml`, `lamp_room.yaml`, `shore_night.yaml`, `forest.yaml`, `archive.yaml`: the D13 sets.
- `assets/sets/host_backdrop.yaml`: the host intro and outro backdrop. It has no place, just a stepped plum spotlight behind the head and a floor.
- `assets/LICENSES.md`: one row per file (own work), sha256 of the committed LF content.
- **Throwaway branch only:**
  - `spike/draw_sets.py`: the authoring helper that writes the YAMLs (circles as Bezier runs, full-width bands over the drift margin). The YAML is the asset. Keep the helper on the spike branch for the next round.
  - `spike/stills.py`: renders every set through the real `sets.set_events`, `character.host_events` and `captions_ass.build_ass`, so the stills show what the pipeline will draw.
  - `.github/workflows/render.yml`: overridden to install FFmpeg and the hash-pinned PyYAML and pydantic blocks of `requirements-render.txt` (`--no-deps --require-hashes`), then run the stills. Same pattern as p3-character-art.

| Set | Layers (depth) | Shapes | Look |
|---|---|---|---|
| night_street | far, mid, near | 12 | indigo sky, moon, skyline with 3 dim lit windows, street lamp with a soft glow |
| desert_rail | far, mid, near | 12 | dusk purple sky with ember bands on the horizon, buttes, a rail line, a telegraph pole |
| lamp_room | far, mid, near | 13 | plum wall, moonlit window, one hanging lamp with a faint light cone, rug, side table |
| shore_night | far, mid, near | 13 | moon with halo and a short reflection, dark sea, lighthouse with a faint beam, a rock |
| forest | far, mid, near | 9 | moon glow behind the head, pine line, two fog bands, two close trunks |
| archive | far, mid, near | 19 | box shelves on both sides, a pale light shaft and pool, a filing cabinet, boxes |
| host_backdrop | far, near | 6 | three stepped rings (a soft spotlight) behind the head, floor with a spot |

## Owner steps (round 1)
1. Push the throwaway branch: `git push -u origin spike/p3-sets-stills`. Do not open a PR; it is never merged.
2. GitHub, **Actions**, **render**, **Run workflow**. Branch: `spike/p3-sets-stills`. Leave the `script` input at its default; the stills ignore it. The repo is public, so the run is not metered. Expect a few minutes: 17 FFmpeg calls on 20 s clips at 10 fps.
3. When the run is green, download artifact **`stills`** (kept 3 days). `order.txt` maps NN to set ids (00 night_street, 01 desert_rail, 02 lamp_room, 03 shore_night, 04 forest, 05 archive, 06 host_backdrop):
   - `sheet_start.png`: every set at half size, 4 by 2, first frame of a scene, host in `talk`, a sample caption at its real place;
   - `start_NN.png`: the same at full 1080 x 1920;
   - `pushin_NN.png`: the last frame of a 20 s `push_in` scene. Drift is at the 120 px cap for every depth and the set is scaled 1.08;
   - `panleft_NN.png`: the last frame of a 20 s `pan_left` scene (drift the other way, capped);
   - `sheet_pushin.png`, `sheet_panleft.png`: those at half size;
   - `dim_00..02.png`: the data-scene default sets (archive, lamp_room, shore_night) dimmed with no host, as under a data card;
   - the `.ass` files.
4. Tell the orchestrator: approved, or what to change per set (mood, colour, props, anything that fights the host or the caption). A changed round edits `spike/draw_sets.py` on the spike branch, regenerates the YAMLs, copies them to `task/p3-sets-art` with new licence hashes, and dispatches again.
5. After approval: delete `spike/p3-sets-stills` on origin and locally, then set this handoff to done.

What visual QA should check on the stills: no black edge at either side in `pushin_NN` and `panleft_NN`; the host's feet sit on the floor (not floating above its top edge) in both `start_NN` and `pushin_NN`; the caption reads clearly on every set; the host's dark outline and hair stand out from what is behind the head.

## Decisions made
- **One layout for every set.** The floor's top edge is at y 960 everywhere, so the host's feet (y 1020, `HOST_GROUND_Y`) stand on it. Everything below that is a dark flat floor, so the caption band (y 1048 to about 1430) sits on a plain dark field.
- **Behind the head is mid-dark, never near-black.** The host's outline and hair are near-black purple, so each set puts a softer value behind the head (moon glow, haze, light cone, rings).
- **Cool dark hues.** Each set has its own hue (indigo, dusk purple, plum, navy, deep green, brown) so two videos on similar topics look different (PLAN.md section 11). Warm accents are small and low-contrast. The host's orange coat stays the brightest thing on screen.
- **Soft bands, no gradients.** Haze, glow and fog are flat shapes at an ASS alpha of 60 to D8. A gradient would need new tools.
- **Outlines only on props**, at 2 to 4 px (the host uses 4 to 5). Sky, bands and silhouettes have none, so the sets stay behind the host.
- **Full-width shapes span x -120 to 1200**, so drift up to the 120 px cap shows no edge. Props sit clear of the host's box (x 303 to 821, y 338 to 1037).
- **Shape counts 6 to 19**, under the cap of 25, to keep render time low.

## Tried and abandoned
- A telegraph wire running right across the desert, from the pole at x 118 to the far edge. In the preview it crossed behind the host's face, so it now runs off the left edge.
- A lighter sand (`26272E`) on shore_night. In the preview it was the brightest floor, so it is now `1D1F26`.

## Known risks
- **Not yet seen in libass.** The design was checked with a rough local Pillow preview, which was not committed. The runner stills are the first real look.
- **Push-in pivot.** `sets.set_events` sets `\org(540,960)`, but libass may scale `\fscx`/`\fscy` about the event position (0, 0) rather than `\org`. In that case the floor edge at y 960 drops to about y 1037 at the end of a push-in, 17 px below the feet, so the host would look like he stands just behind the floor edge. `pushin_NN.png` shows which case holds. If it is the bad one, the fix belongs in `sets.py` or the constants, not in the art.
- **Data-scene sets under the dim.** archive, lamp_room and shore_night have detail on the sides; `dim_NN` shows whether card text in `DATA_PANEL` stays calm over them.
- **Negative x.** No libass render has yet checked that shapes with negative x land where they are drawn. If libass aligned a drawing by its bounding box, they would shift by up to 120 px. Spot-check in `start_NN`: the forest's left trunk is a narrow strip at the left edge, the archive's left shelf starts off-frame, and the night_street moon sits near x 180. A shift would be a `sets.py` or `ass_kit` issue, not an art one.
- **Local test env.** A stray `tests/__init__.py` in the global site-packages (`...\Python311\Lib\site-packages\tests\`) shadows the repo's `tests/` namespace, so a plain local `pytest` fails to collect 63 modules that import `tests.*`. It does not come from this branch and does not affect CI. A workaround that seeds the namespace first is in Evidence.

## Next step
Owner runs the stills (Owner steps above) and approves or asks for changes. After approval: visual QA on the stills, Gate 2, merge `task/p3-sets-art`, and delete the spike branch.

## Docs
- `assets/LICENSES.md`: done in this task.
- At close-out: CLAUDE.md Status (p3-sets-art done once approved); `.harness/status.yaml`. PLAN.md section 9 already names `assets/sets` (p3-plan close-out list); nothing else changes.

## Evidence
- `LOOM_TASK=p3-sets-art python -m pytest -q tests/visuals/test_sets_art.py`: 8 passed (7 sets plus acceptance).
- `ruff check .`: clean. `mypy --strict pipeline/`: no issues in 33 files. `python tests/docs_check.py`: passed.
- Full suite, with the repo's `tests` namespace seeded before pytest starts (to get around the site-packages shadow): `LOOM_TASK=p3-sets-art python -c "import sys,types,pathlib; t=types.ModuleType('tests'); t.__path__=[str(pathlib.Path('tests').resolve())]; sys.modules['tests']=t; import pytest; sys.exit(pytest.main(['-q','--tb=short']))"` gave 1677 passed and 237 skipped (heavy and not-yet-done tasks). That covers the other tests that read sets: `tests/visuals/test_router.py`, `tests/test_render_constants_visuals.py` and `tests/script/test_*_visuals.py`.
- The licence hashes match the committed blobs: `git cat-file blob 9d3d477:assets/sets/<id>.yaml` hashed for all 7 files.
- `spike/stills.py --dry` ran locally: it wrote 17 scene `.ass` files plus caption files and `order.txt` (5144 events in the 20 s push_in archive file). The `render.yml` sed extraction was run locally: 6 packages, all with hashes. No FFmpeg was run locally (CLAUDE.md).
