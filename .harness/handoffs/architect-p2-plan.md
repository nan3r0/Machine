# Handoff: architect-p2-plan

## Goal
Plan pipeline Phase 2 (scripts and fact-check) as a minimal task graph that gets Workflow A to open a real PR of 7 fact-checked scripts, with CSO P1-1, P1-3, P1-6 and phase review N5 handled at entry.

## Status
done (plan). Branch `docs/p2-plan`, committed, not pushed. The plan waits for owner approval and the decisions below. p2-entry-ci and p2-factcheck-exact need no decision and can start once this branch merges.

## What changed (and why)
- `.harness/tasks/phase2/00_*.yaml` to `13_*.yaml`: 14 tasks (below). Narrow `paths_allowed`, no two parallel-ready tasks share a path, no task lists a test file an earlier task owns (tests/conftest.py maps each file to one task).
- `pipeline/factcheck/__init__.py`, `normalise.py`, `exact.py`: contract stubs for p2-factcheck-exact. The docstrings pin every rule (number forms, year words, the zero-to-nine rule, proper-noun rule) so the tests can be exact.
- `tests/factcheck/test_exact.py` (locked by `tests/**`): 61 tests, literals from PLAN.md section 5 plus hypothesis properties against an independent number-to-words oracle written in the test.
- `.harness/config.yaml`: security specialist review now also triggers on `pipeline/script/gemini.py` (secret), `batch.py` (model output into the PR body) and `validate.py` (the P1-3 control).
- `PRD.md`: Phase 2 criteria R8 to R13, research facts with sources in section 7, the old Phase 2 open question replaced by a pointer to D1 to D8.
- `spec.md`: Phase 2 layout, source file, Flag and LineVerdict shapes, proposed numbers, Gemini key handling, "no new dependency". Phase review N7 (the "PLAN.md allows 61 s" note) fixed.
- `architecture.md`: Workflow A flow and job split, Domain layer row, Phase 2 decisions, testing rows, weak points. Phase review N8 fixed (error-handling wording, stale scope-check line).
- `workflow.md`: Phase 2 criterion rows (future test files without backticks so the docs check stays green), Phase 2 module order and status table.
- `CLAUDE.md`: Status line.

## Task graph (14 tasks, in run order)
| # | Task | Role / model | Depends on | Paths |
|---|---|---|---|---|
| 00 | p2-entry-ci | test_author / Opus | none | workflow rules, docs check and their tests, workflow.md |
| 01 | p2-factcheck-exact | implementer / Sonnet | none (tests on this branch) | `pipeline/factcheck/normalise.py`, `exact.py` |
| 02 | p2-contracts | test_author / Opus | p2-entry-ci, owner D2 to D6 | schema, constants, `pipeline/script/**` stubs, `semantic.py` stub, `tests/**` |
| 03 | p2-validate | implementer / Sonnet | p2-contracts | `pipeline/script/validate.py`, `pipeline/render_one.py` |
| 04 | p2-gemini | implementer / Sonnet | p2-contracts | `pipeline/script/gemini.py` |
| 05 | p2-seed-sources | architect / Opus (needs web tools) | p2-contracts | `sources/**` |
| 06 | p2-generate | implementer / Sonnet | p2-validate, p2-gemini | `pipeline/script/sources.py`, `generate.py` |
| 07 | p2-semantic | implementer / Sonnet | p2-gemini | `pipeline/factcheck/semantic.py` |
| 08 | p2-batch | implementer / Sonnet | p2-factcheck-exact, p2-generate, p2-semantic | `pipeline/script/batch.py` |
| 09 | p2-weekly-workflow | implementer / Sonnet | p2-batch, p2-seed-sources, p2-entry-ci | `.github/workflows/weekly_scripts.yml` |
| 10 | p2-qa-lead | qa_lead / Opus | p2-weekly-workflow | read-only |
| 11 | p2-cso | cso / Opus | p2-weekly-workflow | `docs/threat-model.md` |
| 12 | p2-audit | auditor / Opus | p2-weekly-workflow | read-only |
| 13 | p2-phase-review | reviewer / Opus | 10, 11, 12 | read-only |

