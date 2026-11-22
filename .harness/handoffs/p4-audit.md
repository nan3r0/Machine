# Handoff: p4-audit

## Goal
Phase 4 compliance audit (HARNESS.md 6b, `.harness/tasks/phase4/06_audit.yaml`): YouTube API terms and policies for an unverified personal project, OAuth scope, synthetic disclosure, description credit, licences, data retention in a public repo, inauthentic-content risk. The owner approves it.

## Status
done, audited at main 974d76b. Owner approval pending. No blocker for Phase 4 code. Go-live (R18) waits on the owner items below and on the CSO gates P1-2, P1-4 heavy half and P4-1 (threat model v3).

## What changed (and why)
None. Read-only review.

## Web checks (2026-11-22, official Google and GitHub pages)
- youtube.upload cannot call videos.update or videos.delete (each needs youtube, youtube.force-ssl or youtubepartner): pass. The code requires exactly that scope (`pipeline/publish/youtube.py:142-143`, `pipeline/constants.py:126`). Threat model v3 can drop its "re-check at audit" wording.
- The private-only lock on uploads from unverified API projects was lifted (revision history 2026-11-02). No compliance audit is needed for public uploads. The code always sends `public` (`constants.py:128`, `youtube.py:159`). Still confirm on the first live run (R17) that the video is public.
- videos.insert costs 1 unit in its own bucket (100 calls a day): not a constraint. The consent screen must be "In production" or refresh tokens expire in 7 days.

## Findings for the owner
- F1 medium: `paidProductPlacementDetails.hasPaidProductPlacement` no longer defaults to false (revision 2026-11-16) and `youtube.py:150-163` omits it. Effect on a video is unverified. Fix is an Architect contract change (constant plus `part=`). Do before go-live.
- F2 medium (monetisation, not account): of the 7 PLAN section 6 mitigations only human approval and the disclosure are built; cadence is 7 a week (`constants.py:89`) against the plan's 3 to 4. Decide O4 before R18.
- F3 low to medium: the public repo documents a scheduled faceless pipeline and mass-production risk. Options: accept, go private after P1-2 closes, or never link it from the channel. Recommendation: accept and never link.
- F4 pass with notes: the credit line is a courtesy (facts are not copyrightable). Record O3 consent in PRD section 7. The first video credits NOAA while the line says Wikipedia; accept or reword the constant.
- F5 pass: `containsSyntheticMedia = True` is the safe reading and costs nothing.
- F6 low: `sources/cottingley-fairies.yaml` is still in `sources/` with no recorded decision. Decide.
- F7 low: the weekly audit workflow planned in HARNESS.md 6b and PRD.md:207 does not exist. Build it or defer it formally in PRD section 7.
- F8: set Settings, Actions, Artifact and log retention to 30 days or less (logs are public, no secrets in them).
- F9 low, unverified: video ids stay forever in git, Developer Policies III.E.4(c) allow other data 30 days. Recommendation: accept.
- F10 low: API Services ToS section 7 asks for a published privacy policy; accept as a personal tool or add a short public note.
- F11 pass: no GPL files are tracked or distributed (go-public re-check from p1-audit and spec.md:126). No LICENSE file, so all rights reserved.
- A1 and A3 closed. OAuth scopes, secrets and permissions, artifact retention, upload limits: pass.
- pip-audit adds mcp 1.29.0 (GHSA-qx49-fqc8-xw99) and wcmatch 8.5.2 (GHSA-53pm-wgxf-c6qf): dev-tree only (semgrep), not in `requirements-generate.txt`, so unreachable from the secret jobs. Accept.

## Decisions made
Scope, private-lock lift and quota recorded as pass from official pages, with R17 as the live confirmation. F1 rated medium and pre-go-live, not blocking R17. The two advisories recommended for acceptance.

## Tried and abandoned
Confirming what an undeclared paid-placement flag does; confirming whether video ids are exempt from the 30-day rule; finding the run id of the reports artifact. None settled from official pages.

## Known risks
Policy pages change often (two relevant API changes this month). With 2 of 7 mitigations, expect YPP review to be the hard gate. R17 has not run.

## Next step
Owner approves the report and decides F1, F2 (O4), F3, F6, F7, F9, F10, and sets F8. If F1 is accepted, an Architect contract-change task adds `paidProductPlacementDetails`.

## Docs
- `docs/threat-model.md` section 2 YouTube asset row: replace "(re-check on Google's pages at audit)" with "confirmed 2026-11-22 (p4-audit)".
- `spec.md:126`: "this private pipeline" is stale, say no GPL files are tracked or distributed. `spec.md:122`: semgrep is 1.186.0.
- `PLAN.md:311`: cite the 2026-11-02 revision and the creator-settings caveat. `PLAN.md` section 6: note which mitigations are built.
- `PRD.md` section 7: approval, O3 consent, decisions on F1, F3, F6, F7, F9, F10, and the 2026-11-02 and 2026-11-16 API facts with source and date. `PRD.md:207`: weekly audit decision.

## Evidence
No tests run. Read the task YAML, context files, all four workflows, `youtube.py`, `constants.py`, `pick.py`, `spec.md`, threat model v3, lessons.md, the pip-audit and licences reports. Web: developers.google.com YouTube v3 docs (videos insert, update, delete, resource, revision history, developer policies, API services terms), support.google.com YouTube answers 14328491 and 1311392, Google OAuth 2.0 page, GitHub Actions settings docs.
