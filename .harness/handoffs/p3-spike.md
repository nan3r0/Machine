# Handoff: p3-spike (Architect)

## Goal
Answer the Phase 3 plan's open technical questions on the runner before p3-contracts locks anything (`.harness/handoffs/p3-plan.md`, "The look, and how it is built"):
1. Render time against the 600 s FFmpeg timeout.
2. All-libass (method A) or hybrid PNG layers plus libass (method B).
3. Smoothness, judged from frame strips.
4. Push-in jitter.

## Status
done.
- Owner decision 2026-11-25: **method A (all libass)**.
- M0 is satisfied by the spike stills.
- Branch `spike/p3-look` (head `9fc29f4`) is throwaway and never merged. Delete it once this handoff is on main.

## What changed
- **Throwaway branch only:**
  - `b2c3898` puts the `anullsrc` input before `-vf`.
  - `9fc29f4` draws layer PNGs with `subtitles=...:alpha=1`. Run 45715145598 had shown every layer fully transparent. It also adds a per-layer alpha check and a strip of 8 consecutive full-resolution frames.
- **This branch (`docs/p3-spike`):**
  - this handoff;
  - `p3-plan.md` and the phase 3 YAMLs updated for method A;
  - the orchestrator State block.

## Results (run 45719091226, ubuntu-latest, apt FFmpeg)
The test video was 70 s: 10 scenes of 7 s and 2 sets of 3 layers. It had the host (bob, blink, arm wave, a mouth on every word), one counter scene, one bar scene, and captions with fake 0.4 s words.

| | Method A, all libass | Method B, PNG layers plus libass |
|---|---|---|
| Render time | **64.1 s**, one FFmpeg call | **139.8 s** in total: 6 layer PNGs at about 0.2 s each, 10 segments at about 10.7 s, concat 0.08 s, final libass pass 31.8 s |
| mp4 size | 4.97 MB | 4.89 MB |
| Share of the 600 s per-call timeout | 11% | longest call (final pass) 5% |
| Layer alpha | n/a | all 6 layers 1.0 (the fix works) |
| Stills | as expected, nearly the same as B | as expected |
| Motion (owner watched both mp4s) | **clearly smoother** | visibly less smooth |
| `a.ass` size | 2564 Dialogue events | |

The `a_strip30.png` strip (8 consecutive frames from 10 s) shows the arm rotating in even steps, the bob, and the mouth. Nothing jumps between neighbouring frames.

## Why method A
- It is twice as fast: 64 s against 140 s.
- It makes one FFmpeg call instead of 18.
- The owner judged it smoother. libass places and scales shapes with subpixel precision, while B's per-frame `scale` and `crop` round to whole pixels.
- It is simpler: no PNG files, no segment concat, and no second FFmpeg adapter.

Cost: every set shape is redrawn on every frame, so render time grows with the number of shapes. The numbers below keep that bounded.

## Camera under method A (what the spike did, and what is open)
- **Parallax.** Each set layer's shapes get `\move(x0,0,x1,0)` over the scene, where x1 = x0 minus the depth's speed times the scene length. The spike used 6, 14 and 30 px a second for far, mid and near. Layers are drawn 120 px wider than the frame on each side, so the drift never shows an edge.
- **Push-in.** Each shape gets `\org(540,960)` and `\t(0,<scene ms>,\fscx108\fscy108)`, which is 8% over a 7 s scene. It is smooth in the strip and in the owner's view.
- **Fades.** A full-frame black shape fades out over 0.3 s at each scene start.
- **Still open, for p3-contracts:**
  1. Every layer pushes in at the same rate. Depth-dependent zoom (near layers zoom more) is untested. Recommend leaving it out until someone asks for it.
  2. `pan_left` and `pan_right` were not tried. They are the same `\move` with a larger speed.
  3. Scenes can reach about 20 s. At 30 px a second the near layer would drift 600 px against a 120 px margin. Contracts must cap the drift distance per scene, not the speed. Drift = min(speed times length, margin).
  4. The host overlaps the caption band: captions at y 1230, host body down to y 1330. Contracts must place the host so that its feet sit above the caption band, or scale it down. Visual QA checks it.
  5. A Flux painting in slice 2 is a still image under the libass layer. It would get its push-in from FFmpeg, not libass, so the pixel stepping seen in B could come back for that layer only. Test it in the slice 2 spike.

