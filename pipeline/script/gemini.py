"""The only module that talks to Gemini (task p2-gemini). Standard library only (spec.md section 7).

Interactions API, documented shape read 2026-11-16 (PRD.md section 7). Request:
`POST constants.GEMINI_ENDPOINT` with headers `Content-Type: application/json`,
`x-goog-api-key: <key>` and `Api-Revision: constants.GEMINI_API_REVISION`, and the JSON body
`{"model": model, "input": prompt, "response_format": {"type": "text", "mime_type":
"application/json", "schema": schema}}`, plus `"generation_config": {"temperature": t}` only when a
temperature is given. Response: `{"status": "completed", "steps": [{"type": "model_output",
"content": [{"type": "text", "text": "..."}]}], ...}`.
"""

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from pipeline import constants

_EXCERPT_CHARS = 200
_UNEXPECTED_SHAPE = "Gemini response has an unexpected shape"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turns any 3xx into an HTTPError, so the key header is never re-sent to another host."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class GeminiError(Exception):
    """Any failed Gemini call. The message never contains the API key."""


def generate_json(
    model: str, prompt: str, schema: dict[str, Any], temperature: float | None = None
) -> dict[str, Any]:
    """Ask `model` for one JSON object matching `schema` and return it parsed.

    The key is read from the GEMINI_API_KEY environment variable at call time and sent only in the
    x-goog-api-key header: never in the URL, a log record or an exception message. A missing or
    blank key raises GeminiError naming GEMINI_API_KEY before any request.

    Sends with `opener.open(request, timeout=constants.GEMINI_TIMEOUT_S)`, an opener that never
    follows redirects. HTTP 429, any 5xx and a timeout are retried once after
    `time.sleep(constants.GEMINI_RETRY_WAIT_S)`; if the retry fails too, GeminiError. Any other
    failure raises GeminiError at once with no retry: any 3xx (a redirect would re-send the key
    header to another host), HTTP 404 (its message names `model`, since a retired model id is the
    usual cause), other 4xx, an OSError or http.client.HTTPException while sending or reading the
    body (its message names the exception type only), a status other than "completed", `steps` or
    a model_output step's `content` that is not a list, no text in the model_output steps, text
    that is not a JSON object, deeply nested JSON (RecursionError) in the response or the text.
    Error messages give the HTTP status and at most a short excerpt of the response body; if
    reading the error body fails, the message keeps the status (and the model name for 404) and
    has no excerpt.

    The returned text is the text parts of the model_output steps joined in order. The output is
    untrusted: it is only parsed here, and callers validate it.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set")
    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "response_format": {"type": "text", "mime_type": "application/json", "schema": schema},
    }
    if temperature is not None:
        payload["generation_config"] = {"temperature": temperature}
    request = urllib.request.Request(
        constants.GEMINI_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
            "Api-Revision": constants.GEMINI_API_REVISION,
        },
        method="POST",
    )
    raw = _send_with_one_retry(request, model, key)
    return _parse_answer(raw)


def _send_with_one_retry(request: urllib.request.Request, model: str, key: str) -> bytes:
    for attempt in (1, 2):
        try:
            with _OPENER.open(request, timeout=constants.GEMINI_TIMEOUT_S) as response:
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or attempt == 2:
                raise GeminiError(_http_message(error, model, key)) from None
        except TimeoutError:
            if attempt == 2:
                raise GeminiError("Gemini request timed out twice") from None
        except urllib.error.URLError as error:
            if not isinstance(error.reason, TimeoutError):
                raise GeminiError(f"Gemini request failed: {type(error.reason).__name__}") from None
            if attempt == 2:
                raise GeminiError("Gemini request timed out twice") from None
        except (OSError, http.client.HTTPException) as error:
            # Last, since TimeoutError and URLError are OSErrors with their own rules above.
            raise GeminiError(f"Gemini request failed: {type(error).__name__}") from None
        time.sleep(constants.GEMINI_RETRY_WAIT_S)
    raise AssertionError("unreachable")


def _http_message(error: urllib.error.HTTPError, model: str, key: str) -> str:
    # Redact before cutting, so a key split by the cut cannot survive as a prefix.
    message = f"Gemini HTTP {error.code}"
    if error.code == 404:
        message += f" (model {model} not found, it may have been retired)"
    try:
        body = error.read()
    except (OSError, http.client.HTTPException):
        # Raised inside the HTTPError handler, so the sibling excepts do not catch it.
        return message
    excerpt = body.decode("utf-8", errors="replace").replace(key, "[redacted]")
    return f"{message}: {excerpt[:_EXCERPT_CHARS]}"


def _parse_answer(raw: bytes) -> dict[str, Any]:
    try:
        interaction = json.loads(raw)
    except (ValueError, RecursionError):
        raise GeminiError("Gemini response is not JSON") from None
    if not isinstance(interaction, dict) or interaction.get("status") != "completed":
        status = interaction.get("status") if isinstance(interaction, dict) else None
        raise GeminiError(f"Gemini interaction not completed (status {status!r})")
    steps = interaction.get("steps", [])
    if not isinstance(steps, list):
        raise GeminiError(_UNEXPECTED_SHAPE)
    texts: list[str] = []
    for step in steps:
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        content = step.get("content", [])
        if not isinstance(content, list):
            raise GeminiError(_UNEXPECTED_SHAPE)
        texts += [
            part["text"]
            for part in content
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
        ]
    if not texts:
        raise GeminiError("Gemini returned no text")
    try:
        answer = json.loads("".join(texts))
    except (ValueError, RecursionError):
        raise GeminiError("Gemini text is not valid JSON") from None
    if not isinstance(answer, dict):
        raise GeminiError("Gemini text is not a JSON object")
    return answer
