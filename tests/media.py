"""ffprobe and ffmpeg helpers for heavy tests. Argument lists only, never a shell."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FRAMES_DIR = ROOT / "out" / "frames"

CAPTIONS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, \
Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, \
MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,{\\pos(486,1100)}In 1938, a
Dialogue: 0,0:00:03.00,0:00:06.00,Default,,0,0,0,,{\\pos(486,1100)}ballpoint pen
Dialogue: 0,0:00:06.00,0:00:09.50,Default,,0,0,0,,{\\pos(486,1100)}cost $10
"""


def write_captions(path: Path) -> Path:
    """A hand-written caption file, so render tests do not depend on the captions task."""
    path.write_text(CAPTIONS, encoding="utf-8")
    return path


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    data: dict[str, Any] = json.loads(result.stdout)
    return data


def stream(info: dict[str, Any], kind: str) -> dict[str, Any]:
    streams: list[dict[str, Any]] = [s for s in info["streams"] if s["codec_type"] == kind]
    assert len(streams) == 1, f"expected one {kind} stream"
    return streams[0]


def duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def integrated_loudness(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    values = re.findall(r"I:\s+(-?[\d.]+) LUFS", result.stderr)
    assert values, "ebur128 printed no integrated loudness"
    return float(values[-1])


def extract_frames(video: Path, prefix: str, times: tuple[float, ...]) -> list[Path]:
    """PNG frames for the visual-qa reviewer, written to out/frames/<prefix>-<time>s.png."""
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for t in times:
        frame = FRAMES_DIR / f"{prefix}-{t:05.1f}s.png"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(video),
                        "-frames:v", "1", str(frame)], check=True)
        frames.append(frame)
    return frames
