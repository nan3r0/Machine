# Shorts Pipeline: Product Requirements

Checkable requirements, decisions and open questions for the pipeline described in `PLAN.md`. PLAN.md holds the full design; this file does not repeat it.

## 1. Summary

A $0, cloud-only pipeline that scripts, voices, renders and publishes faceless short-form videos to YouTube Shorts, Instagram Reels and TikTok, for one owner running a faceless channel. It runs on GitHub Actions with free APIs and open-source CPU tools. The owner's only regular job is reviewing and merging a weekly pull request of scripts (about 15 minutes). See PLAN.md sections 1 and 2.

## 2. Goals and non-goals

Goals:
- Publish daily with the owner's PC off, at $0 running cost.
- Every published fact traceable to a source and approved by the owner (PLAN.md section 5).
- Videos varied enough to avoid YouTube's inauthentic-content enforcement (PLAN.md section 6).

Non-goals:
- No local compute (GPU, Raspberry Pi, Task Scheduler).
- No dashboard or web UI. Approval is a GitHub PR.
- No fully automatic TikTok posting. One tap per video is accepted.
- No paid APIs or paid tiers.

## 3. Phasing

Phases and their done-when lines are in PLAN.md section 11. Current phase: **Phase 2, scripts and fact-check** (Phase 1 closed 2026-11-16; the Phase 2 plan waits for owner approval). Phase 0 (admin: Google Cloud project, YouTube audit, Meta and TikTok apps, Cloudflare) runs in parallel and is done by the owner.

## 4. Functional requirements and acceptance criteria

### Phase 1: core render

Goal: a hand-written script JSON becomes a good 65 s MP4, inside GitHub Actions.

**R1. Script schema.** A script JSON in the PLAN.md section 7 shape is validated before any work.
- R1.1 A well-formed script JSON validates (tested on `queue/approved/sample-65s.json`; the 40 s sample was removed with the Retention format).
- R1.3 `queue/approved/sample-65s.json` validates, fits the 65 s format's word range and is the render workflow's default script.
- R1.2 A script with a missing or wrong-typed field is rejected with an error naming the field.

**R2. Voice.** Kokoro turns narration text into a mono wav.
- R2.1 The wav is non-empty and its duration fits the word count at roughly 144 wpm (voice speed 0.9).
- R2.2 Model weights load from a cache directory given by the caller.
- R2.3 If Kokoro fails, the run fails with an error. It never continues with a silent or empty file.

**R3. Alignment.** Word timings come from forced alignment of the known script text.
- R3.1 Exactly one timing per script word, same words, same order, punctuation and unicode intact.
- R3.2 Timings are monotonic and lie inside the audio duration. This replaces PLAN.md's "no word timing off by more than 150 ms vs expected speech rate" check.

