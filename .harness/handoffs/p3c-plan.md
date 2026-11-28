# Handoff: p3c-plan (Architect)

## Goal
Re-plan Phase 3 (visuals) after the owner's M1 review on 2026-11-28. Owner direction, final:
1. Remove the host entirely: no intro, outro, mouth sync, bob or host sprite.
2. Scenes change with the story. Example: a whale story starts at the ocean surface, dives deep, then finds the whale. AI-painted stills (Cloudflare Workers AI flux-1-schnell, 4 to 8 per video) share one style prefix. Each scene has a slow Ken Burns zoom, and scenes join with zoom transitions.
3. Art overlays replace the boxed cards and bar charts: a counter or timer that ticks up, or a ring that fills, drawn over the painting with no box.
4. The script writer emits a per-scene image prompt. The validate step and the Gemini quota guard still hold. A fallback covers a Flux failure or used-up quota, at $0.
5. A deep male Kokoro voice, picked by the owner by ear, then re-pinned and re-measured.
6. The Cloudflare account and token are an owner step, stored as a repo secret. Update the threat model and runbook.

## Status
done (plan, task graph, and the contracts that do not depend on a spike), on branch `plan/p3c-dynamic-scenes`.
- Locked now: the Flux client contract (`pipeline/visuals/flux_cf.py` stub and `tests/visuals/test_flux_cf.py`), and the Flux and image constants in `constants.py`.
- Deferred on purpose: the render contracts (Ken Burns, transitions, overlays, router shots) wait for p3c-render-spike and owner gate G2. The voice and length contracts wait for p3c-voice-samples and gate G1. The script-side tests (validate, writer, PR body) are their own task, p3c-contracts-script, so that this session stays one session. All three are test_author tasks in the graph.
- Reason for the split: still images under Ken Burns use FFmpeg image filters. That is the method B ground which lost the p3 spike on smoothness and time (`.harness/handoffs/p3-spike.md`). Locking shot or transition numbers before a runner measurement would repeat the `\org` mistake (lessons.md, "\org is not a scale pivot").

