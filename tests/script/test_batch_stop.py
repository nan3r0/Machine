"""The weekly batch stops early when Gemini cannot answer (task p4d-gemini-quota-guard).

Weekly-scripts runs on 2026-11-23 and 24 met HTTP 503 and the free tier's daily 429. `run` caught
each GeminiError and went on to the next script, so every remaining script spent requests that
could not succeed. Now a GeminiQuotaError from any call stops the batch at once, and
`constants.GEMINI_MAX_CONSECUTIVE_ERRORS` scripts in a row left out by GeminiError stop it too.
Scripts already written still go in the PR; none written still returns 1 with no PR body.
"""

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError, GeminiQuotaError
from tests.script.test_batch import FakeGemini, flagged, slug
from tests.script.test_batch import run as run_batch
from tests.script.test_batch import setup as make_batch

N = constants.GEMINI_MAX_CONSECUTIVE_ERRORS
QUOTA = "HTTP 429: limit reached <b>"  # no per-day text: the batch must stop on the type
REQUESTS = re.compile(r"(\d+) Gemini requests")


def tried(fake: FakeGemini) -> list[str]:
    """Source slugs that got any Gemini call, in first-call order."""
    return list(dict.fromkeys(name for _, name, _ in fake.calls))


def stop_lines(body: str) -> list[str]:
    return [line for line in body.splitlines() if "Stopped early" in line]


def warnings(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING)


def raise_on(target: str, error: Exception, answer: Callable[[str, int], Any]) -> Callable[[str, int], Any]:
    def policy(name: str, n: int) -> Any:
        if name == target:
            raise error
        return answer(name, n)
    return policy


def quota_at(site: str, fake: FakeGemini, target: str) -> None:
    """Make the first `site` call ("write", "check" or "rewrite") for `target` raise GeminiQuotaError."""
    if site == "write":
        fake.write = raise_on(target, GeminiQuotaError(QUOTA), fake.write)
    elif site == "check":
        def check(name: str, n: int, index: int) -> str:
            if name == target:
                raise GeminiQuotaError(QUOTA)
            return "SUPPORTED"
        fake.check = check
    else:
        fake.check = lambda name, n, i: "UNSUPPORTED" if name == target and n == 0 and i == 0 else "SUPPORTED"
        fake.rewrite = raise_on(target, GeminiQuotaError(QUOTA), fake.rewrite)


# --- daily quota -----------------------------------------------------------------------------------

