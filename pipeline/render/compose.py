"""FFmpeg render of background, voice and captions to final.mp4 (task p1-compose).

FFmpeg always gets an argument list through subprocess, never a shell string.
"""

import subprocess
from pathlib import Path, PurePath

from pipeline import constants

# loudnorm resamples to 192 kHz, which most players reject.
_AUDIO_RATE_HZ = "48000"
_STDERR_TAIL_LINES = 20


class ComposeError(RuntimeError):
    """FFmpeg failed. The message ends with the tail of FFmpeg's stderr."""


def subtitles_filter_value(path: PurePath) -> str:
    """Escape `path` for use as `subtitles=<value>` inside an FFmpeg filtergraph.

    Works for Windows paths (backslashes become `/`, the drive colon becomes `\\:`, so
    `C:\\work\\captions.ass` contains `C\\:/work/captions.ass`) and for Linux paths containing
    spaces, `'`, `,`, `[`, `]` or `;`.
    """
    return _quote_filter_arg(path)


def _quote_filter_arg(path: PurePath) -> str:
    """Escape for the option parser (backslash, colon, quote), then single-quote for the filtergraph."""
    option = path.as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return "'" + option.replace("'", "'\\''") + "'"


def build_ffmpeg_args(voice: Path, captions: Path, out: Path, fonts_dir: Path) -> list[str]:
    """Return the FFmpeg argument list for the main render, starting with "ffmpeg".

    Solid BACKGROUND_COLOR at WIDTH x HEIGHT and FPS, captions burned in with the subtitles
    filter (fonts from `fonts_dir`), libx264 with yuv420p, AAC audio normalised with loudnorm to
    LOUDNESS_LUFS, `-hide_banner -loglevel error`, and `out` as the last argument. The video ends
    with the voice.
    """
    subtitles = (f"subtitles=filename={subtitles_filter_value(captions)}"
                 f":fontsdir={_quote_filter_arg(fonts_dir)}")
    size = f"{constants.WIDTH}x{constants.HEIGHT}"
    background = f"color=c={constants.BACKGROUND_COLOR}:s={size}:r={constants.FPS}"
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", background,
        "-i", str(voice),
        "-vf", subtitles,
        "-af", f"loudnorm=I={constants.LOUDNESS_LUFS:g}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(constants.FPS),
        "-c:a", "aac", "-b:a", constants.AUDIO_BITRATE, "-ar", _AUDIO_RATE_HZ,
        "-shortest",
        str(out),
    ]


def compose(voice: Path, captions: Path, out: Path, fonts_dir: Path, log_path: Path) -> Path:
    """Render `out` from `voice` and `captions` and return `out`.

    FFmpeg's full stderr goes to `log_path` (parent folders created). Raises ComposeError, with
    the stderr tail in the message, if an input is missing, FFmpeg exits non-zero or `out` is
    missing or empty afterwards.
    """
    for name in (voice, captions):
        if not name.is_file():
            raise ComposeError(f"input missing: {name}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(build_ffmpeg_args(voice, captions, out, fonts_dir),
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ComposeError(f"could not run ffmpeg: {exc}") from exc
    log_path.write_text(result.stderr, encoding="utf-8")
    tail = "\n".join(result.stderr.splitlines()[-_STDERR_TAIL_LINES:])
    if result.returncode != 0:
        raise ComposeError(f"ffmpeg exited {result.returncode}:\n{tail}")
    if not out.is_file() or out.stat().st_size == 0:
        raise ComposeError(f"ffmpeg wrote no output at {out}:\n{tail}")
    return out
