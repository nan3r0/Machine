"""The Gemini client: request shape, key handling, errors and retries (task p2-gemini, spec.md section 5).

urllib.request.urlopen and time.sleep are replaced by fakes; no test touches the network.
"""

import json
import logging
import time
import traceback
import urllib.request
from typing import Any

import pytest

from pipeline import constants
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError
from tests.script.gemini_fakes import REFERENCE, FakeUrlopen, as_json, http_error, interaction

KEY = "AIzaFAKE-test-key-0123456789abcdefghij"
SCHEMA = {"type": "object", "properties": {"narration": {"type": "string"}}, "required": ["narration"]}
ANSWER = {"narration": "The sound was ice."}


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    calls: list[float] = []
    monkeypatch.setattr(time, "sleep", calls.append)
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    return calls


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeUrlopen:
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    return fake


def call(temperature: float | None = None) -> dict[str, Any]:
    return gemini.generate_json(constants.WRITER_MODEL, "Write one line.", SCHEMA, temperature)


def headers(request: urllib.request.Request) -> dict[str, str]:
    return {name.lower(): value for name, value in request.header_items()}


def body(request: urllib.request.Request) -> dict[str, Any]:
    data = request.data
    assert isinstance(data, bytes)
    loaded: dict[str, Any] = json.loads(data)
    return loaded


