"""The render workflow defaults to the 65 s sample (task p1-sample-65s, owner decision 2026-11-16)."""

from tests import workflow_rules as rules


def test_acceptance() -> None:
    script_input = rules.load("render.yml")["on"]["workflow_dispatch"]["inputs"]["script"]
    assert script_input["default"] == "queue/approved/sample-65s.json"
