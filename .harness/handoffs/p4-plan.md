# Handoff: p4-plan (Architect)

## Goal
Two things. A: stop CI from spending the Actions allowance twice per push (it ran out on 2026-11-21). B: plan Phase 4 down to the first automatic YouTube upload, with what that needs before go-live, and scope a long-form option without building it.

## Status
done (plan, task YAMLs, one locked test). Branch `docs/p4-plan`. Waits for the owner to merge it and to answer O1 to O3 before Phase 4 wave 2. Part A (p2d-ci-triggers) needs no decision, but its CI cannot run until the minutes reset.

## Part A: CI cost (task p2d-ci-triggers)

**Cause.** `ci.yml` has bare `push:` and `pull_request:`. Every push to a branch with an open PR runs the check job twice. Every push to a branch with no PR (docs branches, task branches before their PR) runs it once.

**Measured** with `gh run list`: 300 ci.yml runs between 2026-11-15 12:42 and 2026-11-21 22:27 UTC, about 6.4 days. Wall-clock time includes queue time, so these figures run slightly high; per-job minute rounding adds some back.

| Event | Runs | Wall minutes |
|---|---|---|
| push, non-main branch | 109 | 658 |
| pull_request | 101 | 543 |
| push, main | 81 | 462 |
| workflow_dispatch | 9 | 220 |
| total | 300 | 1883 |

**The change** is in `.harness/tasks/phase2d/00_ci_triggers.yaml`:
- `push` runs on `main` and `scripts/**` only. `pull_request` keeps no filter. `workflow_dispatch` stays.
- Why `scripts/**` stays on push: Workflow A opens that PR with GITHUB_TOKEN. GitHub's GITHUB_TOKEN page says `pull_request` runs for PRs "created or updated" by that token start in an "approval-required state". It does not say whether a later human push to the PR escapes that. Keeping push on `scripts/**` makes R12.3 (every mobile edit checked) certain. It costs about one run per owner edit, a few a week. The bot's own push starts no run.
- Concurrency: one group per PR, and a newer PR run cancels the older one. Every other run gets its own group (`github.run_id`). GitHub cancels a *pending* run in a shared group even when `cancel-in-progress` is false, so a main push must never replace a queued reports dispatch.
- The reports job (mutmut) stays dispatch-only.

**What still works:**
- The scope check runs on the PR event. There, `BRANCH` is `head_ref` and `BASE_REF` is the PR base, the same as today's PR runs. On a main push it skips, as now.
- The docs check and `LOOM_TASK` behave the same.
- The owner's mobile edits on a `scripts/<day>` PR still get CI, through the `scripts/**` push trigger (R12.3).
- The bot's own pushes start no run (GITHUB_TOKEN), as before.

**What changes:** a branch gets CI only once it has a PR. A draft PR is enough. Heavy tasks that hand off as "awaiting CI" need one.

**Expected saving.** The 658 minutes of non-main pushes go to zero, about 35% of the week. Superseded PR runs are cancelled on top of that, which this data cannot size. **This alone does not fit the allowance.** The measured pace was about 295 minutes a day (about 8,800 a month). After the fix it is about 190 a day (about 5,700 a month), against about 2,000. The Phase 2b and 2c bursts did most of this: 81 merges to main in 6 days, plus close-out PRs. See owner decision O8.

**Role pushback.** The brief asked for an implementer. `ci.yml` is locked (`.harness/locks.yaml`), and `tests/scope_check.py` lets only `architect` and `test_author` change locked files. So the task is `test_author`, as p2-entry-ci was. The other way is for the owner to unlock `ci.yml`, which I do not recommend. The security review applies (`.github/workflows/**`).

**Locked test on this branch:**
- `tests/test_ci_triggers.py` belongs to p2d-ci-triggers and skips until then.
- `tests/test_ci_workflow.py::test_ci_runs_on_push_pr_and_dispatch_never_pr_target` replaces the test that required no filters. It is true for both the current and the new ci.yml, so main stays green on either side of the merge.

