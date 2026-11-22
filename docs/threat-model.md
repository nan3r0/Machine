# Threat Model

Version 3, 2026-11-22. Covers the pipeline at the end of the Phase 4 code: the Phase 1 render, Workflow A (weekly scripts, Gemini, fact-check, approval PR) and Workflow B (daily render and YouTube upload). Method: STRIDE per trust boundary (HARNESS.md section 6b). Version 2 (2026-11-18, signed off 2026-11-21) and version 1 (2026-11-16) are in git history.

Rows carried unchanged from version 2 keep its line references. Every new or changed row was checked against the code on 2026-11-22.

**Owner sign-off: pending.** Signing off version 3 is a go-live gate, where go-live means leaving the daily schedule on unattended (`.harness/handoffs/p4-plan.md`, Go-live). Several controls live in GitHub, Google or Claude Code settings that this review cannot see from the repo. Section 7 lists them for the owner to confirm.

Status values used below:
- **Mitigated**: a control exists in the repo today (file:line given).
- **Owner setting**: the control is a setting outside the repo. It is unverified here and listed in section 7.
- **Gap P1-n / P2-n**: found at the end of Phase 1 or 2; details in `.harness/handoffs/p1-cso.md` or `p2-cso.md`.
- **Gap P4-n**: found in this review; a proposed task in `.harness/handoffs/p4-cso.md`.
- **Accepted**: a known risk the owner carries on purpose.
- **Seeded (Phase n)**: does not exist yet; the phase that adds the feature must handle it.

## 1. What the pipeline is now

Four workflows.
- `ci.yml` runs on pushes to `main` and `scripts/**`, on every pull request and by hand, with one concurrency group per PR (`.github/workflows/ci.yml:3-17`).
- `render.yml` is started by hand and uploads a rendered MP4 as an artifact.
- `weekly_scripts.yml` (Workflow A) is as in version 2: `generate` holds `GEMINI_API_KEY` with a read token, `validate` re-runs the queue tests, `open-pr` has the write token and no secret. It stays disabled until the owner's first manual run.
- `daily_publish.yml` (Workflow B) runs daily at 14:07 UTC and by hand, in one concurrency group with no cancel (`.github/workflows/daily_publish.yml:3-15`). Four jobs, so no job holds both a secret and a write token:
  - `render`: read token, no secret, only on `main` (`:21`). Installs the full unhashed dependency set (`:43-47`), picks the next due script (`:55-69`), renders it and uploads only `final.mp4`, kept 1 day (`:76-81`).
  - `claim`: `contents: write`, no secret, runs no repo code. Commits `data/published/<id>.json` with the rendered script's blob SHA and no video id, before any upload (`:85-140`).
  - `upload`: read token and the `youtube` environment, which holds `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` and `YOUTUBE_REFRESH_TOKEN` (`:148`). Checks out `main` without credentials (`:155-158`), installs only hash-checked packages (`:165`), downloads the MP4 to `runner.temp` (`:167-170`), requires this run's claim on `main` before the secret step (`:172-186`), re-checks the script blob and runs `pipeline/publish/youtube.py` (`:188-205`).
  - `record`: `contents: write`, no secret. With a video id it fills in the record and moves the script to `queue/published/` unchanged. With `sent=false` it deletes the claim. Anything else keeps the claim and fails (`:210-270`).

The repo has been **public** since 2026-11-21 (owner decision O1 option b). Code, handoffs, this threat model, workflow logs and artifacts are readable by anyone. Public repos get unmetered Actions minutes on standard runners.

## 2. Assets

