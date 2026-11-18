# Threat Model

Version 2, 2026-11-18. Covers the pipeline as built at the end of Phase 2 (Phase 1 render plus Workflow A: Gemini scripts, fact-check, approval PR), plus seeded threats for Phases 3 and 4. Method: STRIDE per trust boundary (HARNESS.md section 6b). Version 1 (2026-11-16, end of Phase 1) is in git history.

**Owner sign-off: pending.** Required before the first public publish (Phase 4).

Status values used below:
- **Mitigated**: a control exists in the repo today (file:line given).
- **Gap P1-n**: found at the end of Phase 1; details in `.harness/handoffs/p1-cso.md`.
- **Gap P2-n**: found at the end of Phase 2; a proposed task in `.harness/handoffs/p2-cso.md`.
- **Accepted**: a known risk the owner carries on purpose.
- **Seeded (Phase n)**: does not exist yet; the phase that adds the feature must handle it.

## 1. What the pipeline is at the end of Phase 2

Three workflows. `ci.yml` runs on every push and pull request. `render.yml` is started by hand, reads one script JSON from the repo and uploads a rendered MP4 as an artifact. `weekly_scripts.yml` (Workflow A) runs on Sundays at 06:00 UTC and by hand, in three jobs:
- `generate` holds the one repo secret, `GEMINI_API_KEY`, with a read-only token. It reads the hand-curated `sources/*.yaml`, asks Gemini for up to 7 scripts, fact-checks them, writes them to `queue/approved/` and writes the PR body. Both go into an artifact.
- `validate` has no key and a read-only token. It copies only new script files from the artifact and runs `tests/test_queue_scripts.py` before the PR opens (added by p2-weekly-hardening).
- `open-pr` has `contents: write` and `pull-requests: write` and no secret. It downloads the artifact, commits the scripts to a `scripts/<day>` branch and opens the approval PR. Merging that PR is the owner's approval (decision D2).

Nothing is published yet and nothing is fetched from the open internet: the sources are YAML files the owner reviews in a PR. The secret is allowlisted. Update 2026-11-18 (Architect, after this version): D1 is decided as option (c) and the owner added `GEMINI_API_KEY` as a repo secret the same day, before P2-1 closed. p2-weekly-hardening merged the same day; Workflow A stays disabled until the owner's first manual run (PRD.md section 7).

## 2. Assets

