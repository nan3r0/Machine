# FFmpeg output fixtures

Canned tool output for the fast tests that fake `subprocess.run` (task p1-qa-tests).

- `loudnorm_pass1.log`: real. The full `compose.log` from render run 43873059742 (the owner-approved 65 s video), copied unchanged. Pass 2 runs at `-loglevel error` and printed nothing, so the file is pass 1 only.
- `silencedetect.log`, `ffprobe_video.json` and `ffprobe_voice.json`: real. Copied unchanged from the `ffmpeg-capture` folder of the `frames` artifact of CI run 43917100099 (written by `tests/render/test_ffmpeg_fixtures.py`).
