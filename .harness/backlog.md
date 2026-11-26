# Backlog

Findings from reviews and phase-end checks that are not worth a task yet (HARNESS.md section 6b, "Phase-end review policy"). One row per finding, newest at the bottom. Only critical or high findings, or ones that block go-live, become tasks right away; the owner picks the rest. When one becomes a task, add its id in the last column. Never delete a row: mark it `dropped` with a reason.

Severity: critical, high, medium, low. Source: the handoff or review that raised it.

| Severity | Finding | Source | Task |
|---|---|---|---|
| medium | No regression test for `_hides_ascii_digit` on NFKD-folded symbols (e.g. U+32C0) | p2-phase-review, orchestrator 12th | |
| medium | `validate.py` lets U+2028 and U+2029 through, and leaves `topic`, `visual.data`, title, description and tags unchecked; CJK numerals and homoglyph number words also pass | p2 reviews | |
| medium | `pick.py` `_load_approved` does not check file name equals id, or duplicate approved ids | p4-youtube review | |
| low | Log the real HTTP status (201 vs 200) in `youtube.py` | p4-youtube review | |
| low | `_send_video` docstring disagrees with the read_bytes `sent` flag | p4-youtube review | |
| low | `check_script` docstring on unlinked fact ids: only SUPPORTED and PARTIAL convert | p2b wave 3 review | |
| low | Batch QA tests match the `_code` inline span layout; loosen if the layout changes | p2b wave 3 review | |
| low | A scene object with extra keys is rejected, though the docstring says only top-level extras are ignored | p2-generate review | |
| low | Sample scene 4 should also cite Bloop facts 7 and 8 | p2-seed-sources review | |
| low | `kokoro.py`: streaming hash, NaN guard, `repo_id` | p1 review | |
| low | No meaning check on the hook line | p2b-hook-check review | |
| medium | architecture.md: add a Workflow B section (four jobs, claim before upload on the `ledger` branch, run and blob binding, upload verifies the claim before the secret step, hashed render install); fix :64, :66 (alerts dropped by O6), :123 and :134 (repo is public), :141 (14 sources), :144 (gap closed by the claim design) | p4b-plan "Docs owed", split out of p4b-docs 2026-11-23 | |
| low | PLAN.md: :35, :89, :279 repo is public; :74, :112, :257 ledger branch replaces the move to `queue/published/`; :211 cadence 7 a week with refill; :246 "exit cleanly" becomes a red run (O6); :252 drop "skip, try next"; :311 cite the 2026-11-02 revision; :335 narrowed Phase 4 done-when (O5); section 6 built mitigations; section 9 `ledger` branch | p4b-plan "Docs owed", split out of p4b-docs 2026-11-23 | |
| high | CI never installs the hashed lock files, so a Dependabot bump that breaks resolution (pydantic 2.14.4 needs pydantic-core 2.50.5; thinc 10 and curated-transformers 2 conflict with spacy 3.8.18) merges green and fails only in a live workflow. Add a CI job that resolves each hashed lock for Linux CPython 3.12 (for example `pip install --dry-run --require-hashes --only-binary=:all: --platform manylinux2014_x86_64 --python-version 3.12 --target <tmp> -r <lock>`, or resolve without hashes) and fails on ResolutionImpossible; consider a Dependabot group or ignore for packages with exact cross-pins | weekly-scripts run 45232745791 and 45253643834, orchestrator 22nd | |
| high | Push-in anchoring unverified: libass scales `\fscx/\fscy` about the `\pos`/`\move` point (top-left under `\an7`), `\org` only sets the rotation centre, so the push-in may drift the set down and right (about 43 px, 77 px at scale 1.08) instead of zooming about the frame centre. The locked `test_sets.py` asserts the `\org` tag and the move values. Check on the first render (p3-compose golden frames, M1); if confirmed, an Architect task compensates in `\move` and updates the locked test | p3-sets visual QA, 2026-11-26 | |
| medium | p3-sets-art: layers must be full-bleed out to the 120 px margin (drift cap uses all of it); keep near-layer fills dark in y 1048 to 1432 behind the captions; confirm libass anchors drawings with negative coordinates at the art origin | p3-sets visual QA, 2026-11-26 | |
| low | p3-character: wave swing (+`\frz` end) puts the thumb behind the ear; ground shadow bobs with the host; `character.py` docstring says no IO but `host_origin` reads the YAML and `host_events` takes its origin from disk, not `art`; `talking_mouths` of only `rest` gives ZeroDivisionError | p3-character reviews, 2026-11-26 | |
| low | p3-ass-kit and p3-validate-visuals: `text_event` does not reject newlines; item text may carry `{}\` (the renderer must escape); chart value regex accepts `1,`; U+2028 and U+2029 not rejected; the sets.py docstring should say the fade end is clamped | p3 wave 4 and 5 reviews, 2026-11-26 | |
