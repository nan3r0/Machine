# Handoff: p3-plan (Architect)

## Goal
Plan Phase 3 (visual templates) as a task graph. Today every video is the voice plus word captions on a solid dark background (PRD.md section 7, 2026-11-15 "Phase 1 background is a solid colour"). The owner has seen it and wants animation and visuals before go-live. PLAN.md section 11 sets Phase 3 done as "two videos on similar topics look clearly different".

## Status
done (plan and task YAMLs only). No code, no locked tests, nothing pushed. Branch `worktree-agent-a8b5f231de7875d94`. Waiting on the owner to answer D1 to D10 below. Locked tests and import stubs come in p3-contracts, after approval, on a `plan/p3-contracts` branch that merges to main before any implementer starts (lessons.md 2026-11-25).

## What changed
- New: this handoff, and 14 task YAMLs in `.harness/tasks/phase3/` (00_spike to 13_phase_review).
- Uncommitted. Nothing else is touched.
- Implementer YAMLs list only their new test files under `tests`. tests/conftest.py gives a test file to the last task YAML (in sorted path order) that lists it, so listing an existing file such as `test_generate.py` would skip it on main until the Phase 3 task is done.

## The plan in one paragraph
Phase 3 comes in three slices. Slice 1 (Phase 3a) draws animated motion graphics with the tools the render job already has: libass, which already burns in the captions, can also draw shapes, move them, fade them and grow them. Each scene gets a moving card built from the script's own facts: a bar chart, a big number that counts up, numbered steps, a timeline, a place card or a title card. Each of the four templates gets its own colour scheme and background motion. That needs no new API, no new secret, no new Python package and no extra Gemini call. Slice 2 adds Cloudflare Flux illustrations and slice 3 adds Pexels clips as accents. Each of those brings a key, URL hardening, licence rules and a threat model update, and gets its own plan once you answer D8 to D10.

## Milestones you can see
- **M1, after p3-wiring (about 8 tasks in).** Dispatch `render.yml` twice by hand: once on `queue/approved/sample-65s.json` (the Bloop, now with steps and a timeline) and once on a demo script under `tests/fixtures/scripts/` (another template, with a bar chart and a counter). Each run's `frames` artifact shows the difference. `render.yml` itself does not change.
- **M2, after p3-writer-visuals and p3-batch-visuals.** Your first manual run of Workflow A (R13.5) opens a PR whose scripts carry visuals. The PR body shows each scene's on-screen text and chart values for you to check.
- **Phase 3 done (PLAN.md section 11)** after slices 2 and 3. Slice 1 alone already meets "two videos on similar topics look clearly different", because the template sets the colours and background motion and the scene data sets the layouts.

## Scene visual types (slice 1)
The script format stays the same. Every scene already has `visual: {"type": "chart" | "map" | "steps" | "story", "data": {...}}`. Phase 3 defines what `data` may hold. It is either empty `{}` or `{"items": [{"label": str, "value": str}, ...]}`, with 1 to 4 items.

| `type` | `data` | On screen |
|---|---|---|
| `story` | `{}` | The scene's `on_screen_text` as a kinetic title card: words slide and fade in over the template's background motion |
| `chart`, 1 item | value is the number, label says what it counts | A big number that counts up (or pops in if it is a year or a range), label below |
| `chart`, 2 to 4 items | every value a plain number | Bars that grow in one after another, value at the end of each bar |
| `steps`, values empty | labels only | Numbered step cards that appear one at a time |
| `steps`, values set | value is a year or date | A timeline: dots on a line, year and label popping in |
| `map`, 1 item | label is the place, value optional | A place card: animated pin, sonar rings, place name. A real map is deferred (D5) |
| any type with `{}` | | Falls back to the `story` card, so every Phase 2 script (all written with `data: {}`) still renders |

Per template (`Script.template`): its own palette (background, accent, text) and background motif, for example sonar rings for `map`, a faint grid for `chart`, a dotted path for `steps` and slow fog shapes for `story`. All are dark and slow, to keep the suspense tone (PLAN.md section 4).