## What changed
- `pipeline/constants.py`: FLUX_ENDPOINT, FLUX_STEPS, FLUX_TIMEOUT_S, FLUX_RETRY_WAIT_S, FLUX_PROMPT_MAX_CHARS, FLUX_IMAGE_MAX_BYTES, FLUX_RESPONSE_MAX_BYTES, FLUX_IMAGE_SIDE_PX, FLUX_STYLE_PREFIX (a proposal; the owner approves it at G2), IMAGE_PROMPT_MAX_CHARS, IMAGES_PER_VIDEO, FLUX_MAX_IMAGES_PER_BATCH. Nothing is removed yet.
- `pipeline/visuals/flux_cf.py`: a stub with the docstring contract (`generate_image`, `image_size`, `FluxError`, `FluxQuotaError`, `requests_sent`).
- `tests/visuals/test_flux_cf.py`: locked, owned by p3c-flux-client. Covered: request shape, secrets read at call time, account id format, prompt limits, one retry, the quota error never retried, no redirects (through the real opener's handlers), body and image caps, the JPEG header walk, and the token absent from every message and URL.
- `.harness/tasks/phase3c/`: 20 task YAMLs.
- Deleted unbuilt tasks that assumed the host, sets and poses: `phase3/13_writer_visuals.yaml`, `14_batch_visuals.yaml`, `15_cso.yaml`, `16_qa_lead.yaml` and `17_phase_review.yaml`, together with their locked tests `tests/script/test_generate_visuals.py` and `test_batch_visuals.py`. With their owners gone, those tests would have run on main and failed. phase3c replaces all five tasks.

## The look, and how a painted video is built
Each video is 4 to 8 paintings. Each one holds for one or more scenes, back to front:

| Layer | What | How |
|---|---|---|
| 1. Painting | One Flux still per picture, fitted to 9:16 | FFmpeg image inputs in the compose call. Ken Burns inside the shot (push_in, pan_left, pan_right, still), with a zoom transition at each picture change. The method and numbers come from p3c-render-spike |
| 2. Overlay | Counter, timer or ring, no box | libass events in scenes.ass (method A, unchanged): bold white text with a dark outline and shadow, the ring as a `\p1` arc stepped like the counter |
| 3. Captions | as now | unchanged |

Scene timing: spans run from 0 to the last word, contiguous. The hook belongs to scene 1 and the loop line to the last scene. With no intro and no outro, HOST_INTRO_MAX_S and the rest go.

Render budget: RENDER_BUDGET_S is 300 s for the compose call of a 90 s video. Method A drew about 2,500 to 8,100 events in 64 s. Stills add per-frame scaling: 2,700 frames at 1080x1920. A smooth zoom without whole-pixel stepping usually means upscaling the still once (2 to 6 times) before zoompan. The spike times that against the budget. If nothing fits smoothly, the spike stops and brings the owner a choice. It never adds a dependency quietly.

Fit, an open question for G2. The model returns a square (no width, height or seed in its input schema, read 2026-11-28). The options are F1, a centre crop scaled up about 1.9 times (painterly art hides the softness), or F2, the square over a blurred fill (PLAN.md section 3 wording). I expect F1 to look more immersive. The owner judges.

## Scene format (script JSON, no schema change)
`visual.data` per scene, all keys optional (locked by p3c-contracts-script):

| Key | Value | Rule |
|---|---|---|
| `image` | scene prompt, at most IMAGE_PROMPT_MAX_CHARS | Starts a new painting. A scene without one keeps the previous painting (the zoom continues). Scene 1 needs one whenever any scene has one. Validate enforces only the maximum, IMAGES_PER_VIDEO[1]. Fewer than IMAGES_PER_VIDEO[0] is valid and gets a PR flag from batch, because three paintings beat the flat fallback. The writer drops prompts past the maximum in code. Passes the published-field text rules (no URL, `<`, `>` or control characters), since it is shown in the PR body and sent to Cloudflare |
| `camera` | CAMERA_MOVES (push_in, pan_left, pan_right, still) | default push_in, kept from slice 1 |
| `overlay` | `{kind, label, value}` | kind in OVERLAY_KINDS. counter: a plain number with an optional `$` and a short unit; timer: whole seconds, shown as m:ss; ring: an integer 0 to 100 followed by `%`. The label is required. At most VISUAL_DATA_SCENES_MAX overlays per script |

- `set`, `pose` and `items` stop being allowed.
- `visual.type` and `template` stay in the schema. The painted path ignores them, and the set fallback reads DEFAULT_SET[template].
- An empty `data: {}` stays valid. Such a script renders on the set fallback.
- sample-65s is migrated in p3c-validate-images, after a fresh check that `origin/ledger` holds no record for it.
- A new fixture, `paint-demo.json`, replaces demo-data for the new rules.

Timer values are seconds rather than m:ss, so the exact check finds "72" in a fact that says "72 seconds".

## Script writer (generate.py, batch.py)
- **Still one writer call per script.** The free limit counts requests a day, and it does not change. WRITER_MAX_CALLS_PER_BATCH, GeminiQuotaError and GEMINI_MAX_CONSECUTIVE_ERRORS are untouched (the p4d guard holds).
- The writer schema gains flat per-scene fields: `image`, `camera`, `overlay_kind` (with "none"), `overlay_label` and `overlay_value`. There is no anyOf.
- Prompt rules: the pictures follow the places in the story; each one describes a place, objects, light and weather; never a named or real person; never text or signs; people only as distant silhouettes; the subject's words repeat across scenes. **The style prefix is added in flux_cf, never by Gemini**, so every painting shares it.
- A broken visual falls back in code with no extra call: the overlay is dropped, or the scene keeps the previous picture.
- batch.py:
  - The PR body shows each scene's prompt, camera and overlay as code spans.
  - The exact check runs on each overlay label and value. A miss is flagged and the overlay dropped (D4 kept).
  - A script with too few prompts is flagged.
- PR body arithmetic: 7 scripts × 8 prompts × 300 characters is about 17,000 characters. The overlays replace the 160-character items term. p3c-contracts-script re-proves the 60,000 cap.

## Paintings: where they are made (owner gate G4)
- **(a) Workflow A, recommended.** A `paint` job after `validate` holds only the Cloudflare secrets. It calls flux_cf once per prompt, at most 56 a batch, and commits `queue/images/<id>/<scene>.jpg` into the scripts PR.
  - You see every painting before you merge. That is the only $0 control for odd outputs and for text in images.
  - Workflow B (which holds the YouTube secrets) gains no new secret. render.yml reads the images from the checkout.
  - Cost: the public repo grows by about 6 MB a week, about 0.3 GB a year.
- **(b) Workflow B.** A daily job paints the day's script (p3-plan D8 recommended this before images were in scope).
  - Nobody sees the image before it is published.
  - It adds a third-party secret to the publishing workflow.
- My recommendation changes from (b) to (a), because the owner's own risks (odd outputs, text in images) need a human look at $0.
- Repo secret (owner item 6): I follow it. An environment secret limited to `main` would be stronger, because any branch workflow can read a repo secret. p3c-cso weighs it.
- A prompt you edit in the PR does not repaint its image. The runbook says so: delete the image file, and the scene keeps the previous picture, or the fallback is used.

## Fallback when Flux fails or quota runs out ($0)
- One image fails (any FluxError): that scene keeps the previous painting. The batch flags it in the PR, and there is no retry beyond the client's one.
- FluxQuotaError (the 10,000 neurons are used up; it resets at 00:00 UTC): the batch stops calling at once. The rest of the scripts have no images and are flagged.
- A script with no images at all renders on the **existing flat libass sets** (sets.py, built and tested), for the whole video. Paintings and flat sets never mix in one video.
  - The overlays still draw over the dimmed set. The set comes from DEFAULT_SET[template].
  - The owner can merge such a script, rerun the batch later, or drop it.
- No paid tier and no second image provider. A free fallback provider would be a new integration with its own CSO and Auditor work, so YAGNI until Flux fails in practice.
- The quota error body is not documented. The contract treats code 4006 or "daily free allocation" as quota. The spike records the real body if it can, and a wrong guess becomes a contract change.

## Voice (owner gate G1)
- Candidates at the pinned VOICE_REPO_REVISION, sha256 read from the HF tree on 2026-11-28 (LFS oid):

| Voice | sha256 |
|---|---|
| am_fenrir | 98e507eca1db08230ae3b6232d59c10aec9630022d19accac4f5d12fcec3c37a |
| am_michael | 9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37 |
| am_onyx | e8452be16cd0f6da7b4579eaf7b1e4506e92524882053d86d72b96b9a7fed584 |
| am_puck | dd1d8973f4ce4b7d8ae407c77a435f485dabc052081b80ea75c4f30b84f36223 |
| am_echo | 8bcfdc852bc985fb45c396c561e571ffb9183930071f962f1b50df5c97b161e8 |
| am_eric | ada66f0eefff34ec921b1d7474d7ac8bec00cd863c170f1c534916e9b8212aae |
| am_liam | c82550757ddb31308b97f30040dda8c2d609a9e2de6135848d0a948368138518 |
| bm_george | f1bc812213dc59774769e5c80004b13eeb79bd78130b11b2d7f934542dab811b |
| bm_fable | d44935f3135257a9064df99f007fc1342ff1aa767552b4a4fa4c3b2e6e59079c |
| bm_lewis | b5204750dcba01029d2ac9cec17aec3b20a6d64073c579d694a23cb40effbd0e |
| bm_daniel | fc3fce4e9c12ed4dbc8fa9680cfe51ee190a96444ce7c3ad647549a30823fc5d |

- am_adam (low quality) and am_santa (novelty) are left out.
- bm_* voices need VOICE_LANG_CODE "b", and the spike confirms it runs with the pinned packages.
- The weights file and repo revision stay the same; only one `voices/*.pt` entry changes.
- p3c-voice-samples synthesizes the full narrations of sample-65s, demo-data and two other texts with every candidate. That gives the owner mp3s to listen to and gives the length model its numbers in the same run, so no separate re-measure render is needed.
- p3c-contracts-voice then sets VOICE_NAME, VOICE_LANG_CODE, the hash, SPEECH_WPM, TIKTOK_WORDS and TARGET_WORDS. The 62 to 90 s rule and the 65 s target stay. VOICE_SPEED stays 0.9 unless you pick 0.85 by ear.

## Syllable check (backlog row, owner decision): recommend yes
- Kokoro's pace follows syllables and full-stop pauses, not words. demo-data passed the word rule at 163 words and rendered 56.6 s, under the 62 s floor.
- A QA failure after merge costs a publish day and burns a single-use source.
- The voice change forces a new measurement anyway, so syllables per minute and the pause per full stop come from the same spike run at no extra cost.
- The word range stays as a size cap. The length decision moves to the predicted seconds, syllables / rate + full stops × pause.
- Standard library only: a vowel-group count, with digits read as words through the existing normaliser.
- Tasks: p3c-contracts-voice (locked tests) and p3c-syllables (validate.py).

## Retiring the host
| Step | Task | What |
|---|---|---|
| 1 | p3c-plan (this) | Deleted the unbuilt host-shaped tasks 13 to 17 and their tests |
| 2 | p3c-contracts-render | Deletes `tests/visuals/test_character.py`, `test_host_lipsync.py`, `test_cards.py`, `test_charts.py`, `tests/test_lipsync_wiring.py` and `tests/voice/test_levels.py`. Rewrites `test_router.py` and `test_render_one_visuals.py` for p3c-router-paint. Drops the host rows of `test_render_constants_visuals.py` |
| 3 | p3c-router-paint | Deletes `pipeline/visuals/character.py`, `cards.py`, `charts.py` and `pipeline/voice/levels.py`, and their imports in router and render_one |
| 4 | p3c-retire-host (Architect, locked files) | Removes HOST_*, MOUTH_*, BLINK_*, bob and arm constants, POSES, DATA_PANEL and card colours, HostArt and load_host in art.py, `assets/character/` and `assets/sets/host_backdrop.yaml` |

- Deleting tests never turns main red. Removing constants before the code that imports them would, which is why constants go last.
- The done tasks' YAMLs (p3-character, p3b-*) stay, because status.yaml and docs_check need them. A YAML that names a deleted test file is harmless to conftest.
- Locked files change through these Architect tasks, so no CONTRACT_CHANGE.md is needed. The reason is the owner's direction of 2026-11-28, which retires the feature the tests describe, not a wrong test.
- Kept: `sets.py`, the six set assets, `SetArt` and `test_sets*.py`, as the fallback.
- MOUTH tuning and the push_in anchoring backlog rows close as "dropped, host retired".

## Task graph
YAMLs in `.harness/tasks/phase3c/`. At most two tasks a wave, with no shared paths inside a wave.

| Wave | Tasks | Gate before or after |
|---|---|---|
| 1 | p3c-voice-samples, p3c-render-spike (both throwaway spike branches) | Before: G3 (Cloudflare secrets) so the spike uses real paintings. After: G1 voice, G2 look and style prefix, G4 where paintings are made |
| 2 | p3c-flux-client, p3c-contracts-script | owner merges the contracts PR |
| 3 | p3c-validate-images, p3c-contracts-voice | contracts-voice needs G1 |
| 4 | p3c-contracts-render, p3c-writer-images | contracts-render needs G2 and G4 |
| 5 | p3c-overlays, p3c-batch-images | |
| 6 | p3c-compose-stills, p3c-syllables | |
| 7 | p3c-router-paint, p3c-paint | After: **M1 re-render** (owner dispatches render.yml on sample-65s and paint-demo) |
| 8 | p3c-weekly-images, p3c-retire-host | |
| 9 | p3c-cso, p3c-audit | owner signs off threat model v4 and the audit |
| 10 | p3c-qa-lead | |
| 11 | p3c-phase-review | After: **M2**, the first Workflow A run (R13.5) |

Reviews:
- Visual QA on overlays, compose-stills and router-paint.
- Security on flux-client (added by hand), validate-images, batch-images, compose-stills and weekly-images.

## Owner gates
- **G3, Cloudflare (owner step, before wave 1 if possible).** Create a free Cloudflare account with no payment method. Create an API token scoped to Account > Workers AI only. Add the repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. docs/runbook.md gains these steps (owed, see Docs).
- **G1, voice.** Listen to the p3c-voice-samples mp3s and name one voice (and 0.9 or 0.85).
- **G2, look.** Watch the spike mp4s and approve: the Ken Burns method, the fit (F1 or F2), the transition, the overlay look and the FLUX_STYLE_PREFIX wording.
- **G4, where paintings are made:** (a) Workflow A, recommended, or (b) Workflow B.
- **M1 re-render** after wave 7, **threat model v4 and audit sign-off** after wave 9, **M2** after wave 11.
- Still open from before: R17, threat model v3.1, re-enabling daily-publish (now after M2), R13.5 held until M2 (p3-plan D6 kept).

## Decisions made
- No schema change. `visual.data` keys change in validate, as in slice 1.
- Overlays stay libass (method A). Only the painting layer is FFmpeg.
- One painting can span several scenes, so 4 to 8 images fit up to SCENES_MAX 10 scenes without lowering that cap.
- A timer value is seconds, for the exact check.
- The fallback is the existing flat sets for the whole video, never a mix.
- The style prefix is a locked constant, added in flux_cf.
- No seed: the model's input schema has `additionalProperties: false` and lists only prompt and steps. The docs examples pass a seed anyway, and the spike may test whether it is accepted. If it is, a seed per script helps consistency, through a contract change.
- `image_size` reads JPEG headers only, with no Pillow (no new dependency). FFmpeg decodes at render time.
- I disagree with nothing in PLAN.md or HARNESS.md. PLAN.md section 6 item 1 ("4 to 6 visual templates") and section 11 ("Chart + Flux + b-roll") become narrower: paintings plus overlays, with b-roll still deferred (p3-plan D10). PLAN.md section 3 ("square images fitted to 9:16 over a blurred fill") may change with G2. These are doc edits owed at close-out, flagged here for the owner.

## Risks
- **Flux odd outputs** (extra limbs, warped faces, nonsense objects). Mitigations: silhouettes only, owner review of every image in the PR (G4 a), and deleting an image to fall back.
- **Text in images.** "no text, no letters, no signs" sits in the prefix, but schnell has no negative prompt and often draws letters anyway. The spike counts the rate over 20 prompts. The owner review catches the rest. Captions sit over the lower half and hide some.
- **Style consistency** across 4 to 8 images without a seed or reference image. The fixed prefix, repeated subject words and one palette help. Expect drift, and judge it at G2. A stronger fix (a seed, if accepted) is a contract change.
- **Render time and smoothness** of Ken Burns on stills. The spike measures them, a heavy test times them, and fewer images or a smaller upscale are the fallbacks.
- **Softness** of a square crop upscaled to 1080x1920. The owner judges at G2, and F2 is the fallback.
- **Quota.** 56 images a batch against about 173 a day. A same-day rerun of a failed batch fits once more. Images for scripts edited after the PR do not refresh.
- **Repo growth**, about 0.3 GB a year under (a). Pruning published images is a later task if it matters.
- **Inauthentic-content policy and the AI disclosure**: the Auditor checks it. YOUTUBE_SYNTHETIC_MEDIA is already True.
- **The quota error shape is a guess** (code 4006). See Fallback.
- **bm_* voices** need lang code "b". If that needs espeak or another package, those voices drop out at the spike.

## Tried and abandoned
- Keeping the host as a small corner sprite: the owner retired it.
- Lowering SCENES_MAX to 8 so there is one image per scene: it changes locked PR-body arithmetic and the writer's freedom for nothing. A painting spanning scenes is simpler.
- Painting in Workflow B (old D8 b): see G4.
- Pillow to check image size: a new dependency. The JPEG header walk is a few lines.

## Known risks
See Risks. The render contracts are not written yet, so the overlays, compose-stills, router-paint and paint tasks cannot start before wave 4.

## Next step
1. Owner: G3, then push `plan/p3c-dynamic-scenes` and merge it. It holds only YAMLs, the plan, one stub and one locked test, so main stays green.
2. Orchestrator: wave 1 (p3c-voice-samples and p3c-render-spike, both Architect sessions), then the owner gates G1, G2 and G4.

## Docs
- Applied here: none outside the harness files listed under What changed.
- Owed at close-out (orchestrator or Scribe):
  - CLAUDE.md Status: Phase 3c replaces waves 10 to 12 of phase 3; host retired; the next step is wave 1.
  - workflow.md: a `### Phase 3c status` table and the module order.
  - `.harness/handoffs/orchestrator.md` State: it still names the deleted p3-writer-visuals, p3-batch-visuals, p3-cso, p3-qa-lead and p3-phase-review as next, and the M1 host checks. Point it at this plan instead.
  - backlog: close the push_in, MOUTH and host-contrast rows as "dropped, host retired 2026-11-28"; mark the syllable row as p3c-syllables.
- Owed by tasks:
  - PRD.md section 4 and 7 rows (p3c-contracts-script, p3c-contracts-voice).
  - docs/runbook.md: Cloudflare token setup and rotation, an edited prompt does not repaint, deleting an image (p3c-weekly-images handoff Docs; the runbook is outside its paths, so close-out applies it).
  - docs/threat-model.md (p3c-cso).
  - architecture.md sections 1, 2, 4 and 7, spec.md sections 2 to 4 and 7 (Cloudflare as an approved API, no new package), PLAN.md sections 3, 6, 9 and 11, all at phase close-out.
- lessons.md: none.

## Evidence
- Read: CLAUDE.md, lessons.md, PLAN.md, HARNESS.md section 8, p3-plan.md, p3-spike.md, p3b-plan.md, orchestrator.md, backlog.md, constants.py, router.py, render_one.py, compose.py, validate.py, the schema Visual and Script, gemini.py, gemini_fakes.py, conftest.py, the phase3 YAMLs, and the job lists of daily_publish.yml, weekly_scripts.yml and render.yml.
- Fetched 2026-11-28:
  - Cloudflare's flux-1-schnell model page, input and output schemas (prompt and steps only, base64 `image` out).
  - The Workers AI pricing page (10,000 neurons a day, reset 00:00 UTC, 4.8 a tile plus 9.6 a step).
  - The HF tree API for `voices/` at VOICE_REPO_REVISION (sha256 above).
- Test runs used the sibling worktree venv `agent-a84cab27280eafe81`, because of the site-packages `tests` shadowing (lessons 2026-11-15):
  - With `LOOM_TASK=p3c-flux-client` on the stub: 48 failed (NotImplementedError).
  - With a local prototype of flux_cf (then reverted to the stub): 48 passed. Switching the prototype to the default redirecting opener fails `test_a_redirect_is_never_followed`.
  - Full suite without `LOOM_TASK`: 1789 passed, 195 skipped.
  - `pytest .harness/tests`: 90 passed.
  - `ruff check .` clean, `mypy --strict pipeline/` clean (35 files), `python tests/docs_check.py` passed. CLAUDE.md Status and workflow.md were updated so the deleted tasks are no longer named.
