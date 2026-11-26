# Asset licences

Every font, art, music and SFX file under `assets/` has an entry here. The models the pipeline downloads at run time are listed under Models.

| File | Source | Licence | sha256 | Used for |
|---|---|---|---|---|
| `fonts/Montserrat-Bold.ttf` (static Bold) | https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf | SIL Open Font License 1.1, full text in `fonts/OFL.txt` | `bc6e854971cea46b463be6f9eef4d9cd52f51cfc1fc0dd90c9d3e6483dc0ec61` | Burned-in captions |
| `character/host.yaml` | Original work made for this project (ASS vector paths drawn by the project's agents; no third-party image, character or template used) | Project's own work, no third-party licence | `412b8ad8dd02628b183f50a9d338eafe134797b243200980aae738a61a2d5b33` (LF line endings, as committed) | On-screen host character |
| `sets/night_street.yaml` | Original work made for this project (ASS vector paths drawn by the project's agents; no third-party image or template used) | Project's own work, no third-party licence | `f3464fca86480dd353aab0abfd6ca46b5d553f16db193cabfbdfe330b5115360` (LF line endings, as committed) | Scene set |
| `sets/desert_rail.yaml` | Original work, as above | Project's own work, no third-party licence | `f7f8c18354858cc84701abf638434b5acc19cd0b58ee3ffe58b53a0e8dc5b424` (LF) | Scene set |
| `sets/lamp_room.yaml` | Original work, as above | Project's own work, no third-party licence | `5c9f4acf24496fba9510459eed7130277e15fffc727891b1a04f12d8ee7fd969` (LF) | Scene set |
| `sets/shore_night.yaml` | Original work, as above | Project's own work, no third-party licence | `65315feddbd9059619149080fc96d9f998a5d7f556dd864cf36f0c18455cbac1` (LF) | Scene set |
| `sets/forest.yaml` | Original work, as above | Project's own work, no third-party licence | `37de8a01679bcf1566b582881c43ec0a32baf2e45cabf71556dea1a58b3238b7` (LF) | Scene set |
| `sets/archive.yaml` | Original work, as above | Project's own work, no third-party licence | `9315a628c2858ea84998cf06b717eb8db945b4d5cd4e0f662d372fefe668a53c` (LF) | Scene set |
| `sets/host_backdrop.yaml` | Original work, as above | Project's own work, no third-party licence | `e73863763d281f7b240781f50d4356f40ac899899d10adfd5a25e86c14e08160` (LF) | Host intro and outro backdrop |

## Models

Checked on 2026-11-22 against the upstream pages at the pinned revision. Both licences allow commercial use.

| Model | Repo | Pinned revision | Licence | Evidence | Used for |
|---|---|---|---|---|---|
| Kokoro-82M weights (`config.json`, `kokoro-v1_0.pth`) | `hexgrad/Kokoro-82M` on Hugging Face | `f3ff3571791e39611d31c381e3a41a3af07b4987` (`VOICE_REPO_REVISION`) | Apache-2.0 | Model card front matter `license: apache-2.0` and "This is an Apache-licensed model": https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff3571791e39611d31c381e3a41a3af07b4987/README.md. The repo has no separate LICENSE file at this revision. | Narration voice |
| Kokoro voice `voices/af_heart.pt` | `hexgrad/Kokoro-82M` on Hugging Face | same as above | Apache-2.0 (the repo licence; no voice-specific terms) | https://huggingface.co/hexgrad/Kokoro-82M/blob/f3ff3571791e39611d31c381e3a41a3af07b4987/VOICES.md lists `af_heart` with hash prefix `0ab5709b`, matching `VOICE_FILE_SHA256`, and gives it no CC BY entry (only some Japanese and French voices have one) | Narration voice |
| whisper `small.en` | `openai/whisper` (package `openai-whisper==20250625`) | Tag `v20250625`; checkpoint URL `.../models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt` from `whisper/__init__.py`, sha256 checked by openai-whisper | MIT | README at the tag: "Whisper's code and model weights are released under the MIT License": https://github.com/openai/whisper/blob/v20250625/README.md, licence text https://github.com/openai/whisper/blob/v20250625/LICENSE | Caption alignment (`ALIGN_MODEL_NAME`) |
