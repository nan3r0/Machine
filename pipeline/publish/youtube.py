"""The only module that talks to YouTube (task p4-youtube, PRD R15). Standard library only.

YouTube Data API v3 `videos.insert` as a resumable upload, read 2026-11-21. Contract written by
p4-contracts; p4-youtube implements it.
"""

import http.client
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pipeline import constants
from pipeline.schema import Script
from pipeline.script import validate

_LOG = logging.getLogger(__name__)
_EXCERPT_CHARS = 200
_CREDENTIAL_NAMES = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turns any 3xx into an HTTPError, so a token or secret is never re-sent to another host."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class UploadError(Exception):
    """A failed upload. `sent` is False when no byte of the video went out (checks, token refresh or
    the init request failed), so the claim may be released; True once the PUT of the bytes began.
    The message never contains a token or secret."""

    def __init__(self, message: str, *, sent: bool) -> None:
        super().__init__(message)
        self.sent = sent


def upload(script: Script, video_path: Path) -> str:
    """Upload `video_path` with `script`'s metadata and return the 11-character video id.

    Every endpoint, limit and flag is read as `constants.X` at call time. Requests go through one
    opener that refuses every redirect (`opener.open(request, timeout=...)`), as in
    pipeline/script/gemini.py. No retry: the next scheduled run is the retry.

    Before any request, each raising UploadError(sent=False): `validate.problems(script)` must be
    empty; the file must exist with a size from `MIN_FILE_BYTES` to `MAX_FILE_BYTES`; the
    environment variables YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN must be
    set and non-blank (the message names the missing one).

    1. Token: POST `YOUTUBE_TOKEN_ENDPOINT`, `application/x-www-form-urlencoded` body with
       client_id, client_secret, refresh_token and grant_type=refresh_token, timeout
       `YOUTUBE_CONNECT_TIMEOUT_S`. The JSON answer must hold a non-empty `access_token` and a
       `scope` whose space-separated set is exactly {`YOUTUBE_SCOPE`}. An `invalid_grant` error
       says the refresh token was revoked or expired and must be made again. Right after a good
       answer, before the init request, print `::add-mask::<access token>` and a newline to
       stdout, so GitHub masks the derived token in the job log.
    2. Init: POST `YOUTUBE_UPLOAD_ENDPOINT` with the query `uploadType=resumable` and
       `part=snippet,status`, timeout `YOUTUBE_CONNECT_TIMEOUT_S`, headers
       `Authorization: Bearer <access token>`, `Content-Type: application/json; charset=UTF-8`,
       `X-Upload-Content-Length: <file size>` and `X-Upload-Content-Type: video/mp4`, and the body
       {"snippet": {"title": title, "description": description + YOUTUBE_CREDIT_SEPARATOR +
       YOUTUBE_CREDIT_LINE, "tags": tags, "categoryId": YOUTUBE_CATEGORY_ID},
        "status": {"privacyStatus": YOUTUBE_PRIVACY, "selfDeclaredMadeForKids":
       YOUTUBE_MADE_FOR_KIDS, "containsSyntheticMedia": YOUTUBE_SYNTHETIC_MEDIA}}.
       The `Location` header is the session URL: it must be https on exactly
       `YOUTUBE_UPLOAD_HOST`, with no user info and no port other than 443.
    3. Upload: PUT the file's bytes to the session URL, timeout `YOUTUBE_UPLOAD_TIMEOUT_S`, headers
       `Authorization: Bearer <access token>` and `Content-Type: video/mp4`. The JSON answer's `id`
       must match `^[A-Za-z0-9_-]{11}$`.

    Any failure in steps 1 and 2 (HTTP error, any 3xx, OSError, http.client.HTTPException, a
    timeout, a bad answer, a refused session URL) raises UploadError(sent=False); any failure in
    step 3 raises UploadError(sent=True). Messages give the step and HTTP status and at most a short
    body excerpt, with the client secret, refresh token and access token redacted before clipping.
    They name the session host only, never the session URL: its `upload_id` lets anyone holding it
    write to the session. Log records hold status codes and the video id only.
    """
    problems = validate.problems(script)
    if problems:
        raise UploadError("script is not valid: " + "; ".join(problems), sent=False)
    size = _checked_size(video_path)
    credentials = _credentials()
    stored = list(credentials.values())
    access = _refresh_access_token(credentials, stored)
    stored.append(access)
    session_url = _start_session(script, size, access, stored)
    return _send_video(video_path, session_url, access, [*stored, session_url])


def _checked_size(video_path: Path) -> int:
    try:
        size = video_path.stat().st_size
    except OSError as error:
        raise UploadError(f"video file is not readable: {type(error).__name__}", sent=False) from None
    if not constants.MIN_FILE_BYTES <= size <= constants.MAX_FILE_BYTES:
        raise UploadError(
            f"video is {size} bytes, outside {constants.MIN_FILE_BYTES} to {constants.MAX_FILE_BYTES}",
            sent=False,
        )
    return size


def _credentials() -> dict[str, str]:
    values = {name: os.environ.get(name, "").strip() for name in _CREDENTIAL_NAMES}
    for name, value in values.items():
        if not value:
            raise UploadError(f"{name} is not set", sent=False)
    return values


