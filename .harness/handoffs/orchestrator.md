# Handoff: orchestrator

Read this first in any session started without `LOOM_TASK`. Then read only the HARNESS.md sections named below, when needed. Keep this file current: rewrite "State" and "Open items" before you stop.

## Role
You are the Stage 0 orchestrator (HARNESS.md section 10, Stage 0). Model: Sonnet. You launch task sessions, verify their work, run reviews, push, open PRs and log outcomes. The owner only approves the contracts PR and merges PRs. Never edit `.claude/` admin files (owner only, `LOOM_ADMIN=1`).

## How to run a task
1. Worktree per task branch `task/<id>` under `.claude/worktrees/`. Python: `.venv/Scripts/python.exe` in that worktree (create with `python -m venv .venv`, install `requirements.txt` and `requirements-dev.txt` only). Before launching, check `.venv/Scripts/python.exe -c "import pydantic"`; an existing venv may be empty.
2. Launch (window closes itself when the session ends):
   `cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 -Task <id> -Model <from .harness/config.yaml> -WorkDir <worktree> -Message "<brief>"`
   Brief: role, "Follow CLAUDE.md", read the task YAML and handoff, Bash one plain command per call, commit but do not push, finish the handoff including Docs.
3. One background watcher: `sh .harness/scripts/wait_task.sh <worktree> <id> <start-sha> <claude-pid>`.
4. On TASK_DONE: run ruff, `mypy --strict pipeline/`, pytest (with `LOOM_TASK=<id>`), `tests/scope_check.py task/<id> origin/main`. Then one Gate 2 review with `.harness/scripts/run_review.sh` (prompt: read `.claude/agents/reviewer.md`, the task YAML, the handoff, the diff saved to `.harness/reviews/<id>.diff`). Add a specialist review only if `specialist_reviews` paths in config.yaml match.
5. Blocking findings: write `.harness/reviews/<id>-round<N>.md`, relaunch (resume if the session's context is small, else fresh). Non-blocking notes: log them, don't chase them.
6. Push, open the PR, `sh .harness/scripts/wait_ci.sh <pr>` once. Green: tell the owner it's ready. Close the task window by stopping its parent `powershell.exe`, never only `claude.exe`.
7. Close-out after merge: lessons and decisions yourself; Scribe (Haiku) window for status.yaml, workflow.md status, CLAUDE.md status, outcome log. Docs go on a `docs/*` branch, never a task branch.

## Token rules
- Terse replies; caveman style for chat, normal English for docs, commits and PRs.
- Rotate yourself after every task close-out, or at about 50% context, whichever comes first: rewrite State and Open items here. The Stop hook `context_guard.py` does this automatically at 50%: when it blocks your stop with "Context at N%", update this file and the docs it lists, commit, reply ROTATE, and it opens the replacement window. It only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator` (sets `LOOM_ROLE`). Before the hook is registered, tell the owner to start a fresh session (`claude.cmd --model claude-sonnet-5-5`) and type "continue as orchestrator". Cost per turn grows with context, so earlier is cheaper.
- If the hook is not guarding you (you were not started with `-Task orchestrator`), you must rotate yourself: run `/context` at every task close-out and before launching each task, and at 50% write the State block, open the docs PR and tell the owner to start a fresh session. Do not wait to be asked.
- One watcher per task; no polling loops in your own turns.
- One Gate 2 pass per task; chase only blocking findings.

## State (2026-11-17, end of seventh orchestrator session)
- p2-generate merged (PR #67). Close-out on `docs/p2-closeout-2`: status.yaml, workflow.md row, CLAUDE.md status, PLAN.md D3 ledger wording (lines 39, 74, 220, 299), two lessons entries. Next: task 07 p2-semantic, then 08 p2-batch, 09 p2-weekly-workflow.
- p2-semantic brief: its scene facts also go in a delimited data block; point the implementer at `_clean` in `pipeline/script/generate.py` and the 2026-11-17 delimiter lesson (strip until stable).
- Follow-ups for the Architect: locked regression test for the nested delimiter case in `tests/script/test_generate.py`. Non-blocking p2-generate notes: extra keys inside a scene object are rejected (docstring says ignored only at top level); `rewrite_line` raises `IndexError` on a bad index, so p2-batch must bound-check verdict indexes.
- Stale worktrees under `.claude/worktrees/` (about 46) still need cleanup; many have merged branches.

## State (2026-11-16, end of sixth orchestrator session)
- p2-contracts merged (PR #62); added to status.yaml `done` on branch `docs/p2-closeout-1` (this branch).
- Owner merged #63 to #65; their close-out (status.yaml, workflow.md, architecture.md, CLAUDE.md) is on this branch too. Next: task 06 p2-generate. The details below are history.
- Tasks 03 to 05 built, Gate 1 and Gate 2 passed:
  - p2-gemini PR #63: CI green. Gate 2 and security approve.
  - p2-validate PR #64: CI green. Gate 2 and security approve.
  - p2-seed-sources PR #65 (Opus architect agent with web tools, since `open_task_window.ps1` disallows WebFetch and WebSearch): Gate 2 round 1 blocked on Bloop fact 6 abbreviating PMEL, fixed in 1d64fa9. CI was still pending when this session stopped; check `gh pr checks 65`. Owner must review every fact (PR body lists the open questions: BLC1 "unlikely", Cottingley names, Piltdown fact 409 wording).
- After the owner merges 63 to 65: close-out on a new `docs/*` branch (status.yaml `done` += p2-validate, p2-gemini, p2-seed-sources; workflow.md rows; architecture.md render_one flow notes the pre-voice rejection, exit 2; CLAUDE.md status). Then task 06 p2-generate.
- Follow-ups for the Architect (non-blocking review notes):
  - validate.py URL check misses bare domains (`bit.ly/abc`) and fullwidth `www`, short of threat-model P1-3 (description URL allowlist). U+2028/2029 and unassigned code points pass. `topic` and `visual.data` unchecked until they reach a published surface.
  - gemini.py: some failures escape as raw exceptions (connection reset, RecursionError, null steps); urllib's redirect handler would forward the key header on a 3xx.
  - Queue-side: sample scene 4 ("eight years ... not alive") should also cite Bloop facts 7 and 8.
- Both Sonnet implementers this session rewrote source files with a Python script instead of Edit or Write (lessons.md rule). Add a line to the task brief: "Edit and Write only, never a Python or heredoc rewrite".
- Stale worktrees under `.claude/worktrees/` still need cleanup.

## State (2026-11-16, end of fifth orchestrator session)
- Phase 1 closed (owner approved the Auditor report, PR #57). Phase 2 planned (PR #58): 14 tasks in `.harness/tasks/phase2/`, decisions D1 to D8 in `architect-p2-plan.md`.
- Phase 2 done so far: p2-factcheck-exact (PR #59), p2-entry-ci (PR #60). Both merged; their status.yaml and workflow.md close-out is in the p2-contracts branch (see below).
- In flight: task 02 p2-contracts, a Test Author agent on branch `docs/p2-contracts` (agent was spawned from the orchestrator session; if its result never arrived, check the branch `docs/p2-contracts` in `.claude/worktrees/` and `.harness/handoffs/p2-contracts.md`). It also carries the close-out docs and the Opus plan changes. When it is done: verify (ruff, mypy --strict, pytest with and without LOOM_TASK=p2-contracts, docs check), push, open the PR, owner merges, then run tasks 03, 04 and 05 (03 and 04 can run in parallel, max 2 sessions), then 06, 07, 08, 09, then phase-end 10 to 13.
- Owner decisions: D2, D3, D4, D6, D7, D8 default yes; D5 writer `gemini-3.8-flash`, checker `gemini-3.5-flash-lite` (Opus advice 2026-11-16; owner must confirm both allow at least 14 calls a day on the AI Studio dashboard before the first live run; `gemini-2.5-*` retires 2026-12-01, `gemini-3.1-flash-lite` 2027-05-07). D1 (where the Gemini key lives) is still open and blocks only the live Workflow A run: recommended option (c) with a restricted key. Owner admin: enable "Allow GitHub Actions to create and approve pull requests"; start the Google Cloud YouTube setup (Phase 0) in parallel.
- Opus advice folded into the plan: no `story` field (filename is the slug); unique normalised topic test; queue fact ids must resolve to sources; queue/published append-only; picker never reuses a source, short batch says "N of 7: sources exhausted", zero gives no PR; Gemini client fails loudly on 429 and model-not-found. Phase 4 idempotency gap: commit the video id and the queue move right after upload. NotebookLM (Gemini Notebook) is only a manual aid for refilling sources.
- Effort estimate given to the owner: about 30 sessions for Phase 2, 3 to 5 weeks to the first automatic YouTube upload; Phase 3 skipped for the first upload.
- Lesson for the orchestrator: the automatic rotation hook only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator`. A session started any other way must rotate itself at about 50% context.
- PLAN.md lines 127 to 128 (NotebookLM wording) are the owner's edit; the p2-contracts handoff lists the proposed text.
- Non-blocking items for later: phase review N1 to N10 (N4: move the `tests.media` import out of render.yml before Phase 4; N5 runtime word-count check is in p2-validate). To-do artifact: https://claude.ai/artifact/SWmEoSUtr7XwZ5v3o9pPFQ (it is stale; refresh it).
- Stale worktrees under `.claude/worktrees/` need cleanup.

## State (2026-11-16, end of second orchestrator session)
- Phase 1 code complete and owner manual acceptance done: run 43873059742 produced a 69.6 s video (QA passed, no silence), the owner approved the voice, pacing and tone. Decisions in force: every video about 65 s on every platform (62 to 90 s QA range), `VOICE_SPEED` 0.9, tone rules in PLAN.md section 4. Measured speech rate is about 144 wpm (167 words in 69.5 s), `SPEECH_WPM` was 150; now 144 (p1-constants-timeout). Owner still has to set the 65 s average view duration target (PLAN.md section 12 placeholder, after 30 days of data).
- Next: the four phase-end tasks in `.harness/tasks/phase1/` (11 QA lead, 12 CSO, 13 Auditor, 14 phase review; 14 runs last). QA lead and Auditor first need the owner to run the CI `workflow_dispatch` reports job (mutmut and coverage, pip-licenses and pip-audit) and download the output to `out/reports/`: check ci.yml for the job, tell the owner the exact steps. CSO writes `docs/threat-model.md`. These are read-only or docs-only roles on Opus, run each in a fresh visible window or as the matching agent; max 2 at once.
- Usage limit: a 5-hour limit hit once mid-session (Architect agent failed with HTTP 429); resuming it with SendMessage after the reset worked. Add the weekly limit fixture when it happens.
- Launch helper pattern: a small .ps1 taking -Task -Worktree -Brief (Git Bash `cmd //c start` quoting fails). Close windows by stopping the `open_task_window` powershell, excluding your own PID. Process rule: when review requests changes, mark the PR draft before the fix round and tell the owner not to merge.
- Phase 2 (scripts + fact-check) has no task graph yet; the Architect plans it after the phase-end reviews. Darker Kokoro voice and music are deferred (voice needs its own sha256 weights entry; music is Phase 3).

## Open items
- Usage-limit fixture saved (`.harness/tests/fixtures/limit_messages/session_5h-2026-11-15.txt`). Add the weekly one when it happens.
- Known risk: pip-audit ignores two setuptools 81.0.0 advisories because torch 2.11 caps setuptools below 82; drop the ignores when torch lifts the cap (Makefile comment). It also ignores torch PYSEC-2025-194 (fixed in 2.13) because no torchaudio for torch 2.13 exists and stable-ts imports torchaudio at load; move both pins when one ships.
- **Owner to-do, remind them after the first implementer task closes out:** create a reusable skill for this setup, or expand the existing `graph-engineering` skill, with `skill-creator` in an owner-launched admin window (`~/.claude/skills` is protected). It packages the HARNESS.md and CLAUDE.md templates, task, handoff and orchestrator files, all `.harness/scripts`, the lock hook and the rotation hook. It must bake in:
  - tokens: caveman for chat, ponytail for code, model per role (Sonnet orchestrates and implements, Opus advises on architecture, contracts and reviews, Haiku does doc sync), rotation (orchestrator per task or ~50%, tasks at 60%) with automatic handover, one watcher per task, one review pass chasing only blocking findings, low effort for mechanical work, small tool output
  - safety: contracts-first locked tests with a task-aware conftest, lock hook plus CI scope check, `LOOM_ADMIN` for config files, read-only reviewers, specialist reviews only when triggered, clean child-session environments, self-closing windows
  - docs: handoff Docs section, Scribe close-out, CI docs check, lessons logged the same turn
  - cost and limits: $0 rule, heavy tests in CI only, usage-limit pause and resume, at most 2 parallel task sessions
- Doc follow-ups not yet applied: architecture.md line 54 and HARNESS.md section 11 tree comment for `docs_check.py` (add handoff Docs sections, lessons entries, required headings); HARNESS.md section 10 close-out should say status.yaml and the workflow.md row change in the same commit. Pin `huggingface_hub` in `requirements-heavy.txt` (needs owner approval, outside any task's paths). Review notes on kokoro.py (streaming hash, NaN guard, `repo_id`) were non-blocking and are not chased.
