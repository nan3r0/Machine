# Threat Model

Version 1, 2026-11-16. Covers the pipeline as built at the end of Phase 1, plus seeded threats for Phases 2 to 4. Method: STRIDE per trust boundary (HARNESS.md section 6b).

**Owner sign-off: pending.** Required before the first public publish (Phase 4).

Status values used below:
- **Mitigated**: a control exists in the repo today (file:line given).
- **Gap P1-n**: a real risk with no control yet; a proposed task in `.harness/handoffs/p1-cso.md`.
- **Accepted**: a known risk the owner carries on purpose.
- **Seeded (Phase n)**: does not exist yet; the phase that adds the feature must handle it.

## 1. What Phase 1 is

One manually started GitHub Actions job (`.github/workflows/render.yml`) reads a script JSON from the repo, synthesises a voice with Kokoro, aligns the script words with stable-ts, burns captions in with FFmpeg and uploads the MP4 as an artifact kept 3 days. CI (`.github/workflows/ci.yml`) runs on every push and pull request. Both workflows have a read-only `GITHUB_TOKEN` and use no secrets. `gh secret list` on the private repo returned nothing on 2026-11-16.

Nothing is published, nothing is ingested from the internet, and no API key exists yet. Phase 1's real attack surface is the build itself: dependencies and model weights pulled into the runner, the script JSON fed into FFmpeg, and the agent sessions that write the code.

## 2. Assets

| Asset | Why it matters | Exists in Phase 1? |
|---|---|---|
| Approval integrity | Workflow B will treat "file is in `queue/approved/`" as "the owner approved it". Anyone who can put a file there can publish under the owner's channels | Folder exists, nothing reads it automatically yet |
| Publishing tokens (YouTube OAuth refresh token, Instagram long-lived token, TikTok token) | Can post, edit or delete videos on the owner's channels | No (Phase 4) |
| API keys (Gemini, Cloudflare, Pexels, Pixabay) and the fine-grained PAT for the IG token refresh | Quota theft; the PAT can overwrite every repo secret | No (Phases 2 to 4) |
| The channels and their standing | A ban or strike ends the project | No |
| `main` branch | Every scheduled workflow runs main's code with the repo's secrets | Yes |
| Actions minutes (about 2,000 per month, no payment method) | When they run out, every workflow stops until the month resets | Yes |
| Pinned model weights (Kokoro `.pth`, voice `.pt`, whisper `small.en`) | Loaded through pickle, so a swapped file is code execution on the runner | Yes |

No payment method exists on any account (PLAN.md section 3), so a stolen key can exhaust a free quota but cannot create a bill.

## 3. Trust boundaries

1. **The owner.** Writes or edits scripts, reviews and merges every PR, holds every account.
2. **Claude Code agent sessions** on the owner's PC. They run with the owner's git and `gh` credentials, so they can push branches and, technically, push to `main` or merge PRs. lessons.md records several cases of sessions writing or pushing where they should not have; none was malicious, but each shows the boundary is soft.
3. **GitHub Actions runners.** Execute whatever workflow file is on the pushed or dispatched ref.
4. **Upstream code and data sources.** PyPI, the PyTorch CPU index, Hugging Face (Kokoro), the whisper model URL, the Ubuntu apt mirror, GitHub release downloads (gitleaks, actionlint, the spaCy model).
5. **Script JSON.** Owner-written in Phase 1. From Phase 2 it is Gemini-written from ingested internet text, so it becomes attacker-influenced.
6. **External APIs** (Phase 2 onward): Gemini, Cloudflare Workers AI, Pexels, Pixabay, YouTube, Instagram, TikTok, alert channels.

## 4. STRIDE by boundary (Phase 1 as built)

