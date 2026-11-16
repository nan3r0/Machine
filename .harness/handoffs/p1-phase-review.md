# Handoff: p1-phase-review

## Goal
Phase-end architecture check of Phase 1 as a whole (HARNESS.md section 6a): do the interfaces fit, is logic duplicated, does anything contradict PLAN.md, spec.md, PRD.md or architecture.md. Weighs the QA lead, CSO and Auditor handoffs, `docs/threat-model.md`, lessons.md and the recent changes (Retention removed, 144 wpm, compose timeout, golden frames, p1-qa-tests). Read-only; fixes become new tasks.

## Status
done. Verdict: **Phase 1 is not ready to close yet.** The code is sound. What blocks is outside the code: one owner approval, green CI on main, and a docs close-out.

### Blocking
1. **R7.6 not met.** PRD R7.6 needs "the owner has approved the audit report". `p1-audit.md` and the orchestrator state both say approval is pending, and PRD.md section 7 has no entry. Owner action: approve or reject the report, record it in PRD.md section 7. (CSO sign-off of `docs/threat-model.md` gates Phase 4, not R7.6.)
2. **CI on main.** Run 43944253402 on 66add7f (the p1-golden-65s merge) was still in progress at review time. Phase closes only when it is green (Gate 3).
3. **Docs on main are false** (one docs close-out commit; PR #55 does not fix these):
   - `workflow.md` Phase 1 status row "QA lead, CSO, Auditor, phase review" says "not started". The first three are done.
   - `CLAUDE.md` Status says "No pipeline code yet".
   - `CLAUDE.md` "Where things are" and architecture.md section 7 lack the `docs/threat-model.md` pointer the CSO handoff asked for.
   - `.harness/status.yaml` lacks p1-qa-lead, p1-cso, p1-audit (orchestrator decides whether read-only reviews belong there) and p1-golden-65s (PR #55 adds it).
   - `orchestrator.md`, older State block: "SPEECH_WPM is still 150" is stale.

### Interfaces: fit
- `render_one.render` passes `narration_text()` to Kokoro and align; align splits it, which equals `narration_words()` given to QA. Signatures of compose and qa match the call sites.
- Errors: VoiceError, AlignError, ComposeError propagate to `main` (exit 2); QA failures are data (exit 1). Matches architecture.md section 3.
- PLAN.md section 4, spec.md section 4 and constants.py agree: 144 wpm, 149 to 216 words, 62 to 90 s, voice speed 0.9. No Retention leftovers in code, tests or spec.
- Every PRD Phase 1 criterion R1.1 to R7.5 maps to a test in workflow.md and the tests exist; R7.2 done by the owner on 2026-11-16.

### Non-blocking (new tasks or notes)
- N1 `pipeline/render/captions_ass.py:52`: style numbers (Bold 1, BorderStyle 1, Outline 6, Encoding 1) are outside constants.py, against the CLAUDE.md numbers rule. p1-constants-timeout covered only compose and qa. Fix: Architect moves them to constants.py, or records an exception.
- N2 `pipeline/render/qa.py:155` `Check` repeats the `QAFailure.check` Literal in `schema.py:166`. Drift risk if a check is added. Fix: export the alias from schema.py (contract, Architect).
- N3 Duplication accepted: `compose._run_ffmpeg`/`_tail` vs `qa._run`, and `align._wav_seconds` vs `kokoro.check_wav`. Adapters may not import each other and two copies do not justify a shared layer. Revisit on a third copy.
- N4 `.github/workflows/render.yml:54` imports `tests.media` (a locked test helper) on the production runner. Decided in p1-golden-65s; move the helper into `pipeline/` when Phase 4 schedules renders.
- N5 No runtime word-count check: `TIKTOK_WORDS` is used only by tests. At Phase 2 entry, reject a script outside `TIKTOK_WORDS` before the voice step (CSO note).
- N6 `requirements.txt` pins `soundfile`, imported nowhere. Check that kokoro does not need it at runtime, then drop it (tooling, owner approval).
- N7 `constants.py:47` and `spec.md:49` say "PLAN.md allows 61 s"; PLAN.md section 4 now says 62 to 90 s. Fix the comment (Architect) and spec.md.
- N8 architecture.md section 5 says only `render_one.py` catches exceptions, but kokoro, align, compose and qa catch and wrap. Section 7's "until then it is a manual Gate 1 check" is stale (the scope check exists).
- N9 `tests/docs_check.py` missed the workflow.md row in Blocking 3 because the row uses role names, not task ids. Fix: test_author task to require task ids in status rows, or the close-out uses ids.
- N10 Visual QA notes (empty end frame at 69.1 s, two-line caption near 34 to 38 s not sampled) are accepted for Phase 1; revisit with Phase 3 templates.
- Carried forward unchanged: CSO P1-1, P1-3, P1-6 at Phase 2 entry; P1-2, P1-4, P1-5 and Auditor A1 to A3 before the first public publish; QA lead items 14 and 15 skipped by owner rule; orchestrator doc follow-ups and the `huggingface_hub` pin.

## What changed (and why)
Only this handoff. The reviewer is read-only.

## Decisions made
- Blocking means a PRD criterion not met or main inconsistent. Code notes are not blocking: every task already passed Gate 2 and the QA lead gaps were closed by p1-qa-tests.

## Tried and abandoned
- Running the fast suite locally: 15 collection errors from the stray site-packages `tests` package (lessons.md 2026-11-15), even with `PYTHONPATH` set. Relied on CI instead.

## Known risks
- Main CI green is assumed from the run in progress; re-check before closing.

## Next step
Owner approves the audit report. Orchestrator confirms CI green on main, applies Blocking 3 in a docs close-out, turns N1, N2, N7 and N9 into Architect or test_author tasks (N5 at Phase 2 entry), then closes Phase 1 and starts Phase 2 planning.

## Docs
- workflow.md: status row for the phase-end reviews (done), and a p1-phase-review row.
- CLAUDE.md: remove "No pipeline code yet"; add `docs/threat-model.md` to "Where things are"; Status after close.
- architecture.md: section 5 error-handling wording, section 7 stale scope-check line, threat-model pointer.
- spec.md:49: drop "PLAN.md allows 61 s".
- PRD.md section 7: owner's audit approval.
- orchestrator.md: drop the stale SPEECH_WPM 150 line.
- lessons.md, update the 2026-11-15 `tests` shadowing entry: `pyproject.toml` already sets `pythonpath = ["."]` and it does not help. The stray `tests` is a regular package and the repo's `tests/` has no `__init__.py`, so it is a namespace package and loses whatever the path order. Fix: add `tests/__init__.py` (locked, Architect) or uninstall the stray distribution.

## Evidence
- On main 66add7f: `python tests/docs_check.py` passed; `ruff check .` clean; `mypy --strict pipeline/` no issues (11 files); `pytest .harness/tests` 69 passed. Fast suite not runnable locally (see Tried and abandoned); CI on 3a0ec2e green, on 66add7f in progress.
- Read: all of `pipeline/`, PRD.md, architecture.md, spec.md sections 4 and 7, workflow.md, PLAN.md section 4 and 11 (grep), p1-qa-lead, p1-cso and p1-audit handoffs, orchestrator.md, render.yml (grep), PR #55 diff.