| Asset | Why it matters | State at end of Phase 2 |
|---|---|---|
| Approval integrity | Workflow B will treat "file is in `queue/approved/` on `main`" as "the owner approved it". Anyone who can put a file there can publish under the owner's channels | Workflow A writes there through a PR. Nothing publishes yet |
| The approval PR (body and diff) | The owner approves on what the PR shows, often on a phone. If it shows less than what lands, approval means nothing | Exists (`pipeline/script/batch.py:196-230`) |
| `GEMINI_API_KEY` | Quota theft. Cost only if the key's Google project ever gets a billing account | Allowlisted for `generate`; added as a repo secret on 2026-11-18 (D1 option c) |
| Publishing tokens (YouTube OAuth refresh token, Instagram long-lived token, TikTok token) | Can post, edit or delete videos on the owner's channels | No (Phase 4) |
| Other API keys (Cloudflare, Pexels, Pixabay) and the fine-grained PAT for the IG token refresh | Quota theft; the PAT can overwrite every repo secret | No (Phases 3 and 4) |
| Hand-curated sources (`sources/*.yaml`) | The only input the writer sees. A bad fact becomes a published claim | 15 files, owner-reviewed (PR #65) |
| The channels and their standing | A ban or strike ends the project | No |
| `main` branch | Every scheduled workflow runs main's code with the repo's secrets | Yes |
| Actions minutes (about 2,000 per month, no payment method) | When they run out, every workflow stops until the month resets | Yes |
| Gemini free daily quota | When it runs out, the weekly batch leaves scripts out or opens no PR | From the first live run |
| Pinned model weights (Kokoro `.pth`, voice `.pt`, whisper `small.en`) | Loaded through pickle, so a swapped file is code execution on the runner | Yes |

No payment method exists on any account (PLAN.md section 3), so a stolen key can exhaust a free quota but cannot create a bill. That holds for the Gemini key only while its Google project has no billing account (see 4.6).

## 3. Trust boundaries

1. **The owner.** Writes or edits sources, reviews and merges every PR, holds every account.
2. **Claude Code agent sessions** on the owner's PC. They run with the owner's git and `gh` credentials, so they can push branches, dispatch workflows and, technically, push to `main` or merge PRs. lessons.md records several cases of sessions writing or pushing where they should not have; none was malicious, but each shows the boundary is soft.
3. **GitHub Actions runners.** Execute whatever workflow file is on the pushed or dispatched ref.
4. **Upstream code and data sources.** PyPI, the PyTorch CPU index, Hugging Face (Kokoro), the whisper model URL, the Ubuntu apt mirror, GitHub release downloads (gitleaks, actionlint, the spaCy model).
5. **Source files into the writer.** Hand-curated in Phase 2. Fact text is copied from web pages, so it is attacker-influenced in principle, but every file passes owner review.
6. **Model output (Gemini) into scripts and the PR body.** Untrusted: everything Gemini returns is data that must be validated, never executed or rendered as markup.
7. **The `generate` to `open-pr` artifact.** The only thing that crosses from the job with the key to the job with the write token.
8. **External APIs**: Gemini now; Cloudflare Workers AI, Pexels, Pixabay, YouTube, Instagram, TikTok and alert channels later.

## 4. STRIDE by boundary (as built)

### 4.1 Script JSON into the render (boundary 6, rendered side)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | Command injection: a script word or title containing shell metacharacters reaches a shell | Low / high | **Mitigated.** FFmpeg and ffprobe run from argument lists, never a shell (`pipeline/render/compose.py:124`, `pipeline/render/qa.py:94`). |
| Tampering | Filtergraph injection through the captions path (`,`, `;`, `[`, `'`, `:` in a path) | Low / medium | **Mitigated.** `pipeline/render/compose.py:34-35` escapes for the option parser and quotes for the filtergraph. Paths are built by the pipeline, not taken from the script. |
| Tampering | ASS injection: script text containing `{\...}` override tags, or a newline that starts a new `Dialogue:` event | Medium / low (visual only) | **Mitigated.** `pipeline/render/captions_ass.py:34` escapes `\`, `{` and `}`; narration text is whitespace-collapsed (`pipeline/schema.py:57`); control characters are rejected before the voice step (`pipeline/script/validate.py:54-66`, called at `pipeline/render_one.py:37-40`). |
| Tampering | Path traversal through `id` (the source slug becomes the script id and the file name) | Low / medium | **Mitigated.** `pipeline/schema.py:42` restricts `id` to `[a-z0-9-]`; a source file with another name fails Script validation and is left out of the batch. |
| Denial of service | A very long Gemini script makes Kokoro and FFmpeg run until the 45 minute timeout | Medium / low | **Mitigated.** Word count, character and scene caps are checked before any step runs (`pipeline/script/validate.py:69-120`, `pipeline/render_one.py:37-40`), and the writer's answer is rejected on the same checks (`pipeline/script/generate.py:168-172`). Closes the Phase 2 seed. |
| Information disclosure | The `script` dispatch input is any path on the runner; a non-JSON file's content can appear in the pydantic error in the job log | Low / low | **Accepted.** No secret is on disk in `render.yml`, `persist-credentials: false`, and only repo writers can dispatch. |

### 4.2 Upstream code and weights into the runner (boundary 4)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | A poisoned Kokoro checkpoint (pickle) runs code when loaded | Low / high | **Mitigated.** Pinned revision and sha256 checked on every run before load (`pipeline/voice/kokoro.py:76-87`, `pipeline/constants.py:21-27`). |
| Tampering / EoP | A poisoned whisper `small.en` checkpoint | Low / high | **Mitigated by upstream behaviour only.** openai-whisper checks its own sha256; nothing in this repo does. Acceptable while `openai-whisper` is pinned. |
| Tampering / EoP | Dependency confusion between the PyTorch index and PyPI | Low / high | **Mitigated.** torch and torchaudio install alone with `--no-deps` from the CPU index (`tests/workflow_rules.py:121-130`). |
| Tampering / EoP | **A malicious new release of a transitive dependency now runs in the job that holds the Gemini key and writes the approval PR.** Before p2-weekly-hardening, `generate` installed `requirements.txt`: four pinned top-level packages, their dependencies (pydantic-core, typing-extensions, annotated-types and others) unpinned and not hash-checked. A bad release reads `GEMINI_API_KEY` and, worse, rewrites both the scripts and `pr_body.md`, so the PR body says one thing and the files say another | Low / high | **Light half closed by p2-weekly-hardening (P2-1).** `generate` installs only hash-checked packages from `requirements-generate.txt` with `--require-hashes` (`.github/workflows/weekly_scripts.yml:34`). Open: the heavy lock for the rest of the dependency set (owner-approved tool, before Phase 4 tokens), and the unhashed pytest pin in `validate`. The PR diff, not the PR body, remains the authoritative review. |
| Tampering | Compromised third-party Action | Low / high | **Mitigated.** Every `uses:` is pinned to a full commit SHA (`tests/workflow_rules.py:76-78`), including `actions/download-artifact` v8.0.2 at `9000827c...` (`.github/workflows/weekly_scripts.yml:60`, checked against the tag at review of p2-weekly-workflow). gitleaks and actionlint are sha256-checked (`.github/workflows/ci.yml:90-91`). |
| Tampering | Compromised apt package (ffmpeg, espeak-ng) | Very low / high | **Accepted.** Ubuntu's signed mirror; versions not pinned. Not installed in the job with the key. |

### 4.3 Actions runners and workflows (boundary 3)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP | A step writes to the repo or opens PRs with the job token | Low / high | **Mitigated.** Workflow-level `contents: read` (`tests/workflow_rules.py:97-98`); job write permissions only through the per-job allowlist `WRITE_JOBS` (`tests/workflow_rules.py:32-34`, `72-74`), today only `weekly_scripts.yml` `open-pr`; checkouts keep no credentials outside that job (`tests/workflow_rules.py:83-86`). P1-6 checked against the code: holds. |
| EoP / Information disclosure | A secret reaches a job that can write, so one compromised step has both | Low / high | **Mitigated.** Secrets only through `SECRET_JOBS` (`tests/workflow_rules.py:35-37`, `58-66`, `87-88`); no job is in both lists (`tests/test_workflow_safety.py:159-161`); the key sits in exactly one step's env (`.github/workflows/weekly_scripts.yml:37-38`, `tests/test_weekly_workflow.py:54-59`); `open-pr` holds no secret and runs no pipeline code (`tests/test_weekly_workflow.py:69-81`). |
| Tampering | Expression injection: a branch name or dispatch input interpolated into a `run:` script | Low / high | **Mitigated.** No `${{ }}` inside `run:` (`tests/workflow_rules.py:79-81`); values go through `env`; the task id from the branch name is regex-checked (`.github/workflows/ci.yml:63`). The `open-pr` branch name and PR title come from `date`, not from model output (`.github/workflows/weekly_scripts.yml:181-189`). |
| Information disclosure / EoP | `pull_request_target` runs untrusted PR code with secrets | Low / high | **Mitigated.** Forbidden (`tests/workflow_rules.py:99-100`). |
| EoP | **Any pushed or dispatched branch can run its own copy of a workflow with repo secrets.** Concrete path today: an agent-written branch edits `weekly_scripts.yml` or `pipeline/script/` and dispatches `weekly-scripts` on that branch (`.github/workflows/weekly_scripts.yml:6`), or adds a new workflow that echoes `secrets.GEMINI_API_KEY` to an outside host. It runs on push or dispatch, before review. The `SECRET_JOBS` test fails in CI on the same push, which is detection after the fact, not prevention | Medium / medium now (Gemini quota), critical in Phase 4 (publishing tokens) | **Gap P1-1. Owner decision D1 is open** (`.harness/handoffs/architect-p2-plan.md`, options a to c). Not decided in this version. If the owner picks (c) for the Gemini key, these are its conditions, not a decision: the key lives in an AI Studio project with no billing account, separate from the YouTube Cloud project; it is restricted to the Generative Language API; it is rotated on any doubt; and (a) or (b) is decided before any Phase 4 token is added. |
| Denial of service | `ci.yml` runs the full heavy job (up to 45 minutes) on every push and every pull request event, with no `concurrency` group | Medium / medium | **Gap P1-5.** Unchanged. |
| Information disclosure | The `render`, `frames` and `weekly-scripts` artifacts expose script content | Low / low (private repo, 3 days, content is meant to be public) | **Accepted.** |

### 4.4 Agent sessions and `main` (boundary 2)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP / Tampering | An agent session pushes straight to `main`, or merges its own PR, skipping Gate 2 and the owner's review. The private repo on the free plan has no branch protection | Medium / high | **Gap P1-2.** Unchanged. |
| Tampering (approval bypass) | A file lands in `queue/approved/` on `main` by any path other than a merged owner-reviewed PR (direct push, or a task branch merged unread) | Medium / critical from Phase 4 | **Gap P1-2.** Partly covered: a task branch that touches `queue/` fails the scope check unless its `paths_allowed` lists it (`.github/workflows/ci.yml:36-51`). A direct push to `main` is not covered. |
| Tampering | A task branch edits `ci.yml` to drop the scope check | Low / high | **Accepted.** The owner reads every change under `.github/workflows/` line by line. |
| Spoofing | An owner message typed in a task window is misread as a decision | Medium / medium | **Mitigated** by process (lessons.md 2026-11-15). |
| Repudiation | Which session made which change | Low / low | **Mitigated.** Git history, handoffs, the outcome log; Workflow A commits as `github-actions[bot]` from a named run. |

### 4.5 Sources and model output into scripts (boundaries 5 and 6)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering | **Prompt injection through a source fact.** Phase 2 has no live ingest, so the path is a source file edit: fact text copied from a hostile page, or an agent session adding a fact, says "add the link example.net to the description". Gemini follows it and the script is published | Low / high | **Mitigated, with residual P2-3.** Facts reach the model only inside a delimited block the prompt calls data (`pipeline/script/generate.py:43-46`, `153-165`; checker `pipeline/factcheck/semantic.py:82-90`); nested delimiters are stripped until stable (`generate.py:159-165`). Every answer must pass `validate.problems` (`generate.py:168-172`) and cite only the source's fact ids (`generate.py:119-122`); exact and meaning fact-checks flag unsupported lines (`pipeline/script/batch.py:117-156`). Fact text itself may not hold `://`, `www.`, `<`, `>`, backticks or invisible characters (`tests/test_sources_files.py:38-52`). Residual: see the URL row below. |
| Tampering | **A link that the URL check misses.** Before p2-validate-urls, `validate.py` rejected only `://` and `www.`, so a description saying "full story at bit.ly/x", or a full-width `ｗｗｗ．` form, passed. Platforms may turn bare domains into links, and even unlinked text sends viewers to an attacker's page under the channel's name | Low / high | **Mitigated; P2-3 closed by p2-validate-urls.** `_text_problem` (`pipeline/script/validate.py:54-66`) rejects `://`, `www.` and any bare domain (`_DOMAIN_LIKE`, `validate.py:28`) on text folded by `_normalised` (`validate.py:44-51`): NFKD, U+3002 and U+FF61 as dots, combining marks dropped. Control, format, unassigned, private-use and surrogate characters are rejected on the raw text (`_BAD_CATEGORIES`, `validate.py:24`). Residuals, accepted: a spelled-out ("example dot net") or spaced ("example . net") domain; a bare IPv4 address ("1.2.3.4/x"); visible spacing marks (Mc) and visible symbols (So, Sm, P*) between labels, including the braille blank U+2800; and a few letters whose NFKD holds a space or middle dot (U+013F and U+0140, Arabic harakat U+FE70 to U+FE7E). The PR body shows the description verbatim, so the owner's review is still a control. |
| Tampering (approval bypass) | **The PR shows less than what gets published** (old P1-3) | Medium / high | **Mitigated; P1-3 closed with residuals.** The PR body shows hook, every scene's narration with its cited facts, the loop line, and title, description and tags verbatim in one fenced block (`pipeline/script/batch.py:180-193`). Title, description and tags have length caps and reject URLs, `<`, `>`, control, bidi and zero-width characters (`pipeline/script/validate.py:54-120`). Residuals: the URL gap above (P2-3); `on_screen_text` is checked for URLs and invisible characters but has no length cap and is not in the PR body. It is not rendered today (no use under `pipeline/render/`), so this is a Phase 3 seed. |
| Tampering | **PR body injection.** Model text in the body renders as Markdown: a link, an image, an HTML comment that hides a line, or an `@mention` that notifies a stranger | Medium / medium | **Mitigated.** Every model-derived string sits in an inline code span or fenced block longer than any backtick run in it (`pipeline/script/batch.py:159-177`, `191-193`); flag reasons are whitespace-flattened and clipped (`batch.py:100-102`). Fact text and urls are plain Markdown (`batch.py:189`): **Accepted** while sources stay owner-reviewed and pass `tests/test_sources_files.py:38-52`. Any automatic ingest must code-span fact text too (seed). |
| Denial of service | An oversized PR body (GitHub caps it at 65,536 characters) | Low / low | **Mitigated, fails closed.** `pr_body` raises at `PR_BODY_MAX_CHARS` (`batch.py:228-229`, `pipeline/constants.py:103`), so the run fails and opens no PR; it never truncates. |
| Tampering | **The artifact can change already-approved scripts.** The `generate` job's artifact carries all of `queue/approved/` (`weekly_scripts.yml:41-46`), and before p2-weekly-hardening `open-pr` ran `git add queue/approved/*.json`. A buggy or compromised `generate` job (see P1-4) edits a script the owner approved last week. The change shows only in the PR diff, not the PR body, so a body-only review approves it | Low / high | **Mitigated; P2-2 closed by p2-weekly-hardening.** `open-pr` and `validate` copy only new, id-named regular files from the artifact (`weekly_scripts.yml:69-102`, `:136-169`), and a file that differs from the checkout fails the job (`:89-93`, `:156-160`). The artifact is extracted to `runner.temp`, never over the checkout. |
| Tampering (approval bypass) | **The approval PR gets no CI before merge.** The PR is pushed and opened with `github.token` (`weekly_scripts.yml:67`, `76-77`), and per GitHub's documentation events made with that token start no new workflow runs. So `tests/test_queue_scripts.py` (every queue file valid) first runs on `main`, after the owner has approved. The PR shows no checks, which on a phone looks like nothing failed | Low / medium | **Mitigated; P2-4 closed by p2-weekly-hardening.** `generate` validates each new script (`pipeline/script/generate.py:168-172`), and the `validate` job (`weekly_scripts.yml:53-114`) runs `tests/test_queue_scripts.py` on the copied scripts with a read-only token and no secret, before `open-pr` (`:119`). Residual: GitHub still adds no checks to the PR (a `github.token` push), so verify on the first live run. |
| Spoofing | A source fact cites a page served over HTTP or a lookalike domain | Low / medium | **Mitigated.** Fact urls must be `https://` (`pipeline/schema.py:104`); sources are a reviewed folder with CI checks (`tests/test_sources_files.py`). Lookalike domains are left to the owner's review. |
| Tampering | Gemini output tells the checker to pass every line (writer narration is shown to the checker) | Low / medium | **Mitigated.** Narration goes inside the checker's data block (`pipeline/factcheck/semantic.py:82-90`); the exact layer is not a model and cannot be talked round (`batch.py:125-127`); every line is visible in the PR. |

### 4.6 Gemini API (boundary 8)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Information disclosure | The key printed in a log, an exception or a URL | Low / medium | **Mitigated.** Read from env at call time, sent only in the `x-goog-api-key` header (`pipeline/script/gemini.py:59-80`); the response excerpt in an error is redacted before it is cut (`gemini.py:105-111`); the batch logs counts and ids only (`pipeline/script/batch.py:7`, `87`); GitHub masks the secret in logs. |
| Information disclosure | urllib follows a 3xx and copies every non-content header, the key included, to the redirect target | Very low / medium (needs the Google endpoint to redirect elsewhere; HTTPS) | **Mitigated; P2-5 closed by p2-gemini-redirects.** `_NoRedirect` opener: any 3xx raises GeminiError with no retry (`gemini.py:24-31`, `:86`); `tests/script/test_gemini_redirect.py`. |
| Denial of service | **Gemini quota exhaustion.** Budgets count logical calls: 14 writer and 14 checker per batch (`pipeline/constants.py:114-116`, `batch.py:25-36`), but each logical call can be 2 HTTP requests with the one retry (`gemini.py:83-102`), so up to 28 requests per model per run. Anyone with repo write, an agent session included, can dispatch `weekly-scripts` again: each run spends that again, and a second run on the same UTC day spends the quota and then fails at `git push` because the `scripts/<day>` branch exists (`weekly_scripts.yml:181-189`). A stolen key does the same. The Sunday run then gets 429 twice, scripts are left out, and with none written the run fails with no PR (`batch.py:88-89`) | Medium / low (a missed week, no cost) | **Mitigated for overlap; P2-6 closed by p2-weekly-hardening.** The workflow-level concurrency group `weekly-scripts` with no cancel (`weekly_scripts.yml:12-14`) makes runs queue instead of racing. Residual: a second run later the same UTC day still spends the quota (it fails at `git push` after the spend); budgets count logical calls, so real requests can reach twice the cap (spec.md section 4). Fails closed and is visible as a failed run; nothing alerts the owner yet (Phase 4 alerts). |
| Elevation of privilege (cost) | The key's Google project later gets a billing account (for example if it is shared with the YouTube Cloud project), so the key moves to a paid tier and a stolen key can bill | Low / high | **Owner action**, part of D1: create the key in its own AI Studio project with no billing, restricted to the Generative Language API. |
| Spoofing | A retired or wrong model id silently changes behaviour | Low / low | **Mitigated.** 404 names the model and fails loudly (`gemini.py:109-110`). |

### 4.7 The artifact between `generate` and `open-pr` (boundary 7)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | The write job runs something from the artifact | Low / high | **Mitigated.** `open-pr` only runs `git` and `gh` on the files (`weekly_scripts.yml:181-189`); the upload paths are fixed in the workflow (`weekly_scripts.yml:41-46`) and the artifact is extracted to `runner.temp`, never over the checkout (`:134`); `git add` takes a path-prefixed glob, so a file name cannot become an option. |
| Tampering | `generate` and `open-pr` check out the repo separately; if they got different commits, the queue `generate` read would not match the branch the PR is cut from | Low / low | **Accepted.** Assumption: `actions/checkout` without `ref` checks out the run's triggering commit in both jobs, so they match. Even if not, the effect (a reused source) shows in the PR. |

## 5. Seeded threats for Phases 3 and 4

The Phase 2 seeds of version 1 are now rows in section 4. Each phase's Architect turns the relevant rows below into contracts and tests; the CSO re-reviews at each phase end and when a new integration is added.

### Phase 3: visual templates

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Tampering | `on_screen_text` is not whitespace-collapsed like narration, so a newline in it could start a new ASS event, and `drawtext` has its own escaping rules | Collapse whitespace and escape it before it reaches FFmpeg |
| Tampering (approval bypass) | `on_screen_text` appears on screen but not in the PR body, and has no length cap | Show it in the PR body and cap its length before any template renders it |
| Tampering / DoS | `visual.data` is `dict[str, Any]` with no limits (`pipeline/schema.py:26`); a huge or odd chart payload crashes or stalls matplotlib | Validate `data` per template, with size caps |
| Tampering | Pexels or Pixabay returns an unexpected file type or a huge file | Check content type and size before FFmpeg reads it; download over HTTPS from the API's own host only |
| Information disclosure | Cloudflare or Pexels key in logs | As for Gemini (4.6) |
| Repudiation | Licence of each asset unknown later | Per-video asset log (PLAN.md section 10) |

### Phase 4: publishing and token refresh

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Spoofing / EoP | **OAuth token theft.** A stolen refresh token can post or delete on the owner's channels | GitHub Secrets only; minimum scopes; P1-1 decided with option (a) or (b) before any token is added; tokens never printed, masked if derived |
| EoP | The fine-grained PAT used by the IG token refresh can write every repo secret | Single repo, secrets permission only, with an expiry date and an alert before it expires |
| Information disclosure | Publish responses or tokens end up in an artifact or job logs | Publish step writes nothing into `out/`; logs only status codes and platform video IDs |
| Tampering | A script reaches publishing without passing through a merged PR, or a merged one was never validated (P2-4) | Workflow B publishes only scripts that arrived through a merged PR (P1-2) and runs `validate.problems` on each before publishing |
| Tampering | Automatic ingest (RSS) is added | Fact text gets the same code-span treatment in the PR body as model output, and the same URL and character checks as sources |
| Repudiation | Later, nobody can tell which approved version was published | The publish commit records the script's git blob SHA next to the platform video IDs |
| Denial of service | Rate limits, the TikTok pending cap, a revoked token, or a failed weekly batch stop publishing silently | Alerts on every failure (PLAN.md section 10); OAuth consent screen in production so tokens do not expire after 7 days |
| Spoofing | Unofficial upload methods get the account banned | Official APIs only (HARNESS.md section 6b) |
| Spoofing | Alert webhook URL leaked lets anyone post fake alerts | Webhook URL kept in Secrets; alerts never ask the owner to log in through a link |

## 6. Open gaps, ranked

Details for P1-n are in `.harness/handoffs/p1-cso.md`, for P2-n in `.harness/handoffs/p2-cso.md`.

Order before the first live Workflow A run: the owner decides D1, P1-4 is closed for the packages the key job installs (P2-1), then `GEMINI_API_KEY` is added. This narrows the earlier "P1-4 closed before the key" to its light half, because the key reaches only `generate`, which installs only `requirements.txt`; the orchestrator or owner confirms the narrowing. Update 2026-11-18: the key was added before P2-1 closed; the replacement guard is that Workflow A stays disabled, schedule included, until p2-weekly-hardening merges. That merge happened the same day; the workflow stays disabled until the owner's first manual run.

| ID | Severity | Gap | Must be closed before |
|---|---|---|---|
| P1-1 | High | Repo secrets reachable from any pushed or dispatched branch's workflow. D1 decided 2026-11-18: option (c), accepted for the quota-only Gemini key | Adding `GEMINI_API_KEY` (decision); Phase 4 tokens (option a or b) |
| P1-2 | High | No branch protection; agent sessions can push to `main` and `queue/approved/` | Phase 4 publishing |
| P1-3 | High | Closed by p2-validate and p2-batch; residuals tracked as P2-3 and the Phase 3 `on_screen_text` seed | (closed) |
| P1-4 | Medium, now High for the key job | Transitive Python dependencies unpinned and not hash-checked. Light half closed by p2-weekly-hardening (P2-1): `generate` installs hash-checked packages only. Heavy half open | Heavy half before Phase 4 tokens |
| P1-5 | Medium | No `concurrency` on CI; minutes can be drained | Phase 4 daily schedule |
| P1-6 | Medium | Closed 2026-11-16 by p2-entry-ci (PR #60); re-checked against `weekly_scripts.yml` 2026-11-18, holds | (closed) |
| P2-1 | High | Closed by p2-weekly-hardening: `generate` installs hash-checked packages from `requirements-generate.txt` | (closed) |
| P2-2 | Medium | Closed by p2-weekly-hardening: `open-pr` and `validate` copy only new script files from the artifact | (closed) |
| P2-3 | Medium | Closed by p2-validate-urls (bare domains, look-alike forms, marks, unassigned code points); residuals in section 4.5 | (closed) |
| P2-4 | Low to medium | Closed by p2-weekly-hardening: the `validate` job runs the queue tests before the PR opens; GitHub still adds no PR checks (verify on the first live run) | (closed) |
| P2-5 | Low | Closed by p2-gemini-redirects: any 3xx is refused, so the key is never re-sent | (closed) |
| P2-6 | Low | Closed for overlap by p2-weekly-hardening (concurrency group); a later same-day re-dispatch still spends quota | (closed) |
