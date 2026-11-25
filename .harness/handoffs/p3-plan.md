# Handoff: p3-plan (Architect)

## Goal
Plan Phase 3 (visual templates) as a task graph. Today every video is the voice plus word captions on a solid dark background (PRD.md section 7, 2026-11-15). The owner wants animation before go-live, and has approved a direction from a browser mock (`style-preview.html`, HTML/SVG/CSS, not the real renderer).

The target look:
- An original round-head cartoon character.
- Flat layered sets that drift in parallax under a slow camera push.
- Bold word-by-word captions in the lower half.
- Data scenes (counter, bars, timeline, place card) as secondary templates.
- Painted backgrounds (Cloudflare Flux) come later, behind the same layer interface.

PLAN.md section 11 sets Phase 3 done as "two videos on similar topics look clearly different".

## Status
done, revision 2, approved by the owner on 2026-11-25: D1 to D7 and D10 to D13 (D8 and D9 wait for slice 2). Plan and task YAMLs only: no code, no locked tests. Next: p3-spike.

## What changed
- Revision 2 replaces revision 1, which had motion-graphics cards only. The character and the sets come first now, and the data cards become secondary.
- `.harness/tasks/phase3/`: 18 task YAMLs, 00_spike to 17_phase_review.
- The implementer YAMLs list only their new test files. tests/conftest.py gives a test file to the last task YAML (in sorted path order) that lists it, so listing an existing file would skip it on main until the task is done. Existing tests that must keep passing are named in each task's notes.

## The look, and how it is built with no new dependency
Each video has three layers, back to front:

| Layer | What | How (hypothesis, the spike confirms) |
|---|---|---|
| 1. Set | 2 to 4 flat layers (sky, far hills or wall, near floor or props), drifting at different speeds, slow push-in, fade between scenes | Each set is vector art in `assets/sets/<id>.yaml`. FFmpeg draws each layer once to a transparent PNG through libass, then moves the layers with `overlay` (x changes over time) and pushes in with `scale`/`crop`. A Flux painting later slots in as one more layer PNG |
| 2. Character and data cards | The character with poses and expressions; the counter, bars, timeline and place card | One animated `scenes.ass`, drawn by libass: `\p1` vector shapes, `\move`, `\t` with `\fscx`, `\fscy` and `\frz`, and `\fad`. Mouth shapes switch on each word's timing, so the character talks with the narration. Blinks are short events |
| 3. Captions | Bold, white, black outline, current word highlighted, lower half | Already built. Only the y position moves, inside the locked safe-zone range |

Why no cairosvg, rsvg, matplotlib or Pillow: each needs owner approval and the hashed render lock, which broke five times on 2026-11-25. libass and FFmpeg are already on the runner. If the spike shows they cannot do it smoothly in time, that becomes a new owner decision, not a quiet workaround.

The open technical questions, all answered by **p3-spike** on the runner before anything is locked:
1. **All-libass or hybrid.** Does it render faster with everything in libass, or with sets as pre-drawn PNG layers moved by FFmpeg and libass for the character only? I expect the hybrid to win, because animated full-screen libass shapes get redrawn on every frame.
2. **Render time** of a 70 s video against the 600 s FFmpeg timeout, and filtergraph size: about 10 scenes with 3 layers each. One graph, or per-scene segments joined with concat?
3. **Smoothness.** How much the character can move in libass without visible stepping: arm wave with `\frz` and `\org`, a bob, a blink, mouth swaps.
4. **Push-in.** Is it smooth with `scale` and `crop` evaluated per frame? `zoompan` is known to jitter.

## Character
- **One original character, a recurring host.** Round head, simple body, a fixed outfit and fixed proportions on every video, for recognition and consistency. It must not resemble any existing creator's character; the reviewer checks this against the owner's references.
- **Art is data:** `assets/character/host.yaml` holds the ASS drawing paths per part (head, hair, eyes open and closed, brows, mouth shapes, arms per pose, body), colours and anchor points. It is loaded through a small Pydantic model. Art coordinates are art, not rules, so they live in the asset, like a font. Timings and sizes on screen stay in `constants.py`.
- **Poses** (proposed, the owner approves on the still sheet): `talk` (the default), `wave`, `point`, `surprised`, `think`, `shrug`.
- **Always on:** blink, a small idle bob, and the talking mouth synced to the word timings while the narration plays.
- **Owner approves a still sheet first** (task p3-character-art): every pose and expression, rendered on the runner, before any animation code is written.

