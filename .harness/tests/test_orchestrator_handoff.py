from pathlib import Path

HANDOFF = Path(__file__).resolve().parents[1] / "handoffs" / "orchestrator.md"
MAX_BYTES = 12 * 1024  # read at the start of every orchestrator session, so it must stay small


def test_one_state_block() -> None:
    lines = HANDOFF.read_text(encoding="utf-8").splitlines()
    headings = [line for line in lines if line.startswith("## State")]
    assert len(headings) == 1, "State is replaced each session; move old state to orchestrator-history.md"


def test_stays_small() -> None:
    size = len(HANDOFF.read_bytes())
    assert size <= MAX_BYTES, f"orchestrator.md is {size} bytes (limit {MAX_BYTES}); prune it"
