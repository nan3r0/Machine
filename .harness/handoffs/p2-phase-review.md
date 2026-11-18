# Handoff: p2-phase-review

## Goal
Phase-end architecture check of Phase 2 as a whole (HARNESS.md 6a, `.harness/tasks/phase2/13_phase_review.yaml`). It covers how sources, generate, validate, gemini, the exact and semantic fact-checks and batch fit together, duplicated logic, doc consistency, the QA lead, CSO and Auditor handoffs, and PRD R8 to R13.

## Status
done (read-only). Verdict: Phase 2 code can close. No code blockers. Closing the phase still waits on the owner items below. B1 (evidence that the shell tests ran in CI) was cleared by the orchestrator: CI run 44382617178 ran them (one over-strict assertion failed, fixed in PR #80) and run 44387658729 passed.

## What changed (and why)
none

## Decisions made
- The unchecked hook and loop line, non-ASCII digits and the delimiter helper duplication are non-blocking for Phase 2 and must become tasks before Phase 4. Nothing publishes in Phase 2, and the owner reads every line in the PR.
- R13.5 and R13.6 are owner gates, not review findings.

## Tried and abandoned
- Proving the shell tests from repo artifacts: `out/reports/coverage.txt` predates the hardening PRs. The orchestrator used the CI logs instead (see Status).

## Known risks
- The hook and loop line are spoken but neither fact-check layer sees them (N1).
- Gemini response shapes outside the documented one (for example `steps` as an int) raise TypeError, which `batch.py:81` does not catch. The run crashes loudly, so nothing is silently wrong (N5).

## Next step
1. Owner: approve the Auditor report (R13.6), decide F1 to F3, confirm F4 to F6, sign off the threat model, turn on "Allow GitHub Actions to create and approve pull requests", re-enable `weekly-scripts` and dispatch it once (R13.5).
2. Architect turns N1 to N4 and the QA lead's ranked tests into tasks.

## Docs
Applied at close-out on `docs/p2-closeout-6`:
- `architecture.md` heading "Workflow A (Phase 2)" (no longer "planned"); N1 and N2 added to section 7.
- `.harness/handoffs/p2-weekly-hardening.md` status updated with the CI run ids.
Still owed: `PRD.md` section 7, record the owner's approval of the audit and the F1 cadence decision (PLAN.md:211 says 3 to 4 a week; PLAN.md:333 and the batch write 7).

## Evidence
Read: the task YAML, PRD R8 to R13 and section 7, PLAN.md sections 5, 7 and 11, architecture.md sections 1a and 7, the three phase-end handoffs, orchestrator.md State, the weekly-hardening handoff, `pipeline/script/{batch,generate,sources,validate,gemini}.py`, `pipeline/factcheck/{exact,semantic}.py`, `schema.py`, `tests/test_weekly_hardening.py` and `out/reports/coverage.txt`. No commands run by the reviewer.

## Findings

### Blocker (cleared)
- **B1** `tests/test_weekly_hardening.py:136-138`: the open-pr shell tests skip on Windows and no CI evidence was recorded. Cleared: see Status.

### Non-blocking (ranked)
- **N1 (high, before Phase 4)** `batch.py:123-125` and `semantic.py:83-84`: only scene narration is fact-checked. The hook and loop line are voiced (`schema.py:56`) but neither layer sees them, so a made-up number in the hook ("In 1987...") gets no check and no flag. Title and description are not checked either. PLAN section 5 says "each narration line", and the hook is the first spoken line. Fix: check the hook and loop line against all of the script's cited facts, or have the prompt keep numbers and names out of them. Needs an Architect contract change.
- **N2 (high, before Phase 4)** `normalise.py:56`: only ASCII `[0-9]` is read, so full-width and Arabic-Indic digits skip R9.1 (QA lead rank 1). Cheapest fix: NFKC before tokenising, or `validate` rejecting non-ASCII `Nd` characters in spoken fields. Contract change.
- **N3 (medium, maintainability)** `semantic.py:16` imports the private `generate._clean`, `DATA_START` and `DATA_END`, and `generate._data_block` and `semantic._data_block` are two separate data-block builders. Fix: move the delimiters, a public `clean` and one block helper into a small shared module, for example `pipeline/script/prompt_data.py`. Flagged earlier, still open.
- **N4 (medium)** QA lead's ranked tests: `batch.py:150-151` never runs in tests, budgets are only checked with `<=`, flag content is not asserted. Also the flaky UTC-midnight test at `tests/script/test_batch.py:298`. Re-run the reports job first, since the current survivors are stale.
- **N5 (low)** `gemini.py:124-126`: a non-list `steps` or `content` raises TypeError, and `response.read()` errors raise outside URLError. Neither becomes a GeminiError, so the whole batch crashes instead of leaving one script out. Fix: wrap the parse in one try and raise GeminiError.
- **N6 (low)** The weekly `validate` job installs pytest without hashes, and Gate 1 never pip-audits `requirements-generate.txt`. Accept, or fold into the heavy P1-4 lock.
- **N7 (owner)** Audit F1 cadence (7 a week against PLAN 3 to 4), F2 source credit in the description, F3 Cottingley cousins and the Piltdown accusation risk.

### Interfaces (pass)
- sources to batch: the slug becomes the id, and an invalid slug fails Script validation and is left out.
- generate checks source ids and validate before returning.
- semantic always returns one verdict per scene and fails closed. `LineVerdict` (`schema.py:141-145`) enforces that SUPPORTED and PARTIAL name a fact.
- batch's `zip(strict=True)`, the budget reservation, rewrite once then re-check, the PR body code-spans and the over-length ValueError all match R10 to R13.1.
- gemini refuses redirects and redacts the key.
- No contradictions with PLAN, PRD, spec or architecture beyond the Docs items above.

### PRD R8 to R13
- **Met:** R8.1, R9.2 (ASCII), R10.1 to R10.5, R11.1 to R11.3, R12.1 to R12.3, R13.1 to R13.4, and R13.7 (P2-1 to P2-6 merged).
- **Partly met:**
  - R8.2: 15 sources seeded; the F3 content-rule questions are open.
  - R9.1: misses non-ASCII digits and sentence-start names (documented at architecture.md section 7), and the hook is out of scope (N1).
  - R13.6: the reviews are done and the threat model is v2, but the owner has not approved the audit or signed off the threat model.
- **Not met:** R13.5, the manual Workflow A run. The workflow is disabled and waits on the owner.

Recommendation: close Phase 2 once the owner approves the audit (R13.6) and the first manual run passes (R13.5). Raise N1 and N2 as tasks before Phase 4.