## Sets
- **Proposed starting list** (the owner approves the names before contracts and the art later): `night_street`, `desert_rail`, `lamp_room`, `shore_night`, `forest`, `archive`.
- Each set is 2 to 4 layers with a depth (far, mid or near) that sets its drift speed.
- **One layer interface:** a layer is a transparent 1080-wide-or-wider PNG plus its depth. Flat sets produce their PNGs from vector art. In slice 2, a Flux painting is one more far layer. The compose step does not care which.

## Scene format (script JSON, no schema change)
Every scene already has `visual: {"type": "chart" | "map" | "steps" | "story", "data": {...}}`. Phase 3 defines what `data` may hold. All keys are optional:

| Key | Values | Default when missing |
|---|---|---|
| `set` | one of the approved set ids | the template's default set |
| `pose` | one of the approved poses | `talk` |
| `camera` | `push_in`, `pan_left`, `pan_right`, `still` | `push_in` |
| `items` | 1 to 4 `{label, value}`, for data scenes | none |

- **`story`** is the main template: the character in a pose on the set. `on_screen_text` stays off screen in slice 1, because the captions already carry the words. Fewer published fields means fewer checks.
- **`chart`, `steps` and `map`** are secondary. They show the data card over the set, dimmed, with the character hidden:
  - `chart`, 1 item: a counter.
  - `chart`, 2 to 4 items: bars.
  - `steps`: numbered steps or, with years as values, a timeline.
  - `map`: a place card.
- **Fallbacks so old scripts render:**
  - `data: {}` (every Phase 2 script) becomes the template's default set, `talk` and `push_in`.
  - A data type with no items falls back to `story`.
- **Consistency across scenes:**
  - One character asset and one palette per set, so lighting stays the same within a set.
  - Scenes change with a short fade. The set changes only where the script says.
  - The character stands in the same spot in every scene, so it never jumps.

## How the script writer changes (pipeline/script/)
- **Same single Gemini writer call, 0 extra requests.** The free-tier limit is requests a day, and that does not change.
- **`_WRITER_SCHEMA`:** each scene gains flat fields `visual_type`, `set`, `pose`, `camera` (all enums) and `items` (`{label, value}` strings). No `anyOf`, and caps are checked in code.
- **`_VISUAL_RULES` paragraph in the prompt:**
  - Choose a set that fits the place and mood.
  - Keep the same set across consecutive scenes in one place.
  - Choose a pose that fits the line, `surprised` at a reveal for example.
  - Use data scenes only for numbers, dates or places that appear in the facts.
- **A broken visual becomes the fallback in code**, with no retry.
- **`validate.py`** checks the enums and the item caps, and runs the published-field text rules on every label and value.
- **`batch.py`** shows each scene's set, pose and items in the PR body, in code spans. It also runs the exact check on every item label and value against the scene's cited facts. On a miss the scene is flagged and its data card replaced by a story scene (D4).

## Milestones the owner can see
- **M0, after p3-spike and p3-character-art:** stills from the runner. One rough set with the character from the spike, then the character's full pose sheet for approval.
- **M1, after p3-wiring:** two `render.yml` dispatches on the task branch, on `sample-65s` and on a demo script with data scenes, each with a `frames` artifact. `render.yml` does not change.
- **M2, after p3-writer-visuals and p3-batch-visuals:** the owner's first Workflow A run (R13.5) opens a PR whose scripts choose sets and poses.

## Task graph (slice 1)
YAMLs in `.harness/tasks/phase3/`. At most two at once, and no shared paths within a wave. "Art" tasks are Opus (role `architect`) because they need design judgement. They change only `assets/**`, and each ends with an owner-approved still.

