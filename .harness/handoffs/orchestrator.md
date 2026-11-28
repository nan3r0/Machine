# Handoff: orchestrator

Read this first in any session started without `LOOM_TASK`. Then read only the HARNESS.md sections named below, when needed. Keep this file current before you stop: **REPLACE the one State block, never append a new one** (a check in `.harness/tests/test_orchestrator_handoff.py` fails on a second `## State` heading or a file over 12 KB), and edit Open items. Old state goes to `orchestrator-history.md` (append-only, never read at session start) only if it is worth keeping.

## Role
You are the Stage 0 orchestrator (HARNESS.md section 10, Stage 0). Model: Sonnet. You launch task sessions, verify their work, run reviews, push, open PRs and log outcomes. The owner only approves the contracts PR and merges PRs. Never edit `.claude/` admin files (owner only, `LOOM_ADMIN=1`).

## How to run a task
1. Worktree per task branch `task/<id>` under `.claude/worktrees/`. Python: `.venv/Scripts/python.exe` in that worktree (create with `python -m venv .venv`, install `requirements.txt` and `requirements-dev.txt` only). Before launching, check `.venv/Scripts/python.exe -c "import pydantic"`; an existing venv may be empty.
2. Launch (window closes itself when the session ends):
   `cmd /c start "Loom task: <id>" powershell.exe -ExecutionPolicy Bypass -File .harness\scripts\open_task_window.ps1 -Task <id> -Model <from .harness/config.yaml> -WorkDir <worktree> -Message "<brief>"`
   From Git Bash use `powershell -NoProfile -Command` with `Start-Process powershell.exe -PassThru -ArgumentList` and wrap the script path, `-WorkDir` and `-Message` in literal double quotes (spaces in "Claude Projects" otherwise split the arguments and the window dies at once). Confirm the window exists before waiting. Without the claude PID, skip the watcher and ask the owner to say when the window closes (process queries via PowerShell can be denied).
   Brief: role, "Follow CLAUDE.md", read the task YAML and handoff, Bash one plain command per call, commit but do not push, finish the handoff including Docs.
