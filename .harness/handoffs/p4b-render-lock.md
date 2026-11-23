# p4b-render-lock handoff

## Goal
Hash-checked installs for the render job of `daily_publish.yml` and for `render.yml` (CSO P1-4 heavy half).

## Status
`partial`, awaiting install proof. Gate 1 cannot run the Linux install. The owner runs `gh workflow run render.yml --ref task/p4b-render-lock` once the branch is pushed; a green run with QA passed is the proof. The branch is committed, not pushed.

## What changed (and why)
- `requirements-render-torch.txt` (new): `torch==2.11.0+cpu` and `torchaudio==2.11.1`, one wheel hash each, from `pip download` on the PyTorch CPU index and `pip hash`. Regenerate commands are in the header.
- `requirements-render.txt` (new): the full set `requirements.txt` plus `requirements-heavy.txt` resolve to on Linux x86_64 and CPython 3.12 (about 100 pins, one hash each), without torch and torchaudio. Regenerate commands in the header.
- `daily_publish.yml` render job and `render.yml`: the three install lines became two, `pip install -q --no-deps --require-hashes --index-url <CPU index> -r requirements-render-torch.txt` then `pip install -q --require-hashes -r requirements-render.txt`. Nothing else changed.
- `pyproject.toml`: both files added to mutmut `also_copy`.

## Decisions made
- **stable-ts is sdist-only too**, not just openai-whisper. `pip download` with `--platform` refuses `--no-binary`, and a resolve with `--only-binary` finds no stable-ts. So the wheels were resolved without the two sdists, with their dependencies added by hand, and the two sdists were fetched separately (`--no-deps --no-binary=:all:`) and hashed.
- Their dependencies came from a host (Windows, CPython 3.11) `pip download` of the two sdists, which lists names only. Added to the wheel resolve: numba (llvmlite), tqdm, more-itertools, tiktoken (regex, requests and its deps), `triton>=2` (whisper needs it on Linux x86_64). stable-ts adds only numpy, torch, torchaudio, tqdm.
- `pip download --platform` does not change environment markers. Windows-only extras that came along (colorama, win32-setctime) were left out. Linux-only dependencies that markers hid on the host could be missing; triton was the one I knew of. The Linux run will show any other.
- Version pins from `requirements-heavy.txt` were passed to the resolve, so the lock holds the same versions the test demands (filelock 4.2.10, setuptools 81.0.0, networkx 3.7 and so on).
- `en_core_web_sm` stays a direct URL, with the same sha256 as both the URL fragment and a `--hash`, because the test wants a hash on every line.
- Torch deps (the CPU wheel's own dependencies) are in the render lock, since the torch step is `--no-deps`.

## Tried and abandoned
- Tag `manylinux_2_39_x86_64` alone to match the runner's glibc: pip 22.3.1 did not expand it to the lower tags and found no torch wheel. Used the method's three tags.
- `pip install --dry-run --report` and reading the sdists with tar or curl to get their declared dependencies: not allowed in this session. Used the host `pip download` instead.
- A `requirements` input file under `out/`: blocked by the lock hook. Passed requirements on the command line.

## Known risks
- **Build isolation under hash mode is untested.** pip builds the two sdists in an isolated env; build requirements are not hash-checked (pip does not apply `--require-hashes` to them). If the Linux run fails there, the fallback in the task is: pin and hash `setuptools` (already in the lock at 81.0.0) and `wheel`, and add `--no-build-isolation` to the second install. `wheel` is not in the lock now.
- One hash per package, the wheel pip picks for manylinux 2_28 or lower. If the runner (glibc 2.39) prefers a newer manylinux wheel for some package, the hash fails and that package needs the extra hash. Same limit as `requirements-generate.txt`.
- `pydantic-core` resolves to 2.50.4 here, while `requirements-generate.txt` has 2.50.5. Both came from pip's resolution; worth a look if the two locks should agree.
- Host-marker gaps (see Decisions). The first run may name a missing dependency.
- Lock versions of unpinned transitive packages are today's; they only change when someone regenerates.
- The runner's pip cache key still reads `requirements*.txt`, so the new files are covered.

## Next step
1. Orchestrator: push the branch and ask the owner to run `gh workflow run render.yml --ref task/p4b-render-lock`.
2. Green and QA passed: mark done, then the security review.
3. Red: read the pip error, fix the lock (missing dependency, extra hash, or the `--no-build-isolation` fallback), and retry. After two failed tries write `ENV_ISSUE.md`.

## Docs
- `spec.md` section 7 and `architecture.md`: mention that the render jobs install from `requirements-render-torch.txt` and `requirements-render.txt`, and that a bump of `requirements.txt` or `requirements-heavy.txt` needs both regenerated (the test fails until then).
- `CLAUDE.md`: no change.
- `docs/threat-model.md` (p4b-cso): P1-4 heavy half closed once the Linux proof is green.
- `docs/runbook.md` (p4b-runbook): add the regenerate steps from the file headers.
- Deletions needed: none. Wheels sit in `out/wheels` (not committed).

## Evidence
- `pytest -q tests/test_render_lock.py tests/test_daily_publish_workflow.py tests/test_workflows.py`: 22 passed.
- `pytest -q tests -m "not heavy" -k "workflow or ci or lock or docs"`: 225 passed, 2 skipped.
- `ruff check .`: clean. `mypy --strict pipeline/`: clean.
- The Linux install itself: not run (awaiting `render.yml` dispatch).
