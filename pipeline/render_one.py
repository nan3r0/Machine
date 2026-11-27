"""Render one script JSON to final.mp4 (task p1-render-cli).

Usage: python -m pipeline.render_one SCRIPT_JSON OUT_DIR [--cache-dir DIR]

Wiring only. Steps are called through their modules (`kokoro.synthesize`, `align.align_words`,
`captions_ass.build_ass`, `router.build_scenes_ass`, `compose.compose`,
`qa.run_qa`), never imported by name, so tests can replace them with fakes. `--cache-dir`
(default DEFAULT_CACHE_DIR) holds the model weights for both voice and alignment; the Actions
workflow caches it between runs.
"""

import argparse
import sys
import traceback
from pathlib import Path

from pipeline.constants import FONTS_DIR
from pipeline.render import captions_ass, compose, qa
from pipeline.schema import QAReport, Script
from pipeline.script import validate
from pipeline.visuals import router
from pipeline.voice import align, kokoro, levels

DEFAULT_CACHE_DIR = Path(".cache/models")


class ScriptRejected(Exception):
    """The script parses but may not be voiced or published; carries one message per problem."""


def render(script_path: Path, out_dir: Path, cache_dir: Path) -> QAReport:
    """Validate the script, then voice, align, captions, compose and QA.

    Writes voice.wav, captions.ass, scenes.ass, final.mp4 and qa.json to `out_dir` (created if missing), and
    FFmpeg's log to `out_dir/logs/compose.log`. qa.json is written whether QA passes or fails.
    Raises pydantic.ValidationError for an invalid script before any step runs, and lets step
    errors (VoiceError, AlignError, ComposeError) propagate.
    """
    script = Script.model_validate_json(script_path.read_text(encoding="utf-8"))
    found = validate.problems(script)
    if found:
        raise ScriptRejected(found)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_path = out_dir / "voice.wav"
    captions_path = out_dir / "captions.ass"
    scenes_path = out_dir / "scenes.ass"
    video_path = out_dir / "final.mp4"

    kokoro.synthesize(script.narration_text(), voice_path, cache_dir)
    timings = align.align_words(voice_path, script.narration_text(), cache_dir)
    captions_path.write_text(captions_ass.build_ass(timings), encoding="utf-8")
    voice_levels = levels.voice_levels(voice_path)
    scenes_path.write_text(router.build_scenes_ass(script, timings, levels=voice_levels), encoding="utf-8")
    compose.compose(
        voice_path,
        captions_path,
        video_path,
        Path(FONTS_DIR),
        out_dir / "logs" / "compose.log",
        scenes=scenes_path,
    )
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
    except ScriptRejected as rejected:
        print("script rejected:", *rejected.args[0], sep="\n", file=sys.stderr)
        return 2
    # The only real boundary of the CLI. Exit 1 must mean a real QA failure, so any other
    # exception (bad script encoding, a step bug) exits 2 with the full traceback printed.
    except Exception:
        print(f"render failed:\n{traceback.format_exc()}", file=sys.stderr)
        return 2
    for failure in report.failures:
        print(f"QA failed: {failure.check}: {failure.reason}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
