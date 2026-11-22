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
TIKTOK_SECONDS = (62.0, 90.0)  # PLAN.md section 4: target about 65 s, accepted 62 to 90 s
TIKTOK_WORDS = (149, 216)
TARGET_WORDS = 156  # the 65 s target at SPEECH_WPM: 65 s * 144 / 60 = 156

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

# Scripts (Phase 2). Published-field caps (CSO P1-3, owner decision D6): title is YouTube's limit.
SCRIPTS_PER_BATCH = 7
TITLE_MAX_CHARS = 100
DESCRIPTION_MAX_CHARS = 1000
TAGS_MAX = 10
TAG_MAX_CHARS = 30
TAGS_TOTAL_MAX_CHARS = 500
# Size caps that keep a 7-script PR body under PR_BODY_MAX_CHARS (arithmetic in
# tests/script/test_batch.py). TIKTOK_WORDS[1] words at about 7 characters each fit NARRATION_MAX_CHARS.
SCENES_MAX = 10
NARRATION_MAX_CHARS = 1500  # narration_text(): hook, scenes and loop line
FACTS_PER_SOURCE_MAX = 10
FACT_TEXT_MAX_CHARS = 160
FACT_URL_MAX_CHARS = 100
REASON_MAX_CHARS = 120  # a flag or meaning-check reason, clipped by its producer
PR_BODY_MAX_CHARS = 60_000  # GitHub caps a PR body at 65536

# Gemini (owner decision D5). Interactions API, read 2026-11-16 (PRD.md section 7). Writer and
# checker are different models; never a gemini-2.5-* or preview model. Model ids retire: someone
# checks the Gemini API deprecations page every few months (architecture.md section 7).
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_API_REVISION = "2026-05-20"  # Api-Revision header in the structured-output examples
WRITER_MODEL = "gemini-3.8-flash"
CHECKER_MODEL = "gemini-3.5-flash-lite"
CHECKER_TEMPERATURE = 0.0
# 7 scripts, each one first try plus one retry or line rewrite. Must sit inside the free daily limits.
WRITER_MAX_CALLS_PER_BATCH = 14
CHECKER_MAX_CALLS_PER_BATCH = 14
SCRIPT_ATTEMPTS = 2  # write_script calls the batch makes per script: first try plus one retry
GEMINI_TIMEOUT_S = 120
GEMINI_RETRY_WAIT_S = 10  # wait before the single retry after HTTP 429, a 5xx or a timeout

# YouTube (Phase 4, owner decisions O1 to O3 of 2026-11-21). Data API v3 videos.insert, resumable
# upload, read 2026-11-21 (.harness/handoffs/p4-plan.md). One insert a day; no retry inside a run.
YOUTUBE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/youtube/v3/videos"
# The resumable session URL carries the access token, so it must be https on this host.
YOUTUBE_UPLOAD_HOST = "www.googleapis.com"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"  # the only scope the token may hold
YOUTUBE_CATEGORY_ID = "27"  # Education; the owner may change it
YOUTUBE_PRIVACY = "public"
YOUTUBE_MADE_FOR_KIDS = False
YOUTUBE_SYNTHETIC_MEDIA = True  # O2: a realistic synthetic voice narrates real events
# O3: appended to every description after YOUTUBE_CREDIT_SEPARATOR. Names, not links, so it passes
# the published-field URL rule.
YOUTUBE_CREDIT_LINE = ("Sources: Wikipedia (CC BY-SA 4.0) and public records. "
                       "Narrated with a synthetic voice.")
YOUTUBE_CREDIT_SEPARATOR = "\n\n"
YOUTUBE_DESCRIPTION_MAX_BYTES = 5000  # YouTube's limit, in UTF-8 bytes
YOUTUBE_CONNECT_TIMEOUT_S = 60  # token refresh and the upload init request
YOUTUBE_UPLOAD_TIMEOUT_S = 900  # the PUT of up to MAX_FILE_BYTES on a runner