Layout (D2): captions move down to the lower third (y about 1150, still inside the locked safe-zone test), so visuals get a panel from about y 300 to 940. All numbers go in `pipeline/constants.py`.

## How the script writer changes (pipeline/script/)
- **Same single writer call.** No extra Gemini request. Output grows by a few hundred tokens per script. The binding free-tier limit is requests a day (20 on the writer model), and that stays where it is.
- **Writer JSON schema** (`generate.py` `_WRITER_SCHEMA`). Each scene gains two flat fields: `visual_type` (enum chart, map, steps, story) and `items` (array of `{label, value}` strings). No `anyOf`, since Gemini's support for it is not confirmed. Gemini ignores length limits in the schema, so caps are checked in code (PRD.md section 7 research).
- **Prompt.** A new `_VISUAL_RULES` paragraph:
  - Pick a visual per scene.
  - `chart` only for numbers that appear in the facts.
  - `steps` for a sequence, with a year as the value for a timeline.
  - `map` for one place.
  - Otherwise `story`.
  - Labels and values are copied from the facts and kept short.
  - `on_screen_text` is a short teaser of up to 40 characters, not a copy of the narration.
- **Bad visual, no retry.** If the model's visual breaks a rule, `write_script` turns that scene into `story` with `{}` instead of rejecting the script. A retry would spend a scarce request on decoration.
- **`validate.py`** checks `data` per type with the caps above, and runs the published-field rules on every label and value (no URL, no control or look-alike characters, no non-ASCII digits). `render_one` already exits 2 on any problem before the voice step.
- **`batch.py`** changes in two places:
  - The PR body shows each scene's `on_screen_text` and visual items in code spans, so you approve what is drawn. Today it shows neither (threat model section 5, Phase 3 seed).
  - Every number and name in the on-screen text, labels and values goes through the exact check (`exact.unsupported`) against that scene's cited facts. On a miss the scene is flagged, and by D4 its visual drops to a plain card. The run never stops on it.
- No meaning check on visuals: the exact check is free and covers the dangerous part (numbers).

## Task graph (slice 1)
YAMLs in `.harness/tasks/phase3/`. At most two at once, and no shared paths within a wave.

| # | Task | Role | Paths | Depends on |
|---|---|---|---|---|
| 00 | p3-spike | architect | throwaway `spike/p3-ass` branch, never merged | none |
| 01 | p3-contracts | test_author | constants, visuals stubs, locked tests, demo fixture, sample-65s data, locks, workflow.md | p3-spike; owner D1 to D7 |
| 02 | p3-validate-visuals | implementer | `pipeline/script/validate.py` | p3-contracts |
| 03 | p3-ass-kit | implementer | `pipeline/visuals/ass_kit.py` | p3-contracts |
| 04 | p3-cards | implementer | `pipeline/visuals/cards.py` | p3-ass-kit |
| 05 | p3-charts | implementer | `pipeline/visuals/charts.py` | p3-ass-kit |
| 06 | p3-compose | implementer | `pipeline/render/compose.py`, `pipeline/render/captions_ass.py` | p3-contracts |
| 07 | p3-router | implementer | `pipeline/visuals/router.py` | p3-cards, p3-charts |
| 08 | p3-wiring | implementer | `pipeline/render_one.py` | p3-router, p3-compose, p3-validate-visuals |
| 09 | p3-writer-visuals | implementer | `pipeline/script/generate.py` | p3-validate-visuals |
| 10 | p3-batch-visuals | implementer | `pipeline/script/batch.py` | p3-validate-visuals |
| 11 | p3-cso | cso | `docs/threat-model.md` | p3-wiring, p3-writer-visuals, p3-batch-visuals |
| 12 | p3-qa-lead | qa_lead | none | p3-wiring, p3-writer-visuals, p3-batch-visuals |
| 13 | p3-phase-review | reviewer | none | p3-cso, p3-qa-lead |

