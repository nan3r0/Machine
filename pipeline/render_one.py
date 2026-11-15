"""Render one script JSON to final.mp4 (task p1-render-cli).

Usage: python -m pipeline.render_one SCRIPT_JSON OUT_DIR [--cache-dir DIR]

Wiring only. Steps are called through their modules (`kokoro.synthesize`, `align.align_words`,
`captions_ass.build_ass`, `compose.compose`, `qa.run_qa`), never imported by name, so tests can
replace them with fakes. `--cache-dir` (default DEFAULT_CACHE_DIR) holds the model weights; the
Actions workflow caches it between runs.
"""

from pathlib import Path

from pipeline.schema import QAReport

DEFAULT_CACHE_DIR = Path(".cache/models")


def render(script_path: Path, out_dir: Path, cache_dir: Path) -> QAReport:
    """Validate the script, then voice, align, captions, compose and QA.

    Writes voice.wav, captions.ass, final.mp4 and qa.json to `out_dir` (created if missing), and
    FFmpeg's log to `out_dir/logs/compose.log`. qa.json is written whether QA passes or fails.
    Raises pydantic.ValidationError for an invalid script before any step runs, and lets step
    errors (VoiceError, AlignError, ComposeError) propagate.
    """
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the exit code: 0 when QA passes, 1 when QA fails (each failed
    check printed), 2 for an invalid script or a failed step (the error printed to stderr).
    Never lets an exception escape."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
