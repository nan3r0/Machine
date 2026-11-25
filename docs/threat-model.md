# Threat Model

Version 3.1, 2026-11-23. Covers the pipeline after Phase 4b: the Phase 1 render, Workflow A (weekly scripts, Gemini, fact-check, approval PR), Workflow B (daily render and YouTube upload) on the bot-only `ledger` branch with run binding, the hash-checked render installs and the weekly audit. Method: STRIDE per trust boundary (HARNESS.md section 6b). Version 3 (2026-11-22), version 2 (2026-11-18, signed off 2026-11-21) and version 1 (2026-11-16) are in git history.

Every line reference was checked again against `main` at #140 on 2026-11-23, including rows whose content is unchanged from version 2 or 3: `daily_publish.yml`, `youtube.py`, `pick.py` and the workflow tests all moved.

**Owner sign-off: pending.** Signing off version 3.1 is a go-live gate (PRD R18), where go-live means leaving the daily schedule on unattended (`.harness/handoffs/p4b-plan.md`). Several controls live in GitHub, Google or Claude Code settings that this review cannot see from the repo. Section 7 lists them for the owner to confirm.

Status values used below:
- **Mitigated**: a control exists in the repo today (file:line given).
- **Owner setting**: the control is a setting outside the repo. It is unverified here and listed in section 7.
- **Gap P1-n / P2-n / P4-n**: found at the end of Phase 1, 2 or 4; details in `.harness/handoffs/p1-cso.md`, `p2-cso.md` or `p4-cso.md`.
- **Gap P4b-n**: found in this review; a proposed task in `.harness/handoffs/p4b-cso.md`.
- **Accepted**: a known risk the owner carries on purpose.
- **Seeded (Phase n)**: does not exist yet; the phase that adds the feature must handle it.

## 1. What the pipeline is now

Five workflows.
- `ci.yml` runs on pushes to `main` and `scripts/**`, on every pull request and by hand, with one concurrency group per PR (`.github/workflows/ci.yml:3-17`).
- `render.yml` is started by hand, installs only from the hashed render locks (`render.yml:35-38`) and uploads a rendered MP4 as an artifact.
- `weekly_scripts.yml` (Workflow A) is as in version 2: `generate` holds `GEMINI_API_KEY` with a read token, `validate` re-runs the queue tests, `open-pr` has the write token and no secret. It stays disabled until the owner's first manual run.
- `weekly_audit.yml` runs weekly, by hand and on PRs that touch `requirements*.txt`, the Makefile or itself. Read token, no secret; `make audit` and a GPL or AGPL licence rule over an unhashed install (`weekly_audit.yml:5-23`, `:60-73`).
- `daily_publish.yml` (Workflow B) runs daily at 14:07 UTC and by hand, in one concurrency group with no cancel (`.github/workflows/daily_publish.yml:3-15`). Four jobs, so no job holds both a secret and a write token. The publish ledger lives on the orphan `ledger` branch, which holds only `data/published/*.json`; nothing in Workflow B pushes to `main` (`tests/test_daily_publish_ledger.py:123-130`).
  - `render`: read token, no secret, only on `main` (`:22`). Checks out `main` and `ledger` without credentials (`:29-37`), installs torch and the rest only with `--require-hashes` (`:50-53`), picks the next due script against `ledger/data/published` (`:61-75`), renders it and uploads only `final.mp4`, kept 1 day (`:82-87`).
  - `claim`: `contents: write`, no secret, runs no repo code. Checks out `main` without credentials for the blob check and `ledger` with credentials (`:100-109`). Refuses if the ledger already holds a record or main's script differs from the rendered blob (`:135-143`), then commits a claim with `run_id` and `run_attempt` and no video id, and pushes it to `ledger` before any upload (`:144-157`).
  - `upload`: read token and the `youtube` environment, which holds `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` and `YOUTUBE_REFRESH_TOKEN` (`:165`). Checks out `main` and `ledger` without credentials (`:172-182`), installs only hash-checked packages (`:189`), downloads the MP4 to `runner.temp` (`:191-194`), requires a claim from this run and attempt before the secret step (`:196-215`), re-checks the script blob and runs `pipeline/publish/youtube.py` (`:217-234`).
  - `record`: `contents: write`, no secret, checks out only `ledger` (`:249-252`). Requires a claim-only record from this run (`:271-276`). With a video id it fills in the record; with `sent=false` it deletes the claim; anything else keeps the claim and fails (`:279-295`). Scripts stay in `queue/approved/`; the ledger says what was published.

The repo has been **public** since 2026-11-21 (owner decision O1 option b). Code, handoffs, this threat model, workflow logs and artifacts are readable by anyone. Public repos get unmetered Actions minutes on standard runners.

## 2. Assets