| Asset | Why it matters | State now |
|---|---|---|
| Approval integrity | Workflow B publishes any approved script on `main` that is due (`pipeline/publish/pick.py:45-53`). Anyone who can put a file in `queue/approved/` on `main` publishes under the owner's channel | Live |
| The approval PR (body and diff) | The owner approves on what the PR shows. Now public: anyone can read and comment | Exists (`pipeline/script/batch.py:196-230`) |
| YouTube OAuth client id, client secret and refresh token | Together they mint access tokens that post public videos on the channel. Scope `youtube.upload` only. Per the YouTube API reference, `videos.update` and `videos.delete` need broader scopes, so a thief can post but not edit or delete (re-check on Google's pages at audit) | Environment secrets on `youtube` (owner setting, section 7) |
| Derived access token | About an hour of the same upload power | Exists only inside the `upload` step; masked (`pipeline/publish/youtube.py:145`) |
| `GEMINI_API_KEY` | Quota theft. Cost only if its Google project ever gets billing | Repo secret (D1 option c), allowlisted for `generate` |
| The publish ledger (`data/published/`, `queue/published/`) | The only record of what went out. A claim with no video id stops publishing (`pick.py:40-44`); deleting one by hand without checking the channel risks a duplicate | Live |
| Hand-curated sources (`sources/*.yaml`) | The only input the writer sees | 15 files, owner-reviewed |
| The channel and its standing | A strike, a spam flag or an inauthentic-content review ends or demonetises the project | Live from the first upload |
| `main` branch | Every scheduled workflow runs main's code. The `youtube` environment admits only `main`, so `main` is now the gate to the publishing token | Yes |
| Actions minutes | Unmetered while the repo is public. If it goes private again: about 2,000 a month with no payment method; production alone is about 280 (p4-plan, Actions minutes), and the 2026-11-21 overrun shows development can exceed it | Unmetered now |
| Gemini free daily quota | When it runs out, the weekly batch leaves scripts out or opens no PR | From the first live run |
| YouTube upload quota | One `videos.insert` a day against the upload bucket; not a constraint | Live |
| Pinned model weights | Loaded through pickle | Yes |
| Instagram and TikTok tokens, the IG refresh PAT; Cloudflare, Pexels, Pixabay keys | Not present (Phase 4b and Phase 3) | No |

No payment method exists on any account (PLAN.md section 3), so a stolen key or token cannot create a bill. That holds for each Google key only while its project has no billing account.

## 3. Trust boundaries

1. **The owner.** Reviews and merges every PR, holds every account and every setting in section 7.
2. **Claude Code agent sessions** on the owner's PC. They run with the owner's git and `gh` credentials, so they can push branches, push to `main`, merge PRs, dispatch workflows and re-run failed jobs unless a deny rule stops them.
3. **GitHub Actions runners.** Execute whatever workflow file is on the pushed or dispatched ref.
4. **Upstream code and data.** PyPI, the PyTorch CPU index, Hugging Face, the whisper model URL, the Ubuntu mirror, GitHub release downloads, Dependabot PRs.
5. **Source files into the writer.** Hand-curated and owner-reviewed.
6. **Model output (Gemini) into scripts and the PR body.** Untrusted data.
7. **The Workflow A artifact** from `generate` to `validate` and `open-pr`.
8. **External APIs.** Gemini; Google's OAuth token endpoint and the YouTube upload endpoint.
9. **Workflow B job hand-overs.** `render` to `upload` (the MP4 artifact and the `script_id` and `script_blob` outputs) crosses from the unhashed render job into the token job. `upload` to `record` (`video_id`, `sent`) crosses from the token job into a write job.
10. **The public.** Anyone can read the repo, logs and artifacts, comment on PRs and open fork PRs. Fork PR runs get a read token and no secrets.

## 4. STRIDE by boundary (as built)

### 4.1 Script JSON into the render (boundary 6, rendered side)

Unchanged from version 2.

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | Command injection: a script word or title containing shell metacharacters reaches a shell | Low / high | **Mitigated.** FFmpeg and ffprobe run from argument lists, never a shell (`pipeline/render/compose.py:124`, `pipeline/render/qa.py:94`). |
| Tampering | Filtergraph injection through the captions path | Low / medium | **Mitigated.** `pipeline/render/compose.py:34-35` escapes for the option parser and quotes for the filtergraph. Paths are built by the pipeline. |
| Tampering | ASS injection through override tags or a newline | Medium / low (visual only) | **Mitigated.** `pipeline/render/captions_ass.py:34` escapes `\`, `{`, `}`; narration is whitespace-collapsed (`pipeline/schema.py:57`); control characters are rejected before the voice step (`pipeline/script/validate.py:54-66`, `pipeline/render_one.py:37-40`). |
| Tampering | Path traversal through `id` | Low / medium | **Mitigated.** `pipeline/schema.py:42` restricts `id` to `[a-z0-9-]`; every Workflow B job re-checks it with the same pattern (`daily_publish.yml:59`, `:106`, `:177`, `:197`, `:232`). |
| Denial of service | A very long script runs Kokoro and FFmpeg to the 45 minute timeout | Medium / low | **Mitigated.** Caps checked before any step (`pipeline/script/validate.py:69-120`, `pipeline/render_one.py:37-40`). |
| Information disclosure | The `render.yml` `script` input is any path; a non-JSON file's content can appear in the error | Low / low | **Accepted.** No secret on disk, `persist-credentials: false`, only repo writers can dispatch. |

### 4.2 Upstream code and weights into the runner (boundary 4)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | A poisoned Kokoro checkpoint (pickle) | Low / high | **Mitigated.** Pinned revision and sha256 checked before load (`pipeline/voice/kokoro.py:76-87`, `pipeline/constants.py:21-27`). |
| Tampering / EoP | A poisoned whisper `small.en` checkpoint | Low / high | **Mitigated by upstream behaviour only.** openai-whisper checks its own sha256 while pinned. |
| Tampering / EoP | Dependency confusion between the PyTorch index and PyPI | Low / high | **Mitigated.** torch installs alone with `--no-deps` from the CPU index, in `daily_publish.yml:43-47` too (`tests/test_daily_publish_workflow.py:104`). |
| Tampering / EoP | A malicious transitive release in a job that holds a secret | Low / high | **Mitigated for both secret jobs.** `generate` and `upload` install only `requirements-generate.txt` with `--require-hashes` (`weekly_scripts.yml:34`, `daily_publish.yml:165`); no heavy or torch install in `upload` (`tests/test_daily_publish_workflow.py:148-153`). The secret job restores no cache, so a poisoned pip or model cache written by `render` cannot reach the token (`tests/test_daily_publish_workflow.py:160-163`). Residual, accepted: a Dependabot PR that bumps a hashed pin brings the new release's hash with it; the owner's review of that PR is the only check. |
| Tampering | **P1-4 heavy half: a malicious release in the render job's dependencies alters the video that gets published.** `render` installs `requirements.txt` and `requirements-heavy.txt` without hashes (`daily_publish.yml:47`), so a bad release of any transitive package runs during the render. It can rewrite `final.mp4`: overlay a scam URL, swap the audio, splice in other footage. `upload` checks only the file size (`youtube.py:107`) and nobody watches the video before it goes public at 14:07. The render's QA runs in the same compromised process. It cannot choose an unapproved script: `claim` and `upload` re-check the blob against `main` (`:121`, `:135`, `:201`), so the worst script choice is another approved one on `main` | Low / high (a public scam or policy-breaking video under the channel's name, possibly a strike) | **Gap P1-4, heavy half. Go-live gate.** Proposed: a hash-checked lock for the render job's full dependency set (tool needs owner approval, spec.md section 7). |
| Tampering | Compromised third-party Action | Low / high | **Mitigated.** Every `uses:` pinned to a full commit SHA (`tests/workflow_rules.py:88-90`), Workflow B included; gitleaks and actionlint are sha256-checked (`ci.yml:101-102`). |
| Tampering | Compromised apt package (ffmpeg, espeak-ng) | Very low / high | **Accepted.** Signed Ubuntu mirror, not pinned. Not installed in any secret job. |

### 4.3 Actions runners and workflows (boundary 3)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP | A step writes to the repo with the job token | Low / high | **Mitigated.** Workflow-level `contents: read` (`tests/workflow_rules.py:109-110`); job write permissions only through `WRITE_JOBS` (`tests/workflow_rules.py:32-36`, `:81-83`), now `open-pr`, `claim` and `record`. `claim` and `record` run no `python` or `pip` (`tests/test_daily_publish_workflow.py:117-125`) and turn git hooks off (`daily_publish.yml:102-104`, `:228-230`). Checkouts keep no credentials outside those jobs (`tests/workflow_rules.py:95-98`). |
| EoP / Information disclosure | A secret reaches a job that can write | Low / high | **Mitigated.** Secrets only through `SECRET_JOBS` (`tests/workflow_rules.py:37-40`), now `generate` and `upload`; no job is in both lists (`tests/test_workflow_safety.py:272`); the three YouTube secrets sit in exactly one step's env (`tests/test_daily_publish_workflow.py:137-139`, `daily_publish.yml:193-195`). |
| Tampering | Expression injection through a branch name, input or job output | Low / high | **Mitigated.** No `${{ }}` inside `run:` (`tests/workflow_rules.py:91-93`). Workflow B has no dispatch inputs (`tests/test_daily_publish_workflow.py:74`); every job output reaches the shell through `env:` and is regex-checked by each consumer (`daily_publish.yml:59-67`, `:106-113`, `:177-180`, `:197-200`, `:232-235`, `:244-247`). |
| Information disclosure / EoP | `pull_request_target` runs untrusted PR code with secrets | Low / high | **Mitigated.** Forbidden (`tests/workflow_rules.py:111-112`). |
| EoP | **P1-1: a pushed or dispatched branch runs its own workflow copy with the publishing token.** Scenario: an agent session pushes a branch whose `daily_publish.yml` drops the `if:` at `:21` and adds a step that posts `secrets.YOUTUBE_REFRESH_TOKEN` to an outside host, then dispatches it. `SECRET_JOBS` and `ENVIRONMENT_JOBS` fail in CI on that branch, which is detection after the run, not prevention. The `if:` is no control against a branch that deletes it | Medium / critical | **YouTube: owner setting.** The secrets are environment secrets on `youtube` (`daily_publish.yml:148`), the only job allowed to name an environment (`tests/workflow_rules.py:44-46`, `:84-86`). The control that holds is the environment's deployment rule allowing `main` only: a branch run is refused the environment. Unverified from the repo (section 7, item 1). The residual is that `main` is allowed, so P1-1 now reduces to P1-2. **Gemini key: Accepted** under D1 option (c), with the version 2 conditions (own AI Studio project, no billing, API-restricted, rotate on doubt). |
| Denial of service | **P1-5: CI drains the minutes.** | Was medium / medium | **Closed.** `ci.yml` pushes only on `main` and `scripts/**` (`ci.yml:7-10`); one group per PR with newer runs cancelling older ones, every other run in its own group (`ci.yml:15-17`). Workflows A and B each never overlap with themselves (`weekly_scripts.yml:12`, `daily_publish.yml:13-15`). The repo is public, so standard runners are unmetered; the minutes budget returns as an asset if it goes private (section 2). |
| Information disclosure | Workflow logs and artifacts are public | Low / low | **Accepted.** The `weekly-scripts` artifact holds what the public approval PR shows anyway. `final-video` is kept 1 day (`daily_publish.yml:81`) and goes public at upload. Upload logs, next row. |
| Information disclosure | **Upload logs are public.** The task note said logs carry status codes and video ids only. The code is close but not exactly that | Low / low | **Mitigated, with an accepted residual.** Log records hold the step, HTTP status and the video id (`youtube.py:209`, `:222`, `:228`); the access token is masked before it is used (`:145`); the three secrets are masked by GitHub. Residual: the error on stderr (`:275`) carries the step, status and up to 200 characters of Google's response body, after the client secret, refresh token, access token, session URL and its `upload_id` are redacted in plain, URL-encoded and JSON-escaped forms (`:94-99`, `:232-245`). That text is Google's error message, no secret. |

### 4.4 Agent sessions and `main` (boundary 2)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP / Tampering | **P1-2: anything pushed to `main` reaches the publishing token on the next scheduled run.** Scenario: an agent session pushes straight to `main` a change to `pipeline/publish/youtube.py` that sends the refresh token to an outside host, or a script into `queue/approved/`. At 14:07 the `youtube` environment admits the run, because it is `main`. No server-side rule stops the push. Now that the repo is public, branch protection and rulesets are available, but nothing in the repo shows them set (`.harness/handoffs/orchestrator.md` lists them as an owner to-do) | Medium / critical | **Gap P1-2, now critical. Go-live gate.** Needed: a ruleset on `main` requiring a PR and the `check` job, and Claude Code deny rules for agent pushes to `main` and `gh pr merge` (section 7, items 2 and 3). Catch: `claim` and `record` push the ledger to `main` as `github-actions[bot]` (`daily_publish.yml:133-139`, `:267-270`). A ruleset bypass for that actor would be keyed on the actor, not on the workflow or ref (verify on GitHub's rulesets page). Any branch run can ask for `contents: write` at job level, and `WRITE_JOBS` flags that only in CI after the run. So with a bot bypass, an agent-pushed branch that adds an `on: push` workflow could push to `main` as the bot and reach the token at 14:07. Recommended instead: no bypass, and the ledger moves to a bot-only branch (an Architect decision; `pick` and `record` change with it). |
| Tampering (approval bypass) | A file lands in `queue/approved/` on `main` by any path other than a merged owner-reviewed PR | Medium / critical | **Gap P1-2.** `pick` takes any approved, due, valid file (`pick.py:45-53`); the version 2 seed "publish only scripts that arrived through a merged PR" was not built. A ruleset requiring PRs makes every human commit on `main` a merge, so it covers this without new code. Task branches touching `queue/` already fail the scope check (`ci.yml:47-62`). |
| Tampering | An agent dispatches `daily-publish` from `main` with the owner's `gh`, or re-runs it | Low / medium | **Owner setting.** A dispatch publishes only an approved, due script (`pick.py:50`) and runs are serialised, but repeated dispatches publish several due scripts in one day, ahead of the cadence. Re-runs are P4-1 below. Deny rules for agent `gh workflow run` and `gh run rerun` (section 7, item 3). |
| Tampering | A task branch edits `ci.yml` to drop the scope check | Low / high | **Accepted.** The owner reads every change under `.github/workflows/` line by line. |
| Spoofing | An owner message typed in a task window is misread as a decision | Medium / medium | **Mitigated** by process (lessons.md 2026-11-15). |
| Repudiation | Which session or run made which change | Low / low | **Mitigated.** Git history, handoffs, the outcome log; Workflow A and B commit as `github-actions[bot]` from a named run with fixed messages (`daily_publish.yml:132`, `:259`, `:262`). |

### 4.5 Sources and model output into scripts (boundaries 5 and 6)

Unchanged from version 2. The approval PR is now public, see 4.9.

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering | Prompt injection through a source fact | Low / high | **Mitigated, with residuals.** Facts in a delimited data block (`pipeline/script/generate.py:43-46`, `153-165`; `pipeline/factcheck/semantic.py:82-90`); answers pass `validate.problems` and cite only the source's fact ids (`generate.py:119-122`, `168-172`); exact and meaning fact-checks (`batch.py:117-156`); fact text bans links and invisible characters (`tests/test_sources_files.py:38-52`). `upload` runs `validate.problems` again before any request (`youtube.py:89-91`). |
| Tampering | A link that the URL check misses | Low / high | **Mitigated; P2-3 closed.** `pipeline/script/validate.py:24-66`. Residuals accepted as in version 2 (spelled-out or spaced domains, bare IPv4, some visible marks). The fixed credit line is appended after validation and uses names, not links (`pipeline/constants.py:131-135`). |
| Tampering (approval bypass) | The PR shows less than what gets published | Medium / high | **Mitigated; P1-3 closed.** PR body shows every published field verbatim (`batch.py:180-193`). `on_screen_text` is not rendered and not uploaded (Phase 3 seed). |
| Tampering | PR body injection (Markdown, HTML, mentions) | Medium / medium | **Mitigated.** Model text in code spans (`batch.py:159-177`, `191-193`). Fact text accepted while sources stay owner-reviewed. |
| Denial of service | An oversized PR body | Low / low | **Mitigated, fails closed** (`batch.py:228-229`). |
| Tampering | The artifact changes already-approved scripts | Low / high | **Mitigated; P2-2 closed** (`weekly_scripts.yml:69-102`, `:136-169`). |
| Tampering (approval bypass) | The approval PR gets no CI before merge | Low / medium | **Mitigated; P2-4 closed** (`weekly_scripts.yml:53-114`). Verify on the first live run. |
| Spoofing | A source cites an HTTP or lookalike page | Low / medium | **Mitigated** (`pipeline/schema.py:104`); lookalikes left to review. |
| Tampering | Gemini output tells the checker to pass every line | Low / medium | **Mitigated** (`semantic.py:82-90`, `batch.py:125-127`). |

### 4.6 Gemini API (boundary 8)

Unchanged from version 2: key only in a header with redacted errors (`pipeline/script/gemini.py:59-80`, `105-111`), redirects refused (P2-5 closed, `gemini.py:24-31`), quota exhaustion mitigated for overlap (P2-6 closed, `weekly_scripts.yml:12-14`), billing on the key's project is an owner action, a wrong model id fails loudly.

### 4.7 The Workflow A artifact (boundary 7)

Unchanged from version 2: `open-pr` runs only `git` and `gh` on files extracted to `runner.temp` (Mitigated); separate checkouts in `generate` and `open-pr` (Accepted).

### 4.8 Workflow B: publish path and YouTube API (boundaries 8 and 9)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Spoofing / EoP | **OAuth token theft from the upload job.** Code in that job reads the env and posts the tokens out | Low / critical | **Mitigated in the repo** (the branch and `main` paths are P1-1 and P1-2). The job installs hashed packages only (`daily_publish.yml:165`) and restores no cache; checks out without credentials (`:158`); reads the script from its own `main` checkout and re-checks its blob (`:201-204`); treats the artifact as bytes in `runner.temp` (`:170`, `youtube.py:196`) and never runs anything from it. |
| Information disclosure | The access token or secrets go to a host other than Google | Very low / critical | **Mitigated.** Fixed endpoints (`pipeline/constants.py:122-125`); one opener refuses every redirect (`youtube.py:29-36`, `:218`); the resumable session URL must be `https` on exactly `www.googleapis.com`, port 443 at most, no user info, before the bearer token is sent to it (`youtube.py:177-191`, `:194-205`). |
| EoP | The refresh token carries broader rights than upload (owner ticks a wider scope in the Playground) | Low / high | **Mitigated, fails closed.** The token answer's scope set must equal `youtube.upload` exactly (`youtube.py:142-143`, `pipeline/constants.py:126`). Consent screen limited to that scope (owner setting). |
| Tampering | Published metadata differs from the approved script | Low / high | **Mitigated.** Metadata comes from `main`'s copy, whose blob must equal the rendered one (`daily_publish.yml:201-204`); `validate.problems` runs again (`youtube.py:89-91`); privacy, made-for-kids and synthetic-media flags are sent explicitly (`youtube.py:158-162`). The video itself is P1-4 heavy half (4.2). |
| Tampering | A crafted API answer injects a second line into `$GITHUB_OUTPUT` (for example a fake `video_id`) that `record` commits | Very low / medium | **Mitigated.** The id must match `[A-Za-z0-9_-]{11}` before it is written (`youtube.py:207-208`, `:272`); `record` checks it again (`daily_publish.yml:244-247`) and compares `sent` literally (`:260`). |
| Tampering | The ledger records a script version that was never rendered or uploaded | Low / medium | **Mitigated.** The blob is fixed at pick (`:63`) and re-checked by `claim` (`:121`, `:135`), `upload` (`:183`, `:201`) and `record` (`:248-252`). |
| Tampering (at most once) | A run uploads twice, or uploads with no claim on `main` | Medium / medium | **Mitigated, except P4-1.** Claim committed before any upload (`:85-140`); `upload` checks out `main` and requires this run's claim, with no video id and a matching blob, before the secret step (`:155-158`, `:172-186`); `record` keeps the claim on an unknown outcome (`:263-266`); the next `pick` refuses while any claim lacks a video id (`pick.py:40-44`). "Re-run all jobs" re-runs `render`, whose `pick` refuses. After `sent=false` the claim is deleted (`:260-262`), so a re-run of `upload` fails the pre-check. Neither the `ref: main` on the upload checkout nor the pre-check step is held by a locked test (P4-2). |
| Tampering (at most once) | **P4-1: "Re-run failed jobs" after an unknown outcome uploads a second copy.** Scenario: the PUT times out after YouTube received the bytes, so the upload step exits with `sent=true` and `record` keeps the claim and fails. The owner, or an agent with the owner's `gh run rerun --failed`, re-runs the failed jobs. `render` and `claim` are not re-run, the artifact is still within its 1 day, and the claim on `main` still has no video id and the same blob, so the pre-check at `:182-186` passes. The second upload goes public and `record` stores its id; the first video is never recorded | Medium / medium (a duplicate public Short, a spam signal; not account loss) | **Gap P4-1. Go-live gate.** Today only the runbook stops it ("never re-run failed jobs while a claim is kept; check the channel first", workflow.md p4-daily-workflow row). Proposed: bind the claim to the run attempt (for example `claim` writes `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` into its commit message or record, and `upload` refuses unless both match its own), plus a deny rule on agent `gh run rerun`. Check against GitHub's docs that a re-run of failed jobs increments `github.run_attempt`. Trade-off: when `upload` fails before the upload step (install, artifact download), the claim is kept with nothing sent, and re-running the failed jobs is today a correct recovery that uploads once. With the binding, that case becomes a manual reconcile (delete the record, wait for the next run). That fits "a duplicate is worse than a missed day". |
| Tampering | Someone deletes a kept claim by hand to unblock publishing without checking the channel, and the next run uploads again | Low / medium | **Accepted, runbook.** `pick.py:40-44` names the script and says to check the channel first. |
| Repudiation | Later, nobody can tell which approved version was published | Low / medium | **Mitigated; Phase 4 seed closed.** The record holds `script_sha`, the video id and the time (`daily_publish.yml:126-128`, `:253-255`); the script moves unchanged, so its blob equals `script_sha` (`:248-257`). |
| Denial of service | A revoked or expired refresh token, an API error, an expired artifact | Medium / low (a missed day) | **Accepted, fails visibly.** `invalid_grant` says the token must be made again (`youtube.py:238-239`); a failure before any byte is `sent=false` and the claim is released (`:260-262`). A failure before the upload step (artifact gone after 1 day, pre-check) leaves no outputs, so `record` keeps the claim though nothing was sent: the step log shows it. Every failure is a red run and a failure email (owner settings: notifications, consent screen In production so the token does not die after 7 days). No retry inside the upload by design. |
| Spoofing | Unofficial upload methods get the account banned | Low / critical | **Mitigated; Phase 4 seed closed.** Official `videos.insert` resumable upload only (`pipeline/constants.py:123`). |
| Information disclosure | Publish responses or tokens end up in an artifact | Low / high | **Mitigated; Phase 4 seed closed.** The only artifact is `final.mp4` from `render` (`daily_publish.yml:79`, `tests/test_daily_publish_workflow.py:109-111`); `upload` uploads none. |

### 4.9 The public (boundary 10)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | A fork PR adds a script to `queue/approved/` or edits a workflow | Medium / critical if merged | **Mitigated with an owner setting.** Fork runs use `pull_request` with a read token and no secrets (`pull_request_target` forbidden, `tests/workflow_rules.py:111-112`); the owner merges nothing from outside. Owner setting: require approval for fork runs from all outside contributors (section 7, item 4). |
| Spoofing | A stranger comments on the approval PR with a "correction" or link the owner adopts | Low / medium | **Accepted.** Edits on the PR re-run CI (`ci.yml:7-8`), and the URL rules still apply to anything published. |
| Information disclosure | The public repo shows this threat model's open gaps and ties the code to the channel | Medium / medium | **Accepted** with O1 (b); the history was scanned before going public. It is one more reason to close P1-2 and P4-1 before go-live. The inauthentic-content reading of a public "automated channel" repo is the Auditor's. |

## 5. Seeded threats for Phases 3 and 4b

The Phase 4 seeds of version 2 for YouTube are now rows in sections 4.3, 4.4 and 4.8.

### Phase 3: visual templates

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Tampering | `on_screen_text` is not whitespace-collapsed; `drawtext` has its own escaping | Collapse whitespace and escape it before FFmpeg |
| Tampering (approval bypass) | `on_screen_text` appears on screen but not in the PR body, with no length cap | Show it in the PR body and cap it before any template renders it |
| Tampering / DoS | `visual.data` is `dict[str, Any]` with no limits (`pipeline/schema.py:26`) | Validate per template, with size caps |
| Tampering | Pexels or Pixabay returns an unexpected or huge file | Check type and size; HTTPS from the API's own host only |
| Information disclosure | Cloudflare or Pexels key in logs | As for Gemini (4.6) |
| Repudiation | Licence of each asset unknown later | Per-video asset log (PLAN.md section 10) |

### Phase 4b: Instagram, TikTok, alerts, ingest

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Spoofing / EoP | Instagram or TikTok token theft | Environment secrets as for YouTube, minimum scopes, one job per token, P1-2 closed first |
| EoP | The fine-grained PAT used by the IG token refresh can write every repo secret | Single repo, secrets permission only, an expiry date and an alert before it expires |
| Denial of service | Rate limits, the TikTok pending cap, a revoked token | Alerts on every failure |
| Spoofing | A leaked alert webhook lets anyone post fake alerts | Webhook URL in Secrets; alerts never ask the owner to log in through a link |
| Tampering | Automatic ingest (RSS) is added | Fact text gets code spans in the PR body and the same URL and character checks as sources |

## 6. Open gaps, ranked

| ID | Severity | Gap | Must be closed before |
|---|---|---|---|
| P1-2 | **Critical** | No server-side protection on `main`; anything pushed there reaches the publishing token at 14:07, and agents hold the owner's push and merge rights | Go-live |
| P1-4 | High | Heavy half open: the render job installs unhashed packages and can alter the published video. Light half closed for both secret jobs | Go-live |
| P1-1 | High, now owner setting | YouTube: the `youtube` environment's main-only rule (unverified, section 7). Gemini: accepted under D1 (c) | Go-live (verify the setting) |
| P4-1 | Medium | "Re-run failed jobs" after an unknown upload outcome passes the claim pre-check and uploads a duplicate; only the runbook stops it | Go-live |
| P4-2 | Low | `upload`'s `ref: main` checkout and its claim pre-check (`daily_publish.yml:155-158`, `:172-186`) are not held by a locked test, so a later edit can drop them with CI green | Next edit of `daily_publish.yml` |
| P1-5 | Medium | Closed by p2d-ci-triggers (`ci.yml:7-17`); the repo is unmetered while public | (closed) |
| P1-3, P1-6, P2-1 to P2-6 | | Closed in version 2 | (closed) |

## 7. Owner sign-off checklist (settings outside the repo)

None of these can be seen from the repo. Confirm each before signing off.

1. The `youtube` environment exists, holds the three `YOUTUBE_*` values as environment secrets, and its deployment branches are `main` only. No repo-level secret with those names.
2. A ruleset or branch protection on `main` requires a PR and the `check` job, with no bypass for GitHub Actions (a bot bypass lets any branch workflow push to `main`, see 4.4). The ledger then needs its own branch first, an Architect task. Closes P1-2.
3. Claude Code deny rules for agent sessions: `git push` to `main`, `gh pr merge`, `gh run rerun`, and `gh workflow run` of `daily-publish`. Owner-only settings.
4. Fork PR runs need approval for all outside contributors.
5. Google: the YouTube Cloud project is separate from the Gemini AI Studio project, with no billing account on either; the consent screen is In production with only the `youtube.upload` scope; the Playground redirect URI was removed after the token was made.
6. Failure emails for Actions are on, for the account that last edited the cron.
7. Runbook: with a kept claim, never re-run failed jobs; check the channel, then fill in or delete the record. On any doubt about the tokens: revoke the app in the Google account's third-party access page, reset the client secret, make a new refresh token and replace the environment secrets.
