# Handoff: p3-character-art (Architect)

## Goal
Design the original host character as data (`assets/character/host.yaml`) and get the owner's approval from a still sheet rendered in libass on the runner (p3-plan "Character", D12; method A from p3-spike).

## Status
partial, awaiting the owner's still-sheet approval (round 1).
- Task branch `task/p3-character-art`: the asset, the licence row and this handoff. Committed, not pushed.
- Throwaway branch `spike/p3-character-sheet`: the task commit plus the sheet renderer and a `render.yml` override. Committed, not pushed, never merged.

## What changed
- **`assets/character/host.yaml`** (new). One frontal host at reference scale 1.0, in an art box of 609 x 822 px with the origin at the top-left (x right, y down).
  - `palette`: 16 named RGB hex colours. Every shape names its fill by key; `outline_colour` names the outline key.
  - `anchors`: `neck`, `shoulder_left`, `shoulder_right` (the arm rotation origins), `mouth`, `ground` (the point between the feet that sits on the floor).
  - `body`: always-drawn shapes (shadow, legs, boots, coat, coat details, scarf, ears, head, blush, glasses, hair, cowlick).
  - `eyes` (`open`, `closed`, `wide`, `up`), `brows` (`neutral`, `raised`, `furrowed`, `quizzical`), `mouths` (`rest`, `flat`, `open`, `wide`, `o`).
  - `talking_mouths: [rest, open, wide, o]`: the shapes lip sync cycles through.
  - `poses` (`talk`, `wave`, `point`, `surprised`, `think`, `shrug`): default `eyes`, `brows` and `mouth` keys plus `arm_left` and `arm_right` shape lists.
  - Every shape is the same record: `{layer, fill, outline, path}` plus an optional `alpha` (ASS hex, "00" opaque; only the shadow uses it). `layer` is the z order within the host (0 to 19, higher on top); list order carries no meaning. `outline` is the border width in px. `path` uses only `m`, `l` and `b` with integer coordinates, one closed contour per shape, so libass's fill rule never matters.
  - Layer bands: 0 shadow, 1 to 5 legs, boots, coat, scarf, 6 to 9 arms and hands, 10 to 19 the head and face. Arms sit over the coat and under the head, so the `think` fist tucks under the chin.
- **`assets/LICENSES.md`**: one row for `character/host.yaml` (own work), and the intro now says "font, art, music and SFX".
- **Throwaway branch only:**
  - `spike/draw_host.py`: the authoring helper that writes `host.yaml` (arm geometry from angles, mirrored left and right parts, the bounding-box shift). The YAML is the asset; this only saves hand maths. Keep it on the spike branch for the next round.
  - `spike/sheet.py`: checks the asset (colour keys resolve, poses name real variants, paths parse, every point and anchor inside the box), then renders with libass on a plain two-tone backdrop with a sample caption at y 1230.
  - `.github/workflows/render.yml`: overridden to install FFmpeg and PyYAML 6.0.3 and run the sheet (the same pattern as p3-spike; the file is outside `paths_allowed`, which is why it lives only on the throwaway branch).

## Design (originality)
No owner reference set is in the repo, so the comparison against the owner's references has not been done. **The owner does it on the sheet, and that check is part of the approval.**

What the design was built from, and what it avoids:
- **Silhouette:** big round skin-tone head with ears and a single cowlick, short legs, knee-length coat. Avoided: a blank white or featureless head, stick limbs and an animal mascot shape.
- **Face:** round glasses with opaque pale lenses (eyes drawn on them), blush dots, thick brows over the fringe.
- **Outfit and palette:** mustard anorak with a dark centre seam, two toggle buttons and pocket lines; a deep teal scarf with one hanging tail; charcoal trousers; brown boots; plum hair.
- **Risk to check:** round glasses with dark hair and a scarf can echo a famous boy wizard. The colours (plum, mustard, teal) are different, but the owner should judge. If it reads too close, the cheapest change is rounded-square lenses or no glasses.

## Owner steps (round 1)
1. Push the throwaway branch: `git push -u origin spike/p3-character-sheet`. Do not open a PR; it is never merged.
2. GitHub, **Actions**, **render**, **Run workflow**. Branch: `spike/p3-character-sheet`. Leave the `script` input at its default; the sheet ignores it.
3. When the run is green, open it and download artifact **`sheet`** (kept 3 days). It holds:
   - `sheet_poses.png`: the 6 poses at half size, 3 by 2, in the order of `order.txt`;
   - `poses_00.png` to `poses_05.png`: each pose at full 1080 x 1920 and its real place, with the feet at y 1150 above a sample caption at y 1230. These show the true outline weight;
   - `sheet_faces.png`: close-ups of every eyes, brows and mouth variant on the `talk` pose (13 tiles, 4 a row, order in `order.txt`);
   - `wave_swing.png`: the `wave` arm at both ends of the planned ±15 degree swing about the shoulder anchor (one opaque, one half transparent). It checks the anchor, not the look;
   - the `.ass` files and `order.txt`.