def _refresh_access_token(credentials: dict[str, str], stored: list[str]) -> str:
    form = urllib.parse.urlencode({
        "client_id": credentials["YOUTUBE_CLIENT_ID"],
        "client_secret": credentials["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": credentials["YOUTUBE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    request = urllib.request.Request(
        constants.YOUTUBE_TOKEN_ENDPOINT,
        data=form.encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    body, _ = _call(request, constants.YOUTUBE_CONNECT_TIMEOUT_S, "token refresh", stored, sent=False)
    answer = _parse_object(body, "token refresh", sent=False)
    access = answer.get("access_token")
    scope = answer.get("scope")
    if not isinstance(access, str) or not access:
        raise UploadError("token refresh answer has no access token", sent=False)
    if not isinstance(scope, str) or set(scope.split()) != {constants.YOUTUBE_SCOPE}:
        raise UploadError("token refresh answer has a scope other than the upload scope", sent=False)
    # GitHub masks the derived token in the job log only when told to.
    print(f"::add-mask::{access}", flush=True)
    return access


def _start_session(script: Script, size: int, access: str, stored: list[str]) -> str:
    metadata = {
        "snippet": {
            "title": script.title,
            "description": script.description + constants.YOUTUBE_CREDIT_SEPARATOR
            + constants.YOUTUBE_CREDIT_LINE,
            "tags": script.tags,
            "categoryId": constants.YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": constants.YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": constants.YOUTUBE_MADE_FOR_KIDS,
            "containsSyntheticMedia": constants.YOUTUBE_SYNTHETIC_MEDIA,
        },
    }
    query = urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status"}, safe=",")
    request = urllib.request.Request(
        f"{constants.YOUTUBE_UPLOAD_ENDPOINT}?{query}",
        data=json.dumps(metadata).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": "video/mp4",
        },
        method="POST",
    )
    _, location = _call(request, constants.YOUTUBE_CONNECT_TIMEOUT_S, "upload init", stored, sent=False)
    if not location or not _is_allowed_session(location):
        raise UploadError(
            f"upload init gave no session URL on https://{constants.YOUTUBE_UPLOAD_HOST}", sent=False
        )
    return location


def _is_allowed_session(url: str) -> bool:
    try:
        split = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    # The whole netloc is compared, so user info and other ports fail without parsing them out.
    allowed = (constants.YOUTUBE_UPLOAD_HOST, f"{constants.YOUTUBE_UPLOAD_HOST}:443")
    return split.scheme == "https" and split.netloc.lower() in allowed


def _send_video(video_path: Path, session_url: str, access: str, stored: list[str]) -> str:
    try:
        data = video_path.read_bytes()
    except OSError as error:
        raise UploadError(f"video file is not readable: {type(error).__name__}", sent=False) from None
    request = urllib.request.Request(
        session_url,
        data=data,
        headers={"Authorization": f"Bearer {access}", "Content-Type": "video/mp4"},
        method="PUT",
    )
    body, _ = _call(request, constants.YOUTUBE_UPLOAD_TIMEOUT_S, "video upload", stored, sent=True)
    video_id = _parse_object(body, "video upload", sent=True).get("id")
    if not isinstance(video_id, str) or not _VIDEO_ID.fullmatch(video_id):
        raise UploadError("video upload answer has no valid video id", sent=True)
    _LOG.info("uploaded video %s", video_id)
    return video_id


def _call(
    request: urllib.request.Request, timeout: float, step: str, stored: list[str], *, sent: bool
) -> tuple[bytes, str | None]:
    """Send one request; return the body and the Location header. Every failure is an UploadError."""
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            body: bytes = response.read()
            location: str | None = response.headers.get("Location")
    except urllib.error.HTTPError as error:
        _LOG.info("%s: HTTP %s", step, error.code)
        raise UploadError(_http_message(error, step, stored), sent=sent) from None
    except urllib.error.URLError as error:
        raise UploadError(f"{step} failed: {type(error.reason).__name__}", sent=sent) from None
    except (OSError, http.client.HTTPException) as error:
        raise UploadError(f"{step} failed: {type(error).__name__}", sent=sent) from None
    _LOG.info("%s: HTTP 200", step)
    return body, location


def _http_message(error: urllib.error.HTTPError, step: str, stored: list[str]) -> str:
    message = f"{step} failed: HTTP {error.code}"
    try:
        text = error.read().decode("utf-8", errors="replace")
    except (OSError, http.client.HTTPException):
        return message
    if "invalid_grant" in text:
        message += " (the refresh token was revoked or expired, make it again)"
    # Redact before cutting, so a secret split by the cut cannot survive as a prefix.
    for secret in stored:
        text = text.replace(secret, "[redacted]")
    return f"{message}: {text[:_EXCERPT_CHARS]}"


def _parse_object(body: bytes, step: str, *, sent: bool) -> dict[str, Any]:
    try:
        answer = json.loads(body)
    except (ValueError, RecursionError):
        raise UploadError(f"{step} answer is not JSON", sent=sent) from None
    if not isinstance(answer, dict):
        raise UploadError(f"{step} answer is not a JSON object", sent=sent)
    return answer


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m pipeline.publish.youtube SCRIPT_JSON VIDEO_MP4 OUTPUT_FILE`.

    Parses SCRIPT_JSON with `Script.model_validate_json` (a failure counts as sent=False) and calls
    `upload`. Appends exactly one line to OUTPUT_FILE, which is `$GITHUB_OUTPUT` in the workflow:
    `video_id=<id>` and returns 0, or `sent=true` / `sent=false` and returns 1 with the error on
    stderr.
    """
    script_path, video_path, output_path = argv if argv is not None else sys.argv[1:]
    try:
        try:
            script = Script.model_validate_json(Path(script_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise UploadError(f"script is not readable: {type(error).__name__}", sent=False) from None
        line = f"video_id={upload(script, Path(video_path))}"
        code = 0
    except UploadError as error:
        print(error, file=sys.stderr)
        line = f"sent={str(error.sent).lower()}"
        code = 1
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(line + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