Count: 10 build tasks (2 test_author, 7 implementer, 1 research) plus 4 phase-end reviews.

## Owner decisions needed
Defaults are what the task YAMLs assume; a different answer changes p2-contracts before it runs.

**D1. Secrets handling, CSO P1-1 (decide before the Gemini key is added).** Research answer to the open question: **no.** docs.github.com, "Deployments and environments" (read 2026-11-16): "If you are using GitHub Free, environment secrets are only available in public repositories"; deployment branch rules in private repos need Pro or Team, and required reviewers are public-only on Free, Pro and Team. The rulesets page names only Team and Enterprise. So a `main`-only environment secret is not possible here at $0. Options:
- (a) A second private repo, pushed to only by the owner, holds the secrets and runs the secret-bearing workflows against this repo's `main`. Agents would need a Claude Code deny rule for pushing there (owner-only settings change), because they use the owner's credentials.
- (b) Make this repo public. That makes environment secrets with a `main` rule free (and Actions minutes unlimited), but publishes the code, harness and handoffs, and the Auditor's GPL notes start to apply.
- (c) Keep secrets in this repo and accept that any pushed branch can add a workflow that reads them. For the Gemini key alone the damage is its free quota (no payment method, so no bill); restrict the key to the Generative Language API, rotate it on any doubt, and decide (a) or (b) before Phase 4 adds publishing tokens.
- I have not picked one. Workflow A's live run (R13.5) waits for this; every code task before it uses fakes and needs no secret.

**D2. Approval path.** Default: Workflow A writes scripts straight into `queue/approved/` on its PR branch; merge is approval. Drop `queue/pending/` and `on_merge_approve.yml`. (PLAN.md sections 2, 7, 9.)

**D3. Ledger.** Default: a source is used once any of its fact ids is in a script under `queue/`; no `data/used_facts.json`. (PLAN.md sections 2, 7, 9; PRD open question.)

**D4. Sources.** Default: hand-curated `sources/*.yaml`, no RSS, arXiv or news ingest in Phase 2. p2-seed-sources (Opus with web tools) seeds 14 solved mysteries; the owner reviews every fact in that PR. At 7 a week that is two weeks of scripts: how to refill (another research session, or the owner) needs deciding before Phase 4 goes live.

**D5. Gemini models and budget.** The owner reads the writer and checker model ids and their free daily limits off the AI Studio dashboard (the docs page shows one model only). Not a `gemini-2.5-*` model (deprecated 2026-12-01). Default budget: at most 14 writer and 14 checker calls per batch.

**D6. Published-field policy (P1-3).** Default: no URLs at all (no allowlist), no control, bidi or zero-width characters; title up to 100 characters, description up to 1000, at most 10 tags of up to 30 characters and 500 in total.

**D7. Harness stage.** HARNESS.md sections 2a, 4 and 10 put Phase 2 at Stage 1 (build `loom run`). The Stage 0 exit criterion is met (14 outcome records). Default: run Phase 2 at Stage 0 and build Loom later, because Loom is a project of its own and slows the first upload. Needs an owner yes, since it departs from HARNESS.md.

**D8. Deferred.** Vacation-mode `count` input (PLAN.md sections 7, 8), the fallback text provider (sections 3, 10), `hook_stats.json` input (Phase 5), and a `script/prompts/` folder (prompts are constants in `generate.py`).

Owner admin steps (no decision): turn on Settings > Actions > General > "Allow GitHub Actions to create and approve pull requests" (believed off by default; not verified in this session); create the Gemini key with no billing and restrict it; add `GEMINI_API_KEY` only after D1.