| Asset | Why it matters | State now |
|---|---|---|
| Approval integrity | Workflow B publishes any approved script on `main` that is due and has no record on the ledger (`pipeline/publish/pick.py:47-52`). Anyone who can put a file in `queue/approved/` on `main` publishes under the owner's channel | Live |
| The approval PR (body and diff) | The owner approves on what the PR shows. Now public: anyone can read and comment | Exists (`pipeline/script/batch.py:196-230`) |
| YouTube OAuth client id, client secret and refresh token | Together they mint access tokens that post public videos on the channel. Scope `youtube.upload` only. Per the YouTube API reference, `videos.update` and `videos.delete` need broader scopes, so a thief can post but not edit or delete (confirmed 2026-11-22 (p4-audit)) | Environment secrets on `youtube` (owner setting, section 7) |
| Derived access token | About an hour of the same upload power | Exists only inside the upload step; masked (`pipeline/publish/youtube.py:153`) |
| `GEMINI_API_KEY` | Quota theft. Cost only if its Google project ever gets billing | Repo secret (D1 option c), allowlisted for `generate` |
| The publish ledger (`ledger` branch, `data/published/`) | The only record of what went out. Scripts never leave `queue/approved/`, so the ledger alone stops a republish. A claim with no video id stops publishing (`pick.py:41-46`) | Live once the owner bootstraps the branch (section 7) |
| Hand-curated sources (`sources/*.yaml`) | The only input the writer sees | 14 files, owner-reviewed |
| The channel and its standing | A strike, a spam flag or an inauthentic-content review ends or demonetises the project | Live from the first upload |
| `main` branch | Every scheduled workflow runs main's code. The `youtube` environment admits only `main`, so `main` is the gate to the publishing token | Yes |
| Actions minutes | Unmetered while the repo is public. If it goes private again: about 2,000 a month with no payment method; production alone is about 280 (p4-plan, Actions minutes), and the 2026-11-21 overrun shows development can exceed it | Unmetered now |
| Gemini free daily quota | When it runs out, the weekly batch leaves scripts out or opens no PR | From the first live run |
| YouTube upload quota | One `videos.insert` a day against the upload bucket; not a constraint | Live |
| Pinned model weights | Loaded through pickle | Yes |
| Instagram and TikTok tokens, the IG refresh PAT; Cloudflare, Pexels, Pixabay keys | Not present (later Phase 4b work and Phase 3) | No |

No payment method exists on any account (PLAN.md section 3), so a stolen key or token cannot create a bill. That holds for each Google key only while its project has no billing account.

## 3. Trust boundaries

1. **The owner.** Reviews and merges every PR, holds every account and every setting in section 7.
2. **Claude Code agent sessions** on the owner's PC. They run with the owner's git and `gh` credentials, so they can push branches, push to `main` and `ledger`, merge PRs, dispatch workflows and re-run failed jobs unless a deny rule or ruleset stops them.
3. **GitHub Actions runners.** Execute whatever workflow file is on the pushed or dispatched ref.
4. **Upstream code and data.** PyPI, the PyTorch CPU index, Hugging Face, the whisper model URL, the spaCy model release URL, the Ubuntu mirror, GitHub release downloads, Dependabot PRs.
5. **Source files into the writer.** Hand-curated and owner-reviewed.
6. **Model output (Gemini) into scripts and the PR body.** Untrusted data.
7. **The Workflow A artifact** from `generate` to `validate` and `open-pr`.
8. **External APIs.** Gemini; Google's OAuth token endpoint and the YouTube upload endpoint.
9. **Workflow B job hand-overs.** `render` to `upload` (the MP4 artifact and the `script_id` and `script_blob` outputs) crosses from the render job into the token job. `upload` to `record` (`video_id`, `sent`) crosses from the token job into a write job.
10. **The `ledger` branch into Workflow B.** Records are data read by `render` (pick, in Python), `claim`, `upload` and `record` (shell and jq). Anyone with repo write access can push to it.
11. **The public.** Anyone can read the repo, logs and artifacts, comment on PRs and open fork PRs. Fork PR runs get a read token and no secrets.

## 4. STRIDE by boundary (as built)

### 4.1 Script JSON into the render (boundary 6, rendered side)

