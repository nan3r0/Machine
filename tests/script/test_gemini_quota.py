"""Daily-quota 429 and the request counter in the Gemini client (task p4d-gemini-quota-guard).

Weekly-scripts runs on 2026-11-23 and 24 hit HTTP 429 for the free tier's requests per day. The
client retried it once (the retry cannot succeed the same day) and nothing counted the HTTP
requests actually sent. A daily-quota 429 is GeminiQuotaError (a GeminiError), sent once, never
retried. Every other retry rule stays as it was.
"""

import time
import traceback
import urllib.request
from typing import Any

import pytest

from pipeline import constants
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError, GeminiQuotaError
from tests.script.gemini_fakes import FakeUrlopen, as_json, http_error, interaction

KEY = "AIzaFAKE-quota-key-0123456789abcdef"
SCHEMA = {"type": "object", "properties": {"narration": {"type": "string"}}, "required": ["narration"]}
ANSWER = {"narration": "The sound was ice."}
PREAMBLE = "You exceeded your current quota, please check your plan and billing details. " * 4
# The per-day marker sits past the 200-character excerpt, so only the full body can show it.
PLAIN_DAY = f'{{"error": {{"code": 429, "message": "{PREAMBLE} Limit: 20 requests per day."}}}}'
QUOTA_ID_DAY = (f'{{"error": {{"code": 429, "message": "{PREAMBLE}", "details": [{{"violations": '
                f'[{{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}}]}}]}}}}')
PLAIN_MINUTE = f'{{"error": {{"code": 429, "message": "{PREAMBLE} Limit: 5 requests per minute."}}}}'
QUOTA_ID_MINUTE = (f'{{"error": {{"code": 429, "message": "{PREAMBLE}", "details": [{{"violations": '
                   f'[{{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}}]}}]}}}}')


@pytest.fixture(autouse=True)
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waited: list[float] = []
    monkeypatch.setattr(time, "sleep", waited.append)
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    return waited


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeUrlopen:
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    return fake


def call() -> dict[str, Any]:
    return gemini.generate_json(constants.WRITER_MODEL, "Write one line.", SCHEMA)


def sent_by(action: Any) -> int:
    """How many requests the client counted while `action` ran (it may raise GeminiError)."""
    before = gemini.requests_sent
    try:
        action()
    except GeminiError:
        pass
    return gemini.requests_sent - before


# --- daily quota -----------------------------------------------------------------------------------

@pytest.mark.parametrize("body", [PLAIN_DAY, QUOTA_ID_DAY])
def test_daily_quota_is_sent_once_and_never_retried(body: str, monkeypatch: pytest.MonkeyPatch,
                                                    sleeps: list[float]) -> None:
    fake = install(monkeypatch, http_error(429, body), interaction(as_json(ANSWER)))
    with pytest.raises(GeminiQuotaError) as raised:
        call()
    assert isinstance(raised.value, GeminiError), "callers that catch GeminiError still catch it"
    assert len(fake.requests) == 1
    assert sleeps == []


def test_daily_quota_message_keeps_status_and_excerpt(monkeypatch: pytest.MonkeyPatch) -> None:
    """The body is read once: detection must not drain it before the excerpt is taken."""
    install(monkeypatch, http_error(429, PLAIN_DAY))
    with pytest.raises(GeminiQuotaError) as raised:
        call()
    message = str(raised.value)
    assert "HTTP 429" in message
    assert "You exceeded your current quota" in message
    assert len(message) <= 500


def test_daily_quota_never_leaks_the_key(monkeypatch: pytest.MonkeyPatch) -> None:
    body = f'{{"error": {{"message": "key {KEY} has used its 20 requests per day"}}}}'
    install(monkeypatch, http_error(429, body))
    with pytest.raises(GeminiQuotaError) as raised:
        call()
    assert KEY not in "".join(traceback.format_exception(raised.value))


@pytest.mark.parametrize("first", [
    http_error(429, PLAIN_MINUTE), http_error(429, QUOTA_ID_MINUTE), http_error(429),
    http_error(503, PLAIN_DAY),
])
def test_other_429_and_5xx_still_retried_once(first: BaseException, monkeypatch: pytest.MonkeyPatch,
                                              sleeps: list[float]) -> None:
    """Only a 429 whose body names a per-day limit skips the retry; a 503 is overload, not quota."""
    fake = install(monkeypatch, first, interaction(as_json(ANSWER)))
    assert call() == ANSWER
    assert len(fake.requests) == 2
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]


@pytest.mark.parametrize("second", [http_error(429, PLAIN_MINUTE), http_error(503)])
def test_other_failures_twice_are_plain_gemini_error(second: BaseException,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, http_error(503), second)
    with pytest.raises(GeminiError) as raised:
        call()
    assert not isinstance(raised.value, GeminiQuotaError)


def test_daily_quota_on_the_retry_is_quota_error(monkeypatch: pytest.MonkeyPatch,
                                                 sleeps: list[float]) -> None:
    fake = install(monkeypatch, http_error(503), http_error(429, QUOTA_ID_DAY))
    with pytest.raises(GeminiQuotaError):
        call()
    assert len(fake.requests) == 2
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]


# --- request counter -------------------------------------------------------------------------------

def test_counter_counts_every_request_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, interaction(as_json(ANSWER)))
    assert sent_by(call) == 1
    install(monkeypatch, http_error(429), interaction(as_json(ANSWER)))
    assert sent_by(call) == 2
    install(monkeypatch, http_error(503), http_error(503))
    assert sent_by(call) == 2
    install(monkeypatch, TimeoutError("timed out"), TimeoutError("timed out"))
    assert sent_by(call) == 2
    install(monkeypatch, http_error(429, PLAIN_DAY))
    assert sent_by(call) == 1
    install(monkeypatch, http_error(400))
    assert sent_by(call) == 1
    install(monkeypatch, http_error(302))
    assert sent_by(call) == 1
    install(monkeypatch, b"not json")
    assert sent_by(call) == 1


def test_counter_skips_a_call_with_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, interaction(as_json(ANSWER)))
    monkeypatch.delenv("GEMINI_API_KEY")
    assert sent_by(call) == 0
    assert fake.requests == []


def test_acceptance(monkeypatch: pytest.MonkeyPatch, sleeps: list[float]) -> None:
    """A daily-quota 429 is one request, no retry, GeminiQuotaError; an ordinary 429 keeps its one
    retry; the counter matches the requests the fake saw."""
    fake = install(monkeypatch, http_error(429, QUOTA_ID_DAY))
    assert sent_by(call) == 1 == len(fake.requests)
    assert sleeps == []
    fake = install(monkeypatch, http_error(429, PLAIN_MINUTE), interaction(as_json(ANSWER)))
    assert sent_by(call) == 2 == len(fake.requests)
    assert sleeps == [constants.GEMINI_RETRY_WAIT_S]
