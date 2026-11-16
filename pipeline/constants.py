"""Every number the pipeline uses (spec.md section 4). Locked contract: change only through the Architect.

Imports nothing from `pipeline` and does no IO.
"""

# Frame
WIDTH = 1080
HEIGHT = 1920
FPS = 30
BACKGROUND_COLOR = "0x101820"  # Phase 1 solid background, FFmpeg colour syntax

# Audio and loudness
LOUDNESS_LUFS = -14.0
LOUDNESS_TOLERANCE_LU = 1.0
AUDIO_BITRATE = "192k"

# Voice (Kokoro, hexgrad/Kokoro-82M through the `kokoro` package)
VOICE_SAMPLE_RATE = 24_000  # Kokoro's native output rate
VOICE_REPO_ID = "hexgrad/Kokoro-82M"
# Commit of VOICE_REPO_ID the weights are downloaded from, so an upstream push cannot change the voice.
VOICE_REPO_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
# sha256 of every repo file the pipeline loads, by repo path. A voice without an entry is not allowed.
VOICE_FILE_SHA256 = {
    "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
    "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    "voices/af_heart.pt": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
}
VOICE_LANG_CODE = "a"  # American English
VOICE_NAME = "af_heart"
VOICE_SPEED = 0.9  # slower, darker delivery for suspense (owner decision 2026-11-16)
# A wav whose peak amplitude (full scale = 1.0) stays below this counts as silent.
VOICE_MIN_PEAK = 0.01

# Alignment (stable-ts). openai-whisper verifies the checksum of its own model downloads.
ALIGN_MODEL_NAME = "small.en"

# Speech rate (PLAN.md section 4)
# Measured at VOICE_SPEED 0.9: sample-65s (167 words) spoke in 69.5 s in render run 43873059742,
# about 144 wpm. Re-measure from a real render if VOICE_SPEED or VOICE_NAME changes.
SPEECH_WPM = 144
# Voice duration must lie within this fraction of the word count's expected duration at SPEECH_WPM.
SPEECH_RATE_TOLERANCE = 0.4

# Format (PLAN.md section 4): every video is over a minute. (min, max) seconds and words.
# TIKTOK_WORDS is TIKTOK_SECONDS at SPEECH_WPM, rounded inwards: 62 s * 144 / 60 = 148.8 -> 149,
# 90 s * 144 / 60 = 216.0 -> 216.
TIKTOK_SECONDS = (62.0, 90.0)  # PLAN.md allows 61 s, but QA requires at least 62 s
TIKTOK_WORDS = (149, 216)

# QA
MAX_SILENCE_S = 1.5
SILENCE_NOISE_DB = -40  # ffmpeg silencedetect noise floor
DURATION_MATCH_TOLERANCE_S = 0.2  # video duration vs voice duration
ALIGNMENT_SLACK_S = 0.05  # word timings may end this far past the voice duration (rounding)
MIN_FILE_BYTES = 100_000  # smaller means an empty or broken render
MAX_FILE_BYTES = 100_000_000  # well under every platform's upload limit
QA_FPS_TOLERANCE = 0.01  # measured fps may differ from FPS by this much (30000/1001 does not pass)
QA_TOOL_TIMEOUT_S = 300  # per ffprobe or silencedetect call
QA_STDERR_TAIL_LINES = 5  # stderr lines kept in a QA tool error

# Render (FFmpeg)
AUDIO_SAMPLE_RATE_HZ = 48_000  # loudnorm resamples to 192 kHz, which most players reject
TRUE_PEAK_DBTP = -1.0  # loudnorm true-peak ceiling; leaves linear mode room to reach LOUDNESS_LUFS
COMPOSE_STDERR_TAIL_LINES = 20  # FFmpeg stderr lines kept in a ComposeError
# Per FFmpeg call (loudnorm measure, then render). The whole render step (voice, alignment, compose,
# QA) of the 69.6 s video took 125 s in run 43873059742, so 600 s leaves headroom for a 90 s video
# well inside render.yml's 45 minute job limit.
COMPOSE_TIMEOUT_S = 600

# Captions. The safe zone keeps text clear of platform UI: nothing in the top 15%, bottom 25%
# or right 15% of the frame, plus a 5% left margin. Values are pixel bounds of the frame.
SAFE_LEFT_PX = 54
SAFE_RIGHT_PX = 918
SAFE_TOP_PX = 288
SAFE_BOTTOM_PX = 1440
CAPTION_FONT_NAME = "Montserrat"  # open-licence font committed under FONTS_DIR
CAPTION_FONT_SIZE = 96
CAPTION_MAX_WORDS_PER_LINE = 3
FONTS_DIR = "assets/fonts"

# Golden render: frames extracted at these times for the visual-qa reviewer, plus one frame
# GOLDEN_END_OFFSET_S before the video ends. Fixed times stay below TIKTOK_SECONDS[0], so they fit
# every video that passes QA; the end frame covers the rest of a longer video.
GOLDEN_FRAME_TIMES_S = (1.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0)
GOLDEN_END_OFFSET_S = 0.5