| # | Task | Role | Paths | Depends on |
|---|---|---|---|---|
| 00 | p3-spike | architect | throwaway `spike/p3-look` branch | none |
| 01 | p3-character-art | architect | `assets/character/**`, `assets/LICENSES.md` | p3-spike |
| 02 | p3-contracts | test_author | constants, `visuals/` stubs and art models, locked tests, fixtures, sample-65s data, docs | p3-character-art; owner approvals |
| 03 | p3-validate-visuals | implementer | `pipeline/script/validate.py` | p3-contracts |
| 04 | p3-ass-kit | implementer | `pipeline/visuals/ass_kit.py` | p3-contracts |
| 05 | p3-character | implementer | `pipeline/visuals/character.py` | p3-ass-kit |
| 06 | p3-background | implementer | `pipeline/render/background.py` | p3-contracts |
| 07 | p3-sets-art | architect | `assets/sets/**`, `assets/LICENSES.md` | p3-contracts |
| 08 | p3-cards | implementer | `pipeline/visuals/cards.py` | p3-ass-kit |
| 09 | p3-charts | implementer | `pipeline/visuals/charts.py` | p3-ass-kit |
| 10 | p3-compose | implementer | `pipeline/render/compose.py`, `pipeline/render/captions_ass.py` | p3-background |
| 11 | p3-router | implementer | `pipeline/visuals/router.py` | p3-character, p3-cards, p3-charts |
| 12 | p3-wiring | implementer | `pipeline/render_one.py` | p3-router, p3-compose, p3-validate-visuals, p3-sets-art |
| 13 | p3-writer-visuals | implementer | `pipeline/script/generate.py` | p3-validate-visuals |
| 14 | p3-batch-visuals | implementer | `pipeline/script/batch.py` | p3-validate-visuals |
| 15 | p3-cso | cso | `docs/threat-model.md` | p3-wiring, p3-writer-visuals, p3-batch-visuals |
| 16 | p3-qa-lead | qa_lead | none | p3-wiring, p3-writer-visuals, p3-batch-visuals |
| 17 | p3-phase-review | reviewer | none | p3-cso, p3-qa-lead |

Waves:
1. p3-spike, then **M0** stills.
2. p3-character-art. The owner approves the pose sheet.
3. p3-contracts on `plan/p3-contracts`. The owner merges it.
4. p3-validate-visuals and p3-ass-kit.
5. p3-character and p3-background.
6. p3-sets-art and p3-cards. The owner approves the set stills.
7. p3-charts and p3-compose.
8. p3-router.
9. p3-wiring, then **M1**.
10. p3-writer-visuals and p3-batch-visuals, then **M2**.
11. p3-cso and p3-qa-lead (reports dispatched after the close-out merges).
12. p3-phase-review.

Reviews:
- Visual QA: every task touching `pipeline/visuals/**`, `pipeline/render/**` or `assets/**`.
- Security: p3-background and p3-compose (FFmpeg argument lists), p3-validate-visuals and p3-batch-visuals.
- No Auditor in slice 1: the art is original and logged in `assets/LICENSES.md` as own work, and there is no new API.

**How visual QA judges stills:**
- Golden frames every 10 s, as now.
- p3-contracts adds a strip of 8 frames, 0.25 s apart, across one scene change and one blink. Stills cannot show motion, so the strip shows stepping, flicker and a broken fade.
- Checklist:
  - The character is whole, inside the frame and never under the captions.
  - It is the same character, the same size and the same place in every scene.
  - Captions are readable over every set.
  - Data values are readable.
  - Nothing important is in the platform UI zones.
- The owner watches the M1 mp4 for real motion.

### Later slices (planned after their decisions; no YAMLs yet)
- **Slice 2, painted sets (Cloudflare Flux):**
  - A Flux image becomes one far layer of a set, through the same layer interface.
  - `pipeline/visuals/flux_cf.py`: standard-library client like `gemini.py`, refusing redirects, https on the Cloudflare host only, key never logged.
  - PNG or JPEG magic-byte, size and pixel checks.
  - A separate job holds the key (D8).
  - CSO and Auditor.
  - Before planning, read Cloudflare's current pricing and model pages.
- **Slice 3, b-roll:** deferred (D10). Real stock footage clashes with a cartoon look.

## Decisions made
These are my calls; the owner can overrule them. D ids here are p3-plan ids, not Phase 2's D1 to D8 in PRD.md.
- **No schema change.**
  - `visual.data` gets per-type rules in `validate.py`, as the threat model asks.
  - There is no `schema_version` bump, and Phase 2 scripts with `{}` stay valid.
  - `sample-65s` is migrated in p3-contracts after checking again that `origin/ledger` holds no record for it. On 2026-11-25 it held only `.gitkeep`.
