"""A left-out script's reason must reach the run log (task p4c-batch-log-reason).

When every script fails, `run` writes no PR body, so the warning log is the only place the reason
can show. Weekly-scripts run 45278431238 wrote 0 of 7 scripts and left no reason anywhere.
"""

import logging
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.script.gemini import GeminiError
from tests.script.test_batch import run as run_batch
from tests.script.test_batch import setup as make_batch
from tests.script.test_batch import slug


def warnings_when_every_script_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                     caplog: pytest.LogCaptureFixture, message: str) -> list[str]:
    caplog.set_level(logging.WARNING)
    dirs, fake = make_batch(tmp_path, monkeypatch, count=2)

    def write(name: str, n: int) -> Any:
        raise GeminiError(message)

    fake.write = write
    assert run_batch(dirs) == 1
    assert not (dirs.out / "pr_body.md").exists()
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                    caplog: pytest.LogCaptureFixture) -> None:
    logged = warnings_when_every_script_fails(tmp_path, monkeypatch, caplog, "HTTP 429: quota")
    for name in (slug(1), slug(2)):
        assert any(name in line and "HTTP 429: quota" in line for line in logged), \
            f"the warning for {name} must carry the error text"


def test_long_reason_is_clipped_in_the_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                           caplog: pytest.LogCaptureFixture) -> None:
    cap = constants.REASON_MAX_CHARS
    logged = warnings_when_every_script_fails(tmp_path, monkeypatch, caplog, "q" * (cap * 5))
    mine = [line for line in logged if slug(1) in line]
    assert mine, "a warning names the left-out script"
    assert all("q" * cap in line and "q" * (cap + 1) not in line for line in mine)
