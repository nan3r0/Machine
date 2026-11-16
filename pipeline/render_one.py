"""Render one script JSON to final.mp4 (task p1-render-cli).

Usage: python -m pipeline.render_one SCRIPT_JSON OUT_DIR [--cache-dir DIR]

Wiring only. Steps are called through their modules (`kokoro.synthesize`, `align.align_words`,
`captions_ass.build_ass`, `compose.compose`, `qa.run_qa`), never imported by name, so tests can
replace them with fakes. `--cache-dir` (default DEFAULT_CACHE_DIR) holds the model weights for
both voice and alignment; the Actions workflow caches it between runs.
"""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from pipeline.constants import FONTS_DIR
from pipeline.render import captions_ass, compose, qa
from pipeline.render.compose import ComposeError
from pipeline.schema import QAReport, Script
from pipeline.voice import align, kokoro
from pipeline.voice.align import AlignError
from pipeline.voice.kokoro import VoiceError

DEFAULT_CACHE_DIR = Path(".cache/models")


def render(script_path: Path, out_dir: Path, cache_dir: Path) -> QAReport:
    """Validate the script, then voice, align, captions, compose and QA.

    Writes voice.wav, captions.ass, final.mp4 and qa.json to `out_dir` (created if missing), and
    FFmpeg's log to `out_dir/logs/compose.log`. qa.json is written whether QA passes or fails.
    Raises pydantic.ValidationError for an invalid script before any step runs, and lets step
    errors (VoiceError, AlignError, ComposeError) propagate.
    """
    script = Script.model_validate_json(script_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_path = out_dir / "voice.wav"
    captions_path = out_dir / "captions.ass"
    video_path = out_dir / "final.mp4"

    kokoro.synthesize(script.narration_text(), voice_path, cache_dir)
    timings = align.align_words(voice_path, script.narration_text(), cache_dir)
    captions_path.write_text(captions_ass.build_ass(timings), encoding="utf-8")
    compose.compose(voice_path, captions_path, video_path, Path(FONTS_DIR), out_dir / "logs" / "compose.log")
    report = qa.run_qa(video_path, voice_path, timings, script.narration_words())
    (out_dir / "qa.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the exit code: 0 when QA passes, 1 when QA fails (each failed
    check printed), 2 for an invalid script or a failed step (the error printed to stderr).
    Never lets an exception escape."""
    parser = argparse.ArgumentParser(prog="pipeline.render_one")
    parser.add_argument("script", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args(argv)
    try:
        report = render(args.script, args.out_dir, args.cache_dir)
    # Boundary of the CLI: every step wraps its own failures, but a missing file or a bad
    # script is not one of theirs. The message is printed, never dropped.
    except (ValidationError, OSError, VoiceError, AlignError, ComposeError) as err:
        print(f"render failed: {err}", file=sys.stderr)
        return 2
    for failure in report.failures:
        print(f"QA failed: {failure.check}: {failure.reason}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
