# Handoff: p3-spike (Architect)

## Goal
Answer the Phase 3 plan's open technical questions on the runner before p3-contracts locks anything (`.harness/handoffs/p3-plan.md`, "The look, and how it is built"):
1. Render time against the 600 s FFmpeg timeout.
2. All-libass (method A) or hybrid PNG layers plus libass (method B).
3. Smoothness, judged from frame strips.
4. Push-in jitter.

## Status
partial, awaiting the owner's render.yml dispatch. The fixed spike is commit `9fc29f4` on local branch `spike/p3-look-fix`, a fast-forward of `origin/spike/p3-look` (07e7f11, then b2c3898, then 9fc29f4). Not pushed: pushing needs the owner's go-ahead. The branch is throwaway and never merged.

## What changed
Only the throwaway branch:
- `b2c3898`, made in the other worktree (`spike-p3-look`): `spike/spike.py` puts the `anullsrc` input before `-vf`. This fixes `Option vf ... cannot be applied to input url anullsrc` in a_render and b_final.
- `9fc29f4`, made in this session:
  - Layer PNGs are drawn with `subtitles=...:alpha=1`. If this FFmpeg has no alpha option, the spike falls back to drawing on magenta and keying it out with `colorkey`.
  - Each layer is checked for a non-zero alpha, and the method fails loudly if a layer is empty.
  - A second strip of 8 consecutive full-resolution frames (crop 360x640 at x 360, y 560, from 10 s) shows stepping between neighbouring frames.

## Findings so far (run 45715145598, both methods failed at the final call)
- **Method B's background path works on the runner's FFmpeg.**
  - All 6 layer PNGs rendered, in 0.15 to 0.34 s each.
  - All 10 scene segments (7 s each, 3 overlays with x(t) and `scale` with `eval=frame` plus `crop`) rendered, in 11.9 to 12.7 s each, about 122 s for 70 s of background.
  - The concat took 0.08 s.
  - So per-frame `scale` and `crop` is accepted and per-scene segments work. That leaves about 480 s of the 600 s budget for the final libass pass.
- **A second bug the first fix alone would not have caught:**
  - Every layer PNG in that run was fully transparent (alpha max 0, checked by decoding the artifact).
  - libass paints only RGB unless the subtitles filter gets `alpha=1`.
  - Method B would have "worked" with an empty background. 9fc29f4 fixes this and checks for it.
- **Method A** never reached libass, so it has no timing yet.

## Dispatch (owner, Actions page)
1. Push `spike/p3-look-fix` to `origin/spike/p3-look` (a fast-forward), or tell the orchestrator to.
2. Actions, then **render**, then **Run workflow**:
   - Branch: `spike/p3-look`.
   - Input `script`: leave the default. The spike workflow ignores it.
3. Artifact `spike` (kept 3 days) holds:
   - `results.json`: per-call seconds and exit codes, `a_total`, `b_total`, the mp4 sizes and each layer's alpha check;
   - `a.mp4` and `b.mp4`;
   - stills `a_story.png`, `a_counter.png`, `a_lamp.png`, `a_bars.png` and their `b_` versions;
   - strips `a_strip.png` and `b_strip.png` (8 frames 0.25 s apart);
   - strips `a_strip30.png` and `b_strip30.png` (8 consecutive frames at full resolution);
   - FFmpeg logs.

## Still to answer from that run
| Question | Read from | Pass bar |
|---|---|---|
| Render time | `results.json`: `a_render`, every `b_*`, `b_total` | Each FFmpeg call well under 600 s. The plan wants headroom; real renders add voice and alignment time (Phase 1 baseline 125 s for 69.6 s of video) |
| A or B | totals, stills, strips | Pick the faster method that looks as good. B is expected to win because static layers are drawn once |
| Smoothness | `*_strip.png`: blink, mouth, arm wave | No missing or frozen frames, no flicker at the scene fade |
| Push-in jitter | `*_strip30.png` | Even spacing between neighbouring tiles. `scale` with `eval=frame` rounds to whole pixels and can step. If it does, fallbacks are a lower push rate, pan only, or a larger supersampled layer |
| Layer alpha | `*_alpha_max` in `results.json`, `*_colorkey` calls | 1.0 for every layer. A colorkey call means `alpha=1` is missing, and magenta fringes need checking in the stills |

Then this handoff gets the numbers, the chosen method, the proposed constants for p3-contracts (panel and character placement, caption y, drift speeds, push-in rate, fade and blink timings), and the M0 stills for the owner. Status then becomes done.

## Decisions made
- Kept the spike throwaway and dispatch-only. No new tool or package: the alpha check decodes the PNG with the standard library only (zlib).

## Tried and abandoned
- FFmpeg `alphaextract,signalstats` for the alpha check. The gray-to-YUV range conversion makes a zero alpha read as 16, so it was replaced by a direct PNG check. That check was verified on the transparent artifact layer (0.0) and on a synthetic PNG with one opaque pixel (1.0).

## Known risks
- If the runner's FFmpeg lacks the subtitles `alpha` option, the colorkey fallback can leave magenta edge fringes. The stills show it.
- 5 lines over the ruff length limit predate this change. The branch is never linted by CI (no PR) and is never merged.

## Next step
1. Owner: push the fix (step 1 above) and dispatch.
2. Orchestrator: hand the artifact to a fresh p3-spike session, or this Architect, to finish this handoff.

## Docs
none (throwaway spike; findings go to p3-contracts through this handoff).

## Evidence
- `gh run view 45715145598 --log-failed`: both failures were the `-vf` option order.
- The artifact of that run, downloaded: the timings above, and every layer PNG had alpha max 0.
- Locally: `python spike/spike.py --dry` exit 0. `ruff check spike/spike.py` shows 5 pre-existing E501, none new. The alpha checker was tested on the real and synthetic PNGs above. FFmpeg was not run locally (CI only, per CLAUDE.md).
