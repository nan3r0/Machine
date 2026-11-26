# Asset licences

Every font, art, music and SFX file under `assets/` has an entry here. The models the pipeline downloads at run time are listed under Models.

| File | Source | Licence | sha256 | Used for |
|---|---|---|---|---|
| `fonts/Montserrat-Bold.ttf` (static Bold) | https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf | SIL Open Font License 1.1, full text in `fonts/OFL.txt` | `bc6e854971cea46b463be6f9eef4d9cd52f51cfc1fc0dd90c9d3e6483dc0ec61` | Burned-in captions |
| `character/host.yaml` | Original work made for this project (ASS vector paths drawn by the project's agents; no third-party image, character or template used) | Project's own work, no third-party licence | `412b8ad8dd02628b183f50a9d338eafe134797b243200980aae738a61a2d5b33` (LF line endings, as committed) | On-screen host character |

## Models

Checked on 2026-11-22 against the upstream pages at the pinned revision. Both licences allow commercial use.

| Model | Repo | Pinned revision | Licence | Evidence | Used for |
|---|---|---|---|---|---|
| Kokoro-82M weights (`config.json`, `kokoro-v1_0.pth`) | `hexgrad/Kokoro-82M` on Hugging Face | `f3ff3571791e39611d31c381e3a41a3af07b4987` (`VOICE_REPO_REVISION`) | Apache-2.0 | Model card front matter `license: apache-2.0` and "This is an Apache-licensed model": https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff3571791e39611d31c381e3a41a3af07b4987/README.md. The repo has no separate LICENSE file at this revision. | Narration voice |
| Kokoro voice `voices/af_heart.pt` | `hexgrad/Kokoro-82M` on Hugging Face | same as above | Apache-2.0 (the repo licence; no voice-specific terms) | https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff3571791e39611d31c381e3a41a3af07b4987/VOICES.md lists `af_heart` with hash prefix `0ab5709b`, matching `VOICE_FILE_SHA256`, and gives it no CC BY entry (only some Japanese and French voices have one) | Narration voice |
| whisper `small.en` | `openai/whisper` (package `openai-whisper==20250625`) | Tag `v20250625`; checkpoint URL `.../models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt` from `whisper/__init__.py`, sha256 checked by openai-whisper | MIT | README at the tag: "Whisper's code and model weights are released under the MIT License": https://github.com/openai/whisper/blob/v20250625/README.md, licence text https://github.com/openai/whisper/blob/v20250625/LICENSE | Caption alignment (`ALIGN_MODEL_NAME`) |