4. Tell the orchestrator: approved, or what to change (look, outfit, any pose or expression, resemblance to your references). A changed round edits `host.yaml` on `task/p3-character-art`, merges it into the spike branch and dispatches again.
5. After approval: delete `spike/p3-character-sheet` on origin and locally.

## Decisions made
- **Art box and placement.** Origin at the top-left of the bounding box of every shape in every pose, so all coordinates are non-negative. At scale 1.0 with `ground` at screen (540, 1150) the host spans y 348 to 1150 and x 261 to 870, clear of the caption band at y 1230 (spike open item 4). p3-contracts locks the screen placement in `constants.py`; the sheet uses (540, 1150) as the proposal.
- **Arms are drawn per pose, not rotated from one rest arm.** Bent arms (think, shrug, surprised) need an elbow, and ASS gives one rotation origin per event. Each arm still rotates as a unit about its shoulder anchor for the wave swing.
- **Extra variants beyond the YAML note:** `eyes.wide` and `eyes.up` (surprised, think), `brows.quizzical` (think), `mouths.flat` (think, shrug). Without them those poses read as the `talk` face. p3-contracts can drop any the owner does not want.
- **`talking_mouths`** names the lip-sync cycle in the asset, so the animation code does not hard-code mouth names.
- **Colours are RGB hex** (as people write them); the renderer converts to ASS BGR.
- **The sha256 in LICENSES.md is of the LF file** as committed. Git converts to CRLF on Windows checkouts, so a local hash there differs.

## Tried and abandoned
- Mitred one-piece sleeves for sharp bends (think, surprised): the mitre turns into a spike. Bends over 100 degrees now draw a rounded upper arm with the forearm over it.
- A full-length think arm (upper arm 100 px): the fist could not reach the chin. The think upper arm is 60 px, which reads as pointing at the camera.
- Glasses as transparent rings: libass border behaviour under a transparent fill is uncertain, so the lenses are opaque pale shapes with the eyes drawn over them.

## Known risks
- **Not yet seen in libass.** The design was iterated with a rough local Pillow preview (not committed). The runner render is the first real look: outline weight, joins and anti-aliasing may differ.
- **Resemblance** (above): the owner's reference check is still open.
- **`size` is the bounding box of path points;** outlines reach up to 6 px past it. Placement leaves room for that.
- **Shape count:** a pose is 41 to 45 shapes, against about 20 for the spike host. Each shape is one event per animation segment, so p3-character should keep segments long or merge static parts. The timed heavy test from p3-spike catches a slow render.
- **`render.yml` on the spike branch** pins setup-python by SHA but installs PyYAML by version, not hash. Acceptable for a throwaway branch that has no secrets and no write token.

## Next step
1. Owner: steps 1 to 4 above.
2. On approval: the orchestrator records it here (date and words), sets the status to done, recomputes the sha256 row if `host.yaml` changed, and merges `task/p3-character-art` (asset, licence row and handoff only).
3. Then p3-contracts writes `pipeline/visuals/art.py` to fit this file. Field names map one to one: a `Shape` record, a `Pose` record and the top-level `HostArt`.

## Docs
- `assets/LICENSES.md`: done here (row and intro).
- At close-out: CLAUDE.md Status line "p3-character-art done" once approved; `.harness/handoffs/orchestrator.md` State.
- spec.md file tree: add `assets/character/host.yaml` (p3-contracts, with the model).
- Nothing else.

## Evidence
- `python spike/draw_host.py` regenerates the committed `host.yaml` byte for byte (sha256 `412b8ad8...5b33`).
- `python spike/sheet.py --dry`: the structural check passed and all 20 `.ass` files were written (6 poses, 13 face variants, 1 swing).
- `yaml.safe_load` of `host.yaml` gives the keys listed above.
- Local Pillow preview of all 6 poses, 5 mouths and the closed eyes was viewed (rough, not libass).
- `python tests/docs_check.py`: passed. `pytest .harness/tests -q`: 90 passed.
- No FFmpeg run locally (CLAUDE.md); the runner render is the owner step.
