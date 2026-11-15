"""FFmpeg render of background, voice and captions to final.mp4 (task p1-compose).

FFmpeg always gets an argument list through subprocess, never a shell string.
"""

from pathlib import Path


class ComposeError(RuntimeError):
    """FFmpeg failed. The message ends with the tail of FFmpeg's stderr."""


def subtitles_filter_value(path: Path) -> str:
    """Escape `path` for use as `subtitles=<value>` inside an FFmpeg filtergraph.

    Works for Windows paths (backslashes become `/`, the drive colon becomes `\\:`, so
    `C:\\work\\captions.ass` contains `C\\:/work/captions.ass`) and for Linux paths containing
    spaces, `'`, `,`, `[`, `]` or `;`.
    """
    raise NotImplementedError


def build_ffmpeg_args(voice: Path, captions: Path, out: Path, fonts_dir: Path) -> list[str]:
    """Return the FFmpeg argument list for the main render, starting with "ffmpeg".

    Solid BACKGROUND_COLOR at WIDTH x HEIGHT and FPS, captions burned in with the subtitles
    filter (fonts from `fonts_dir`), libx264 with yuv420p, AAC audio normalised with loudnorm to
    LOUDNESS_LUFS, `-hide_banner -loglevel error`, and `out` as the last argument. The video ends
    with the voice.
    """
    raise NotImplementedError


def compose(voice: Path, captions: Path, out: Path, fonts_dir: Path, log_path: Path) -> Path:
    """Render `out` from `voice` and `captions` and return `out`.

    FFmpeg's full stderr goes to `log_path` (parent folders created). Raises ComposeError, with
    the stderr tail in the message, if an input is missing, FFmpeg exits non-zero or `out` is
    missing or empty afterwards.
    """
    raise NotImplementedError