3. One background watcher: `sh .harness/scripts/wait_task.sh <worktree> <id> <start-sha> <claude-pid>`.
4. On TASK_DONE: run ruff, `mypy --strict pipeline/`, pytest (with `LOOM_TASK=<id>`), `tests/scope_check.py task/<id> origin/main`. Then one Gate 2 review with `.harness/scripts/run_review.sh` (prompt: read `.claude/agents/reviewer.md`, the task YAML, the handoff, the diff saved to `.harness/reviews/<id>.diff`). Add a specialist review only if `specialist_reviews` paths in config.yaml match.
5. Blocking findings: write `.harness/reviews/<id>-round<N>.md`, relaunch (resume if the session's context is small, else fresh). Non-blocking notes: log them, don't chase them. **At most 2 review rounds per task.** If round 2 still has blocking findings, stop: escalate to Opus for the fix (HARNESS.md section 6) or tell the owner, never start round 3 with the same implementer. Round 2 reruns only the reviewer(s) that blocked in round 1 (Gate 2 only, or security only), unless the fix touches files outside the blocked findings, then rerun both. The round-2 reviewer gets the round-1 findings and the fix diff only (`git diff <round-1-sha>..HEAD`), not the whole task again.
6. Push, open the PR, `sh .harness/scripts/wait_ci.sh <pr>` once. Green: tell the owner it's ready. Close the task window by stopping its parent `powershell.exe`, never only `claude.exe`.
7. Close-out after merge: lessons and decisions yourself; Scribe (Haiku) window for status.yaml, workflow.md status, CLAUDE.md status, outcome log. Docs go on a `docs/*` branch, never a task branch.

## Token rules
- Terse replies; caveman style for chat, normal English for docs, commits and PRs.
- Rotate yourself after every task close-out, or at about 50% context, whichever comes first: rewrite State and Open items here. The Stop hook `context_guard.py` does this automatically at 50%: when it blocks your stop with "Context at N%", update this file and the docs it lists, commit, reply ROTATE, and it opens the replacement window. It only guards an orchestrator started with `open_task_window.ps1 -Task orchestrator` (sets `LOOM_ROLE`). Before the hook is registered, tell the owner to start a fresh session (`claude.cmd --model claude-sonnet-5-5`) and type "continue as orchestrator". Cost per turn grows with context, so earlier is cheaper.
- If the hook is not guarding you (you were not started with `-Task orchestrator`), you must rotate yourself: run `/context` at every task close-out and before launching each task, and at 50% write the State block, open the docs PR and tell the owner to start a fresh session. Do not wait to be asked.
- One watcher per task; no polling loops in your own turns.
- One Gate 2 pass per task; chase only blocking findings (round cap in step 5).
- Phase-end reviews follow HARNESS.md section 6b "Phase-end review policy": launch the full set only at its triggers, and put findings in `.harness/backlog.md`, not straight into new tasks.
- Weekly limit near (the owner says so, or a limit message appears): finish the current task's close-out, then stop. Do not start a new wave or a new review. Write the State block so the next session can resume. HARNESS.md section 10b describes the 5-hour and weekly freeze; this session only does the close-out part by hand.

## State (2026-11-28, 31st session, replaces all earlier State blocks)
- Owner M1 review of the render (2026-11-28): boxed cards and bar charts rejected, host bounce rejected, transitions not smooth, voice should be a deep male. Owner decision: remove the host entirely; scenes change with the story (AI paintings, Ken Burns, zoom transitions, timer or counter overlay instead of boxes).
- Architect planned Phase 3c, merged as PR #217: 20 tasks in `.harness/tasks/phase3c/`, plan in `.harness/handoffs/p3c-plan.md`. It replaces old waves 10 to 12 (unbuilt phase3 tasks 13 to 17 deleted). Flux client contract and 48 locked tests are on main; render, voice and script contracts come from later test_author tasks.
- Owner gates: G3 done (Cloudflare account, secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` added). G4 decided: option A, paintings made in the weekly scripts PR so the owner reviews every image. G1 (pick the voice by ear from the spike mp3s) and G2 (approve Ken Burns method, fit, zoom, overlay look, style prefix) come later.
- Next: wave 1, p3c-voice-samples and p3c-render-spike (throwaway spike branches; the render spike uses real Flux paintings and records the daily-quota error body). Then wave 2 p3c-flux-client and p3c-contracts-script, and so on per the plan.
- Weekly usage limit nearly used (owner, 2026-11-28): no wave launched. Resume next week.
- By-hand follow-ups: add a security review for `pipeline/visuals/flux_cf.py` (config.yaml globs do not match its path); PLAN.md narrows in sections 3, 6 item 1 and 11. The syllable length check is decided yes (task p3c-syllables).
- Owner steps open: R17, threat model v3.1 sign-off (v4 comes with p3c-cso), re-enable `daily-publish`. `weekly-scripts` active; no real run until M2. Owner may remove `git push` from the global deny list; not done. render.yml takes a script path input (demo-data is `tests/fixtures/scripts/demo-data.json`).
- Process: owner pushes. Owner pushes and merges with one-line `!` commands using absolute `git -C` paths; I open PRs with gh and wait for CI (`wait_ci.sh` takes about 10 min, runs in the background past the 600 s limit). Contracts commit goes to main on `plan/<id>` BEFORE the implementer starts. Locked-test fixes (review finding, broken acceptance via CONTRACT_CHANGE.md) go to the Architect on `plan/<id>-tests`, merged to main first; then I merge main into the task branch locally (never rebase) and the owner pushes; CI scope check fails until the plan branch is on main. Round cap: at 2 blocked rounds the Architect fixes it. `gh workflow run` is denied (give Actions page steps). Agents cannot watch video: visual QA reads frames. A done task needs a workflow.md row and a status.yaml id. Match `^## State \(` by line when scripting edits. Launch: `Agent` with `isolation: worktree`, `run_in_background`; architect for tests, YAMLs and locked files. Local pytest: a stray `tests` package in site-packages shadows the repo's; preload the repo tests dir as `sys.modules['tests']` and set `LOOM_TASK`.
- Non-blocking: ci.yml `check` and `reports` install torch without `--require-hashes`; `error.read()` in gemini.py has no size cap.

## Open items
Owner:
- Push and merge each branch the orchestrator names, including `docs/p3-wave7`. Dispatch `render.yml` for M1 (sample-65s and demo-data) from the Actions page. Then R17 by hand, then re-enable `daily-publish`.
- Sign off threat model v3.1. Approve the Phase 4 audit. Confirm the credit line text ("Narrated with a synthetic voice." after the sources line).
- Create the reusable harness skill: expand `graph-engineering` or make a new one with `skill-creator` in an owner admin window (`~/.claude/skills` is protected). It bakes in: caveman for chat, ponytail for code, model per role, rotation (orchestrator ~50%, tasks 60%), one watcher per task, one review pass chasing only blocking findings, the round cap and the phase-end review policy; contracts-first locked tests, lock hook plus scope check, `LOOM_ADMIN`, read-only reviewers, clean child environments; handoff Docs section, Scribe close-out, docs check; $0 rule, heavy tests in CI only, limit pause and resume, at most 2 parallel sessions.
- Pin `huggingface_hub` in `requirements-heavy.txt` (outside any task's paths).
- Decide on `git push` in the global deny list (see State).
- Uninstall the stray `tests` package in global site-packages (backlog).
- To-do artifact (stale, republish when tasks change): https://claude.ai/artifact/JAc72genBdoDjz2NaWqrpZ.

Orchestrator:
- Architect task owed: `test_captions_exact.py` accepts the frame centre or `CAPTION_POS_Y`; narrow it now that p3-compose is merged.
- lessons.md entries for waves 4 to 7 were not written by the Scribe (its rules forbid it). Write them: p3-charts (plain-string ASS tags), p3-cards (measure real font widths), and the `plan/<id>-tests` branch rule.
- Save the weekly usage-limit message to `.harness/tests/fixtures/limit_messages/` when it happens (only `session_5h-2026-11-15.txt` exists).
- Clean up stale worktrees under `.claude/worktrees/`. `git worktree remove` fails on path length: retry with `\\?\`.
- Doc follow-ups not applied: architecture.md line 54 and HARNESS.md section 11 tree comment for `docs_check.py` (add handoff Docs sections, lessons entries, required headings).
- Known risk: pip-audit ignores two setuptools 81.0.0 advisories and torch PYSEC-2025-194; drop the ignores when torch or torchaudio ships.
- Non-blocking follow-ups live in `.harness/backlog.md` (the owner picks which become tasks).
