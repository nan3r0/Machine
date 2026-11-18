# Handoff: p2-audit

## Goal
Phase 2 compliance audit (HARNESS.md 6b) covering Gemini terms, key handling, weekly workflow permissions, source attribution and copying, niche content rules and the CI reports from run 44360049860. The owner approves it.

## Status
done. Owner approval is pending. Blocking: none. Phase 1 findings A1 to A3 and CSO P1-1 are carried forward and not repeated here.

## What changed (and why)
None. This was a read-only review.

### Blocker
none

### For owner
- **F1 Cadence (PLAN.md:211).** One batch writes 7 scripts, one per day from the next Monday (`pipeline/script/batch.py:42-43,71,79`; PRD.md:71). That is 7 videos a week, but PLAN.md section 6.6 says "start at 3-4/week". Nothing publishes before Phase 4, so pick 3-4 a week or amend PLAN.md before go-live.
- **F2 Attribution.** 14 of 15 sources cite Wikipedia (CC BY-SA 4.0). Only `sources/bloop.yaml` cites NOAA, which is US public domain. No yaml file has a licence note. The writer asks the model for a `description` (`pipeline/script/generate.py:67`) and forbids URLs in it (generate.py:33). No code adds a source credit. Only the hand-written sample credits its source (`queue/approved/sample-65s.json:53`). Decide before Phase 4, for example a fixed "Sources: Wikipedia (CC BY-SA 4.0)" line added by code to the description.
- **F3 Niche rules (PLAN.md:161-163), three sources need care:**
  - `sources/cottingley-fairies.yaml:4,7` names two cousins who were children (16 and 9) and private people at the time. The prompt says "No private individuals" (generate.py:33), which clashes with the source. Keep them as historical figures or drop the source.
  - `sources/piltdown-man.yaml:4,28`: fact 401 names Dawson as the finder and fact 409 says the work was "of one person". A script could join these into "Dawson faked it", an accusation that no fact states. The meaning check should flag that, but the owner should watch for it in review.
  - `sources/antikythera-mechanism.yaml` is weak as a "solved" mystery. Its date is a range (fact 603), and the 2021 reconstruction (609) is not a final resolution. Acceptable if scripts frame it as "what it was", not as a closed case.
  - The other 12 sources have documented resolutions, name only public figures or organisations and are not centred on a death. Pass.
- **F4 Gemini key setup is owner-attested, not verified.** Own AI Studio project, no billing, restricted to the Gemini API, repo secret `GEMINI_API_KEY` (D1 option c). The repo cannot show this. Owner confirms once.
- **F5 Gemini terms (unverified, no web access).** Free-tier prompts may be used to improve Google products and read by human reviewers. Prompts carry only public facts and rules, with no personal data or secrets (generate.py:100-104), so the free-tier use clause passes. Owner should re-read the current Gemini API Additional Terms for the age and regional clauses on Unpaid Services.
- **F6 Server-side retention (unverified).** The client calls the Interactions endpoint (`pipeline/constants.py:108`) and sends no storage setting (`pipeline/script/gemini.py:62-68`). The repo does not record what the provider keeps by default. The content is public, so severity is low. Check the docs and send a no-store flag if the API offers one.
- **F7 Workflow state.** weekly-scripts was disabled until p2-weekly-hardening merged. That has merged (#82). Re-enable it only on owner say-so. The repo setting "Allow GitHub Actions to create and approve pull requests" must be on.

### Notes (pass unless stated)
- **Weekly token permissions: pass.**
  - Top level is `contents: read` (weekly_scripts.yml:8-9). `generate` inherits read-only. `validate` sets read (57-58). `open-pr` alone has `contents: write` and `pull-requests: write` (122-124), the minimum needed for push plus `gh pr create`.
  - Only `open-pr` keeps checkout credentials (25, 62 vs 129). Hooks are off for every git call in that step (177-179).
  - All 7 action uses are SHA-pinned. No `pull_request_target`.
- **Secret scope: pass.** The key is set in a single step's env (38-39), and only `generate` gets it. gemini.py sends it in a header only (72-75), refuses redirects (24-31) and redacts it from error excerpts (107). batch.py logs only ids and counts.
- **The validate job installs pytest without hashes**: `pytest==9.2.0` and its unpinned deps (weekly_scripts.yml:111). Low risk, since the job has no key and a read-only token.
- **Artifact retention: pass.** The weekly-scripts artifact is kept 3 days (weekly_scripts.yml:48). ci.yml and render.yml are unchanged since Phase 1. Job-log retention is a repo setting carried over from p1-audit.
- **Copying limits: pass.** Every fact is one short sentence, mostly reworded from the source. No long verbatim passages. Facts themselves are not copyrightable.
- **Dependency licences: pass.** All 10 pins in `requirements-generate.txt` match licenses.md versions and are permissive. The soundfile wheel bundles libsndfile (LGPL), which only matters on distribution, as in Phase 1.
- **pip-audit, 9 entries:**
  - mcp 1.29.0 (4 CVEs, fixed in 1.30.0) and opentelemetry-api 1.37.0 (2 CVEs, fixed in 1.45.1 and 1.45.2) are in no requirements file. They come in through `requirements-dev.txt` in ci.yml:82 and :139. The parent is almost certainly semgrep (`requirements-dev.txt:12`), inferred from its dependency set, not verified.
  - Neither can reach the weekly workflow. `generate` and `validate` install only the hashed `requirements-generate.txt` plus pytest, and `open-pr` installs nothing. So they are dev CI only: accept, and semgrep bumps will clear them.
  - setuptools 81.0.0 (3 entries, one duplicate) is the known ignore (Makefile:21).
  - Gate 1 never audits `requirements-generate.txt` itself. Its pins equal `requirements.txt`, which is audited, so the gap is small.
- **Assets:** unchanged. Only the Montserrat font and OFL.txt. No music or SFX yet.

## Decisions made
- The mcp and opentelemetry advisories are recommended for acceptance, not ignores, because they are unreachable from the key-holding jobs.
- Cadence, attribution and the three sources are for the owner, not blockers, because nothing publishes in Phase 2.

## Tried and abandoned
- Confirming the parent of mcp and opentelemetry: no CI site-packages were available locally.
- Checking the live Gemini terms and the Interactions storage default: no web access.

## Known risks
- Scripts PRs opened with GITHUB_TOKEN start no CI run (architecture.md:137). The `validate` job is the only automated check.
- Gate 1 still never audits the dev tree.

## Next step
- Owner: approve the report, decide F1 to F3, confirm F4 to F6, and re-enable weekly-scripts (F7).
- Optional: add `pip show mcp opentelemetry-api` to the reports job. Its "Required-by" line confirms the parent with no new dependency.

## Docs
- docs/threat-model.md:28 says `GEMINI_API_KEY` is "not yet added". That is stale. Update it.
- docs/threat-model.md:171: P2-1 can close now that `requirements-generate.txt` installs with `--require-hashes` (covered by the close-out).
- `.harness/handoffs/p2-weekly-workflow.md:11` says "requirements.txt only", which the hardening task superseded (history only, optional).
- PRD.md section 7: record the owner's approval and the F1 and F2 decisions.

## Evidence
- No tests run (read-only review).
- Read: the task YAML; weekly_scripts.yml, ci.yml and render.yml; Makefile; all four requirements files; `out/reports/licenses.md` and `pip-audit.json`; all 15 `sources/*.yaml`; the sample script fields; gemini.py, generate.py:28-117 and batch.py (grep); PLAN.md:121-212; the p1-audit handoff; and grep hits in orchestrator.md, architecture.md and the threat model.