## Decisions made
- Contracts are split: the exact layer's tests are on this branch (no decision touches them); everything else waits for p2-contracts after D2 to D6, matching how late Phase 1 work wrote tests just before each task.
- Gemini over the standard library (`urllib`), so Phase 2 adds no dependency.
- Two jobs in Workflow A: the key never shares a job with a write token (P1-6).
- `validate.py` (not schema.py) holds the P1-3 caps and word bounds, because schema.py may not import constants.
- The P1-6 test covers every workflow file and allowlists per-job write permissions and secrets, instead of relaxing `assert_safe` for everyone.
- `visual.data` stays `{}` from the generator; Phase 3 fills it.
- p2-seed-sources runs as `architect` because the implementer agent has no web tools.

## Tried and abandoned
- One heredoc batch for the task YAMLs: two files came out empty or missing (unterminated heredoc). Rewritten with the Write tool.
- Putting p2-contracts' acceptance in `tests/test_schema.py`: that file belongs to p1-contracts, and conftest maps a file to the last task listing it, so main would have skipped it. A new `tests/test_schema_sources.py` is named instead.

## Known risks
- D1 has no free, strong answer inside one private repo. Option (c) is acceptable only because the Gemini key has a quota-only blast radius.
- The exact layer misses some cases on purpose (sentence-first names, number words below ten, "point"). It misses rather than false-flags; the meaning check and the owner's review cover it.
- Free Gemini limits are not confirmed for any model (D5). If the writer's daily limit is below 14, the batch flags more lines than it rewrites.
- Sources run out after two weekly batches without a refill plan (D4).
- The scripts PR starts no CI run (GITHUB_TOKEN rule), so the batch's own validation is the gate until the owner edits.
- p2-validate edits `render_one.py`, so its CI run includes the heavy render.

## Next step
1. Owner reviews this branch, answers D1 to D8, merges.
2. Orchestrator runs p2-entry-ci and p2-factcheck-exact (independent paths; may run two at once).
3. After D2 to D6: p2-contracts, then the graph in workflow.md order.
4. Rough effort: 14 task sessions, about 9 Gate 2 reviews and 4 security reviews, plus 4 to 6 fix rounds if Phase 1's rate holds. About 30 sessions, with Opus spending most on p2-contracts, p2-seed-sources and the reviews.

## Docs
- PRD.md, spec.md, architecture.md, workflow.md, CLAUDE.md: changed on this branch (see What changed).
- PLAN.md (owner, after D1 to D8): section 2 diagram and section 7 Workflow A (no `queue/pending/`, no merge action, ledger from queue files, sources only, no hook_stats in Phase 2, PR shows title, description and tags); section 3 fallback provider deferred; section 8 vacation mode deferred; section 9 tree (no `ingest/`, no `on_merge_approve.yml`, no `data/used_facts.json`; add `script/validate.py`, `script/gemini.py`, `script/batch.py`); section 11 Phase 0 line "All keys stored in GitHub Secrets" depends on D1.
- HARNESS.md (owner, if D7 holds): sections 2a, 4 and 10 say Phase 2 runs at Stage 1.
- PRD.md section 7: record D1 to D8 as owner decisions once answered (R13.4 needs D1 there).
- docs/threat-model.md: p2-cso updates it at phase end.
- `.harness/status.yaml`: none now.
- lessons.md: none (no mistake found in shipped work).

## Evidence
Worktree venv with requirements.txt and requirements-dev.txt only (Windows):
- `ruff check .`: all checks passed. `mypy --strict pipeline/`: no issues, 14 files. `python tests/docs_check.py`: passed.
- `pytest` without LOOM_TASK: 325 passed, 75 skipped (the new exact tests are owned by p2-factcheck-exact, so skipped).
- `LOOM_TASK=p2-factcheck-exact pytest tests/factcheck`: 60 failed, 1 passed (the oracle self-test), as expected against the stubs.
- Passable: a throwaway implementation (not committed) passed all 61 tests; the stubs were restored from a copy.
- `pytest .harness/tests`: 69 passed.
- Sources read 2026-11-16: docs.github.com "Deployments and environments", "GITHUB_TOKEN" and "About rulesets"; aistudio.google.com/docs rate-limits, pricing and structured-output pages.