### 4.1 Script JSON into the render (boundary 5)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | Command injection: a script word or title containing shell metacharacters reaches a shell | Low / high | **Mitigated.** FFmpeg and ffprobe run from argument lists, never a shell (`pipeline/render/compose.py:120`, `pipeline/render/qa.py:104`). |
| Tampering | Filtergraph injection through the captions path (`,`, `;`, `[`, `'`, `:` in a path) | Low / medium | **Mitigated.** `pipeline/render/compose.py:37-40` escapes for the option parser and quotes for the filtergraph. Paths are built by the pipeline, not taken from the script. |
| Tampering | ASS injection: script text containing `{\...}` override tags, or a newline that starts a new `Dialogue:` event | Medium (Phase 2) / low (visual only) | **Mitigated.** `pipeline/render/captions_ass.py:34` escapes `\`, `{` and `}`. The stronger control is `pipeline/schema.py:57`: narration text is whitespace-collapsed, so no newline can reach the `.ass` file. |
| Tampering | Path traversal once `id` becomes a file name (queue moves in Phase 4) | Low / medium | **Mitigated.** `pipeline/schema.py:42` restricts `id` to `[a-z0-9-]`. |
| Information disclosure | The `script` dispatch input is any path on the runner; a non-JSON file's content can appear in the pydantic error in the job log | Low / low (no secrets on disk, `persist-credentials: false`, only repo writers can dispatch) | **Accepted** for Phase 1. Workflow B picks scripts itself and has no free-form path input. |
| Denial of service | A very long script makes Kokoro and FFmpeg run until the 45 minute timeout, burning minutes | Low now, medium in Phase 2 / low | **Gap P1-5** (minutes budget) covers the cost side; the word-count bounds are only checked by QA after rendering. Seeded for Phase 2 below. |

### 4.2 Upstream code and weights into the runner (boundary 4)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| Tampering / EoP | A poisoned Kokoro checkpoint (pickle) runs code when loaded, either from a compromised upstream repo or a poisoned Actions cache | Low / high | **Mitigated.** Files are fetched at a pinned revision and their sha256 is checked on every run, cached or not, before kokoro or torch loads them (`pipeline/voice/kokoro.py:76-87`, `pipeline/constants.py:21-27`). |
| Tampering / EoP | A poisoned whisper `small.en` checkpoint | Low / high | **Mitigated by upstream behaviour only.** openai-whisper checks its own sha256 on download and on load (`pipeline/constants.py:34`). Nothing in this repo verifies it. Acceptable while `openai-whisper` is pinned. |
| Tampering / EoP | Dependency confusion between the PyTorch index and PyPI | Low / high | **Mitigated.** torch and torchaudio install alone with `--no-deps` from the CPU index, everything else from PyPI only (`tests/workflow_rules.py:46-52`). |
| Tampering / EoP | A malicious new release of a transitive dependency (stable-ts, kokoro, misaki, transformers and spaCy pull dozens of unpinned packages) runs at install time | Low / high (code execution on the runner; from Phase 4 the runner holds publishing tokens) | **Gap P1-4.** Only top-level packages are pinned and nothing is hash-checked. The spaCy model wheel is the one hash-pinned exception (`requirements-heavy.txt`). pip-audit catches known CVEs, not fresh malicious releases. |
| Tampering | Compromised third-party Action | Low / high | **Mitigated.** Every `uses:` is pinned to a full commit SHA (`tests/workflow_rules.py:36-39`). gitleaks and actionlint are sha256-checked (`.github/workflows/ci.yml:90-91`). |
| Tampering | Compromised apt package (ffmpeg, espeak-ng) | Very low / high | **Accepted.** Ubuntu's signed mirror; versions are not pinned. |

### 4.3 Actions runners and workflows (boundary 3)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP | A step writes to the repo or opens PRs with the job token | Low / high | **Mitigated.** `permissions: contents: read` and `persist-credentials: false` in both workflows (`tests/workflow_rules.py:32-35`, `tests/test_ci_workflow.py:47`). |
| Tampering | Expression injection: a branch name or dispatch input interpolated into a `run:` script | Low / high | **Mitigated.** No `${{ }}` inside `run:` (`tests/workflow_rules.py:40`); the script input goes through `env` (`.github/workflows/render.yml:48-50`); the task id from the branch name is regex-checked before it is written to `GITHUB_ENV` (`.github/workflows/ci.yml:63`). |
| Information disclosure / EoP | `pull_request_target` runs untrusted PR code with secrets | Low / high | **Mitigated.** Forbidden by `tests/workflow_rules.py:35`. |
| EoP | **Any pushed branch can add or edit a workflow, and repo secrets are available to workflows on every branch.** When Phase 4 adds tokens, an agent-written branch (or a workflow edit hidden in a large diff) could print or send them out on push, before anyone reviews the PR | Medium / critical | **Gap P1-1.** Nothing today, because there are no secrets yet. Must be decided before the first secret is added. |
| Tampering | The safety rules only cover workflow files the tests name. A new workflow added in Phase 2 escapes them, and `assert_safe` hardcodes `contents: read`, which Workflow A (opens PRs) must break | Medium / high | **Gap P1-6.** |
| Denial of service | `ci.yml` runs the full heavy job (up to 45 minutes) on every push and every pull request event, with no `concurrency` group. An agent fix loop pushing repeatedly, or push plus PR events for the same commit, drains the monthly minutes. When they run out, scheduled publishing stops | Medium / medium | **Gap P1-5.** |
| Information disclosure | The `render` and `frames` artifacts expose script content | Low / low (private repo, 3 days, content is meant to be public) | **Accepted.** |

### 4.4 Agent sessions and `main` (boundary 2)

| STRIDE | Threat and scenario | Likelihood / impact | Status |
|---|---|---|---|
| EoP / Tampering | An agent session pushes straight to `main`, or merges its own PR, skipping Gate 2 and the owner's review. The private repo on the free plan has no branch protection | Medium / high | **Gap P1-2.** Today the only control is the owner noticing. architecture.md section 7 lists the lock hook's own limits; they are not repeated here. |
| Tampering (approval bypass) | From Phase 4, a file pushed into `queue/approved/` by anything other than a merged owner-reviewed PR gets published | Medium / critical | **Gap P1-2.** |
| Tampering | A task branch edits `ci.yml` to drop the scope check. The check script is taken from the base ref, but the workflow that calls it comes from the branch (`.github/workflows/ci.yml:33-35`) | Low / high | **Accepted.** The control is the owner's PR diff review; any change under `.github/workflows/` should be read line by line. |
| Spoofing | An owner message typed in a task window is misread as a decision | Medium / medium | **Mitigated** by process (lessons.md 2026-11-15, decisions confirmed by the orchestrator). |
| Repudiation | Which session made which change | Low / low | **Mitigated.** Git history, handoffs and the outcome log. |

## 5. Seeded threats for Phases 2 to 4

Each phase's Architect turns the relevant rows into contracts and tests; the CSO re-reviews at each phase end and when a new integration is added.

### Phase 2: ingest, Gemini scripts, approval PRs

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Tampering | **Prompt injection via ingested content.** An RSS item tells Gemini to add a link or a claim to the script, which is later published | Source text passed as delimited data, never as instructions; the fact-check gate; a URL allowlist for `description`; the owner's PR review (HARNESS.md section 6b) |
| Tampering (approval bypass) | **The PR shows less than what gets published.** PLAN.md section 7 Workflow A step 5 lists hook, narration, sources and flags in the PR summary, but not `title`, `description` or `tags`. The schema puts no limits on them (`pipeline/schema.py:48-50`): no URL check, no length cap, no filter on control, bidi or zero-width characters. An injected link in the description passes a mobile review | The PR summary shows every field that is published, verbatim; schema or fact-check rejects URLs outside an allowlist, control and invisible characters, and over-long fields. (High; listed as P1-3) |
| Denial of service | Gemini writes a script far outside the word bounds, which renders for 45 minutes before QA rejects it | Check `narration_words()` against the format bounds before the voice step |
| EoP | Workflow A needs `contents: write` and `pull-requests: write` | Write permissions per job, only on the job that opens the PR; covered by P1-6 |
| Information disclosure | The Gemini key printed in a log or an exception | Key read from env only, never logged; HTTP errors logged without headers |
| Spoofing | A feed served over HTTP, or a lookalike domain added to the source list | HTTPS only; sources listed in a reviewed file |

### Phase 3: visual templates

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Tampering | `on_screen_text` is not whitespace-collapsed like narration, so a newline in it could start a new ASS event, and `drawtext` has its own escaping rules | Collapse whitespace and apply `escape_ass_text` (or drawtext escaping) before it reaches FFmpeg |
| Tampering / DoS | `visual.data` is `dict[str, Any]` with no limits (`pipeline/schema.py:26`); a huge or odd chart payload crashes or stalls matplotlib | Validate `data` per template in the router, with size caps |
| Tampering | Pexels or Pixabay returns an unexpected file type or a huge file | Check content type and size before FFmpeg reads it; download over HTTPS from the API's own host only |
| Information disclosure | Cloudflare or Pexels key in logs | As for Gemini |
| Repudiation | Licence of each asset unknown later | Per-video asset log (PLAN.md section 10) |

### Phase 4: publishing and token refresh

| STRIDE | Threat and scenario | Required control |
|---|---|---|
| Spoofing / EoP | **OAuth token theft.** A stolen refresh token can post or delete on the owner's channels | GitHub Secrets only; minimum scopes (YouTube upload scope, not full account; Instagram content publish only; TikTok `video.upload` only); P1-1 decided before any secret is added; tokens never printed, masked if derived |
| EoP | The fine-grained PAT used by the IG token refresh can write every repo secret | Single repo, secrets permission only, with an expiry date and an alert before it expires |
| Information disclosure | Publish responses or tokens end up in the `out/render` artifact or job logs | Publish step writes nothing into `out/`; logs only status codes and platform video IDs |
| Tampering | A script reaches publishing without passing through a merged PR | Workflow B publishes only scripts that arrived through a merged PR (see P1-2) |
| Repudiation | Later, nobody can tell which approved version was published | The publish commit records the script's git blob SHA next to the platform video IDs |
| Denial of service | Rate limits and the TikTok pending cap, or a revoked token, stop publishing silently | Alerts on every failure (PLAN.md section 10); OAuth consent screen in production so tokens do not expire after 7 days |
| Spoofing | Unofficial upload methods get the account banned | Official APIs only (HARNESS.md section 6b) |
| Spoofing | Alert webhook URL leaked lets anyone post fake alerts | Webhook URL kept in Secrets; alerts never ask the owner to log in through a link |

## 6. Open gaps, ranked

Details, failure scenarios and fix hints are in `.harness/handoffs/p1-cso.md`.

P1-1 conflicts with PLAN.md section 11, Phase 0 ("All keys stored in GitHub Secrets"). Until P1-1 is decided, no key goes into the repo's secrets.

| ID | Severity | Gap | Must be closed before |
|---|---|---|---|
| P1-1 | High | Repo secrets reachable from any pushed branch's workflow | Any secret is added to the repo |
| P1-2 | High | No branch protection; agent sessions can push to `main` and, later, to `queue/approved/` | Phase 4 publishing |
| P1-3 | High | PR review does not show every published field; no limits on title, description, tags | Phase 2 Workflow A |
| P1-4 | Medium | Transitive Python dependencies unpinned and not hash-checked | The first secret is added |
| P1-5 | Medium | No `concurrency` on CI; minutes can be drained | Phase 4 daily schedule |
| P1-6 | Medium | Workflow safety tests cover only named files and assume read-only tokens | The first new workflow (Phase 2) |