- **Art lives in `assets/`, checked by a Pydantic model in `pipeline/visuals/art.py`** (a contract file from p3-contracts). Numbers that are rules stay in `constants.py`.
- **Imports.**
  - `pipeline/visuals/` may import `escape_ass_text` from `render/captions_ass.py` rather than copying it.
  - Inside `visuals/`, imports point one way: router to character, cards and charts; those to ass_kit; ass_kit to art.
  - No test enforces the import boundary (grep of `tests/`), so nothing locked changes.
  - Text is drawn only through ASS, never FFmpeg `drawtext`.
- **Compose** gets keyword-only arguments that default to today's behaviour, so the existing locked compose tests stay true. New behaviour is tested in new files. p3-contracts edits two existing locked tests so they hold both before and after the change: `tests/script/test_generate.py:112` and the fake compose in `tests/test_render_one.py:51`.
- **Scene timing** is a pure function in the router. It counts the words of the hook, each scene and the loop line and maps them onto the word timings. The hook and the loop line use the first and last scene's set, with the `talk` pose.
- **Captions keep the script's exact words and case.** The mock is all caps, but spec.md section 4 says a caption word never differs from the script word. Forced capitals would be a rule change (D11).

## Owner decisions
The defaults are what the YAMLs assume.

1. **D1. Character and flat sets first; Flux paintings later (slice 2), behind the same layer interface.** Recommend yes.
2. **D2. Captions in the lower half.** About y 1200, just inside the locked limit of 1248. The character stands above them. Recommend yes.
3. **D3. No new package for drawing.** libass plus FFmpeg only, chosen by the spike. If the spike fails, I come back with cairosvg or rsvg as a costed request (hashed lock and approval) instead of working around it. Recommend yes.
4. **D4. A data value the facts do not back:** flag it in the PR and replace the data card with a story scene automatically. Recommend yes.
5. **D5. `map` is a place card for now;** a real drawn map is deferred. Recommend yes.
6. **D6. Hold the first Workflow A run (R13.5) until M2.** Sources are single-use, and an earlier run would spend 7 of the 14 on scripts with only the default set and pose. Recommend yes.
7. **D7. Go-live waits for slice 1 (M1, M2) and the other R18 gates, not for Flux.** Recommend yes.
8. **D8. Where Flux paintings are made (slice 2).**
   - (a) In Workflow A, committed to the scripts PR. You see every image, but the public repo grows about 0.5 to 1 GB a year.
   - (b) In a separate Workflow B job holding the Cloudflare token as an environment secret (main only). You approve the prompt text, not the image.
   - Recommend (b).
9. **D9. Painted style matches the cartoon:** stylised, never photoreal, never a real identifiable person. Recommend yes.
10. **D10. B-roll (Pexels and Pixabay) is deferred out of Phase 3.** Real footage clashes with the cartoon look. This narrows PLAN.md section 11's Phase 3 line ("Chart + Flux + b-roll"). Recommend yes.
11. **D11. Captions keep the script's case** (the "caption equals script word" rule), rather than forced capitals as in the mock. Recommend yes; say if you want display-only capitals and the rule changes.
12. **D12. The character.**
    - One original host with a fixed outfit on every video.
    - Poses `talk`, `wave`, `point`, `surprised`, `think`, `shrug`.
    - You approve the still sheet from p3-character-art before p3-contracts.
    - Recommend yes. Name the character if you want one; it is never spoken.
13. **D13. Starting sets:** `night_street`, `desert_rail`, `lamp_room`, `shore_night`, `forest`, `archive`. You approve the names before p3-contracts and the stills in p3-sets-art. Recommend yes; add or swap names freely now, since later changes mean a contracts change.

## What the owner approves before p3-contracts
1. This plan: D1 to D7 and D10 to D13 (D8 and D9 can wait for slice 2).
2. The spike result: render time with headroom under the 600 s timeout, and the M0 stills look right. If not, the spike handoff brings a revised D3.
3. The character still sheet from p3-character-art: look, outfit and every pose and expression.
4. The set id list (D13). The set art itself is approved later, in p3-sets-art.
5. The PRD.md section 7 entries for these answers, written by p3-contracts.

## Cost in free-tier calls
| Slice | Gemini | Cloudflare | Actions |
|---|---|---|---|
| 1 | 0 extra requests (same writer call, a few hundred more output tokens) | none | Render time: the spike measures it, and I expect about 1 to 3 extra minutes a video. The repo is public, so minutes are not metered. If it goes private again: about 15 code and art tasks at about 8 CI runs of about 6 min each, roughly 700 minutes once |
| 2 | 0 extra | about 1 painting per set used, a few a day, against the free daily allowance (PLAN.md says about 170 images a day; unverified until the slice 2 plan reads the pricing page) | one small job a day |

