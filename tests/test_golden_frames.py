"""The render workflow extracts the same golden frames as the heavy test (task p1-golden-65s)."""

from tests import workflow_rules as rules


def test_acceptance() -> None:
    """One helper picks the frames, so the render artifact also shows the end of the video."""
    text = rules.run_text(rules.load("render.yml"))
    assert "media.extract_golden_frames(" in text
    assert "GOLDEN_FRAME_TIMES_S" not in text, "times come from the helper, not a second copy"
