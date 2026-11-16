"""Hand-built Gemini Interactions API responses (not captured from a live call: no key exists yet,
owner decision D1). REFERENCE is the example response of interactions.create copied verbatim from
https://aistudio.google.com/api-reference/interactions-api, read 2026-11-16 (PRD.md section 7).
`interaction(text)` keeps that envelope and swaps in the model's text."""

import copy
import io
import json
import urllib.error
import urllib.request
from typing import Any

REFERENCE: dict[str, Any] = {
    "created": "2025-12-04T15:01:45Z",
    "id": "v1_ChdXS0l4YWZXTk9xbk0xZThQczhEcmlROBIXV0tJeGFmV05PcW5NMWU4UHM4RHJpUTg",
    "model": "gemini-3.8-flash",
    "object": "interaction",
    "status": "completed",
    "steps": [
        {
            "type": "model_output",
            "content": [
                {
                    "type": "text",
                    "text": "Hello! I'm doing well, functioning as expected. "
                            "Thank you for asking! How are you doing today?",
                }
            ],
        }
    ],
    "updated": "2025-12-04T15:01:45Z",
    "usage": {
        "input_tokens_by_modality": [{"modality": "text", "tokens": 7}],
        "total_cached_tokens": 0,
        "total_input_tokens": 7,
        "total_output_tokens": 23,
        "total_thought_tokens": 49,
        "total_tokens": 79,
        "total_tool_use_tokens": 0,
    },
}


def interaction(*texts: str, status: str = "completed") -> dict[str, Any]:
    """REFERENCE with one model_output step holding `texts` as its text parts."""
    body = copy.deepcopy(REFERENCE)
    body["status"] = status
    body["steps"] = [{"type": "model_output", "content": [{"type": "text", "text": t} for t in texts]}]
    return body


def as_json(data: Any) -> str:
    return json.dumps(data)


class Response:
    """What urllib.request.urlopen returns: a context manager with read()."""

    def __init__(self, body: bytes) -> None:
        self.status = 200
        self._body = body

    def read(self, *args: Any) -> bytes:
        return self._body

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def http_error(code: int, body: str = '{"error": {"code": 0, "message": "fake"}}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://generativelanguage.googleapis.com/v1beta/interactions", code, "fake error", None,  # type: ignore[arg-type]
        io.BytesIO(body.encode("utf-8")))


class FakeUrlopen:
    """Replaces urllib.request.urlopen. Each call takes the next outcome: a dict (sent as the JSON
    body), raw bytes, or an exception to raise. Records every request and timeout."""

    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[Any] = []

    def __call__(self, request: urllib.request.Request, *args: Any, **kwargs: Any) -> Response:
        self.requests.append(request)
        self.timeouts.append(kwargs.get("timeout", args[1] if len(args) > 1 else None))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, bytes):
            return Response(outcome)
        return Response(json.dumps(outcome).encode("utf-8"))
