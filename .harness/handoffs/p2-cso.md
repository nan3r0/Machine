# Handoff: p2-cso

## Goal
Phase 2 threat model update: turn the section 5 Phase 2 seeds into section 4 rows with file:line controls, record the state of P1-1 (D1), check P1-3 and P1-6 against the code, cover the new Gemini, sources, approval PR and write-permission surface, and list new gaps as proposed tasks.

## Status
done (docs only). Uncommitted: this session had no shell (Read, Grep, Glob, Edit, Write only), so the orchestrator commits `docs/threat-model.md` and this handoff on `task/p2-cso`. Owner sign-off of the threat model is still pending (required before the first public publish).

## What changed (and why)
- `docs/threat-model.md` rewritten as version 2:
  - Section 1 describes Phase 2 as built: three workflows, the two-job Workflow A, one allowlisted secret not yet added.
  - New assets: the approval PR, `GEMINI_API_KEY`, the sources, the Gemini quota.
  - New boundaries: sources into the writer, model output, the artifact between jobs.
  - New tables 4.5 (sources and model output), 4.6 (Gemini API) and 4.7 (artifact).
  - The Phase 2 seeds are now section 4 rows. Section 5 keeps Phases 3 and 4 only, with three new seeds (`on_screen_text` in the PR body, Workflow B re-validates, ingest code-spans fact text).
  - Gap list ranked with P2-1 to P2-6.
- Orchestrator notes recorded:
  - PR body injection row.
  - Gemini quota exhaustion row, including that the budgets count logical calls (up to 28 HTTP requests per model per run) and that a same-day rerun fails at `git push`.
  - Fact text renders as plain Markdown, accepted while sources are owner-reviewed.
  - The separate-checkout note, as low and with its assumption stated.
  - The artifact carrying all of `queue/approved/` (P2-2).
  - The `actions/download-artifact` v8.0.2 pin `9000827c`.

## Decisions made
- **D1 recorded as open.** Option (c)'s conditions are listed as conditions, not as a decision: own AI Studio project with no billing, separate from the YouTube Cloud project, key restricted to the Generative Language API, rotate on doubt, (a) or (b) before Phase 4 tokens.
- **P1-3 marked closed with residuals.** The PR body shows title, description and tags verbatim (`pipeline/script/batch.py:180-193`), with caps and character checks in `pipeline/script/validate.py:37-74`. Residuals:
  - bare-domain and full-width URLs (P2-3);
  - `on_screen_text` is not in the PR body and has no length cap. It is not rendered today, so this is a Phase 3 seed.
- **P1-6 re-checked, holds.** `WRITE_JOBS` and `SECRET_JOBS` are disjoint (`tests/test_workflow_safety.py:159-161`), and the key is in one step's env only.
- **P1-4 raised for the key job.** `generate` holds the key and also writes the scripts and the PR body, so a bad transitive release could make the body disagree with the files. The PR diff, not the body, is the authoritative review until P1-4 closes.
- **The key waits only on the light half of P1-4.** The orchestrator state said "P1-4 closed before the key". This narrows it to P2-1, because the key reaches only `generate`, which installs only `requirements.txt`. The heavy half stays a gate on Phase 4 tokens. The orchestrator or owner confirms the narrowing.
- **Line references carried over from version 1 were re-checked and corrected:** `compose.py:124` and `:34-35`, and `qa.py:94`.
- **Phase 2 has no live ingest.** The prompt-injection path is therefore a source-file edit, not RSS.
- No owner decision was changed.

## Tried and abandoned
- none

## Known risks
- P2-4 rests on GitHub's documented rule that events made with `GITHUB_TOKEN` start no workflow runs. Not observed yet; verify on the first live run that the scripts PR shows no checks.
- The 4.7 checkout row assumes `actions/checkout` without `ref` checks out the triggering commit in both jobs. Not verified against the action's source in this session.
- `gh secret list` was not re-run (no shell). Version 1 found no secrets on 2026-11-16; the orchestrator state says the key has not been added.
- Whether platforms auto-link bare domains in descriptions was not checked. P2-3 stands either way, because a printed domain still sends viewers somewhere.

## Next step
1. The orchestrator commits this branch, then turns the proposed tasks below into task YAMLs or owner decisions.
2. Before the first live Workflow A run, in this order: the owner decides D1, then P2-1 lands, then `GEMINI_API_KEY` is added (after the repo setting for Actions-created PRs is on), then P2-2 and the P2-6 docs part land.

### Proposed tasks
Each finding has a location, severity, failure scenario and fix hint.

**P2-1. Hash-pin the light requirements (the light half of P1-4).** High.
- Location: `requirements.txt`, installed in the key-holding job at `.github/workflows/weekly_scripts.yml:28-29`.
- Scenario: a malicious new release of an unpinned dependency of pydantic is installed on the Sunday run. It reads `GEMINI_API_KEY`, and it rewrites a queued script while leaving `pr_body.md` clean.
- Fix hint: a separate hashed file (for example `requirements-generate.txt`) that pins every package `requirements.txt` resolves to, with `--hash=sha256:...` lines. Only the `generate` job installs it, with `--require-hashes`. Take the hashes for the runner's wheels (`pip download --platform manylinux... --python-version 3.12 --only-binary=:all:`, then `pip hash`), because pydantic-core, numpy and soundfile ship per-platform wheels. This needs no new tool.
- Do not add hashes to `requirements.txt` itself. `ci.yml:82` and `:139` install it in the same pip call as the unhashed dev and heavy files, and one hashed line switches that whole call into hash-checking mode, which breaks CI and the local venv setup.
- The workflow test is locked, so the Architect owns it. The heavy lock stays P1-4.

