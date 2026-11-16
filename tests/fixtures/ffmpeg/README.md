# FFmpeg output fixtures

Canned tool output for the fast tests that fake `subprocess.run` (task p1-qa-tests).

- `loudnorm_pass1.log`: real. The full `compose.log` from render run 43873059742 (the owner-approved 65 s video), copied unchanged. Pass 2 runs at `-loglevel error` and printed nothing, so the file is pass 1 only.
- `silencedetect.log`, `ffprobe_video.json` and `ffprobe_voice.json`: stand-ins in FFmpeg's print format, because no real capture existed in any CI log or artifact (QA never logs this output). They must be replaced before p1-qa-tests is done. `tests/render/test_ffmpeg_fixtures.py` (heavy, CI only) writes the real output of the commands qa runs to `out/frames/ffmpeg-capture/` on every run (the `frames` artifact). Copy those three files here unchanged.