**Other workflows.**
- `render.yml` is dispatch-only and `weekly_scripts.yml` is schedule plus dispatch, already with a no-cancel concurrency group.
- Neither has the problem. Neither gets a change.

**Not done (cheap and safe was the bar):**
- **pip and model caching.** Already in place.
- **`paths-ignore` for docs-only PRs.** Rejected. Docs PRs change `status.yaml`, which switches tests on, and they are where docs drift happens.
- **Skipping the check job on dispatch.** It would save 7 minutes per reports run, but it would remove the only way to get CI on a branch without a PR.
- **A light and heavy split of the check job, so heavy installs and tests run only when `pipeline/voice`, `pipeline/render`, `render_one.py`, `requirements*` or `tests/` change.** This is the largest remaining lever, probably more than half of each run. It is a real ci.yml redesign and the scope-check logic it would touch is security-relevant, so it waits for O8.
- **Caching the apt install of ffmpeg and espeak-ng.** It would save about a minute per run, but it adds a cache keyed on an unpinned apt state. Not worth it.

## Part B: Phase 4 plan

### Scope (YAGNI)
The target is the first automatic YouTube upload, from the daily workflow, at $0.

**In scope:**
- YouTube only.
- The daily render-and-publish workflow at 14:00 UTC.
- At-most-once publishing with a committed ledger.
- Failure equals a red run (GitHub's failure email is the alert).
- The phase-end reviews.

**Dropped or deferred, with the reason:**
- **Instagram (Graph API, token refresh workflow, fine-grained PAT).** Deferred to a Phase 4b. It adds a second token, a PAT that can write every repo secret (threat model section 5), and a weekly workflow, none of which the first upload needs. This narrows PLAN.md's Phase 4 done-when line, so it is owner decision O5.
- **TikTok.** Deferred; manual posting is fine meanwhile (O5).
- **Telegram or Discord alerts.** Dropped for now. A failed scheduled run emails the owner (O6).
- **"Skip, alert, try the next script" on a QA failure.** Dropped for now. The run fails, the owner fixes or deletes the script, and the next day retries. A QA failure is deterministic, so trying the next script only hides it for a day.
- **Retries inside an upload.** Dropped. The next scheduled run is the retry.
- **`publishAt` scheduling.** Dropped. Uploads are public at run time.
- **Workflow C (analytics) and `hook_stats.json`.** These are Phase 5.
- **Phase 3 visuals.** Still skipped for the first upload (orchestrator fifth session).
- **A meaning or number check on title, description, tags and on_screen_text (p2c O1).** Deferred:
  - `on_screen_text` is not rendered (no Phase 3), so it is never published, so it is dropped.
  - Title, description and tags are shown verbatim in the PR the owner merges.
  - The numbers-only check (about one small task) is judged on the first real Workflow A PR (R13.5), as p2c proposed.

### Facts checked for this plan (2026-11-21)
- **YouTube `videos.insert`** ([developers.google.com/youtube/v3/docs/videos/insert](https://developers.google.com/youtube/v3/docs/videos/insert)):
  - It costs 1 unit in the separate Video Uploads quota bucket.
  - "Videos uploaded from unverified API projects are not restricted to private viewing mode."
  - Scopes are `youtube.upload` or broader; we use `youtube.upload` only.
  - `status.containsSyntheticMedia`, `selfDeclaredMadeForKids` and `privacyStatus` (defaults to public on insert) are settable.
  - `publishAt` needs `private` and a never-published video.
  - This settles the PRD section 8 question on paper. The first live run (R17) still confirms it.
- **YouTube altered or synthetic disclosure** ([support.google.com/youtube/answer/14328491](https://support.google.com/youtube/answer/14328491)):
  - Disclosure is required for realistic content: a real person shown saying something, altered real events, realistic scenes that never happened, and AI music as the main focus.
  - AI help with scripts does not need it. Neither does clearly unrealistic animation.
  - A generic text-to-speech narrator is not named either way. Phase 3 photoreal Flux images would need the flag.
- **YouTube inauthentic content** ([support.google.com/youtube/answer/1311392](https://support.google.com/youtube/answer/1311392), dated update 2025-07-15):
  - It is renamed from "repetitious content".
  - It is ineligible for monetisation when it "looks like it's made with a template" or is "AI-generated content made with generic or unoriginal templates giving the impression of mass production".
  - Also ineligible: "image slideshows, templated storylines, or scrolling text with minimal or no narrative, commentary, or educational value", and "content that exclusively features readings of other materials you did not originally create".
  - Reports of a further 2026 update come from secondary sources only. **Unverified.**
- **TikTok, Content Posting API** ([content-sharing-guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines) and [upload-video reference](https://developers.tiktok.com/doc/content-posting-api-reference-upload-video), both updated 2026-08-04):
  - Unaudited Direct Post is `SELF_ONLY`. The posting account must be set to private at posting time. At most 5 users in 24 hours.
  - The inbox upload (`video.upload` scope) creates a draft the user finishes in the app. At most 5 pending shares in 24 hours (`spam_risk_too_many_pending_share`). It has **no AI-content field**.
  - A third-party source says Direct Post has a `post_info.is_aigc` flag. **Unverified** for video, and not usable unaudited anyway. On TikTok the AI label is set by hand in the app when posting.
- **TikTok Creator Rewards:**
  - TikTok's own announcement: original content over one minute, judged on originality, play duration, search value and engagement.
  - Whether a fully AI-voiced faceless video qualifies: sources conflict. **Unverified.**
  - Account thresholds (10,000 followers, 100,000 views in 30 days, 18+): third-party only. **Unverified.**
  - YouTube Partner Program thresholds: not on the page read. **Unverified** here.

### Phase 0 status (YouTube) and what the owner still has to do
Nothing in the repo records the YouTube Cloud setup as done (orchestrator.md lists it as an owner item), so treat it as not started. Steps, all at $0:
1. **Create a Google Cloud project for YouTube only.** Keep it separate from the AI Studio project that holds the Gemini key. Add no billing account.
2. **Enable "YouTube Data API v3"** in that project.
3. **Set up the OAuth consent screen.**
   - User type External.
   - Add only the scope `https://www.googleapis.com/auth/youtube.upload`.
   - Then **Publish app → In production**. In "Testing", refresh tokens die after 7 days.
   - The app stays unverified (personal use, under 100 users). You click through the warning once.
4. **Create an OAuth client of type "Web application"** with the redirect URI `https://developers.google.com/oauthplayground`.
5. **Get the refresh token in the OAuth 2.0 Playground** (no code needed).
   - Open the settings gear and tick "Use your own OAuth credentials". Paste the client id and secret.
   - Authorise the `youtube.upload` scope, signing in as the channel's account. If it is a Brand Account, pick the channel.
   - Exchange the code for tokens and copy the refresh token.
   - Then delete the client's Playground redirect URI. The client is not needed for anything else.
6. **Store `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` and `YOUTUBE_REFRESH_TOKEN`** only where O1 says, and only after O1 is decided.
7. **Turn on failure emails.** GitHub → Settings → Notifications → Actions: "Send notifications for failed workflows only". For scheduled runs, GitHub notifies the user who last edited the cron, which will be the owner merging the workflow PR.
8. **Set the channel's default upload language and audience** in YouTube Studio. The API sets made-for-kids per video anyway.

### Design
**Workflow B, `daily_publish.yml`.** It runs daily at 14:07 UTC: the 14:00 slot, off the full hour, which GitHub delays and drops most. It can also be started by hand. A workflow-level concurrency group with no cancel means runs never overlap. Four jobs, because no job may hold both a secret and a write token (locked `tests/test_workflow_safety.py::test_no_job_gets_both_a_secret_and_write_permissions`):

| Job | Token | Secret | Does |
|---|---|---|---|
| render | read | none | pick the next script, `render_one` (validate, voice, captions, compose, QA), artifact = `final.mp4` only |
| claim | write | none | commit `data/published/<id>.json` with `script_sha` and no video id, before any upload |
| upload | read | the 3 YOUTUBE_* | hashed light install; script from its own checkout, mp4 from the artifact in `runner.temp`; resumable `videos.insert`; outputs `video_id` or `sent` |
| record | write | none | with a video id: fill it in and `git mv` the script to `queue/published/` unchanged. With `sent=false`: delete the claim. Otherwise: leave the claim and fail |

**Idempotency (the Opus note, adapted).** Commit the video id right after the upload, as the note asks. One job cannot do that, so a claim is committed *before* the upload:
- A claim with no video id means an upload may have reached YouTube without being recorded.
- The next run's `pick` refuses to publish anything and fails, naming the script. The owner checks the channel and then fills in or deletes the record.
- That gives at most once. A duplicate video is worse for the channel than a missed day.
- The `sent` flag keeps the common failure (token refresh or init request failed, no byte sent) self-healing: `record` releases the claim and the next run retries.

**Ledger.**
- `data/published/<id>.json` holds one `PublishRecord` per video and is append-only once it has a video id. `queue/published/` is append-only too (D3).
- Records live outside `queue/` because `tests/test_queue_scripts.py` parses every `queue/**/*.json` as a Script. Adding the id to the Script itself would bump the schema.
- The script moves unchanged, so its git blob SHA equals `script_sha` in the record. This meets the threat model's "which approved version was published" seed.

**Bot commits.** The claim and record jobs push to main with `github.token`. These pushes start no CI run (GitHub docs, PRD section 7 research), so publishing costs no CI minutes. A rejected push gets one `pull --rebase` and one retry.

**Upload client** (`pipeline/publish/youtube.py`).
- Standard-library `urllib`, like `gemini.py`. No new dependency.
- Any redirect is refused, and the resumable session URL must be https on the allowed host. The access token travels with it.
- The description gets the O3 credit line appended.
- All three status flags are sent explicitly.
- Tokens are never logged; error text is redacted before it is clipped.

**Quota.** One `videos.insert` a day against the 100-a-day upload bucket; the token refresh uses no quota. There is no other API call. Quota is not a constraint.

**Secrets and the threat model.**
- The secret job installs only the hash-checked `requirements-generate.txt`. That covers pydantic and pyyaml, and the job needs nothing heavy. So P1-4's heavy half does not reach the token. Its remaining effect is that a compromised render dependency could alter the video handed to `upload`, and the CSO rates that.
- The upload job reads metadata from its own checkout, never from the artifact.
- p4-cso writes threat model version 3; owner sign-off is a go-live gate.

### Contracts (for p4-contracts)
- `PublishRecord` in `schema.py`:
  - `script_id` (Script id pattern)
  - `script_sha` (40 lowercase hex)
  - `claimed_at` (UTC datetime)
  - `youtube_video_id` (`^[A-Za-z0-9_-]{11}$` or null)
  - `published_at` (UTC datetime or null; set exactly when the id is)
- Constants: token endpoint `https://oauth2.googleapis.com/token`, upload endpoint `https://www.googleapis.com/upload/youtube/v3/videos`, allowed session host, scope string, category id (27, Education, owner may change), privacy `public`, made-for-kids false, synthetic flag (O2), credit line (O3), timeouts.
- `pick.next_script(queue_dir, records_dir, today) -> str`: returns the id, or raises `PickError`. The CLI prints the id or exits 1.
- `youtube.upload(script, video_path) -> str`: returns the id, or raises `UploadError(sent: bool)`. The CLI writes one `key=value` line to the given output file.

**Why no Phase 4 locked tests are on this branch.**
- A test file that imports a module that does not exist fails at collection, before `tests/conftest.py` can skip it. The stubs belong with the contracts, as in p2-contracts.
- The workflow allowlists (`WRITE_JOBS`, `SECRET_JOBS`, and possibly `environment:`) depend on O1.
- So p4-contracts writes them after O1 to O3.

### Task graph

| # | Task | Role | Paths | Depends on |
|---|---|---|---|---|
| 2d-00 | p2d-ci-triggers | test_author | `.github/workflows/ci.yml` | none |
| 4-00 | p4-contracts | test_author | schema, constants, publish stubs, `tests/publish/**`, workflow tests, `workflow_rules.py`, workflow.md, locks | p2d-ci-triggers; owner O1 to O3 |
| 4-01 | p4-pick | implementer | `pipeline/publish/pick.py` | p4-contracts |
| 4-02 | p4-youtube | implementer | `pipeline/publish/youtube.py` | p4-contracts |
| 4-03 | p4-daily-workflow | implementer | `.github/workflows/daily_publish.yml` | p4-pick, p4-youtube |
| 4-04 | p4-licences | architect | `assets/LICENSES.md`, `spec.md` | none |
| 4-05 | p4-cso | cso | `docs/threat-model.md` | p4-daily-workflow |
| 4-06 | p4-audit | auditor | none | p4-daily-workflow, p4-licences |
| 4-07 | p4-qa-lead | qa_lead | none | p4-daily-workflow |
| 4-08 | p4-phase-review | reviewer | none | p4-qa-lead, p4-cso, p4-audit |

Waves. At most two at once, and no shared paths within a wave:
1. p2d-ci-triggers and p4-licences (once the minutes reset).
2. p4-contracts (after O1 to O3).
3. p4-pick and p4-youtube.
4. p4-daily-workflow. Then the **owner's first live run (R17)**: add the secrets, dispatch by hand, and check the video is public and labelled.
5. p4-cso and p4-qa-lead (reports dispatch after the close-out merges).
6. p4-audit.
7. p4-phase-review.

Security review: p2d-ci-triggers, p4-youtube, p4-daily-workflow. No visual QA (no render change).

**Go-live**, meaning leaving the daily schedule on unattended, needs:
- threat model v3 signed off
- the Auditor report approved
- A1 to A3 closed
- O1 implemented
- the source refill decided (O4)

The first live run can come before all of that, because the owner starts it and watches it.

### Actions minutes (now a scarce budget)
- **Daily publish run**, billed per job and rounded up:
  - render about 5 (render.yml runs took 3 to 4 minutes wall clock)
  - claim 1
  - upload 1 to 2
  - record 1
  - Total about 8 to 9 minutes a run: about 60 a week, about 260 a month.
- **Weekly scripts:** three short jobs, about 5 minutes a week, about 20 a month.
- **Bot pushes** start no CI.
- **Production: about 280 minutes a month**, 14% of the roughly 2,000-minute allowance. **It fits.**
- **Phase 4 build:**
  - About 4 code tasks at about 8 CI runs each (PR pushes, the main merge, the close-out PR) at about 6 minutes: about 200 minutes.
  - About 5 docs-only PRs at about 3 runs: about 90 minutes.
  - One reports dispatch: about 32 minutes.
  - Total **about 350 minutes**, after p2d-ci-triggers.
  - Production plus the Phase 4 build fits in one month **only if** the 2b and 2c pace (about 190 minutes a day after the fix) does not return. See O8.
- **The allowance is exhausted now.** Nothing in CI runs until the billing cycle resets: not this branch's PR, not p2d-ci-triggers, not the R13.5 Workflow A run, not a first upload. The owner should check the reset date under Settings → Billing.

### Owner decisions
The defaults are what the tasks assume. O1 to O3 block p4-contracts. The rest block only go-live or nothing.

**O1. Where the YouTube tokens live (CSO P1-1; D1 said option (a) or (b) before any publishing token). Blocks p4-contracts.**
- **(a) A second private repo, pushed to only by the owner, holds the secrets and the publish workflow.**
  - Needs a read token for this repo.
  - Needs a Claude Code deny rule so agents never push there (owner-only settings).
  - Its minutes come out of the same account allowance.
  - P1-2 stays open.
- **(b) Make this repo public.**
  - Environment secrets with a `main`-only rule, branch protection or rulesets (closes P1-2), and **unlimited Actions minutes on standard runners**, which also solves O8.
  - The cost: the code, harness and handoffs become public. A public "automated faceless channel" repo could be read against the channel in an inauthentic-content review. The history must hold no personal details (commits use the noreply address). The Auditor's GPL notes start to apply.
  - Unverified: whether a ruleset can let `github-actions[bot]` push the ledger to `main`. If not, the ledger moves to a bot-only branch.
- **(c) A repo secret here, as with the Gemini key.**
  - Any pushed branch can read the token, and the token can post on the channel.
  - Rejected by the threat model for publishing tokens.
- **Recommendation: (b) if you accept public code, otherwise (a).** Under either, add a deny rule for agent pushes to `main` and for `gh pr merge` (P1-2).

**O2. `containsSyntheticMedia` (audit A2). Default: `true`.**
- The narrator is a realistic synthetic voice reading real events.
- YouTube's page does not name TTS narration. Disclosing has no stated monetisation penalty. Phase 3 photoreal images would require it anyway.
- `false` is defensible for solid-background videos.

**O3. Description credit line (audit F2). Default: "Sources: Wikipedia (CC BY-SA 4.0) and public records. Narrated with a synthetic voice."**
- It is a fixed constant appended by the upload client.
- It also discloses the AI voice in text on every platform.
- It must pass the URL rules, so it uses names, not links.

**O4. Cadence and source refill (audit F1, PRD section 8). Default for the first upload: as built, 7 scripts a week, one a day.**
- The 15 sources last about 2 weeks at this rate.
- Before go-live, decide one of:
  - 3 to 4 a week, which PLAN.md section 6.6 recommends (sources then last about 4 weeks). It changes `SCRIPTS_PER_BATCH` and the `publish_after` spacing: one small contracts plus batch task.
  - Keep daily, and plan a refill session every two weeks.

**O5. Platforms. Default: YouTube only in Phase 4. Instagram and TikTok become a Phase 4b after go-live.** This narrows PLAN.md section 11's Phase 4 done-when line, which needs your OK. Meanwhile:
- You may post to TikTok by hand from the render artifact (kept 1 day) or the YouTube download. Set TikTok's AI-generated label in the app. The inbox API has no field for it.
- Unaudited Direct Post is private-only, so the planned inbox-draft route (one tap a day) is still the only automatic TikTok option at $0. It needs the `video.upload` scope approved.

**O6. Alerts. Default: a red run is the alert.**
- "Queue empty" fails the run, which contradicts PLAN.md section 7's "exit cleanly". GitHub's failure email is the only free alert with no new secret.
- Telegram or Discord can come with Phase 4b.

**O7. First video. Default: `queue/approved/sample-65s.json`** (the Bloop, `publish_after` 2026-11-23). You approved its render on 2026-11-16, and it is the oldest approved script, so `pick` chooses it first. Move it out of `queue/approved/` if it should not go public. render.yml and the tests reference it, so that is a small task.

**O8. CI minutes at development pace. Default: p2d-ci-triggers plus discipline.**
- Discipline means: push once per task when possible, fold the close-out into fewer PRs, and dispatch reports only at phase end.
- Larger levers:
  - O1 (b), which gives unlimited minutes.
  - A light and heavy split of ci.yml, so heavy installs and tests run only when render, voice, requirements or tests change. One test_author task, security-reviewed.

**Audit follow-ups:**
- **F1:** see O4.
- **F2:** see O3.
- **F3** (Cottingley names children; the Piltdown "Dawson faked it" risk; Antikythera framed as "what it was"). Content review in the approval PR; no task. Default: drop `sources/cottingley-fairies.yaml` before go-live unless you accept naming the cousins as historical figures. That is your call.
- **F4:** you confirm the Gemini key setup once.
- **F5, F6:** you re-read the Gemini Additional Terms and check whether the Interactions API has a no-store option. No task unless you find one.
- **A1 and A3:** task p4-licences.
- **A2:** O2.

### Monetisation reality (a risk, not a blocker)
- **YouTube.** The policy above targets templated, mass-produced AI content and pure readings of others' material. This pipeline is exactly that shape until Phase 3 visuals exist: one template, a solid background, an AI voice reading facts drawn from Wikipedia.
  - Mitigations already in the plan: human approval of every script, original structure and suspense writing, sourced facts. The remaining ones are visual variety (Phase 3) and a moderate cadence (O4).
  - Expect YPP review to be the hard gate, not the upload.
- **TikTok Creator Rewards** wants original videos over one minute (ours are about 65 s). Whether a fully AI-voiced faceless video counts as original is **unverified**, and sources conflict.
- **Revenue.** PLAN.md section 4 already notes that Shorts revenue is small. Monetisation is not this phase's success measure.

### Optional: long-form option (scoped, not built)
The owner is considering videos of 10 minutes or more on the main channel, in the same genre, fed by the Shorts.

**What it would need:**
1. **Visuals first.** Ten minutes of solid background with captions is exactly what the inauthentic-content policy names. So Phase 3 (charts, Flux images, b-roll), landscape 1920x1080 templates and a new render path come first. The constants are portrait-only today.
2. **Bigger contracts.**
   - About 1,440 words at 144 wpm, against today's limits: `NARRATION_MAX_CHARS` 1500 (about 250 words), `SCENES_MAX` 10, one source per script, 10 facts per source.
   - It would need a long-form Script type with chapters, multi-source scripts, and sources of about 30 to 50 facts.
   - That is a schema version bump and new validate rules.
3. **Fact-check and PR.**
   - The meaning check is one checker call per script today. A long script needs chunked calls, and the batch budgets grow.
   - The PR body cap (60,000 characters) fits about one long script per PR.
   - The owner's review time grows about 6-fold per video.
4. **Gemini free quota.** Per video: about 1 writer call with an output 6 to 10 times longer, plus about 5 to 10 checker chunks. At one long video a week that fits the 14-call budgets in principle. The real limits are on the owner's AI Studio dashboard: **unverified here**. Output-token caps per call may force chunked writing.
5. **Render and minutes.**
   - Kokoro on a 2-core runner runs at about real time or slower for 10 minutes of audio. Whisper alignment of 10 minutes runs at a few minutes. FFmpeg at 1080p is about 0.5 to 1 times real time.
   - Estimate 20 to 40 minutes per render, under the 45-minute job timeout but close. Raise it to 90.
   - One long video a week is about 120 to 160 minutes a month. That fits only with the minutes discipline in O8, or with O1 (b).

**Go or no-go gate.** Decide after 30 to 60 days of Shorts data (YouTube Analytics, Shorts only). **Go only if all of these hold:**
- Average view duration is at least 60% of the video length (about 39 s on 65 s). PLAN.md section 12 leaves the target to the owner; this is the proposed bar.
- At least 1,000 subscribers gained from Shorts.
- Median engaged views per Short are at least 2,000 and not falling over the last 30 days.
- At least 3 Shorts topics with clearly above-median retention, as candidate long-form subjects.
- Zero factual corrections needed after publishing.
- Phase 3 visual templates shipped and the YouTube channel in good standing (no inauthentic-content warning).

Any miss is no-go. Re-check 30 days later. None of these numbers is a decided target; they are the Architect's proposal for the owner to adjust.

## Decisions made
- **The CI task is `test_author`, not implementer.** `ci.yml` is locked. The other option is the owner unlocking it.
- **Workflow-table placement.** The p2d-ci-triggers status row sits in workflow.md's `### Phase 2 status` table. The docs check reads only headings matching `### Phase <digits> status`, so a `### Phase 2d status` table would fail CI at close-out. p2c's `### Phase 2c status` table has the same trap: move its rows into the Phase 2 table at its close-out.
- **Push on main and `scripts/**` only, plus PR concurrency keyed on the PR number, `run_id` otherwise.** This avoids GitHub's rule of cancelling pending runs in a shared group.
- **Claim before upload (at most once).** The Opus note's "commit right after upload" cannot share a job with the token, so the gap is closed from the other side.
- **The ledger is in `data/published/`, not inside Script and not under `queue/`.** No schema bump, and the queue tests stay as they are.
- **Phase 4 locked tests go to p4-contracts**, because they depend on stubs and on O1.
- **Upload is standard-library urllib**, like Gemini. No new dependency.

## Tried and abandoned
- Proving the new CI test by editing ci.yml in this worktree. The session's permission classifier refused the edit. I checked against a patched copy under `out/` instead (Evidence).

## Known risks
- **Minutes:** the allowance is exhausted, and even after the fix the development pace is about 3 times the allowance (O8).
- **The record job can fail after a good upload.** The claim then blocks publishing until the owner reconciles by hand. This is accepted in exchange for never uploading a video twice.
- **Under O1 (b), a ruleset may block the bot's pushes to main.** Unverified.
- **No retry in the upload.** A transient error loses a day.
- **The render job's unhashed heavy install can still tamper with the video it hands to upload** (CSO to rate).
- **Policy facts marked unverified above can change under us.** The Auditor rechecks them at phase end.

## Next step
1. Owner:
   - Merge `docs/p4-plan` once the minutes reset.
   - Answer O1 to O3 (O4 to O8 can take the defaults).
   - Do the Phase 0 steps 1 to 5 and 7. Add the secrets (step 6) only after O1.
2. Orchestrator:
   - Run wave 1: p2d-ci-triggers (Opus test_author, security review) and p4-licences.
   - Close out.
   - Then run p4-contracts once O1 to O3 are answered.
3. Waves 3 to 7 as above. R17 (the first live upload) is the owner's run between waves 4 and 5.

## Docs
- Applied here:
  - workflow.md: Phase 2d and Phase 4 module order and status tables.
  - PRD.md: Phase 4 requirements R14 to R18, the phasing line, and the section 8 YouTube question marked as answered on paper.
  - CLAUDE.md: the Status "Next" line.
- Owed at close-out of p2d-ci-triggers:
  - CLAUDE.md Commands line ("awaiting CI" needs a PR; a draft is enough).
  - workflow.md Stage 0 step 4.
  - orchestrator.md How to run a task, steps 4 and 6.
  - PRD.md R7.3 wording.
  - threat model section 1 and the P1-5 rows (CSO).
- Owed when the owner answers:
  - PRD.md section 7: O1 to O8 and A2.
  - PLAN.md section 11: the Phase 4 done-when line if O5 is accepted; section 7: queue-empty fails the run (O6); section 9: `data/published/`.
- Owed at Phase 4 close-out:
  - architecture.md: section 1b for Workflow B, and drop the "Phase 4 gap" weak point once the claim design ships.
  - spec.md: layout, `PublishRecord`, the YouTube secrets.
- lessons.md: one entry for the minutes overrun (the cause was in ci.yml since p1-contracts; caught when the allowance ran out).

## Evidence
Commands were run with `../p2b-qa-tests-batch/.venv/Scripts/python.exe`.
- `LOOM_TASK=p2d-ci-triggers pytest tests/test_ci_triggers.py tests/test_ci_workflow.py` on the current ci.yml: 3 failed (push filter, concurrency, acceptance) and 22 passed. That is the intended red.
- Against a patched copy of ci.yml (push on main, the concurrency block) in `out/wf/`, every test in both files passed, `assert_safe` included.
- `pytest` without LOOM_TASK: 1216 passed, 55 skipped (the new file skips). `tests/docs_check.py`: passed (an earlier run caught "p4-plan" in the CLAUDE.md Status being read as a task id; reworded). `pytest .harness/tests`: 69 passed. `ruff check .`: passed.
- Not run: mypy (no pipeline code changed), actionlint (no workflow changed on this branch).
- `gh run list --workflow ci.yml --limit 400` gave 300 runs (table in part A). `gh run list --workflow render.yml`: 2 runs, 3 and 4 minutes wall clock.
