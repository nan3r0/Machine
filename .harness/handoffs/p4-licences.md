# p4-licences handoff

## Goal
Close audit findings A1 (no licence record for the model weights) and A3 (unknown licence of `espeakng-loader` 0.2.4) before the first public publish.

## Status
done

## What changed (and why)
- `assets/LICENSES.md`: new Models table (A1) with Kokoro-82M weights, the `af_heart` voice and whisper `small.en`, each with repo, pinned revision, licence and a link to the evidence at that revision. The intro line now says the file also covers models, so it stays true.
- `spec.md` section 7: one licence-note bullet for `espeakng-loader` 0.2.4 (A3).

## Decisions made
- Kokoro: the repo has no LICENSE file at `f3ff357`, so the evidence is the model card front matter (`license: apache-2.0`). The `af_heart` voice has no voice-specific terms in VOICES.md, so it falls under the repo licence. Its listed hash prefix `0ab5709b` matches `VOICE_FILE_SHA256`.
- whisper: there is no Hugging Face commit, so the pin is the `openai-whisper==20250625` package, tag `v20250625`, and the sha256 in the `small.en` checkpoint URL. The weights licence is cited from the README line saying the code and model weights are MIT, since LICENSE alone reads as covering code.
- espeakng-loader: recorded as "no licence at 0.2.4", not "MIT". The MIT LICENSE was added after that release (2025-11-01) and no later release exists. The wheel bundles libespeak-ng 1.52.0 and espeak-ng-data (GPL-3.0). This is a note, not a blocker: nothing forbids commercial use, and nothing is distributed.

## Tried and abandoned
none

## Known risks
- espeakng-loader 0.2.4 has no licence grant of its own. The author's later MIT licence shows intent, but it does not formally cover 0.2.4. Low risk while the pipeline stays private; re-check if the repo or a built image is ever distributed.
- Kokoro's training data includes some CC BY audio (README). The model is Apache-2.0 and no attribution duty on generated audio is stated, so no action.

## Next step
Owner reads the findings. A1 and A3 can close: no licence forbids commercial use, so neither blocks go-live. A2 (AI disclosure) is a separate task.

## Docs
- `assets/LICENSES.md`: Models table added (done here).
- `spec.md` section 7: espeakng-loader note added (done here).
- `.harness/handoffs/p1-audit.md`: A1 and A3 can be marked closed at close-out (outside paths_allowed).
- The audit's note that spec.md said whisper `base.en` is already fixed: spec.md has no `base.en`.

## Evidence
- Sources read on 2026-11-22: Kokoro README.md and VOICES.md and the file tree at `f3ff3571791e39611d31c381e3a41a3af07b4987`; whisper README.md, LICENSE and `whisper/__init__.py` at tag `v20250625`; PyPI JSON for espeakng-loader 0.2.4 and misaki 0.9.4; GitHub API for espeakng-loader (commit history of LICENSE and pyproject.toml, tree at `146599e`); the 0.2.4 manylinux x86_64 wheel listed with `python -I -m zipfile -l` (372 entries, no licence file, METADATA has no License field).
- `tests/render/test_font.py` acceptance reads LICENSES.md only for the font path and hash, both unchanged.
- `python tests/docs_check.py`: docs check passed (exit 0).