@pytest.mark.parametrize("site", ["write", "check", "rewrite"])
def test_quota_stops_the_batch_at_once(site: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The script that met the quota is left out (a rewrite may have landed unchecked) and no later
    source gets a call. Script 1 is written and goes in the PR."""
    dirs, fake = make_batch(tmp_path, monkeypatch, count=5)
    quota_at(site, fake, slug(2))
    assert run_batch(dirs) == 0
    assert sorted(dirs.written()) == [slug(1)]
    assert tried(fake) == [slug(1), slug(2)]
    calls_for_2 = [kind for _, name, kind in fake.calls if name == slug(2)]
    assert calls_for_2[-1] == site, "nothing more is asked for the script after the quota error"
    body = dirs.body()
    assert flagged(body, "limit reached") == [slug(2)]
    lines = stop_lines(body)
    assert len(lines) == 1 and "daily quota" in lines[0]
    assert "limit reached" not in lines[0] and "<b>" not in lines[0], "the stop line is fixed text"


def test_quota_with_nothing_written_fails_and_logs_why(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                       caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    dirs, fake = make_batch(tmp_path, monkeypatch, count=4)
    quota_at("write", fake, slug(1))
    assert run_batch(dirs) == 1
    assert not (dirs.out / "pr_body.md").exists()
    assert tried(fake) == [slug(1)]
    assert "daily quota" in warnings(caplog)
    assert REQUESTS.search(caplog.text), "the request count is logged even when the run fails"


# --- errors in a row -------------------------------------------------------------------------------

def gemini_down(fake: FakeGemini, down: set[str]) -> None:
    fake.write = raise_on_any(down, fake.write)


def raise_on_any(down: set[str], answer: Callable[[str, int], Any]) -> Callable[[str, int], Any]:
    def policy(name: str, n: int) -> Any:
        if name in down:
            raise GeminiError("HTTP 503: overloaded")
        return answer(name, n)
    return policy


def test_errors_in_a_row_stop_the_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                        caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    dirs, fake = make_batch(tmp_path, monkeypatch, count=N + 2)
    gemini_down(fake, {slug(n) for n in range(1, N + 3)})
    assert run_batch(dirs) == 1
    assert not (dirs.out / "pr_body.md").exists()
    assert tried(fake) == [slug(n) for n in range(1, N + 1)]
    assert "in a row" in warnings(caplog)


def test_errors_in_a_row_keep_the_scripts_already_written(tmp_path: Path,
                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    dirs, fake = make_batch(tmp_path, monkeypatch, count=N + 3)
    gemini_down(fake, {slug(n) for n in range(2, N + 4)})
    assert run_batch(dirs) == 0
    assert sorted(dirs.written()) == [slug(1)]
    assert tried(fake) == [slug(n) for n in range(1, N + 2)]
    lines = stop_lines(dirs.body())
    assert len(lines) == 1 and "in a row" in lines[0]
    assert "overloaded" not in lines[0]


def test_fewer_errors_than_the_limit_go_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """N-1 errors, a written script (the count restarts), N-1 errors again, one more written."""
    count = 2 * N
    dirs, fake = make_batch(tmp_path, monkeypatch, count=count)
    down = {slug(n) for n in range(1, count + 1)} - {slug(N), slug(count)}
    gemini_down(fake, down)
    assert run_batch(dirs) == 0
    assert sorted(dirs.written()) == [slug(N), slug(count)]
    assert tried(fake) == [slug(n) for n in range(1, count + 1)]
    assert stop_lines(dirs.body()) == []


def test_a_rejected_answer_breaks_the_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GenerateError means Gemini answered, so a script left out by it is not part of an outage:
    N-1 GeminiErrors, one GenerateError, N-1 GeminiErrors, then a script that is written."""
    count = 2 * N
    dirs, fake = make_batch(tmp_path, monkeypatch, count=count)
    rejected = slug(N)
    down = {slug(n) for n in range(1, count)} - {rejected}
    good = fake.write
    fake.write = raise_on_any(down, lambda name, n: {"hook": "broken"} if name == rejected else good(name, n))
    assert run_batch(dirs) == 0
    assert sorted(dirs.written()) == [slug(count)]
    assert tried(fake) == [slug(n) for n in range(1, count + 1)]


# --- request count ---------------------------------------------------------------------------------

def count_two_per_call(monkeypatch: pytest.MonkeyPatch, fake: FakeGemini) -> None:
    """Every call stands for a first try plus one retry; the counter starts mid-process."""
    monkeypatch.setattr(gemini, "requests_sent", 40)

    def generate_json(*args: Any, **kwargs: Any) -> Any:
        gemini.requests_sent += 2
        return fake(*args, **kwargs)

    monkeypatch.setattr(gemini, "generate_json", generate_json)


def logged_requests(caplog: pytest.LogCaptureFixture) -> list[int]:
    return [int(m.group(1)) for r in caplog.records if r.levelno >= logging.INFO
            for m in [REQUESTS.search(r.getMessage())] if m]


def test_request_count_is_this_runs_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                             caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    dirs, fake = make_batch(tmp_path, monkeypatch, count=3)
    count_two_per_call(monkeypatch, fake)
    assert run_batch(dirs) == 0
    assert logged_requests(caplog) == [2 * len(fake.calls)]


def test_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                    caplog: pytest.LogCaptureFixture) -> None:
    """Quota on script 3 of 7: scripts 1 and 2 go in the PR with one stop line, sources 4 to 7 get
    no call, and the run's real request count is logged. A clean run has no stop line."""
    caplog.set_level(logging.INFO)
    dirs, fake = make_batch(tmp_path, monkeypatch)
    count_two_per_call(monkeypatch, fake)
    quota_at("write", fake, slug(3))
    assert run_batch(dirs) == 0
    assert sorted(dirs.written()) == [slug(1), slug(2)]
    assert tried(fake) == [slug(1), slug(2), slug(3)]
    assert len(stop_lines(dirs.body())) == 1
    assert "daily quota" in warnings(caplog)
    assert logged_requests(caplog) == [2 * len(fake.calls)]

    clean = tmp_path / "clean"
    clean.mkdir()
    dirs, fake = make_batch(clean, monkeypatch)
    assert run_batch(dirs) == 0
    assert len(dirs.written()) == constants.SCRIPTS_PER_BATCH
    assert stop_lines(dirs.body()) == []
