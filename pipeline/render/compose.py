"""FFmpeg render of background, voice and captions to final.mp4 (task p1-compose).

FFmpeg always gets an argument list through subprocess, never a shell string.
"""

import json
import subprocess
from pathlib import Path, PurePath

from pipeline import constants

# loudnorm option name -> field in its pass 1 JSON.
_MEASURED_FIELDS = {"measured_I": "input_i", "measured_TP": "input_tp",
                    "measured_LRA": "input_lra", "measured_thresh": "input_thresh",
                    "offset": "target_offset"}


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


def _loudnorm_target() -> str:
    return f"loudnorm=I={constants.LOUDNESS_LUFS:g}:TP={constants.TRUE_PEAK_DBTP:g}"


def build_measure_args(voice: Path) -> list[str]:
    """Return the FFmpeg argument list for loudnorm pass 1: measure `voice`, write nothing."""
    return ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "info", "-i", str(voice),
            "-af", f"{_loudnorm_target()}:print_format=json", "-f", "null", "-"]


def parse_loudnorm_json(stderr: str) -> dict[str, str]:
    """Return the measured_* values loudnorm printed as a JSON block at the end of `stderr`."""
    start, end = stderr.rfind("{"), stderr.rfind("}")
    try:
        data = json.loads(stderr[start:end + 1])
        return {option: str(data[field]) for option, field in _MEASURED_FIELDS.items()}
    except (ValueError, KeyError) as exc:
        raise ComposeError("loudnorm pass 1 printed no measurement") from exc


def build_ffmpeg_args(voice: Path, captions: Path, out: Path, fonts_dir: Path,
                      measured: dict[str, str] | None = None, *,
                      scenes: Path | None = None) -> list[str]:
    """Return the FFmpeg argument list for the main render, starting with "ffmpeg".

    Solid BACKGROUND_COLOR at WIDTH x HEIGHT and FPS, captions burned in with the subtitles
    filter (fonts from `fonts_dir`), libx264 with yuv420p, AAC audio normalised with loudnorm to
    LOUDNESS_LUFS, `-hide_banner -loglevel error`, and `out` as the last argument. The video ends
    with the voice. With `measured` (from `parse_loudnorm_json`) loudnorm runs as pass 2 in linear
    mode, which lands on the target; without it, single pass. With `scenes` (an .ass file), it is
    burned in first, so the captions sit on top of it.
    """
    loudnorm = _loudnorm_target()
    if measured:
        loudnorm += "".join(f":{option}={value}" for option, value in measured.items())
        loudnorm += ":linear=true"
    fontsdir = f":fontsdir={_quote_filter_arg(fonts_dir)}"
    layers = ([scenes] if scenes else []) + [captions]
    subtitles = ",".join(f"subtitles=filename={subtitles_filter_value(layer)}{fontsdir}" for layer in layers)
    size = f"{constants.WIDTH}x{constants.HEIGHT}"
    background = f"color=c={constants.BACKGROUND_COLOR}:s={size}:r={constants.FPS}"
    return [
        "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", background,
        "-i", str(voice),
        "-vf", subtitles,
        "-af", loudnorm,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(constants.FPS),
        "-c:a", "aac", "-b:a", constants.AUDIO_BITRATE, "-ar", str(constants.AUDIO_SAMPLE_RATE_HZ),
        "-shortest",
        str(out),
    ]


def compose(voice: Path, captions: Path, out: Path, fonts_dir: Path, log_path: Path, *,
            scenes: Path | None = None) -> Path:
    """Render `out` from `voice`, `captions` and the optional `scenes` .ass, and return `out`.

    FFmpeg's full stderr goes to `log_path` (parent folders created). Raises ComposeError, with
    the stderr tail in the message, if an input is missing, FFmpeg exits non-zero or `out` is
    missing or empty afterwards.
    """
    for name in (voice, captions, *([scenes] if scenes else [])):
        if not name.is_file():
            raise ComposeError(f"input missing: {name}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    measured = parse_loudnorm_json(_run_ffmpeg(build_measure_args(voice), log_path))
    render_log = _run_ffmpeg(build_ffmpeg_args(voice, captions, out, fonts_dir, measured, scenes=scenes),
                              log_path)
    if not out.is_file() or out.stat().st_size == 0:
        raise ComposeError(f"ffmpeg wrote no output at {out}:\n{_tail(render_log)}")
    return out


def _tail(stderr: str) -> str:
    return "\n".join(stderr.splitlines()[-constants.COMPOSE_STDERR_TAIL_LINES:])


def _log_partial(log_path: Path, partial: str | bytes | None) -> None:
    """Append what FFmpeg printed before a timeout; TimeoutExpired may hold bytes or None."""
    if isinstance(partial, bytes):
        partial = partial.decode("utf-8", errors="replace")
    if partial:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(partial)


def _run_ffmpeg(args: list[str], log_path: Path) -> str:
    """Run FFmpeg, append its stderr to `log_path` and return it. Raises ComposeError on failure."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=constants.COMPOSE_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        _log_partial(log_path, exc.stderr)
        raise ComposeError(f"ffmpeg timed out after {constants.COMPOSE_TIMEOUT_S} s") from exc
    except OSError as exc:
        raise ComposeError(f"could not run ffmpeg: {exc}") from exc
    with log_path.open("a", encoding="utf-8") as log:
        log.write(result.stderr)
    if result.returncode != 0:
        raise ComposeError(f"ffmpeg exited {result.returncode}:\n{_tail(result.stderr)}")
    return result.stderr