Waves:
1. p3-spike.
2. p3-contracts. Owner merges the `plan/p3-contracts` PR.
3. p3-validate-visuals and p3-ass-kit.
4. p3-cards and p3-charts.
5. p3-compose and p3-router.
6. p3-wiring, then **M1** (two render.yml dispatches plus visual QA of the frames).
7. p3-writer-visuals and p3-batch-visuals, then **M2** (your first Workflow A run, R13.5).
8. p3-cso and p3-qa-lead (dispatch the reports job only after the close-out merges, lessons.md 2026-11-21).
9. p3-phase-review.

No Auditor in slice 1: it adds no asset, licence, API or platform rule. The Auditor runs with slices 2 and 3. Specialist reviews (`.harness/config.yaml`):
- Visual QA: p3-ass-kit, p3-cards, p3-charts, p3-router (`pipeline/visuals/**`), p3-compose and p3-wiring (frames).
- Security: p3-compose, p3-validate-visuals and p3-batch-visuals.

### Slices 2 and 3 (planned after D8 to D10, no YAMLs yet)
- **Slice 2, Flux illustrations for `story` scenes.** These tasks:
  - Constants, a `visual.data.prompt` rule and locked tests.
  - `pipeline/visuals/flux_cf.py`: standard-library client like `gemini.py`, refusing redirects, https on the Cloudflare host only, key never logged.
  - Image checks: PNG or JPEG magic bytes, a size cap and a pixel-size check.
  - A new job in Workflow B, per D8.
  - CSO v4.1 and Auditor (Cloudflare terms, AI image disclosure).
  - Before planning, check Cloudflare's current Workers AI pricing and model pages (lessons.md 2026-11-15).
- **Slice 3, Pexels clips as accents.** These tasks:
  - `pipeline/visuals/broll.py`: search, then download over https from Pexels hosts only, with a type and size cap.
  - The fixed credit "Video from Pexels", appended by the upload job when the committed script has a b-roll scene. The upload job never reads the artifact (R16.4), so the script must say it.
  - The licence log per video.
  - CSO and Auditor.

## Decisions made
Architect decisions. No owner action is needed unless you object. Decision ids D1 to D10 in this file are p3-plan ids, not Phase 2's D1 to D8 in PRD.md section 7.
- **No schema change.** `Visual` keeps `type` and `data`. The rules per type live in `validate.py`, as the threat model asks ("validate per template, with size caps"). There is no `schema_version` bump and no queue migration. Phase 2 scripts with `{}` stay valid.
- **sample-65s gets new data.** Its `steps` data (`{"step": 1, "label": ...}`) changes to the new `items` shape in p3-contracts. The `ledger` branch holds no record for it (checked 2026-11-25: only `.gitkeep`), so it is unpublished and may change. p3-contracts checks again before editing.
- **Escaping.** `pipeline/visuals/` may import `escape_ass_text` from `pipeline/render/captions_ass.py`, a pure function, instead of copying it (DRY). architecture.md section 2 records the exception.
  - Imports inside `visuals/` point one way: router to cards and charts, and both of those to ass_kit.
  - No test or semgrep rule enforces the import boundary (grep of `tests/`, checked 2026-11-25), so nothing locked needs changing.
  - Text is drawn only through ASS, never FFmpeg `drawtext`, whose separate escaping the threat model flags.
- **Compose** chains two `subtitles=` filters, visuals first, then captions, and takes the background colour from the template's palette. The new arguments are keyword-only with today's behaviour as the default, so the existing locked compose tests stay true. New behaviour goes in new test files.
- **Existing locked tests** that the change would break are edited in p3-contracts so they hold before and after the change: `tests/script/test_generate.py:112` (`data == {}`) and the fake `compose` in `tests/test_render_one.py:51`. New behaviour is tested in new files owned by the new tasks, so main stays green.
- **Scene timing** is a pure function in the router. It counts words per part (hook, each scene, loop line) and maps them onto the word timings. The hook and loop line show only the background motion; the captions carry them.
- **Caps** keep the PR body under `PR_BODY_MAX_CHARS`. Per field: on-screen text 40, label 24, value 12, at most 4 items. Per script: a screen-text total, so that 7 scripts at every cap still fit. p3-contracts does the arithmetic in the locked batch test, as Phase 2 did.

## Owner decisions
Recommendations are the defaults the YAMLs assume. D1 to D7 block p3-contracts. D8 to D10 block only slices 2 and 3.

