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
VOICE_LANG_CODE = "a"  # American English
VOICE_NAME = "af_heart"
VOICE_SPEED = 1.0
# A wav whose peak amplitude (full scale = 1.0) stays below this counts as silent.
VOICE_MIN_PEAK = 0.01

# Speech rate (PLAN.md section 4)
SPEECH_WPM = 160
# Voice duration must lie within this fraction of the word count's expected duration at SPEECH_WPM.
SPEECH_RATE_TOLERANCE = 0.4

# Formats (PLAN.md section 4): (min, max) seconds and words
RETENTION_SECONDS = (25.0, 45.0)
RETENTION_WORDS = (70, 120)
TIKTOK_SECONDS = (62.0, 90.0)  # PLAN.md allows 61 s, but QA requires at least 62 s
TIKTOK_WORDS = (165, 230)

# QA
MAX_SILENCE_S = 1.5
SILENCE_NOISE_DB = -40  # ffmpeg silencedetect noise floor
DURATION_MATCH_TOLERANCE_S = 0.2  # video duration vs voice duration
ALIGNMENT_SLACK_S = 0.05  # word timings may end this far past the voice duration (rounding)
MIN_FILE_BYTES = 100_000  # smaller means an empty or broken render
MAX_FILE_BYTES = 100_000_000  # well under every platform's upload limit

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

# Golden render: frames extracted at these times for the visual-qa reviewer
GOLDEN_FRAME_TIMES_S = (1.0, 10.0, 20.0, 30.0)
