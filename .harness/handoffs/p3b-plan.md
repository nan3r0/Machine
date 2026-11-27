# Handoff: p3b-plan (Architect)

## Goal
Diagnose the two defects the owner found in the first M1 render (PR #206, render.yml run 45917646665 on `queue/approved/sample-65s.json`) and plan the fixes as small tasks with locked tests: (1) the host stands too high, (2) the mouth does not match the voice.

## Status
done (plan, contracts and locked tests). Three tasks are ready: p3b-host-placement and p3b-host-lipsync can run in parallel now. p3b-lipsync-wiring waits for PR #206.

## Diagnosis

### Defect 1: the host looks too high. Cause: push_in zooms from the set's top-left corner
- **The host is placed as designed.** I measured boot pixels (`6B4226`) in the run's golden frames. The lowest boot row is y 1009 to 1019 in every frame, which is HOST_GROUND_Y 1020 minus the 0 to 10 px idle bob. The hair top is about y 336 to 345, against a design value of 338. The numbers in the report (feet 965, head 225) do not match any frame.
- **The \an7 hypothesis is wrong for the host.** libass draws a `\p1` drawing with its (0,0) at the `\pos`/`\move` point and scales its coordinates from there. `host_origin()` already allows for that, so `pos + HOST_SCALE * ground` lands on 1020. Nothing in character.py needs to change.
- **The real anchor bug is in sets.py push_in.** `\org` sets only the rotation centre, so `\org(540,960)` has no effect on `\fscx`/`\fscy`. Each set layer therefore scales about its own `\move` point, which is the top-left corner (0,0) plus the drift. The set grows down and to the right, and its ground slides down under a host who stays put.
- **Evidence for the push_in bug.** shore_night has the moon at art y 420 and the sand top at art y 960. At 40 s the scene is a pan (scale 1) and they are drawn at y 420 and about 960. At 60 s the scene is a push_in, 7.5 s into an 11.42 s scene, so the scale is 1.0525:
  - The moon is at y 441. Scaling about the top-left gives 420 × 1.0525 = 442; scaling about the centre would give 392.
  - The sand top is at y 1010. Top-left gives 960 × 1.0525 = 1010; the centre would give 960.
  - At the scene end (S = 1.08) the sand top reaches 1037. The host's feet stay at 1020, so he ends up standing on the foam and sea instead of the sand. That is the "about 55 px too high" look.
- **Question for the owner.** The caption named in the report ("Laboratory kept listening.", 37.7 to 39.8 s) falls in a pan scene (35.14 to 45.12 s). At 40 s in that scene the feet measure y 1017 and sit on the sand. Was the frame you measured from a push_in scene (2.4 to 20.7 s, 30.8 to 35.1 s or 45.1 to 63.9 s)? Or do you want the host lower or smaller in story scenes as a design change? That second option would mean changing the HOST_* constants, which is a different task.
- **The fix is exact.** `\move` and the linear `\t` scale both run over the same window. Move the anchor from (0,0) to `(dx + W/2·(1−S), H/2·(1−S))` and the frame centre stays fixed, apart from the drift. Coverage stays safe because scaling about the centre only grows the art outward. I checked this fix locally against the new tests (15 passed), then reverted it.

### Defect 2: lip sync. Cause: one static mouth per whisper word
How `host_events` works today:
- The window is cut at every word edge.
- While a word is spoken, one talking mouth shows for the whole word. It is chosen by cycling the word index through `talking_mouths` minus "rest".
- Between words the pose's own mouth shows.
- There is no audio input and no timing offset (compose does not delay the voice).

Why this looks wrong:
1. **The mouth is held open for whole words.** Whisper words usually touch (end == next start), so the mouth never closes within a sentence. It just swaps shapes at word edges, and the shape choice is effectively random.
2. **Whisper timings are loose against the sound.** "listening." runs to 39.78 s, but the RMS of voice.wav is 0 from about 39.2 s. So the mouth stays open through about 0.5 s of silence. In the 1.0 s golden frame, "the" is highlighted while the mouth is closed.
3. **Some poses hold an open mouth through every pause.** wave (`wide`), point (`open`) and surprised (`o`) do this, including the 2 s SCENE_TAIL_S after the last word of the outro, which uses wave.

## Lip-sync options compared
| | A: voice loudness (recommended) | B: syllables from the text |
|---|---|---|
| Input | RMS of voice.wav per 40 ms window, normalised | vowel groups per word, spread over whisper word spans |
| Silence and pauses | closed, because it follows the real sound | still open wherever whisper spans run into silence (fault 2 above) |
| Rhythm | follows the real syllable energy | even and guessed; a word like "1947" counts as one syllable |
| Shapes | by loudness: open (small), o (round), wide | by vowel letter |
| Cost | stdlib `wave` plus numpy (already approved, spec.md section 7); needs wiring through router and render_one | character.py only |

I recommend A. B cannot fix the mouth being open during silence, and that is the owner's main complaint. A dry run on this render's voice.wav, using the prototype state machine with the constants below, gave:
- 4.9 openings a second over the whole video, pauses included
- the mouth open 49% of the time
- all three open shapes used (124 open, 116 o, 98 wide)
- the mouth closed from 39.04 to 39.8 s, the silence after "listening."

Bilabial closure (m, b, p) is skipped. Loudness dips already close the mouth on those sounds.

## What changed
- `pipeline/constants.py`: added MOUTH_WINDOW_S, MOUTH_LEVEL_PERCENTILE, MOUTH_OPEN_LEVEL, MOUTH_CLOSE_LEVEL, MOUTH_HOLD_S, MOUTH_OPEN_MAX_S, MOUTH_SHAPES and HOST_CLOSED_MOUTHS. These are tuning knobs; the starting values come from the dry run above.
- `pipeline/visuals/character.py`: the `host_events` docstring now holds the new mouth contract. A keyword-only `levels` parameter is added as a stub and is ignored for now.
- `pipeline/visuals/router.py`: `build_scenes_ass` gains a keyword-only `levels` parameter as a stub, and its docstring says to forward it.
- `pipeline/visuals/sets.py`: the docstring now holds the push_in contract (the scale anchor moves; `\org` is not a scale pivot). The code is unchanged.
- `pipeline/voice/levels.py`: new stub `voice_levels(wav)` with its contract. It raises NotImplementedError.
- New locked tests:
  - `tests/visuals/test_push_in.py` (p3b-host-placement)
  - `tests/visuals/test_host_lipsync.py` (p3b-host-lipsync)
  - `tests/voice/test_levels.py` and `tests/test_lipsync_wiring.py` (p3b-lipsync-wiring)
- Relaxed existing tests, so they pass on both the current code and the fixed code:
  - `test_sets.py`: the push_in `\move` y0 == y1 and drift checks, and the `\org` check, are removed, because `\org` is not the pivot.
  - `test_character.py`: the "talking mouth at the word midpoint" check is now "a talking mouth at some point inside each word".
  - `test_render_one_visuals.py`: the fake `build` accepts `**kwargs`, so PR #206 still passes and so will the wiring.
- Tasks: `.harness/tasks/phase3/18_host_placement.yaml`, `19_host_lipsync.yaml` and `20_lipsync_wiring.yaml`.

## Decisions made
- **The placement fix lives in sets.py, not character.py.** p3b-host-placement keeps its id, but its paths_allowed is sets.py only.
- **The mouth is closed in silence for every pose**, using the pose mouth if it is closed and "rest" otherwise. This overrides the open default mouths of wave, point and surprised. Owner: say so if you want those expressions kept during pauses.
- **`levels=None` falls back to the word spans** (level 1 inside a word). That keeps one code path and lets the lip-sync task land before the wiring.
- **The mouth is gated to [first word start, last word end]**, so a breath or click in the tail never opens it.
- **Event budget:** mouth runs are separate events. The body is not re-cut at mouth or word edges. A locked test caps body cuts.
- **New tests go in new files owned by the new tasks**, so main stays green. Old test files keep their owners.

## Tried and abandoned
- Writing a light test asserting the host's feet at HOST_GROUND_Y. It would pass on the current code, because the event math is right. The existing `test_same_anchor_in_every_scene` already guards this, so I added nothing.
- A heavy render test of feet placement. The golden-frame measurement settled the question without one.

## Known risks
- The MOUTH_* values are tuned on one voice and one render. The owner should look at the first render from p3b-lipsync-wiring, and the implementer reports any retune numbers.
- Whisper's first word can start up to about 0.2 s after the sound. The narration gate then cuts the very first syllable, which is minor. Gating on the voice alone would avoid it, but would let the tail click through.
- p3b-lipsync-wiring cannot start until PR #206 is merged.

## Next step
1. Orchestrator: run p3b-host-placement and p3b-host-lipsync in parallel. Their paths do not overlap.
2. After PR #206 is merged, run p3b-lipsync-wiring.
3. The owner dispatches render.yml on that branch and watches the mouth and a push_in scene.
4. Owner: answer the placement question above.

## Docs
- CLAUDE.md Status: add Phase 3b (host fixes: push_in centring and voice-driven lip flap) and its tasks.
- architecture.md section 7 (weak points): lip sync depends on MOUTH_* tuning, and libass scales `\p1` drawings about their `\pos` point, not `\org`.
- lessons.md: add an entry "\org is not a scale pivot in libass". p3-sets wrote push_in with `\org` and its locked test asserted `\org`, so nobody checked it in a render. Rule: any transform anchor gets a check against a rendered frame.
- workflow.md status table: the three p3b tasks.

## Evidence
- Artifacts from run 45917646665 were downloaded to a temp folder, and frames were measured with PIL (boot and hair rows; edge rows at x 60).
- With `LOOM_TASK` set, run through a sys.path shim because of the site-packages `tests` package (lessons 2026-11-15):
  - test_push_in.py: 5 failed. The centre ends at (541.2, 1036.8) instead of (498, 960).
  - test_host_lipsync.py: 12 failed and 3 guards passed. Failures are on assertions: open in silence, 0 to 1 openings instead of 16, held open past the cap, too many body cuts (32 > 28.25).
  - test_levels.py: 5 failed with NotImplementedError.
  - test_lipsync_wiring.py: 3 failed on assertions.
- Prototype fixes were applied locally and then reverted: sets.py gave 15 passed; character.py gave 27 passed (lip-sync plus character tests); levels.py gave 5 passed.
- Full suite without `LOOM_TASK`: 1803 passed, 147 skipped. `pytest .harness/tests`: 90 passed. ruff clean. mypy --strict pipeline/ clean (34 files). docs check passed.