**D1. Slice order: motion graphics first, then Flux, then Pexels.** Recommend yes. Slice 1 needs no key, no account and no new package, and gives a visible change in one render.yml run.

**D2. Caption position.** Recommend moving captions to the lower third (y about 1150). Visuals then get the upper panel (y about 300 to 940), and both stay inside the platform safe zone. The other way: keep captions in the centre and squeeze visuals into a band above them (about 430 px tall), which suits a big number or a title but not a bar chart.

**D3. How charts are drawn.** Recommend libass vector drawing (no new package). The other way is matplotlib, which renders nicer static charts, but:
- It adds matplotlib, pillow, fonttools, kiwisolver, contourpy, cycler, pyparsing, python-dateutil and packaging to the hashed render lock. That lock broke five times on 2026-11-25.
- It needs your approval (spec.md section 7).
- It gives still images that FFmpeg then has to animate.

Revisit after you see M1.

**D4. A chart value or on-screen name that the facts do not back.** Recommend: flag it in the PR and replace that scene's visual with a plain card automatically. A wrong number drawn big on screen is the worst failure here. The other way is flag only and you fix it before merging, which is cheaper but relies on you catching every flag on your phone.

**D5. `map` scenes.** Recommend a place card (pin, sonar rings, place name) in slice 1, with a real map deferred. A drawn map needs map data: Natural Earth outlines are public domain, but they add an asset, a licence entry and work with little payoff for this niche.

**D6. When to run Workflow A for the first time (R13.5).** Recommend after p3-writer-visuals and p3-batch-visuals merge (M2). Sources are single-use. A run now spends 7 of the 14 sources on scripts with plain title cards only. They would still render, but with less variety.

**D7. Go-live.** Recommend that go-live (turning on `daily-publish`) waits for slice 1 (M1 and M2) and the other R18 gates, but not for Flux and Pexels. Slice 1 already removes the "solid background" look you rejected. The other two add variety later.

**D8. Where Flux images are made (slice 2).** Recommend (b).
- (a) In Workflow A at script time, committed into the scripts PR. You see every image before it can be published. The cost: the public repo grows by about 1 to 3 MB per video, about 0.5 to 1 GB a year, and git keeps it forever.
- (b) In Workflow B, in a new `visuals` job that holds the Cloudflare token as an environment secret (main only, like `youtube`), with a read-only token and the hashed light install. It hands the images to the render job as an artifact, which the render job filters by type and size. You approve the image prompt text in the PR, not the image itself.

**D9. Image style.** Recommend stylised illustration, never photoreal, and never a real identifiable person. This keeps the images from passing as evidence of real events, which matters for a "solved mysteries" channel. `containsSyntheticMedia` is already true (O2).

**D10. Stock footage.** Recommend Pexels only and dropping Pixabay: one key, one credit rule, one licence. B-roll stays an accent (PLAN.md section 3), at most one or two clips per video.