**R4. Captions.** A word-by-word `.ass` file for 1080x1920.
- R4.1 Every script word appears in the file, in order, with its aligned timing.
- R4.2 All caption positions lie inside the safe zone set in `pipeline/constants.py`.
- R4.3 ASS control characters in words (`{`, `}`, `\`) are escaped, so they show as text.

**R5. Render.** FFmpeg produces `final.mp4`.
- R5.1 1080x1920, 30 fps, H.264 video, AAC audio.
- R5.2 Integrated loudness is -14 LUFS, within 1 LU.
- R5.3 Video duration equals voice duration within 0.2 s.

**R6. QA gate.** A QA report is produced for every render.
- R6.1 Fails a video with a silence longer than 1.5 s, a duration outside the format's range, or a missing word timing, and names each failed check.
- R6.2 Passes the rendered sample.
- R6.3 The render command exits non-zero when QA fails.

**R7. Runs in the cloud.**
- R7.1 A manual `workflow_dispatch` run on GitHub renders the sample and uploads `final.mp4` as an artifact.
- R7.2 Manual check: the owner watches the artifact and judges it a good 65 s video (clear voice, captions in sync by eye, nothing cut off).
- R7.3 Gate 1 (ruff, mypy, pytest) runs green in CI on every push.
- R7.4 Main stays green while tasks are unbuilt: a task's tests run only once it is listed in `.harness/status.yaml` or is the current `LOOM_TASK`.
- R7.5 CI's `make check` also runs the docs check, bandit, semgrep, gitleaks, pip-audit and actionlint, with no high-severity findings.
- R7.6 Phase-end QA Lead, CSO and Auditor reviews are done, `docs/threat-model.md` exists, and the owner has approved the audit report.

### Phase 2: scripts and fact-check

Goal: Workflow A opens a real pull request of 7 fact-checked scripts, with flags readable on the GitHub mobile app (PLAN.md section 11). Kept minimal: no RSS ingest, no vacation-mode count, no fallback provider, no hook stats. The defaults below follow the owner decisions D1 to D8 proposed in `.harness/handoffs/architect-p2-plan.md`; a different answer changes the matching criterion before p2-contracts runs.

**R8. Sources.** Facts come from hand-curated files in `sources/`, one solved mystery per file.
- R8.1 Every `sources/*.yaml` validates as a source file: a topic and at least one fact, each fact with a unique integer id, its text and an https url. No two sources share a topic once case and punctuation are ignored, and every fact id a script in `queue/` cites resolves to one source file.
- R8.2 At least 14 sources are seeded, each following the PLAN.md section 4 content rules. Manual: the owner reviews the facts in the seeding PR.

**R9. Exact fact-check.** PLAN.md section 5, exact layer.
- R9.1 Every number and proper noun in a narration line must appear in the facts linked to that line; anything missing is reported.
- R9.2 Standard forms agree: `$45M`, `45 million dollars` and `45,000,000` are one number, and so are `2024` and `twenty twenty-four`.

**R10. Script generation.**
- R10.1 A generated script validates as a Script, its word count lies inside `TIKTOK_WORDS`, and its `source_fact_ids` come only from its own source.
- R10.2 Source facts reach the model inside a delimited data block that the prompt says is data, never instructions.
- R10.3 A source is used once: a source with any fact id in a script under `queue/` (`approved/` or `published/`) is not picked again. The queue files are the ledger; there is no `used_facts.json`.
- R10.4 Invalid model output is retried once, then the script is left out and listed in the PR body.
- R10.5 With fewer than 7 unused sources the batch writes what it can and the PR body says "N of 7: sources exhausted". With none, it opens no PR and the run fails visibly.

**R11. Meaning check and flags.**
- R11.1 One checker call per script, at temperature 0, returns one verdict per line; a missing or malformed verdict counts as UNSUPPORTED, never as a pass. A SUPPORTED or PARTIAL verdict must name a fact id linked to that line; one that names none counts as UNSUPPORTED.
- R11.2 A line that fails either layer is rewritten once and re-checked; if it still fails, the script stays in the batch with a flag naming the line and the reason. The run never stops on a fact-check result.
- R11.3 A batch never makes more model calls than the writer and checker budgets in `pipeline/constants.py`; when a budget is used up, lines are flagged instead of rewritten.

**R12. Publishable fields** (CSO P1-3, phase review N5).
- R12.1 A script is rejected if any spoken or published field contains a URL, a bare domain (a dot then a TLD of 2 or more letters, such as `example.com`), `www.`, `<` or `>`, a control, bidi or zero-width character, or any format, unassigned, private-use or surrogate character (newlines allowed in the description only), or exceeds the title, description, tag, scene-count or narration-length caps. The URL and angle-bracket checks run on text folded with NFKD and combining marks dropped, so full-width and look-alike forms are caught. A narration that contains a non-ASCII digit (any symbol that folds to an ASCII digit) is rejected too, so the exact fact-check never skips a number.
- R12.2 The render command exits 2 before the voice step for a script outside `TIKTOK_WORDS`.
- R12.3 Every JSON file under `queue/` passes R12.1 and the word bounds in CI, so a mobile edit of an approval PR is checked.

**R13. Approval pull request (Workflow A).**
- R13.1 The PR body lists every flag first, then per script the hook, each line's narration with its fact texts and urls, and the title, description and tags verbatim. It stays under `PR_BODY_MAX_CHARS`; an over-long body fails the run instead of being cut. Every model-derived string (flag reasons, hook, narration, title, description, tags) sits inside a code block or span that its text cannot close, so no link, image, HTML or @mention from the model renders.
- R13.2 `weekly_scripts.yml` runs on Sunday 06:00 UTC and by hand. The Gemini key is only in the job that calls Gemini, which has a read-only token; only the job that opens the PR has write permissions, and it holds no other secret.
- R13.3 Every file in `.github/workflows/` passes the safety rules, and any job-level write permission or secret must be on an explicit per-job allowlist (CSO P1-6).
- R13.4 CSO P1-1 is decided and recorded in section 7 before the Gemini key is added to the repo.
- R13.5 Manual: the owner runs Workflow A; a PR with 7 scripts opens and its flags read well on the GitHub mobile app.
- R13.6 Phase-end QA Lead, CSO and Auditor reviews are done, `docs/threat-model.md` covers Phase 2, and the owner has approved the audit report.
- R13.7 CSO P2-1 to P2-6 are closed before the first live run of Workflow A: the key job installs only hash-checked packages, the PR adds only new id-named scripts, a read-only job re-checks the queue before the PR opens, runs never overlap, published fields reject bare domains and look-alike URL forms, and the Gemini client refuses redirects.

### Later phases

Requirements are written when each phase starts, from PLAN.md sections 5, 7 and 11.

## 5. Non-functional requirements

- Cost: $0. Free tiers only; a run fits comfortably in GitHub Actions free minutes (PLAN.md section 3).
- Run time: one video renders in under 15 minutes on `ubuntu-latest`, including dependency install from cache.
- Security: secrets live only in GitHub Actions secrets and never appear in logs, code or commits.
- Licensing: fonts, music and SFX are open-licence, each logged in `assets/LICENSES.md`.

## 6. Risks and flags

The main list is PLAN.md section 10. Added during kickoff:
- Kokoro is the only voice, so a Kokoro break stops the pipeline until fixed. Accepted for a CPU model with pinned weights.
- stable-ts and Kokoro pull in torch. Install size and time on Actions need caching or the 15-minute target fails.
- Heavy tests (ffmpeg, torch, Kokoro) run only in CI, so tasks that need them can't pass Gate 1 without a GitHub repo, and each fix round waits on a CI run.

## 7. Decisions

Confirmed by the owner:
- 2026-11-15: PLAN.md is the product and HARNESS.md is the build process. Both are the source of truth.
- 2026-11-15: Model routing per HARNESS.md section 3 (Opus plans, writes tests and reviews; Sonnet implements; Haiku formats).
- 2026-11-15: Phase 1 runs at Harness Stage 0: manual sessions, one fresh session per task.
- 2026-11-15: Phase 1 task graph approved.
- 2026-11-15: Kokoro is the only voice. edge-tts is dropped (overrides PLAN.md sections 3 and 7).
- 2026-11-15: Voice package is the PyTorch `kokoro` package with misaki pronunciation, not `kokoro-onnx`. Owner's bar: no loss in voice or timing quality, it must sound human and the captions must sit on the speech with no lag. `kokoro-onnx` is only reconsidered if a side-by-side listen proves it equal. Weights are pinned to a Hugging Face revision and sha256 hashes.
- 2026-11-15: The owner is hands-off for Stage 0. An orchestrating Claude session launches each task session (in a visible window the owner can watch and type into), runs the gates and reviews, pushes, opens PRs and logs outcomes. The owner approves the contracts PR and merges PRs.
- 2026-11-15: Docs must stay aligned with the project automatically, through the harness rather than loops or scheduled agents (owner: "extremely important"). Four parts: a required Docs section in every handoff; Gate 2 checklist item 8 "Docs aligned"; a Haiku Scribe doc-sync session at every task close-out, with lessons and decisions written by the orchestrator; and a free, model-free CI check `tests/docs_check.py` (task p1-docs-check). Rejected: `/loop`, which dies with the session, and a scheduled cloud agent, which spends usage even when nothing changed.
- 2026-11-15: QA's 150 ms speech-rate rule is replaced by alignment sanity checks (R3.2).
- 2026-11-15: Heavy tests run in CI only, never locally.
- 2026-11-15: Main stays green with a locked, task-aware `tests/conftest.py` driven by `.harness/status.yaml`.
- 2026-11-15: The deviations from HARNESS.md listed under "Assumed by Claude" below are accepted.
- 2026-11-15: PLAN.md updated for Kokoro-only voice, the alignment QA rule and the Phase 1 contract files.
- 2026-11-15: The "Office / dashboard" in HARNESS.md sections 6b and 10b is the owner's general-purpose tool, not part of this project. Nothing is built for it here.
- 2026-11-15: Code lives in the private GitHub repo `nan3r0/Machine`, default branch `main`.
- 2026-11-15: Everything must be completely free. Free tiers only, and no payment method on any account (GitHub, Google Cloud, Meta, TikTok, Cloudflare), so nothing can ever bill.
- 2026-11-15: Platform research applied to PLAN.md. Sources: developers.google.com/youtube (v3 quota, videos.insert, revision history, Analytics metrics), support.google.com/cloud (OAuth testing and verification), aistudio.google.com/docs (Gemini pricing, rate limits, structured output), developers.facebook.com/docs/instagram-platform (content publishing, token refresh), developers.tiktok.com (Content Posting API, updated 2026-08-04), developers.cloudflare.com/workers-ai (pricing, updated 2026-11-12), docs.github.com (Actions billing), Pexels and Pixabay API docs and licences.
  - YouTube: no audit needed for public uploads since 2 Nov 2026; uploads use their own quota (1 unit each, 100/day). OAuth consent screen "In production" as a personal unverified app.
  - Gemini: strongest free model writes scripts, Flash-Lite runs the meaning check (one call per script), large batches spread over several days.
  - Instagram: Facebook Login for Business with resumable upload, so no public video hosting. Weekly scheduled token refresh (60-day tokens) writing back to GitHub Secrets with a fine-grained token.
  - TikTok: inbox upload needs only `video.upload` scope approval; one tap per video, at most 5 drafts pending.
  - Analytics: engaged views, average percentage viewed and retention for Shorts, pulled at days 3 and 7 (no swipe-away metric; 48–72 h lag).
  - Images: Flux output fitted to 9:16 over a blurred fill. Pexels clips credited in the description.
- 2026-11-16: Every video, on every platform, targets about 65 s once the pipeline is live (about 175 words, accepted 62 to 90 s, mandatory curiosity reset at about 25 to 30 s). The Retention format stays in code and tests but is not used by default. PLAN.md sections 4, 7, 11 and 12 updated. (Retention part superseded by the 2026-11-16 over-a-minute entry below.)
- 2026-11-16: Delivery is slower, darker and mysterious to build suspense, while videos stay about 65 s. Voice speed 0.9, about 150 wpm, so the 65 s format is about 160 words (accepted 156 to 225) and the Retention format 70 to 112 words (superseded below: 144 wpm, 149 to 216 words, Retention removed). A darker Kokoro voice and background music are deferred. Tone rules in PLAN.md section 4.
- 2026-11-16: Speech rate set to the measured 144 wpm (167 words in 69.5 s, render run 43873059742), so the 65 s format accepts 149 to 216 words (62 and 90 s at 144 wpm, rounded inwards). A 225-word script would have run about 94 s. The numbers private to compose.py and qa.py move to constants.py, and compose's FFmpeg calls get a 600 s timeout (task p1-constants-timeout).
- 2026-11-16: The only hard length rule is that every video runs over a minute; 65 s is a target, not a requirement. QA keeps the 62 to 90 s range (62 s lower bound, 90 s cap). The Retention format (25 to 45 s, 70 to 112 words) is removed from code, tests, PLAN.md and spec.md: it was unused, and QA's word-count switch let a short script pass against 25 to 45 s, breaking the over-a-minute rule. QA now checks every video against 62 to 90 s whatever its word count. The 40 s sample is deleted and the golden render uses the 65 s sample. This closes the open Retention word range question.
- 2026-11-16: Golden render frames cover the whole video: 1 to 60 s every 10 s (below the 62 s QA minimum, so they fit every passing video) plus one frame 0.5 s before the end, through one helper shared by the heavy test and render.yml (task p1-golden-65s). They are frames for visual review, not reference images: nothing is committed or pixel-compared, because ffmpeg, libass and x264 come unpinned from apt and CPU torch is not bit-exact, so a diff would be flaky.
- 2026-11-15: Niche is "Solved Internet & Everyday Mysteries", with the content rules in PLAN.md section 4 (sourced resolutions only, no private individuals, no graphic violence). Proposed by Claude, pending owner OK: the rules themselves.

- 2026-11-16: Phase 2 owner decisions (defaults from `.harness/handoffs/architect-p2-plan.md`):
  - D2: Workflow A writes into `queue/approved/` on its PR branch; merging is approval. No `queue/pending/`, no `on_merge_approve.yml`.
  - D3: The queue files are the ledger (approved and published). No `data/used_facts.json`. `queue/published/` is append-only.
  - D4: Hand-curated `sources/` only. NotebookLM or a Gemini notebook may be used by hand to help refill sources; no API and no task for it.
  - D5: Writer `gemini-3.8-flash`, checker `gemini-3.5-flash-lite` (different models; no `gemini-2.5-*` and no preview model). Ids live only in `pipeline/constants.py`. The checker runs at temperature 0 and every verdict names its supporting fact id. At most 14 writer and 14 checker calls per batch.
  - D6: No URLs in any published field; title 100 characters, description 1000, at most 10 tags of 30 characters and 500 in total. The 65 s sample keeps its NOAA credit by name only.
  - D7: Phase 2 runs at Stage 0; Loom is built later.
  - D8: Deferred: vacation-mode count, fallback text provider, `hook_stats.json` input, a `script/prompts/` folder.
  - D1 (CSO P1-1, where the Gemini key lives), decided 2026-11-18: option (c). `GEMINI_API_KEY` is a repo secret in this repo, added by the owner on 2026-11-18 from a new AI Studio project with no billing, the key restricted to the Gemini API. Accepted because the key's damage is capped at its free quota; option (a) or (b) is still decided before Phase 4 adds publishing tokens. Condition (CSO P2-1): the key must not reach an unpinned install, so Workflow A does not run, by hand or on its Sunday schedule, until p2-weekly-hardening has merged; the owner disables the workflow until then.
- 2026-11-18: The owner approved CSO P2-1 to P2-6 (`.harness/handoffs/p2-cso.md`). They become tasks p2-validate-urls, p2-gemini-redirects and p2-weekly-hardening, which run before the first live Workflow A run and before the phase-end reviews (R13.7). Gemini call caps count logical calls; each can make up to 2 HTTP requests (spec.md section 4).

Research for the Phase 2 plan, 2026-11-16 (Architect; facts, not decisions):
- GitHub, docs.github.com "Deployments and environments" (Actions reference): "If you are using GitHub Free, environment secrets are only available in public repositories"; deployment branch and tag rules in private repositories need GitHub Pro or Team; required reviewers and wait timers are public-repo only on Free, Pro and Team. So CSO P1-1 option (b), environment secrets with a `main`-only rule, is not available in this private repo at $0. The rulesets page names only Team and Enterprise for private repositories.
- GitHub, docs.github.com "GITHUB_TOKEN": pushes made with `GITHUB_TOKEN` start no new workflow runs, and `pull_request` runs on a PR it opens wait for a user with write access to approve them. So Workflow A must validate scripts before it opens the PR; CI runs only on the owner's own edit commits.
- Gemini, aistudio.google.com/docs (pricing, rate limits, structured output): REST endpoint `https://generativelanguage.googleapis.com/v1beta/interactions`, key in the `x-goog-api-key` header, JSON output through `response_format` (`mime_type: application/json` plus a JSON Schema). `minLength` and `maxLength` in that schema are ignored, so field caps are checked in code. `gemini-2.5-flash` and `gemini-2.5-pro` are marked deprecated, routing to other models on 2026-12-01. The rate-limit page lists free figures for one model only and points to the AI Studio dashboard for real values, so the writer and checker model ids and their daily limits come from the owner's dashboard (open question below). Free-tier content may be used to improve Google's products.
- Gemini Interactions API, aistudio.google.com/api-reference/interactions-api and docs/structured-output, read 2026-11-16 for p2-contracts: `response_format` is a top-level request field (`{"type": "text", "mime_type": "application/json", "schema": {...}}`); the structured-output curl examples send an `Api-Revision: 2026-05-20` header, which the reference page does not mention. The response holds `status` (`completed` when done) and `steps[]`; the model's text is in the `model_output` step's `content[]` parts of type `text`. Temperature is named only in the overview ("`generation_config` ... including `thinking_level`, `temperature`"); the reference's `GenerationConfig` block does not list it, so `generation_config.temperature` is unconfirmed until the first live call. No HTTP error body is documented.

Assumed by Claude (owner can overrule):
- 2026-11-15: The hook learns the current task from the `LOOM_TASK` environment variable set at launch, not from a file the agent could edit.
- 2026-11-15: Phase 1 background is a solid colour. Visual templates wait for Phase 3.
- 2026-11-15: Contracts are two locked files, `pipeline/schema.py` and `pipeline/constants.py`, plus signature stubs that p1-contracts writes in each module. No Protocols, since each step has one implementation. `pipeline/render_one.py` is added as the entry point.
- 2026-11-15: HARNESS.md section 6b calls every specialist read-only, but the CSO must update `docs/threat-model.md`. The CSO agent gets Edit and Write, limited to that one file through its task's `paths_allowed`.
- 2026-11-15: The QA Lead stays read-only. It proposes missing tests in its handoff, and the Test Author writes them as a new locked-test task, instead of the QA Lead writing tests itself as section 6b suggests.
- 2026-11-15: semgrep, gitleaks, actionlint and mutmut run in CI only (no `make` or native Windows support locally), so Gate 1 is "free" but not "instant" for those tools.
- 2026-11-15: The weekly scheduled audit workflow (section 6b) is not built in Phase 1. The phase-end Auditor covers Phase 1. The weekly workflow is planned for Phase 4, before go-live.
- 2026-11-15: Usage-limit message fixtures (HARNESS.md section 10b) go in `.harness/tests/fixtures/limit_messages/`, not `tests/fixtures/`, because the parser is harness code and `tests/**` is locked.
- 2026-11-15: The contracts task also owns tooling (`pyproject.toml`, requirements, CI), so no implementer can change pins or gates.
- 2026-11-15: Tests needing ffmpeg or torch carry a `heavy` marker, skip locally when the tool is missing, and always run in CI.
- 2026-11-15: Code targets Python 3.11+ (owner's machine has 3.11); CI runs 3.12.
- 2026-11-16: The owner approved the Phase 1 Auditor report (R7.6). No Phase 1 blockers. A1 to A3 and CSO P1-2, P1-4, P1-5 are Phase 4 pre-go-live items; CSO P1-1, P1-3 and P1-6 are Phase 2 entry items. Phase 1 is closed once main CI is green.
- 2026-11-21: The owner approved the Phase 2 Auditor report (R13.6) and signed off threat model version 2. Still open: enable weekly-scripts and run it once by hand (R13.5).

## 8. Open questions

- **[Decision needed]** Average view duration target for 65 s videos (PLAN.md section 12), to be set by the owner after the first 30 days of data.
- **[Decision needed before Phase 4]** How `sources/` is refilled: 14 seeded sources last two weekly batches.
- To verify in Phase 4: one test upload confirms an unaudited YouTube project's uploads and `publishAt` schedules go public (official docs say yes since 2 Nov 2026, but no example covers an unaudited project).
- To verify in Phase 2: Gemini free-tier limits for the chosen models in the owner's AI Studio dashboard (published figures come from third parties). Each model's free daily limit must cover 28 requests, since a run can make up to 28 HTTP requests per model (CSO P2-6).
