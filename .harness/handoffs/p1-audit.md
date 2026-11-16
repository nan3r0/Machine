# Handoff: p1-audit

## Goal
Phase-end compliance audit for Phase 1 (licences, vulnerable dependencies, secrets and permissions, data retention, platform policy), for the owner to approve (PRD.md R7.6).

## Status
done. The report is complete; owner approval is pending.

**Blocking findings for Phase 1 approval: none.** Three findings (A1, A2, A3) must be closed before the first public publish (Phase 4). Everything else passes, is a note, or is not yet applicable.

## What changed (and why)
No files changed. The Auditor is read-only, so the report lives in this handoff (written by the orchestrator from the Auditor's output).

### 1. Licences

**Asset log: pass.**
- `assets/` holds only `fonts/Montserrat-Bold.ttf` and `fonts/OFL.txt`.
- The font has an entry in `assets/LICENSES.md:7` (source, OFL 1.1, sha256, use), with the OFL text next to it.
- OFL 1.1 allows commercial use and burning the glyphs into video.
- No music or SFX yet (deferred, PRD.md:114), so those entries are not yet applicable.

**Python dependencies (`out/reports/licenses.md`): pass, with notes.**
- Almost everything is permissive (MIT, BSD, Apache-2.0, PSF, ISC).
- File-level copyleft used unmodified, so fine: certifi, tqdm, pathspec and hypothesis are MPL-2.0. hypothesis is dev-only.
- Copyleft that runs in the pipeline:
  - `phonemizer-fork` 3.3.2 is GPLv3+ (licenses.md:104), pulled in by `misaki[en]`.
  - The apt package `espeak-ng` is GPL (ci.yml:74, render.yml:33).
  - `num2words` 0.5.14 is LGPL (licenses.md:86).
  - GPL duties apply when software is distributed, not to its output. The pipeline runs privately on Actions and distributes no binaries, and the videos are output, not derived works, so a monetised channel is fine. If the repo ever goes public or ships a built image, the GPL parts must keep their licence and source terms.
- Dev-only copyleft: `semgrep` 1.183.0 is LGPL-2.1 (licenses.md:136). It runs only in CI.
- Licence listed as UNKNOWN:
  - `espeakng-loader` 0.2.4 (licenses.md:42) is in the pipeline (via misaki) and may bundle espeak-ng (GPL) data. See A3.
  - `face` 26.0.1 (licenses.md:44) and `peewee` 3.19.0 (licenses.md:103) are dev-only, inferred to come via semgrep (not checked with pipdeptree). Note only.
- `misaki` shows URL UNKNOWN but licence Apache. Fine.

**Models and weights: open (A1).**
- No file records a licence for:
  - the Kokoro-82M weights `kokoro-v1_0.pth` and `config.json` at the pinned revision (`pipeline/constants.py:19-27`)
  - the `voices/af_heart.pt` voice file
  - the whisper `small.en` checkpoint (`pipeline/constants.py:35`)
- `en_core_web_sm` 3.8.0 is reported as MIT by pip-licenses (licenses.md:41), so it is covered.
- pip-licenses cannot see checkpoints downloaded from Hugging Face or whisper's CDN, and `assets/LICENSES.md` covers only files under `assets/`.
- The Auditor's understanding is that Kokoro-82M is Apache-2.0 and the whisper weights are MIT, both allowing commercial use. Not verified at the pinned revision (no web access in that session).

### 2. pip-audit (`out/reports/pip-audit.json`, CI run 43903542144, full environment, no ignores)

Nine entries, eight distinct advisories: setuptools PYSEC-2026-3447 appears twice with its aliases in a different order.

| # | Package | Version | ID | Fixed in | Where it runs | Reachable here? | In Gate 1? | Recommendation |
|---|---|---|---|---|---|---|---|---|
| 1 | mcp | 1.29.0 | CVE-2026-59951 / GHSA-84m7-p3x7-pcfv (HTTP server sessions never expire) | 1.30.0, 2.2.0 | dev, transitive (inferred via semgrep) | No, no MCP server runs | Not audited | Accept; moves with semgrep |
| 2 | mcp | 1.29.0 | CVE-2026-116685 / GHSA-5h93-6whr-6q8j (client follows cross-origin redirects) | 1.30.0, 2.2.0 | dev | No, no MCP client runs | Not audited | Accept |
| 3 | mcp | 1.29.0 | CVE-2026-116684 / GHSA-w4fh-qvv9-3v23 (no token audience check) | 1.30.0, 2.2.0 | dev | No | Not audited | Accept |
| 4 | mcp | 1.29.0 | CVE-2026-116686 / GHSA-rwrf-2pqf-9j8j (`$ref` fetch in client) | 1.30.0, 2.2.0 | dev | No | Not audited | Accept |
| 5 | opentelemetry-api | 1.37.0 | CVE-2026-114603 / GHSA-xcq7-p3pf-p88h (tracestate ReDoS) | 1.45.1 | dev (inferred via semgrep) | No, no server takes untrusted headers | Not audited | Accept |
| 6 | opentelemetry-api | 1.37.0 | CVE-2026-126360 / GHSA-mf5v-w3w3-f6cg (traceparent ReDoS) | 1.45.2 | dev | No | Not audited | Accept |
| 7 | setuptools | 81.0.0 | PYSEC-2026-3447 (MANIFEST.in exclude bypass on macOS) | 83.0.0 | pinned in `requirements-heavy.txt:11` for torch; not used at runtime | No, needs an sdist build on macOS | Ignored (Makefile:21) | Keep the ignore until torch lifts its cap |
| 8 | setuptools | 81.0.0 | PYSEC-2026-3447 (duplicate record) | 83.0.0 | same as 7 | same as 7 | same as 7 | same as 7 |
| 9 | setuptools | 81.0.0 | GHSA-xmj3-9gf7-h52w (Windows `install_as_egg` path escape) | 84.1.0 | same as 7 | No, runners are Linux and the owner's Windows machine never installs the heavy file | Ignored (Makefile:21) | Keep the ignore |

- **New compared with Gate 1:** rows 1 to 6. Not regressions: Gate 1 audits only `requirements.txt` and the heavy file (Makefile:21), never `requirements-dev.txt` or its transitive packages. None is reachable, so accepting them is safe. Dependabot (`.github/dependabot.yml:3-6`) moves semgrep, and the rows clear when semgrep pins newer versions.
- **torch PYSEC-2025-194** (ignored in Gate 1, fixed in 2.13.0, reason at Makefile:5-7) is not in this report. The full-environment audit skipped `torch`, `torchaudio` (2.11.0+cpu) and `en-core-web-sm` as "not found on PyPI". The advisory text was not in any file read, so no reachability claim. Recommendation: keep the documented ignore, and the owner reads the advisory once. If it concerns `torch.load` of untrusted checkpoints, the sha256 pinning of the Kokoro files (`pipeline/kokoro.py`, threat model 4.2) is the mitigation.
- **Coverage gap (note, low):** the reports job (ci.yml:160-162) cannot audit torch, torchaudio or `en_core_web_sm`. Gate 1 covers torch and torchaudio through the `sed 's/+cpu//'` copy. `en_core_web_sm` (a direct wheel URL, `requirements-heavy.txt:26`) is audited by neither; it is hash-pinned, which limits the risk.
- **setuptools upgrade is undone (note, low):** ci.yml:30-31 installs `setuptools>=84.1.0`, then ci.yml:82 installs `requirements-heavy.txt`, which pins `setuptools==81.0.0` (`requirements-heavy.txt:11`), so pip downgrades it again. The reports job never upgrades at all. Both final environments run 81.0.0, matching the report. The step is locked by `tests/test_ci_workflow.py:119-123`, which only checks that the step exists. If the step has no remaining purpose, change it through CONTRACT_CHANGE, not by editing the test.

### 3. Secrets and permissions
- **Secrets only in GitHub Actions secrets: pass.** No `secrets.` reference in either workflow. gitleaks runs in Gate 1 (Makefile:20). No personal details found in the repo, including `.harness/` and `.github/`. Adding the first secret is gated on CSO gap P1-1 (`docs/threat-model.md:130-134`).
- **Minimal `GITHUB_TOKEN` permissions: pass.** Both workflows set `permissions: contents: read` (ci.yml:8-9, render.yml:12-13) and use `persist-credentials: false` (ci.yml:22, ci.yml:124-125, render.yml:21-22). No `pull_request_target`. All Actions pinned by SHA. The token-permission lint from HARNESS.md 6b is covered by `tests/workflow_rules.py`.
- **Minimal OAuth scopes: not yet applicable.** Phase 4 check: YouTube upload scope only (plus analytics read-only for Workflow C); Instagram content publish plus basic only; TikTok `video.upload` only. The fine-grained PAT for the Instagram token refresh (PLAN.md:138) should be one repo, Secrets permission only, with an expiry. The scope list is seeded in `docs/threat-model.md:117`.

### 4. Data retention
- **Artifacts: pass.** Every upload sets a short retention: `frames` 7 days (ci.yml:116), `phase-reports` 14 days (ci.yml:170), `render` 3 days (render.yml:63), render `frames` 3 days (render.yml:72). Matches PLAN.md:261.
- **Job logs: unverified.** Log retention is a repo setting (Settings > Actions > General > "Artifact and log retention"), not a file. The owner should set it to 30 days or less. Logs hold script text (public content anyway) and no secrets.
- **Local reports: pass.** `out/` and `.cache/` are gitignored (`.gitignore:8,10`).
- **Actions cache: pass.** Holds only public model weights; GitHub evicts entries unused for 7 days.

### 5. Platform policy (PLAN.md sections 4, 6 and 10)
- **YouTube inauthentic and repetitive content:** not yet applicable for code (Phase 1 publishes nothing). The plan's mitigations pass: templates, custom visuals, hook rotation, human approval of every script, moderate cadence (PLAN.md:207-215, 326). Note: Phase 1 output is one template with one voice and should never be published on a schedule as it stands.
- **AI and synthetic content disclosure: open (A2).** The plan covers realistic AI imagery only (PLAN.md:215); the voice is synthetic (Kokoro).
- **Instagram and TikTok terms: not yet applicable** (no publishing code). The TikTok pending-draft cap and Instagram limits are noted for Phase 4 (PLAN.md:136, 259).
- **Music and asset rights:** fonts pass; music and SFX not yet applicable. Note: PLAN.md:325 names YouTube Audio Library as a music source, while PLAN.md:174 sends every video to all three platforms. Check that its terms allow use outside YouTube before choosing it. The Pexels credit (PLAN.md:134) applies from Phase 3.
- **Niche content rules (PLAN.md:160-164): pass as a plan.** Enforced by script review in later phases.

### Findings to close before the first public publish

**A1. Model and voice weights have no licence record.** Severity: medium.
- Where: `pipeline/constants.py:19-27, 35`; `assets/LICENSES.md:5-7` has no model rows.
- Scenario: a platform or rights claim asks for proof that the narration voice may be used commercially. No repo file shows the licence of the Kokoro weights, the `af_heart` voice or whisper `small.en` at the pinned revision. If upstream changed the licence, or the voice file carried different terms, nobody would notice.
- Fix: add a "Models" table to `assets/LICENSES.md` (or spec.md section 7) with repo, pinned revision, licence and a link to the licence file at that revision, filled from the upstream model card or LICENSE.

**A2. No disclosure decision for the synthetic voice.** Severity: medium.
- Where: PLAN.md:215 (imagery only); PLAN.md:136 (all three platforms).
- Scenario: every video has an AI narrator reading real events. If a platform's current labelling rules count this as synthetic content and the label is missing, the risk is takedowns or monetisation strikes. The plan does not mention the Instagram or TikTok AI labels.
- Fix: before Phase 4, the owner checks the current YouTube, Instagram and TikTok AI-labelling rules and records a decision in PRD.md section 7. The Phase 4 publish tasks then set the matching API or upload flag per platform.

**A3. One pipeline licence is unknown: `espeakng-loader` 0.2.4.** Severity: low.
- Where: `out/reports/licenses.md:42`.
- Scenario: the package may bundle espeak-ng (GPL) binaries or data under unrecorded terms. That matters only if the code is distributed, but a licence audit cannot pass on "unknown".
- Fix: check the upstream repo licence and add a line to spec.md section 7 or a licence note.

## Decisions made
- Runtime GPL and LGPL (phonemizer-fork, espeak-ng, num2words) accepted for now: obligations apply to distribution, and nothing is distributed. Re-check if the repo goes public.
- mcp and opentelemetry advisories (rows 1 to 6) recommended for acceptance, not ignores: dev-only and unreachable, and Gate 1 never audits the dev tree.
- None of A1 to A3 blocks Phase 1: nothing is published in Phase 1 and the licences are very likely permissive. They block go-live instead (HARNESS.md 6b: audit signed off before the first public publish).
- No overlap with `docs/threat-model.md`: P1-1 to P1-6 are cited, not repeated.

## Tried and abandoned
- Confirming which package pulls in mcp, opentelemetry, face and peewee: pipdeptree was not installed and no CI site-packages were available locally, so "via semgrep" is inferred from the dependency set (uvicorn, starlette, sse-starlette, httpx-sse) and is not verified.
- Checking model licences at the pinned revisions: no web access in that session.

## Known risks
- Gate 1 never audits `requirements-dev.txt` or its transitive packages. A reachable dev-tool CVE would only show in this manual reports run; the weekly scheduled audit is deferred to Phase 4 (PRD.md:124).
- `en_core_web_sm` is audited by no tool.
- Three Gate 1 ignores (Makefile:21) stay until torch lifts its setuptools cap and a torchaudio for torch 2.13 or later ships. Nothing reminds anyone to drop them.
- The setuptools upgrade step (ci.yml:30-31) has no lasting effect (section 2).

## Next step
- Owner: approve or reject this report (R7.6).
- Owner: check log retention in repo Settings > Actions.
- Owner: read the torch PYSEC-2025-194 advisory once.
- Orchestrator: open Phase 4 pre-go-live tasks for A1 (model licence table), A2 (AI-disclosure decision plus publish flags) and A3 (espeakng-loader licence).
- Optional: a CONTRACT_CHANGE on `tests/test_ci_workflow.py:119-123` if the setuptools upgrade step is to be removed or made effective.
- Optional: add `pipdeptree -r -p mcp,opentelemetry-api` to the reports job to confirm where those packages come from.

## Docs
- spec.md:92 says the alignment model is whisper `base.en`, but `pipeline/constants.py:35` uses `small.en`. Update spec.md.
- spec.md:87 lists `hypothesis` 6.170.14 and `ruff` 0.17.3, but `requirements-dev.txt:5-6` pins 6.170.15 and 0.17.5. Update spec.md.
- PRD.md section 7: record the owner's audit approval, and later the A2 disclosure decision.
- `assets/LICENSES.md`: add the model rows (A1, Phase 4 task).
- workflow.md and CLAUDE.md status: mark the Auditor review done once the owner approves.

## Evidence
- Tests: none run (read-only review; no code changed).
- Inputs read: `out/reports/licenses.md` and `out/reports/pip-audit.json` (CI run 43903542144 at e99e630), `assets/LICENSES.md`, `.github/workflows/ci.yml`, `.github/workflows/render.yml`, `.github/dependabot.yml`, `Makefile`, the three requirements files, `pipeline/constants.py` (grep), `tests/test_ci_workflow.py:117-128`, PLAN.md sections 3, 4, 6, 7B and 10, HARNESS.md 6b and 7, spec.md section 7, PRD.md:60-124, `docs/threat-model.md` sections 4.2, 4.3 and 6, `lessons.md`.
- Searches: `secrets.`, `pull_request_target` and `permissions` in `.github/` (only the two `permissions:` blocks matched); personal details across the repo and `.harness/` (no matches); glob of `assets/**` (one font plus OFL.txt, no music or SFX).
