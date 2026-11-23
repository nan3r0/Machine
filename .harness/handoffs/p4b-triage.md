# Handoff: p4b-triage

Proposal for the owner to decide. No task YAML was changed. State checked against `origin/main` (b2b7ad3, PR #140), `gh pr list` and `.harness/status.yaml` on 2026-11-23.

## Summary

- There are 16 task YAMLs in `.harness/tasks/phase4b/`, not 15: `15_youtube_redact.yaml` was added after the plan (PR #135).
- 13 are merged. Nothing is in flight. Three are still open: `p4b-runbook`, `p4b-docs`, `p4b-cso`.
- None of the 16 is in `.harness/status.yaml` `done` yet. The close-outs (status.yaml, workflow.md rows, CLAUDE.md status, outcome log) are owed for all of them. That is one docs PR, mechanical (Scribe, Haiku). Do not mark `p4b-youtube-survivors` done before `p4b-youtube-redact`.
- Per the new phase-end policy (HARNESS.md 6b), 4b is a follow-up sub-phase, so it gets no phase-end QA lead, auditor or phase review. Go-live is a full-set trigger, but Phase 4's QA lead, audit and phase review already ran (`p4-qa-lead`, `p4-audit`, `p4-phase-review`). Only the CSO delta (`p4b-cso`, threat model v3.1) is new before go-live.

## Table

Models: test_author, architect, CSO and every review are Opus; implementer is Sonnet; scribe is Haiku. "Reviews" = Gate 2, plus security where `.harness/config.yaml` path triggers match.

| # | Task | Status | Bucket | Why | Model, reviews |
|---|---|---|---|---|---|
| 00 | p4b-youtube-contracts | merged #127 | before go-live | Locked tests for F1 (paid placement false), token characters, credit line | Opus test_author, Gate 2 |
| 01 | p4b-drop-cottingley | merged #126 | before the first weekly-scripts run | Audit F6, locked `MIN_FILES` | Opus test_author, Gate 2 |
| 02 | p4b-youtube | merged #129 | before go-live | F1 and the token check, a go-live gate in PRD R18 | Sonnet, Gate 2 and security (Opus) |
| 03 | p4b-ledger-contracts | merged #128 | before go-live | P1-2 (critical): contract for the bot-only ledger branch and run binding | Opus test_author, Gate 2 |
| 04 | p4b-pick-ledger | merged #131 | before go-live | Pick rules for the ledger design | Sonnet, Gate 2 and security (Opus) |
| 05 | p4b-ledger-workflow-tests | merged #130 | before go-live | Locked tests for Workflow B on the ledger branch, P4-1 and P4-2 | Opus test_author, Gate 2 |
| 06 | p4b-ledger-workflow | merged #132 | before go-live | P1-2 and P4-1 are go-live gates | Sonnet, Gate 2 and security (Opus) |
| 07 | p4b-youtube-survivors | merged #133 | **backlog candidate**, already spent | Mutation-survivor tests, a quality gain, not a go-live gate. It found the redaction bug, which is why 15 exists | Opus test_author, Gate 2 |
| 08 | p4b-render-lock-tests | merged #134 | before go-live | P1-4 heavy half (hashed render install) is a go-live gate | Opus test_author, Gate 2 |
| 09 | p4b-audit-tests | merged #137 | before first public publish | F7 weekly audit, locked tests and the `make audit` target | Opus test_author, Gate 2 |
| 10 | p4b-render-lock | merged #136 | before go-live | P1-4 heavy half. Security path | Sonnet, Gate 2 and security (Opus) |
| 11 | p4b-weekly-audit | merged #140 | before first public publish | F7 (owner-accepted) | Sonnet, Gate 2 and security (Opus) |
| 12 | p4b-runbook | **open** | before go-live | R17, the first live run, needs the owner's one-time setup steps and the kept-claim procedure (never re-run failed jobs). The owner cannot safely run R17 without it | Haiku scribe. Propose docs-only Gate 2 on Sonnet (no code, no security path); or keep Opus if you prefer |
| 13 | p4b-docs | **open, shrink** | split: PRD R14.1, R16.3, R17, R18, section 7, CLAUDE.md status and the spec.md claims about `queue/published` = before go-live; the rest of the "Docs owed" list = backlog | R18 gates in PRD are what the go-live decision is made against, and the docs check reads CLAUDE.md. PLAN.md private-repo wording, architecture.md stale lines (:64, :66, :123, :134, :141) and the section 6 and 9 notes do not block anything | Sonnet instead of Opus: the plan lists every edit and every decision is made. Opus only for the new architecture.md Workflow B section if you want it written fresh. One review pass, docs check |
| 14 | p4b-cso | **open** | before first public publish | Threat model v3.1 sign-off is a go-live gate (R18); P1-2 was rated critical; new secrets and the ledger branch are exactly the "new integration or secret" trigger | Opus CSO. Keep as is. It is the only phase-end review 4b needs |
| 15 | p4b-youtube-redact | merged #138 | before go-live | Found by the survivor tests: a secret fragment can survive in an error message. Security path | Sonnet, Gate 2 and security (Opus) |

Merged count: 00 to 11 and 15 = 13 tasks.

## Suggested next steps for the owner

1. Decide 13 (shrink or keep whole), and whether 12 can use a Sonnet Gate 2.
2. Launch 12 and 14 in parallel (no shared paths), then 13 once 12 has merged.
3. One close-out PR for all 16 tasks (Scribe).
4. Go-live gates that are owner actions, not tasks: `ledger` branch bootstrap, rulesets, deny rules, F8 retention, audit approval, threat model v3.1 sign-off, R17 by hand.
5. The CI reports re-dispatch (mutation and coverage) is only needed if you want fresh QA numbers. The new policy does not run a QA lead for 4b, so it can wait for the Phase 4 go-live review or be skipped.

## Docs

none (proposal only; `.harness/backlog.md` is new and described in HARNESS.md section 6b).

## Evidence

`gh pr list --state all`, `git branch -a`, `.harness/status.yaml`, `.harness/tasks/phase4b/*.yaml`, `p4b-plan.md`, `p4-phase-review.md`. No tests run for this file.
