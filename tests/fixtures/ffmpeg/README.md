# FFmpeg output fixtures

Canned tool output for the fast tests that fake `subprocess.run` (task p1-qa-tests).

- `loudnorm_pass1.log`: real. The full `compose.log` from render run 43873059742 (the owner-approved 65 s video), copied unchanged. Pass 2 runs at `-loglevel error` and printed nothing, so the file is pass 1 only.
- `silencedetect.log`, `ffprobe_video.json` and `ffprobe_voice.json`: no real capture existed in any CI log or artifact when the task was written (QA never logs this output). They follow FFmpeg's print format, with numbers from the same run's `qa.json`. `tests/render/test_ffmpeg_fixtures.py` (heavy, CI only) runs the real tools and fails, printing the real output, if their shape differs. Replace them with that real output when it does.