def test_request_shape(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    fake = install(monkeypatch, interaction(as_json(ANSWER)))
    assert call() == ANSWER
    [request] = fake.requests
    assert request.full_url == constants.GEMINI_ENDPOINT
    assert request.get_method() == "POST"
    sent = headers(request)
    assert sent["x-goog-api-key"] == KEY
    assert sent["api-revision"] == constants.GEMINI_API_REVISION
    assert sent["content-type"] == "application/json"
    assert body(request) == {
        "model": constants.WRITER_MODEL, "input": "Write one line.",
        "response_format": {"type": "text", "mime_type": "application/json", "schema": SCHEMA}}
    assert fake.timeouts == [constants.GEMINI_TIMEOUT_S]
    assert KEY not in request.full_url


@pytest.mark.parametrize("temperature", [0.0, 0.7])
def test_temperature_sent_when_given(temperature: float, monkeypatch: pytest.MonkeyPatch,
                                     sleeps: list[float]) -> None:
    fake = install(monkeypatch, interaction(as_json(ANSWER)))
    call(temperature)
    assert body(fake.requests[0])["generation_config"] == {"temperature": temperature}


def test_text_parts_of_model_output_steps_are_joined(monkeypatch: pytest.MonkeyPatch,
                                                     sleeps: list[float]) -> None:
    response = interaction('{"narration": ', '"The sound was ice."}')
    response["steps"].insert(0, {"type": "thought", "content": [{"type": "text", "text": "not json"}]})
    install(monkeypatch, response)
    assert call() == ANSWER


def test_reference_example_text_is_not_json(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    """The documented example's text is prose, so asking for JSON and getting it is an error."""
    install(monkeypatch, REFERENCE)
    with pytest.raises(GeminiError):
        call()


def test_key_read_at_call_time(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSECOND-key-value")
    fake = install(monkeypatch, interaction(as_json(ANSWER)))
    call()
    assert headers(fake.requests[0])["x-goog-api-key"] == "AIzaSECOND-key-value"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_key_names_the_variable(value: str | None, monkeypatch: pytest.MonkeyPatch,
                                        sleeps: list[float]) -> None:
    if value is None:
        monkeypatch.delenv("GEMINI_API_KEY")
    else:
        monkeypatch.setenv("GEMINI_API_KEY", value)
    fake = install(monkeypatch)
    with pytest.raises(GeminiError, match="GEMINI_API_KEY"):
        call()
    assert fake.requests == []


@pytest.mark.parametrize("code", [429, 500, 503])
def test_retryable_status_retried_once_then_succeeds(code: int, monkeypatch: pytest.MonkeyPatch,
                                                     sleeps: list[float]) -> None:
    fake = install(monkeypatch, http_error(code), interaction(as_json(ANSWER)))
    assert call() == ANSWER
    assert len(fake.requests) == 2
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]


@pytest.mark.parametrize("first", [http_error(429), http_error(502), TimeoutError("timed out")])
def test_second_failure_raises_after_one_retry(first: BaseException, monkeypatch: pytest.MonkeyPatch,
                                               sleeps: list[float]) -> None:
    fake = install(monkeypatch, first, http_error(429), interaction(as_json(ANSWER)))
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) == 2
    assert len(sleeps) == 1


def test_timeout_retried_once(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    fake = install(monkeypatch, TimeoutError("timed out"), interaction(as_json(ANSWER)))
    assert call() == ANSWER
    assert len(fake.requests) == 2


def test_model_not_found_fails_at_once_naming_the_model(monkeypatch: pytest.MonkeyPatch,
                                                         sleeps: list[float]) -> None:
    fake = install(monkeypatch, http_error(404), interaction(as_json(ANSWER)))
    with pytest.raises(GeminiError, match=constants.WRITER_MODEL) as caught:
        call()
    assert "404" in str(caught.value)
    assert len(fake.requests) == 1
    assert sleeps == []


@pytest.mark.parametrize("code", [400, 401, 403])
def test_other_client_errors_are_not_retried(code: int, monkeypatch: pytest.MonkeyPatch,
                                             sleeps: list[float]) -> None:
    fake = install(monkeypatch, http_error(code), interaction(as_json(ANSWER)))
    with pytest.raises(GeminiError, match=str(code)):
        call()
    assert len(fake.requests) == 1


@pytest.mark.parametrize("response", [
    interaction(as_json(ANSWER), status="failed"),
    interaction(as_json(ANSWER), status="incomplete"),
    interaction(),
    {**REFERENCE, "steps": []},
    interaction("not json at all"),
    interaction("[1, 2]"),
    interaction('{"narration": "cut off'),
    b"<html>not an interaction</html>",
    b"",
], ids=["failed", "incomplete", "no text", "no steps", "prose", "list", "truncated", "html", "empty"])
def test_bad_answers_raise(response: Any, monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    fake = install(monkeypatch, response, interaction(as_json(ANSWER)), interaction(as_json(ANSWER)))
    with pytest.raises(GeminiError):
        call()
    assert len(fake.requests) <= 2


def test_key_never_in_errors_or_logs(monkeypatch: pytest.MonkeyPatch, sleeps: list[float],
                                     caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    echo = f'{{"error": {{"message": "bad key {KEY}"}}}}'
    install(monkeypatch, http_error(429, echo), http_error(429, echo))
    with pytest.raises(GeminiError) as caught:
        call()
    assert KEY not in "".join(traceback.format_exception(caught.value))
    assert KEY not in caplog.text
    install(monkeypatch, http_error(400, echo))
    with pytest.raises(GeminiError) as caught:
        call()
    assert KEY not in "".join(traceback.format_exception(caught.value))
    assert KEY not in caplog.text


def test_error_excerpt_is_short(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    install(monkeypatch, http_error(400, "x" * 100_000))
    with pytest.raises(GeminiError) as caught:
        call()
    assert len(str(caught.value)) <= 500


def test_acceptance(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    """One documented-shape call returns the parsed object; 429 is retried exactly once; a retired
    model fails loudly; a missing key fails before any request; the key is only in the header."""
    fake = install(monkeypatch, http_error(429), interaction(as_json(ANSWER)))
    assert call() == ANSWER
    assert len(fake.requests) == 2
    assert headers(fake.requests[1])["x-goog-api-key"] == KEY
    assert KEY not in fake.requests[1].full_url and KEY not in str(fake.requests[1].data)
    install(monkeypatch, http_error(404))
    with pytest.raises(GeminiError, match=constants.WRITER_MODEL):
        call()
    monkeypatch.delenv("GEMINI_API_KEY")
    with pytest.raises(GeminiError, match="GEMINI_API_KEY"):
        call()