## Numbers p3-contracts needs
These are proposed; p3-contracts locks them in `pipeline/constants.py`.

| Constant | Proposed | Why |
|---|---|---|
| Render budget | the compose call must stay under half of `COMPOSE_TIMEOUT_S`. The spike used about 11% for 70 s | Headroom for a 90 s video, more shapes and a busy runner |
| Set layers | 2 to 4 per set | The spike used 3. Each layer adds shapes on every frame |
| Shapes per set | at most 25 in total | The spike sets had about 10 to 12. Cost grows with the count |
| Drift speed, far, mid and near | 6, 14 and 30 px a second, capped at the layer margin per scene | From the spike, and the owner found it smooth |
| Layer margin | 120 px a side (layers 1320 px wide) | From the spike |
| Push-in | 8% per scene, centred on (540, 960) | From the spike |
| Scene fade | 0.3 s | From the spike |
| Blink | 0.2 s, every 3.6 s, first at 2.2 s into a scene | From the spike. Deterministic |
| Bob and arm swing | 10 px and ±15 degrees, on 0.4 s half-cycles | From the spike |
| Caption y | 1230 (inside the locked maximum of 1248) | From the spike. The host moves up to clear it |
| Shapes for the counter | one event per 0.1 s step, 30 steps | 31 events per counter, well within the budget |

A heavy acceptance test should assert the render time against the budget, so a slow change shows up in CI.

## Carried into p3-plan.md and the YAMLs (this branch)
- **Method A replaces the hybrid.** The set layers become animated libass shapes in the same `scenes.ass` as the host and the cards.
- **p3-background is deferred to slice 2** (Flux image layers need FFmpeg). Its YAML is removed so it cannot be launched by mistake; the slice 2 plan writes it again.
- **p3-compose** depends on p3-contracts again, and it chains only `subtitles=scenes` then `subtitles=captions`.
- **p3-sets-art:** no PNG wording.
- **p3-wiring:** writes only `scenes.ass`.
- **p3-router:** adds the set layers.
- **p3-contracts:** no `background.py` stub.

## Decisions made
- Method A, owner decision 2026-11-25 (above).
- p3-background's YAML is removed and its job moves to the slice 2 plan, which needs an image-layer path anyway. `p3-plan.md` records this.

## Tried and abandoned
- Method B: slower and less smooth (above).
- The FFmpeg `alphaextract,signalstats` alpha check: a range conversion reads zero alpha as 16. It was replaced by a direct PNG check.

## Known risks
- **Render time grows with the shape count.** It is bounded by the caps above and a timed heavy test.
- **The host overlapped the captions in the spike.** Placement goes into contracts and visual QA.
- **The Flux layer push-in may step (slice 2).**

## Next step
1. Owner: push `docs/p3-spike` and merge its PR. Then delete `spike/p3-look` on origin and locally, together with the `spike-p3-look` worktree.
2. Orchestrator: launch p3-character-art. Its still sheet uses method A.

## Docs
- `p3-plan.md` and the phase 3 YAMLs are updated here.
- `.harness/handoffs/orchestrator.md` State is updated here.
- PRD.md section 7 records the method A decision when p3-contracts writes the owner's p3-plan answers (already in its YAML).
- Nothing else.

## Evidence
- `results.json` from artifact `spike` of run 45719091226, read from the orchestrator's download (not downloaded again).
- `a_strip30.png` viewed.
- The owner watched both mp4s.
- After the edits:
  - `python tests/docs_check.py`: passed.
  - `pytest .harness/tests -q`: 90 passed.
  - `pytest -q tests` without `LOOM_TASK`: 1656 passed, 92 skipped, run with the sibling worktree venv (lessons.md 2026-11-15, the `tests` package shadowing).
  - All 18 phase 3 YAMLs parse, and every `depends_on` names an existing task.
