"""Exceptions that still escape gemini.generate_json as something other than GeminiError (task
p2c-gemini-escapes).

The batch catches only GeminiError, so any other exception crashes the whole weekly run instead of
leaving one script out. Two paths still escape: a failed read of an HTTP error's body (it happens
inside the HTTPError handler, where the sibling except clauses do not apply), and json.loads
raising RecursionError on deeply nested JSON (RecursionError is not a ValueError).
"""

import http.client
import io
import time
import urllib.error
import urllib.request
from typing import Any

import pytest

from pipeline import constants
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError
from tests.script.gemini_fakes import FakeUrlopen, interaction

KEY = "AIzaFAKE-errors-key-0123456789"
SCHEMA = {"type": "object", "properties": {"narration": {"type": "string"}}, "required": ["narration"]}
DEPTH = 100_000  # far past the interpreter's recursion limit


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    return sleeps


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeUrlopen:
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    return fake


def call() -> dict[str, Any]:
    return gemini.generate_json(constants.WRITER_MODEL, "Write one line.", SCHEMA)


class BrokenBody(io.RawIOBase):
    """An error body whose read fails, as a dropped connection does."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def readable(self) -> bool:
        return True

    def read(self, *args: Any) -> bytes:
        raise self.error


def http_error_with_broken_body(code: int, error: BaseException) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        constants.GEMINI_ENDPOINT, code, "fake error", None, BrokenBody(error))  # type: ignore[arg-type]


READ_ERRORS = [
    http.client.IncompleteRead(b'{"error": {"co'),
    ConnectionResetError(104, "Connection reset by peer"),
    TimeoutError("timed out"),
]


@pytest.mark.parametrize("code", [400, 403, 404])
@pytest.mark.parametrize("error", READ_ERRORS, ids=lambda e: type(e).__name__)
def test_a_failed_error_body_read_is_gemini_error_naming_the_status(
    monkeypatch: pytest.MonkeyPatch, env: list[float], code: int, error: BaseException
) -> None:
    fake = install(monkeypatch, http_error_with_broken_body(code, error))
    with pytest.raises(GeminiError) as raised:
        call()
    assert str(code) in str(raised.value)
    assert KEY not in str(raised.value)
    assert len(fake.requests) == 1 and env == [], "a 4xx is never retried"


def test_a_404_with_a_broken_body_still_names_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, http_error_with_broken_body(404, ConnectionResetError(104, "reset")))
    with pytest.raises(GeminiError, match=constants.WRITER_MODEL):
        call()


@pytest.mark.parametrize("code", [429, 503])
def test_a_retryable_status_with_a_broken_body_keeps_its_one_retry(
    monkeypatch: pytest.MonkeyPatch, env: list[float], code: int
) -> None:
    broken = http.client.IncompleteRead(b"")
    fake = install(monkeypatch, *(http_error_with_broken_body(code, broken) for _ in range(2)))
    with pytest.raises(GeminiError) as raised:
        call()
    assert str(code) in str(raised.value)
    assert len(fake.requests) == 2 and env == [constants.GEMINI_RETRY_WAIT_S]


NESTED = ["[" * DEPTH, '{"a": ' * DEPTH, "[" * DEPTH + "]" * DEPTH]


@pytest.mark.parametrize("text", NESTED, ids=["open-arrays", "open-objects", "closed-arrays"])
def test_deeply_nested_envelope_is_gemini_error(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    fake = install(monkeypatch, text.encode("utf-8"))
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 1, "a malformed answer is not retried"


@pytest.mark.parametrize("text", NESTED, ids=["open-arrays", "open-objects", "closed-arrays"])
def test_deeply_nested_answer_text_is_gemini_error(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    fake = install(monkeypatch, interaction(text))
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 1, "a malformed answer is not retried"


def test_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, http_error_with_broken_body(400, http.client.IncompleteRead(b"")))
    with pytest.raises(GeminiError):
        call()
    install(monkeypatch, ("[" * DEPTH).encode("utf-8"))
    with pytest.raises(GeminiError):
        call()
    install(monkeypatch, interaction('{"a": ' * DEPTH))
    with pytest.raises(GeminiError):
        call()