**P2-2. `open-pr` must add only new scripts.** Medium.
- Location: `.github/workflows/weekly_scripts.yml:39-41` (the artifact carries all of `queue/approved/`) and `:74` (`git add queue/approved/*.json`).
- Scenario: a `generate` bug or a compromised dependency edits last week's approved script. The edit rides into the weekly PR, and the PR body does not mention it.
- Fix hint: in `open-pr`, before `git add`, fail if `git diff --quiet -- queue/approved/` reports a change to a tracked file. Add only untracked files whose names match `^[a-z0-9]+(-[a-z0-9]+)*\.json$`. This uses shell only, with no pipeline code in the write job. Extend `tests/test_weekly_workflow.py` (locked, Architect).

**P2-3. URL check misses bare domains and look-alike forms.** Medium.
- Location: `pipeline/script/validate.py:38-40`.
- Scenario: an injected fact makes the writer put "full story at example.net/case" or a full-width `ｗｗｗ．` form into the description. Every check passes, and the text is published under the channel.
- Fix hint: NFKC-normalise before the checks. Also reject domain-like tokens: a dot followed by 2 or more letters as a TLD (so "3.5" passes), with an optional path. Add tests for `bit.ly/x`, `example.net`, full-width forms and decimals (contract change, Architect).

**P2-4. The approval PR runs no CI before merge.** Low to medium. `generate` already validates each new script (`generate.py:168-172`); what is missing is a check outside the job that wrote the files.
- Location: `.github/workflows/weekly_scripts.yml:67`, `76-77`.
- Scenario: a queue file that fails `tests/test_queue_scripts.py` is merged on a PR that shows no checks. CI fails on `main` only after approval, and from Phase 4 it can be published before anyone looks.
- Fix hint: a third, read-only job in `weekly_scripts.yml`, with no secret and no write token. It downloads the artifact onto a fresh checkout, runs the queue check (`tests/test_queue_scripts.py` logic: every file parses, passes `validate.problems` and is named after its id), and `open-pr` gets `needs:` on it.
- For Phase 4, Workflow B also runs `validate.problems` on each queue file before publishing (the section 5 seed).
- Rejected:
  - Dispatching `ci.yml` by hand also starts the 90 minute `reports` job (`ci.yml:118-121`) on top of the 45 minute check, every week, which spends the minutes P1-5 protects.
  - A PAT for `open-pr` would add a secret to the write job.

**P2-5. Refuse HTTP redirects in the Gemini client.** Low.
- Location: `pipeline/script/gemini.py:74`, which uses urllib's default opener.
- Scenario: the endpoint answers 3xx to another host, and urllib re-sends the `x-goog-api-key` header there.
- Fix hint: use an opener whose `HTTPRedirectHandler.redirect_request` returns None, and treat any 3xx as a GeminiError. Add a test with a fake 302 (the test is locked, Architect).

**P2-6. Gemini quota: say what the caps count, and stop overlapping runs.** Low.
- Location: `pipeline/constants.py:114-116`, `pipeline/script/gemini.py:71-90`, `.github/workflows/weekly_scripts.yml:6`.
- Scenario: repeated dispatches, or a same-day rerun that fails at `git push`, spend up to 28 requests per model each and leave the Sunday run with nothing.
- Fix hint:
  - spec.md says the caps are logical calls, with up to twice as many HTTP requests;
  - the owner confirms each model's free daily limit covers 28 requests;
  - add a `concurrency: { group: weekly-scripts, cancel-in-progress: false }` to the workflow;
  - optionally, the run fails early when `scripts/<day>` already exists.

## Docs
- `docs/threat-model.md`: version 2, written by this task.
- `PRD.md` section 7: when D1 is answered, record it there and in the threat model's P1-1 row. Until then, no change.
- `architecture.md` section 7: add P2-2 (the artifact can alter approved scripts) and P2-4 (the approval PR runs no CI) as weak points. The line 134 P1-1 text stays.
- `spec.md`: Gemini caps count logical calls, with up to 2 HTTP requests each (P2-6).
- `PLAN.md` section 11 Phase 0: unchanged. Keys go into Secrets only after D1, and only after P2-1 for the Gemini key.
- `CLAUDE.md` Status: p2-cso done; P2-1 to P2-6 proposed.
- `lessons.md`: none.

## Evidence
- No code changed; no tests apply. Docs check not run (no shell in this session).
- Read: task YAML, orchestrator State blocks, the version 1 threat model, `p1-cso.md`, the D1 section of `architect-p2-plan.md`, HARNESS.md section 6b, and architecture.md (security lines).
- Workflows read: `weekly_scripts.yml`, `ci.yml`, `render.yml` (triggers and permissions).
- Code read: `tests/workflow_rules.py`, `tests/test_weekly_workflow.py`, `tests/test_workflow_safety.py:159-161`, `tests/test_sources_files.py:38-52`, `tests/test_queue_scripts.py`, `pipeline/script/{batch,gemini,generate,validate,sources}.py`, `pipeline/factcheck/semantic.py` (data block), `pipeline/schema.py:99-119`, `pipeline/render_one.py:30-44`, `pipeline/constants.py` (Gemini numbers), `requirements.txt`.
- Grep: `on_screen_text` has no use under `pipeline/render/`.
