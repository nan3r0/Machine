"""Phase review N5: odd response shapes and failed body reads are GeminiError (task p2b-gemini-shapes).

gemini.generate_json documents GeminiError for any failed call, and the batch only catches
GeminiError, so a TypeError or a raw socket error here would crash the whole weekly run instead of
leaving one script out.
"""

import http.client
import time
import urllib.request
from typing import Any

import pytest

from pipeline import constants
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError
from tests.script.gemini_fakes import REFERENCE, FakeUrlopen, as_json

SCHEMA = {"type": "object", "properties": {"narration": {"type": "string"}}, "required": ["narration"]}
GOOD_TEXT = as_json({"narration": "The sound was ice."})


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFAKE-shapes-key-0123456789")
    return sleeps


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeUrlopen:
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    return fake


def call() -> dict[str, Any]:
    return gemini.generate_json(constants.WRITER_MODEL, "Write one line.", SCHEMA)


def with_steps(steps: Any) -> dict[str, Any]:
    return {**REFERENCE, "steps": steps}


ODD_SHAPES = [
    with_steps(5),
    with_steps(None),
    with_steps(True),
    with_steps([{"type": "model_output", "content": 5}]),
    with_steps([{"type": "model_output", "content": None}]),
    with_steps([{"type": "model_output", "content": 1.5}]),
    with_steps([{"type": "model_output", "content": [{"type": "text", "text": GOOD_TEXT}]},
                {"type": "model_output", "content": 7}]),
]


@pytest.mark.parametrize("response", ODD_SHAPES)
def test_odd_response_shapes_raise_gemini_error(monkeypatch: pytest.MonkeyPatch, response: Any) -> None:
    fake = install(monkeypatch, response)
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 1, "a malformed answer is not retried"


class BrokenRead:
    """A response whose body read fails part way, as a dropped connection does."""

    def __init__(self, error: BaseException) -> None:
        self.status = 200
        self.error = error

    def read(self, *args: Any) -> bytes:
        raise self.error

    def __enter__(self) -> "BrokenRead":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


READ_ERRORS = [
    http.client.IncompleteRead(b'{"status": "comp'),
    ConnectionResetError(104, "Connection reset by peer"),
    http.client.RemoteDisconnected("Remote end closed connection without response"),
]


@pytest.mark.parametrize("error", READ_ERRORS, ids=lambda e: type(e).__name__)
def test_a_failed_body_read_raises_gemini_error_without_retry(
    monkeypatch: pytest.MonkeyPatch, env: list[float], error: BaseException
) -> None:
    requests: list[Any] = []

    def broken(request: Any, *args: Any, **kwargs: Any) -> BrokenRead:
        requests.append(request)
        return BrokenRead(error)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", broken)
    with pytest.raises(GeminiError) as raised:
        call()
    assert len(requests) == 1 and env == [], "only 429, 5xx and timeouts are retried"
    assert "AIzaFAKE" not in str(raised.value)


def test_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, with_steps(5))
    with pytest.raises(GeminiError):
        call()
    monkeypatch.setattr(urllib.request.OpenerDirector, "open",
                        lambda *a, **k: BrokenRead(ConnectionResetError(104, "reset")))
    with pytest.raises(GeminiError):
        call()