## Cost in free-tier calls
| Slice | Gemini | Cloudflare | Pexels | Actions |
|---|---|---|---|---|
| 1 | 0 extra requests (same writer call, a few hundred more output tokens) | none | none | Render may take about 30 to 60 s longer (p3-spike measures it). The repo is public, so minutes are not metered. If it goes private again: about 11 code tasks at about 8 CI runs of about 6 min each, roughly 530 minutes once, plus about 2 extra minutes a day |
| 2 | 0 extra (the prompt is a field of the same call) | about 3 to 5 images a video, so 3 to 5 a day against the free daily allowance (PLAN.md says about 170 flux-1-schnell images a day; **unverified until the slice 2 plan reads Cloudflare's pricing page**) | none | one more small job a day, about 1 to 2 min |
| 3 | 0 extra | none | 1 to 3 requests a video against 200 an hour (PLAN.md section 3) | downloads add well under a minute |

## Risks
- **libass speed.** Many animated shapes at 1080x1920 and 30 fps could slow the render. p3-spike measures it before anything is locked, against the 600 s FFmpeg timeout.
- **Looks.** Vector cards can look like slides. Visual QA reviews frames on every render task, and you judge M1. D3 is the fallback.
- **Inauthentic-content policy.** Visuals made from templates are still templates. Four palettes, five layouts and per-script data give real variety, and Flux and Pexels add more. How YouTube judges this is unverified (p4-plan research).
- **A wrong number drawn on screen.** Covered by the exact check, D4 and the PR body showing every value.
- **The model picks poor visuals.** These become plain cards in code at no extra request, and you can edit the JSON in the PR.
- **The PR body cap.** New fields grow the body. Caps are set by arithmetic in a locked test.
- **Heavy tests run only in CI.** Every render task waits for a CI run on a draft PR.
- **Locked-test churn.** Two existing locked tests change, keeping both the before and after states true. A mistake there turns main red. p3-contracts runs the full suite without `LOOM_TASK` before handing off.

## Tried and abandoned
- matplotlib for slice 1: see D3.
- A `gradients` or `geq` FFmpeg background: `geq` is too slow at this frame size, and `gradients` depends on the runner's FFmpeg version. Background motion is drawn in ASS instead.
- A `schema_version` 2 with a typed visual model: it needs a migration and gives no safety beyond per-type checks in `validate.py`.

## Known risks
See Risks above. One more: slices 2 and 3 have no YAMLs yet, so the Phase 3 done-when line cannot close until they are planned.

## Next step
1. Owner: answer D1 to D10 (or accept the defaults).
2. Orchestrator: run p3-spike (Architect, throwaway branch), then p3-contracts on `plan/p3-contracts`. The owner merges it, then the waves above follow.

## Docs
- Owed by p3-contracts:
  - workflow.md: a `### Phase 3 status` table (that exact heading, so `tests/docs_check.py` reads it), the Phase 3 module order, and criterion-to-test rows.
  - PRD.md section 4: Phase 3 requirements R19 (visual data rules and caps), R20 (render layers and layout), R21 (writer and PR body), R22 (M1 and M2 manual checks). PRD.md section 3: the current-phase line.
  - The owner's decisions go into PRD.md section 7.
- Owed at slice 1 close-out:
  - architecture.md: section 1 diagram (router and scenes.ass), section 2 (`visuals/` layer and the `escape_ass_text` import exception), and section 4 (decisions).
  - spec.md: section 2 layout, section 3 (visual data), section 4 (new numbers).
  - PLAN.md section 11: a Phase 3 slice note, if D1 is accepted.
  - CLAUDE.md: Status.
  - PRD.md section 7: retire the 2026-11-15 "solid colour" assumption.
- lessons.md: none (no mistake found).

## Evidence
- Read: PLAN.md, PRD.md, spec.md, architecture.md, lessons.md, HARNESS.md section 8, docs/threat-model.md sections 5 to 7, `pipeline/schema.py`, `pipeline/constants.py`, `pipeline/render/compose.py`, `pipeline/render/captions_ass.py`, `pipeline/render_one.py`, `pipeline/script/generate.py`, `pipeline/script/batch.py` (checks and PR body), `.github/workflows/render.yml`, `.harness/handoffs/p4-plan.md` and the phase4 and phase4d YAMLs.
- Checked:
  - matplotlib and pillow are in no requirements file.
  - `origin/ledger` holds only `data/published/.gitkeep`.
  - The only queued script is `queue/approved/sample-65s.json` (template `steps`).
  - The locked tests that pin today's behaviour: `tests/script/test_generate.py:112`, `tests/test_render_one.py:51`, and `tests/render/test_compose_exact.py:33`, which keeps passing with default arguments.
- Checked: `out/` is git-ignored, so p3-spike writes its throwaway files under `spike/`.
- `python tests/docs_check.py` with the new YAMLs: passed.
- `pytest .harness/tests -q`: 90 passed.
- `pytest -q tests` without `LOOM_TASK`: 1656 passed, 92 skipped.
  - Run with the venv of the sibling worktree `agent-a84cab27280eafe81`.
  - The system Python's site-packages holds a `tests` package that shadows the repo's `tests/` (lessons.md 2026-11-15), so collection failed there.
- Not run: ruff and mypy (no Python changed).
