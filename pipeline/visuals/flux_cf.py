"""The only module that talks to Cloudflare Workers AI (task p3c-flux-client). Standard library only.

flux-1-schnell over the REST API, read 2026-11-28 (.harness/handoffs/p3c-plan.md). Request:
`POST constants.FLUX_ENDPOINT` (with the account id filled in) with headers
`Authorization: Bearer <token>` and `Content-Type: application/json`, and the JSON body
`{"prompt": FLUX_STYLE_PREFIX + prompt, "steps": FLUX_STEPS}`. Response: Cloudflare's envelope
`{"success": true, "errors": [], "messages": [], "result": {"image": "<base64 JPEG>"}}`.
"""

requests_sent = 0


class FluxError(Exception):
    """Any failed image call. The message never contains the API token."""


class FluxQuotaError(FluxError):
    """The free daily neuron allocation is used up. It cannot clear before 00:00 UTC, so it is never
    retried. A FluxError, so callers that catch FluxError still catch it."""


def generate_image(prompt: str) -> bytes:
    """Paint one scene and return the JPEG bytes, checked by `image_size`.

    The token and account id are read from the CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID
    environment variables at call time. A missing or blank one raises FluxError naming the variable,
    and an account id that is not exactly 32 lowercase hex characters raises FluxError, both before
    any request. The token goes only in the Authorization header: never in the URL, a log record or
    an exception message.

    The sent prompt is `constants.FLUX_STYLE_PREFIX + prompt`. A blank `prompt`, or a sent prompt
    longer than `FLUX_PROMPT_MAX_CHARS`, raises FluxError before any request.

    Sends with `opener.open(request, timeout=constants.FLUX_TIMEOUT_S)` through an opener that never
    follows redirects, to the https host of FLUX_ENDPOINT only. HTTP 429, any 5xx and a timeout are
    retried once after `time.sleep(constants.FLUX_RETRY_WAIT_S)`; if the retry fails too, FluxError.
    An HTTP 4xx (429 included) whose error body holds Cloudflare's daily-allocation error (code 4006,
    or the words "daily free allocation", any case) raises FluxQuotaError at once with no retry, also
    when it is the retry's answer. Any other failure raises FluxError at once: any 3xx, other 4xx
    (401 and 403 say the token was refused), an OSError or http.client.HTTPException while sending
    or reading (the message names the exception type only), a body over FLUX_RESPONSE_MAX_BYTES (read
    at most one byte past the cap), a body that is not a JSON object, `success` not true, no string
    `result.image`, base64 that does not decode strictly, or an image `image_size` rejects. Error
    messages give the HTTP status and at most a 200-character excerpt of the body.

    The module-level `requests_sent` counts the HTTP requests handed to the opener (retries
    included), never a call that fails before sending.
    """
    raise NotImplementedError


def image_size(data: bytes) -> tuple[int, int]:
    """(width, height) of a baseline or progressive JPEG, read from its first SOF marker.

    Raises FluxError if `data` is over FLUX_IMAGE_MAX_BYTES, does not start with the JPEG magic
    FF D8 FF, ends before a start-of-frame marker (C0 to CF, except C4, C8 and CC), or if either side
    lies outside FLUX_IMAGE_SIDE_PX (inclusive). Reads only marker headers; never decodes pixels.
    """
    raise NotImplementedError