Unchanged from version 2 in substance; references updated.

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | Command injection: a script word or title containing shell metacharacters reaches a shell | Low / high | **Mitigated.** FFmpeg and ffprobe run from argument lists, never a shell (`pipeline/render/compose.py:124`, `pipeline/render/qa.py:94`). |
| Tampering | Filtergraph injection through the captions path | Low / medium | **Mitigated.** `pipeline/render/compose.py:34-35` escapes for the option parser and quotes for the filtergraph. Paths are built by the pipeline. |
| Tampering | ASS injection through override tags or a newline | Medium / low (visual only) | **Mitigated.** `pipeline/render/captions_ass.py:34` escapes `\`, `{`, `}`; narration is whitespace-collapsed (`pipeline/schema.py:57`); control characters are rejected before the voice step (`pipeline/script/validate.py:54-66`, `pipeline/render_one.py:37-40`). |
| Tampering | Path traversal through `id` | Low / medium | **Mitigated.** `pipeline/schema.py:42` restricts `id` to `[a-z0-9-]`; every Workflow B job re-checks it with the same pattern (`daily_publish.yml:65`, `:120`, `:201`, `:226`, `:263`). |
| Denial of service | A very long script runs Kokoro and FFmpeg to the 45 minute timeout | Medium / low | **Mitigated.** Caps checked before any step (`pipeline/script/validate.py:69-120`, `pipeline/render_one.py:37-40`). |
| Information disclosure | The `render.yml` `script` input is any path; a non-JSON file's content can appear in the error | Low / low | **Accepted.** No secret on disk, `persist-credentials: false`, only repo writers can dispatch. |

### 4.2 Upstream code and weights into the runner (boundary 4)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | A poisoned Kokoro checkpoint (pickle) | Low / high | **Mitigated.** Pinned revision and sha256 checked before load (`pipeline/voice/kokoro.py:76-87`, `pipeline/constants.py:21-27`). |
| Tampering / EoP | A poisoned whisper `small.en` checkpoint | Low / high | **Mitigated by upstream behaviour only.** openai-whisper checks its own sha256 while pinned. |
| Tampering / EoP | Dependency confusion between the PyTorch index and PyPI | Low / high | **Mitigated.** torch installs alone with `--no-deps` from the CPU index, then everything else from PyPI only (`daily_publish.yml:50-53`, `render.yml:35-38`; `tests/workflow_rules.py:138-148`, called from `tests/test_daily_publish_workflow.py:84`). |
| Tampering / EoP | A malicious transitive release in a job that holds a secret | Low / high | **Mitigated for both secret jobs.** `generate` and `upload` install only `requirements-generate.txt` with `--require-hashes` (`weekly_scripts.yml:34`, `daily_publish.yml:189`); no heavy or torch install in `upload` (`tests/test_daily_publish_workflow.py:132-137`). The secret job restores no cache (`tests/test_daily_publish_workflow.py:144-147`). Residual, accepted: a Dependabot PR that bumps a hashed pin brings the new release's hash with it; the owner's review of that PR is the only check. |
| Tampering | **P1-4 heavy half: a malicious release in the render job's dependencies alters the video that gets published.** Nobody watches the video before it goes public at 14:07, and the render's QA runs in the same process. The worst script choice is another approved one on `main`: `claim` and `upload` re-check the blob (`daily_publish.yml:140-143`, `:230-233`) | Low / high (a public scam or policy-breaking video under the channel's name, possibly a strike) | **Mitigated, with residuals (P4b-1). Go-live gate stays until the Linux proof is recorded.** Both render paths install only from `requirements-render-torch.txt` and `requirements-render.txt` with `--require-hashes` (`daily_publish.yml:50-53`, `render.yml:35-38`, held by `tests/test_render_lock.py:107-111`). Residuals: (a) the p4b-render-lock handoff is still `partial` and records no green `render.yml` run on Linux; (b) openai-whisper and stable-ts ship only sdists (`requirements-render.txt:4-6`), so pip builds them in an isolated environment whose build backend (setuptools, wheel) comes from PyPI without hash checks: still unhashed code in the render job; (c) their dependencies were added by hand from a Windows resolve, so a Linux-only dependency could be missing (fails closed: the install fails). Since 2026-11-25 the `lock-resolve` job in `ci.yml` resolves the locks on Linux for every push and PR. Its dry run builds the two sdists (openai-whisper, stable-ts) with unhashed build dependencies, as `render.yml` does; the job holds no secret and a read-only token. |
| Tampering | The render job's pip cache is seeded by an unhashed install. `weekly_audit.yml` and `ci.yml` install without hashes on `main` and save the pip cache under the same `requirements*.txt` key (`weekly_audit.yml:36-37`, `:57-58`) that `render` restores (`daily_publish.yml:42-43`) | Low / high | **Mitigated for wheels, residual in P4b-1.** `--require-hashes` rejects any cached wheel whose hash differs. A wheel that pip built from one of the two sdists with an unhashed backend, then cached, is the same residual as P4b-1 (b). GitHub cache scoping keeps branch and fork caches away from `main` runs. |
| Tampering | Compromised third-party Action | Low / high | **Mitigated.** Every `uses:` pinned to a full commit SHA (`tests/workflow_rules.py:88-90`), every workflow included; gitleaks and actionlint are sha256-checked (`ci.yml:101-102`). |
| Tampering | Compromised apt package (ffmpeg, espeak-ng) | Very low / high | **Accepted.** Signed Ubuntu mirror, not pinned. Not installed in any secret job. |
| Tampering | The weekly audit installs unhashed packages (`weekly_audit.yml:60-73`) | Low / low | **Accepted.** Read token, no secret, no artifact, nothing published; a red run is its only output. |

### 4.3 Actions runners and workflows (boundary 3)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP | A step writes to the repo with the job token | Low / high | **Mitigated.** Workflow-level `contents: read` (`tests/workflow_rules.py:109-110`); job write permissions only through `WRITE_JOBS` (`tests/workflow_rules.py:32-36`, `:81-83`): `open-pr`, `claim` and `record`. `claim` and `record` run no `python` or `pip` and turn git hooks off (`tests/test_daily_publish_workflow.py:104-112`; `daily_publish.yml:116-118`, `:259-261`). Checkouts keep no credentials outside those jobs (`tests/workflow_rules.py:95-98`). In `claim` the credentials go to the `ledger` checkout only (`daily_publish.yml:100-109`, `tests/test_daily_publish_ledger.py:104-105`). |
| EoP / Information disclosure | A secret reaches a job that can write | Low / high | **Mitigated.** Secrets only through `SECRET_JOBS` (`tests/workflow_rules.py:37-40`): `generate` and `upload`; no job is in both lists (`tests/test_workflow_safety.py:272`); the three YouTube secrets sit in exactly one step's env (`tests/test_daily_publish_workflow.py:122-123`, `daily_publish.yml:222-224`). |
| Tampering | Expression injection through a branch name, input or job output | Low / high | **Mitigated.** No `${{ }}` inside `run:` (`tests/workflow_rules.py:91-93`). Workflow B has no dispatch inputs (`tests/test_daily_publish_workflow.py:54`); every job output reaches the shell through `env:` and is regex-checked by each consumer (`daily_publish.yml:65-73`, `:120-127`, `:201-204`, `:226-229`, `:263-266`, `:280-283`). The run numbers come from the runner, are regex-checked and enter jq as `--argjson` (`:129-132`, `:145-148`, `:205-212`, `:267-273`); no step overrides a `GITHUB_*` variable (`tests/test_daily_publish_ledger.py:133-143`). |
| Information disclosure / EoP | `pull_request_target` runs untrusted PR code with secrets | Low / high | **Mitigated.** Forbidden (`tests/workflow_rules.py:111-112`). |
| EoP | **P1-1: a pushed or dispatched branch runs its own workflow copy with the publishing token.** Scenario: an agent session pushes a branch whose `daily_publish.yml` drops the `if:` at `:22` and adds a step that posts `secrets.YOUTUBE_REFRESH_TOKEN` to an outside host, then dispatches it. `SECRET_JOBS` and `ENVIRONMENT_JOBS` fail in CI on that branch, which is detection after the run, not prevention | Medium / critical | **YouTube: owner setting.** The secrets are environment secrets on `youtube` (`daily_publish.yml:165`), the only job allowed to name an environment (`tests/workflow_rules.py:44-46`, `:84-86`). The control that holds is the environment's deployment rule allowing `main` only (section 7, item 1). The residual is that `main` is allowed, so P1-1 reduces to P1-2. **Gemini key: Accepted** under D1 option (c), with the version 2 conditions (own AI Studio project, no billing, API-restricted, rotate on doubt). |
| Denial of service | **P1-5: CI drains the minutes.** | Was medium / medium | **Closed.** `ci.yml` pushes only on `main` and `scripts/**` (`ci.yml:7-8`); one group per PR with newer runs cancelling older ones, every other run in its own group (`ci.yml:15-17`). Workflows A and B each never overlap with themselves (`weekly_scripts.yml:12`, `daily_publish.yml:13-15`); each weekly audit run has its own group (`weekly_audit.yml:17-19`). |
| Information disclosure | Workflow logs and artifacts are public | Low / low | **Accepted.** The `weekly-scripts` artifact holds what the public approval PR shows anyway. `final-video` is kept 1 day (`daily_publish.yml:87`) and goes public at upload. Upload logs, next row. Log and artifact retention of 30 days or less is an owner setting (F8, section 7). |
| Information disclosure | **Upload logs are public.** | Low / low | **Mitigated, with an accepted residual.** Log records hold the step, HTTP status and the video id (`youtube.py:222`, `:235`, `:241`); the access token is masked before it is used (`:153`); the three secrets are masked by GitHub. Residual: the error on stderr (`:294`) carries the step, status and up to 200 characters of Google's response body, after the client secret, refresh token, access token, session URL and its `upload_id` are redacted in plain, URL-encoded and JSON-escaped forms, longest first (`:99-104`, `:256-264`). Two secrets that partly overlap can still leave a fragment; that text is Google's error message. |
| Tampering | **Workflow command injection through the access token.** A token answer holding a newline would end the `::add-mask::` line, leave the rest unmasked or inject a workflow command | Very low / medium | **Mitigated.** The access token must match `[\x21-\x7e]+` before it is masked or used (`youtube.py:27`, `:150-153`), else `sent=False` with no token in the message (`tests/publish/test_youtube_placement.py:99-111`). The three secrets are stripped of outer whitespace (`youtube.py:121`). |

### 4.4 Agent sessions and `main` (boundary 2)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP / Tampering | **P1-2: anything pushed to `main` reaches the publishing token on the next scheduled run.** Scenario: an agent session pushes straight to `main` a change to `pipeline/publish/youtube.py` that sends the refresh token to an outside host, or a script into `queue/approved/`. At 14:07 the `youtube` environment admits the run, because it is `main` | Medium / critical | **Repo half mitigated; the rest is an owner setting and a go-live gate.** The ledger moved to a bot-only branch, so Workflow B needs no push to `main` and no ruleset bypass: every push in the workflow names `ledger`, and only `claim` and `record` push (`daily_publish.yml:154-157`, `:296-299`; `tests/test_daily_publish_ledger.py:123-130`). What closes P1-2 is the `main` ruleset (PR and the `check` job required, no bypass list) plus the agent deny rules (section 7, items 2 and 3). The orchestrator state on 2026-11-23 lists them as not yet on. |
| Tampering (approval bypass) | A file lands in `queue/approved/` on `main` by any path other than a merged owner-reviewed PR | Medium / critical | **Owner setting (P1-2).** `pick` takes any approved, due file with no record (`pick.py:47-52`). The `main` ruleset requiring PRs makes every human commit on `main` a merge. Task branches touching `queue/` already fail the scope check (`ci.yml:47-62`). |
| Tampering | An agent dispatches `daily-publish` from `main` with the owner's `gh`, or re-runs it | Low / medium | **Owner setting.** A dispatch publishes only an approved, due script (`pick.py:49`) and runs are serialised, but repeated dispatches publish several due scripts in one day, ahead of the cadence. Deny rules for agent `gh workflow run` and `gh run rerun` (section 7, item 3). |
| Tampering | A task branch edits `ci.yml` to drop the scope check | Low / high | **Accepted.** The owner reads every change under `.github/workflows/` line by line. |
| Spoofing | An owner message typed in a task window is misread as a decision | Medium / medium | **Mitigated** by process (lessons.md 2026-11-15). |
| Repudiation | Which session or run made which change | Low / low | **Mitigated.** Git history, handoffs, the outcome log; Workflow A and B commit as `github-actions[bot]` with fixed messages (`daily_publish.yml:152`, `:288`, `:291`), and each claim names its `run_id` and `run_attempt` (`:145-148`). |

### 4.5 Sources and model output into scripts (boundaries 5 and 6)

Unchanged from version 2 except the `youtube.py` references. The approval PR is public, see 4.10.

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering | Prompt injection through a source fact | Low / high | **Mitigated, with residuals.** Facts in a delimited data block (`pipeline/script/generate.py:43-46`, `153-165`; `pipeline/factcheck/semantic.py:82-90`); answers pass `validate.problems` and cite only the source's fact ids (`generate.py:119-122`, `168-172`); exact and meaning fact-checks (`batch.py:117-156`); fact text bans links and invisible characters (`tests/test_sources_files.py:38-52`). `upload` runs `validate.problems` again before any request (`youtube.py:94-96`). |
| Tampering | A link that the URL check misses | Low / high | **Mitigated; P2-3 closed.** `pipeline/script/validate.py:24-66`. Residuals accepted as in version 2 (spelled-out or spaced domains, bare IPv4, some visible marks). The fixed credit line is appended after validation and uses names, not links (`pipeline/constants.py:131-135`). |
| Tampering (approval bypass) | The PR shows less than what gets published | Medium / high | **Mitigated; P1-3 closed.** PR body shows every published field verbatim (`batch.py:180-193`). `on_screen_text` is not rendered and not uploaded (Phase 3 seed). |
| Tampering | PR body injection (Markdown, HTML, mentions) | Medium / medium | **Mitigated.** Model text in code spans (`batch.py:159-177`, `191-193`). Fact text accepted while sources stay owner-reviewed. |
| Denial of service | An oversized PR body | Low / low | **Mitigated, fails closed** (`batch.py:228-229`). |
| Tampering | The artifact changes already-approved scripts | Low / high | **Mitigated; P2-2 closed** (`weekly_scripts.yml:69-102`, `:136-169`). |
| Tampering (approval bypass) | The approval PR gets no CI before merge | Low / medium | **Mitigated; P2-4 closed** (`weekly_scripts.yml:53-114`). With the `main` ruleset on, the bot-opened PR's CI run waits for the owner's approval before it can merge. Verify on the first live run. |
| Spoofing | A source cites an HTTP or lookalike page | Low / medium | **Mitigated** (`pipeline/schema.py:104`); lookalikes left to review. |
| Tampering | Gemini output tells the checker to pass every line | Low / medium | **Mitigated** (`semantic.py:82-90`, `batch.py:125-127`). |

### 4.6 Gemini API (boundary 8)

Unchanged from version 2: key only in a header with redacted errors (`pipeline/script/gemini.py:59-80`, `105-111`), redirects refused (P2-5 closed, `gemini.py:24-31`), quota exhaustion mitigated for overlap (P2-6 closed, `weekly_scripts.yml:12-14`), billing on the key's project is an owner action, a wrong model id fails loudly.

### 4.7 The Workflow A artifact (boundary 7)

Unchanged from version 2: `open-pr` runs only `git` and `gh` on files extracted to `runner.temp` (Mitigated); separate checkouts in `generate` and `open-pr` (Accepted).

### 4.8 Workflow B: publish path and YouTube API (boundaries 8 and 9)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Spoofing / EoP | **OAuth token theft from the upload job.** Code in that job reads the env and posts the tokens out | Low / critical | **Mitigated in the repo** (the branch and `main` paths are P1-1 and P1-2). The job installs hashed packages only (`daily_publish.yml:189`) and restores no cache; checks out without credentials (`:172-182`); reads the script from its own `main` checkout and re-checks its blob (`:230-233`); treats the artifact as bytes in `runner.temp` (`:191-194`, `youtube.py:209`) and reads the ledger with jq only (`:209-212`). |
| Information disclosure | The access token or secrets go to a host other than Google | Very low / critical | **Mitigated.** Fixed endpoints (`pipeline/constants.py:122-125`); one opener refuses every redirect (`youtube.py:30-37`, `:231`); the resumable session URL must be `https` on exactly `www.googleapis.com`, port 443 at most, no user info, before the bearer token is sent to it (`youtube.py:190-193`, `:197-204`). |
| EoP | The refresh token carries broader rights than upload (owner ticks a wider scope in the Playground) | Low / high | **Mitigated, fails closed.** The token answer's scope set must equal `youtube.upload` exactly (`youtube.py:147-148`, `pipeline/constants.py:126`). Consent screen limited to that scope (owner setting). |
| Tampering | Published metadata differs from the approved script | Low / high | **Mitigated.** Metadata comes from `main`'s copy, whose blob must equal the rendered one (`daily_publish.yml:230-233`); `validate.problems` runs again (`youtube.py:94-96`); privacy, made-for-kids, synthetic-media and paid-placement flags are sent explicitly from constants (`youtube.py:166-174`). The video itself is P1-4 heavy half (4.2). |
| Tampering | A crafted API answer injects a second line into `$GITHUB_OUTPUT` (for example a fake `video_id`) that `record` commits | Very low / medium | **Mitigated.** The id must match `[A-Za-z0-9_-]{11}` before it is written (`youtube.py:26`, `:220`, `:291`); `record` checks it again (`daily_publish.yml:280-283`) and compares `sent` literally (`:289`). |
| Tampering | The ledger records a script version that was never rendered or uploaded | Low / medium | **Mitigated.** The blob is fixed at pick (`:69`) and re-checked by `claim` (`:140-143`) and `upload` (`:210-212`, `:230-233`); the claim stores it (`:145-148`) and `record` only adds the video id and time (`:284-286`). |
| Tampering (at most once) | A run uploads twice, or uploads with no claim on the ledger | Medium / medium | **Mitigated.** Claim pushed to `ledger` before any upload (`:144-157`); a second run that claimed the same script first makes the rebase conflict and the push fail (`tests/test_daily_publish_ledger.py:391`); `upload` requires the claim, unconfirmed and with a matching blob, before the secret step (`:196-215`); `record` keeps the claim on an unknown outcome (`:292-295`); the next `pick` refuses while any claim lacks a video id (`pick.py:41-46`). "Re-run all jobs" re-runs `render`, whose `pick` refuses. **P4-2 closed:** the `ref: main` and `ref: ledger` checkouts and the guard running before the only step with the secrets are held by a locked test (`tests/test_daily_publish_ledger.py:86-93`, `:108-112`). |
| Tampering (at most once) | **P4-1: "Re-run failed jobs" after an unknown outcome uploads a second copy.** Scenario: the PUT times out after YouTube received the bytes; `record` keeps the claim and fails; someone re-runs the failed jobs | Medium / medium | **Mitigated; P4-1 closed in the repo.** The claim stores `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` (`daily_publish.yml:129-132`, `:145-148`); `upload` refuses unless both equal its own (`:205-215`; `tests/test_daily_publish_ledger.py:441`, `:133-143`). GitHub documents that `run_attempt` increments with each re-run while `run_id` stays (quoted in `p4b-plan.md`, F1 evidence); not yet seen on a live "re-run failed jobs". `record` checks `run_id` only (`:271-276`), so a re-run of just `record` after a failed push still records the earlier attempt's upload, and cannot send anything. **Accepted** trade-off: a failure before the upload step leaves a claim with nothing sent, which is now a manual reconcile. **Owner setting:** the deny rule on agent `gh run rerun`. |
| Tampering | Someone deletes a kept claim by hand to unblock publishing without checking the channel, and the next run uploads again | Low / medium | **Accepted, runbook.** `pick.py:41-46` names the script and says to check the channel first. |
| Repudiation | Later, nobody can tell which approved version was published | Low / medium | **Mitigated.** The record holds `script_sha`, the video id, the time and the run (`daily_publish.yml:145-148`, `:284-286`); the script stays unchanged in `queue/approved/`, so its blob equals `script_sha`. |
| Denial of service | A revoked or expired refresh token, an API error, an expired artifact | Medium / low (a missed day) | **Accepted, fails visibly.** `invalid_grant` says the token must be made again (`youtube.py:251-252`); a failure before any byte is `sent=false` and the claim is released (`daily_publish.yml:289-291`). A failure before the upload step (artifact gone after 1 day, the claim check) leaves no outputs, so `record` keeps the claim though nothing was sent: the step log shows it. Every failure is a red run and a failure email (owner settings). No retry inside the upload by design. |
| Spoofing | Unofficial upload methods get the account banned | Low / critical | **Mitigated.** Official `videos.insert` resumable upload only (`pipeline/constants.py:123`). |
| Information disclosure | Publish responses or tokens end up in an artifact | Low / high | **Mitigated.** The only artifact is `final.mp4` from `render` (`daily_publish.yml:82-87`, `tests/test_daily_publish_workflow.py:89-92`); `upload` uploads none. |

### 4.9 The `ledger` branch (boundary 10)

New in version 3.1. The ledger is data only: no job runs anything from it, and every workflow that touches it comes from `main`.

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | **Who can push to `ledger`.** The owner; agent sessions with the owner's git credentials; and any workflow on any branch whose job asks for `contents: write`, including a workflow file committed to `ledger` itself, which runs on its own push. `WRITE_JOBS` catches such a job only in CI after it ran. Until the `main` ruleset is on, the same job can push `main` too (P1-2) | Medium / medium | **Owner setting.** The `ledger` ruleset blocks deletion and force pushes (section 7, item 2); "restrict updates" is left off because it would block the bot. Agent deny rule on `git push` to `ledger` (item 3). A workflow on `ledger` gets no YouTube secret: the `youtube` environment admits `main` only (item 1). The Gemini key is readable by any branch run (D1 option c, Accepted). |
| Tampering | **A deleted completed record republishes its script.** Scripts never leave `queue/approved/`, so with the record gone `pick` sees a due script with no record (`pick.py:47-52`) and the next run uploads it again. Scenario: the owner follows the kept-claim runbook but deletes the wrong file, or a writer resets a record's `youtube_video_id` to null and then deletes it as a "stuck claim". Restricting deletions protects the branch, not files inside commits | Low / medium (a duplicate public video, a spam signal) | **Accepted, runbook.** Only claim-only records may be deleted, after checking the channel. A forced push back to an older ledger is blocked by the ruleset (owner setting). |
| Tampering / DoS | **A forged record.** A forged claim-only record stops all publishing until the owner checks (`pick.py:41-46`). A forged completed record skips its script for good. Neither can choose what is sent: the script comes from `main` behind the blob check (`daily_publish.yml:230-233`), and `upload` sends only with a claim from its own run and attempt (`:205-215`) | Low / low | **Accepted.** Fails visibly or skips one script. Needs repo write access, which already allows worse. |
| Tampering / Information disclosure | **A symlinked record.** A record that is itself a symlink is refused by `claim` (`daily_publish.yml:135`), `upload` (`:210`, `tests/test_daily_publish_ledger.py:449`) and `record` (`:272`). `pick` follows it (`pick.py:57-59`): a link to a non-JSON runner file fails the parse, and pydantic's error can quote the start of that file in the public render log. A symlinked parent folder (`data/` or `data/published/`) is not checked by any step | Low / low | **Accepted, untested.** Expected to fail closed: a link to anything but valid records fails the parse in `pick`, and `git add` refuses a path beyond a symlink in `claim` (`:151`) and `record` (`:287`, `:290`). The render job holds no secret and no write token, so a file it can read is no more than the runner image. Needs repo write access. |
| Denial of service | The `ledger` branch is missing (not bootstrapped, or deleted) | Low / low | **Mitigated, fails closed.** The `ref: ledger` checkout in `render` fails and nothing is claimed (`daily_publish.yml:33-37`); `pick` also refuses a missing records folder (`pick.py:38-39`). |
| EoP | Code execution from ledger content in a write job (git hooks, attributes) | Very low / high | **Mitigated.** Hooks are off in every git call of `claim` and `record` (`daily_publish.yml:116-118`, `:259-261`; `tests/test_daily_publish_ledger.py:555`); the write jobs run no `python` or `pip` (`tests/test_daily_publish_workflow.py:104-107`); the record is read with jq only. |

### 4.10 The public (boundary 11)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | A fork PR adds a script to `queue/approved/` or edits a workflow | Medium / critical if merged | **Mitigated with an owner setting.** Fork runs use `pull_request` with a read token and no secrets (`pull_request_target` forbidden, `tests/workflow_rules.py:111-112`); the owner merges nothing from outside. A fork PR that touches `requirements*.txt` also triggers the weekly audit, which holds no secret either. Owner setting: require approval for fork runs from all outside contributors (section 7, item 4). |
| Spoofing | A stranger comments on the approval PR with a "correction" or link the owner adopts | Low / medium | **Accepted.** Edits on the PR re-run CI (`ci.yml:7-9`), and the URL rules still apply to anything published. |
| Information disclosure | The public repo shows this threat model's open gaps and ties the code to the channel | Medium / medium | **Accepted** with O1 (b); the history was scanned before going public. It is one more reason to close P1-2 before go-live. The channel never links the repo (owner decision F3). |

## 5. Seeded threats for Phases 3 and 4b

The Phase 4 seeds of version 2 for YouTube are rows in sections 4.3, 4.4 and 4.8.

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
| Tampering | A second platform publishes from the same ledger | Its own record field or file per platform, with the same claim-before-upload and run binding |

## 6. Open gaps, ranked

| ID | Severity | Gap | Must be closed before |
|---|---|---|---|
| P1-2 | **Critical** until the owner settings are on | Repo half done (no push to `main` from Workflow B). Open: the `main` ruleset with no bypass, the `ledger` ruleset and the agent deny rules (section 7, items 2 and 3) | Go-live |
| P1-1 | High, owner setting | YouTube: the `youtube` environment's main-only rule (unverified, section 7). Gemini: accepted under D1 (c) | Go-live (verify the setting) |
| P1-4 | Medium, residual P4b-1 | Render installs are hash-checked. Open: no recorded green Linux run of the lock, and the two sdists build with an unhashed backend | Go-live: the Linux proof. The build backend: next lock regeneration |
| P4b-1 | Low | openai-whisper and stable-ts build from sdist under build isolation, so setuptools and wheel come from PyPI without hashes into the render job; a cached wheel built that way is reused | Next edit of the render locks |
| P4-1 | | Closed by the run binding (`daily_publish.yml:205-215`); live confirmation of `run_attempt` on a re-run is pending | (closed) |
| P4-2 | | Closed by `tests/test_daily_publish_ledger.py:108-112` | (closed) |
| P1-5 | | Closed by p2d-ci-triggers (`ci.yml:7-17`); the repo is unmetered while public | (closed) |
| P1-3, P1-6, P2-1 to P2-6 | | Closed in version 2 | (closed) |

## 7. Owner sign-off checklist (settings outside the repo)

None of these can be seen from the repo. Confirm each before signing off.

1. The `youtube` environment exists, holds the three `YOUTUBE_*` values as environment secrets, and its deployment branches are `main` only. No repo-level secret with those names.
2. Rulesets, turned on after the ledger workflow merged:
   - The orphan `ledger` branch exists, bootstrapped as in `p4b-plan.md` (otherwise every daily run fails at the render checkout).
   - `main`: restrict deletions, block force pushes, require a pull request and the `check` status, no bypass list. Closes P1-2.
   - `ledger`: restrict deletions, block force pushes, no bypass. Not "restrict updates", which would block the bot.
3. Claude Code deny rules for agent sessions: `git push` to `main` and to `ledger`, `gh pr merge`, `gh run rerun`, and `gh workflow run` of `daily-publish`. Owner-only settings.
4. Fork PR runs need approval for all outside contributors.
5. Google: the YouTube Cloud project is separate from the Gemini AI Studio project, with no billing account on either; the consent screen is In production with only the `youtube.upload` scope; the Playground redirect URI was removed after the token was made.
6. Failure emails for Actions are on, for the account that last edited the cron. Artifact and log retention is 30 days or less (F8).
7. `daily-publish` stays disabled until go-live (the orchestrator state on 2026-11-23 says it is still active). The render lock's Linux proof (a green `render.yml` run with QA passed) is recorded before go-live.
8. Runbook: with a kept claim, never re-run failed jobs; check the channel, then fill in or delete the claim-only record on `ledger`. Never delete a record that holds a video id. On any doubt about the tokens: revoke the app in the Google account's third-party access page, reset the client secret, make a new refresh token and replace the environment secrets.
