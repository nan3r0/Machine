"""The only module that talks to Gemini (task p2-gemini). Standard library only (spec.md section 7).

Interactions API, documented shape read 2026-11-16 (PRD.md section 7). Request:
`POST constants.GEMINI_ENDPOINT` with headers `Content-Type: application/json`,
`x-goog-api-key: <key>` and `Api-Revision: constants.GEMINI_API_REVISION`, and the JSON body
`{"model": model, "input": prompt, "response_format": {"type": "text", "mime_type":
"application/json", "schema": schema}}`, plus `"generation_config": {"temperature": t}` only when a
temperature is given. Response: `{"status": "completed", "steps": [{"type": "model_output",
"content": [{"type": "text", "text": "..."}]}], ...}`.
"""

from typing import Any


class GeminiError(Exception):
    """Any failed Gemini call. The message never contains the API key."""


def generate_json(
    model: str, prompt: str, schema: dict[str, Any], temperature: float | None = None
) -> dict[str, Any]:
    """Ask `model` for one JSON object matching `schema` and return it parsed.

    The key is read from the GEMINI_API_KEY environment variable at call time and sent only in the
    x-goog-api-key header: never in the URL, a log record or an exception message. A missing or
    blank key raises GeminiError naming GEMINI_API_KEY before any request.

    Sends with `urllib.request.urlopen(request, timeout=constants.GEMINI_TIMEOUT_S)`. HTTP 429, any
    5xx and a timeout are retried once after `time.sleep(constants.GEMINI_RETRY_WAIT_S)`; if the
    retry fails too, GeminiError. Any other failure raises GeminiError at once with no retry: HTTP
    404 (its message names `model`, since a retired model id is the usual cause), other 4xx, a
    status other than "completed", no text in the model_output steps, text that is not a JSON
    object. Error messages give the HTTP status and at most a short excerpt of the response body.

    The returned text is the text parts of the model_output steps joined in order. The output is
    untrusted: it is only parsed here, and callers validate it.
    """
    raise NotImplementedError