## Risks
- **Render time and smoothness.** These are the biggest unknowns, which is why the spike comes before contracts. Fallbacks:
  - fewer moving layers;
  - per-scene segments;
  - a lighter push-in;
  - D3 revisited with the owner.
- **The character looks cheap or off-model between poses.** The still sheet is approved first, and visual QA checks consistency on every render task.
- **The character could resemble an existing creator's.** It is designed as original, reviewed against the owner's references, and logged as own work.
- **Inauthentic-content policy.** A recurring host, varied sets and per-script poses give more variety than cards alone. How YouTube judges this is still unverified.
- **A wrong number on screen.** Covered by the exact check, D4 and the PR body.
- **The PR body cap.** New fields grow the body, so caps are set by arithmetic in a locked test.
- **The model picks poor sets or poses.** The fallbacks are free, and the owner can edit the JSON in the PR.
- **Locked-test churn.** Two existing locked tests change so they pass before and after; p3-contracts runs the full suite without `LOOM_TASK`.
- **Heavy tests run only in CI.** Every render or art task waits for a run on a draft PR.

## Tried and abandoned
- **Revision 1**, motion-graphics cards only, with no character and no sets. Superseded by the owner's direction.
- **matplotlib, cairosvg, rsvg or Pillow** to draw: new dependencies (D3).
- **`geq` or `gradients` FFmpeg backgrounds:** `geq` is too slow at 1080x1920, and `gradients` depends on the FFmpeg version. Skies are flat bands, or soft-blurred bands in the layer art.
- **`on_screen_text` on screen in slice 1:** dropped, because the captions already carry the words. It stays in the schema, unrendered.

## Known risks
See Risks. Slice 2 has no YAMLs yet, so PLAN.md's Phase 3 done line closes only when it is planned, or narrowed by D10.

## Next step
1. Owner: done (2026-11-25, D1 to D7 and D10 to D13 approved).
2. Orchestrator: run p3-spike, then p3-character-art, then p3-contracts once the owner approves the items above.

## Docs
- Owed by p3-contracts:
  - workflow.md: a `### Phase 3 status` table (exact heading), the module order and criterion-to-test rows.
  - PRD.md section 4: R19 (scene data and fallbacks), R20 (layers, layout, timing), R21 (writer and PR body), R22 (M0, M1 and M2 manual checks).
  - PRD.md sections 3 and 7.
- Owed at slice 1 close-out:
  - architecture.md: sections 1, 2 and 4 (layers, the `visuals/` package, the art assets, the import exception).
  - spec.md: sections 2 to 4.
  - PLAN.md: section 11 (Phase 3 line, per D1 and D10) and section 9 (`assets/character`, `assets/sets`).
  - CLAUDE.md: Status.
  - PRD.md section 7: retire the 2026-11-15 "solid colour" assumption.
  - assets/LICENSES.md: rows from the art tasks.
- lessons.md: none.

## Evidence
- Read: PLAN.md, PRD.md, spec.md, architecture.md, lessons.md, HARNESS.md section 8, docs/threat-model.md sections 5 to 7, `pipeline/schema.py`, `constants.py`, `render/compose.py`, `render/captions_ass.py`, `render_one.py`, `script/generate.py`, `script/batch.py`, `render.yml`, `.harness/handoffs/p4-plan.md`, and the owner's mock `style-preview.html`.
- Checked:
  - No drawing library is in any requirements file.
  - `origin/ledger` holds only `.gitkeep`.
  - `out/` is git-ignored, so spike files go under `spike/`.
  - No test enforces import boundaries.
- `python tests/docs_check.py`: passed with these YAMLs.
- `pytest .harness/tests -q`: 90 passed.
- `pytest -q tests` without `LOOM_TASK`: 1656 passed, 92 skipped, with the revision 2 YAMLs.
- All 18 YAMLs parse, and their ids are unique.
  - Run with the venv of the sibling worktree `agent-a84cab27280eafe81`, because a site-packages `tests` package shadows the repo's `tests/` in the system Python (lessons.md 2026-11-15).
