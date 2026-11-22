"""The only module that talks to YouTube (task p4-youtube, PRD R15). Standard library only.

YouTube Data API v3 `videos.insert` as a resumable upload, read 2026-11-21. Contract written by
p4-contracts; p4-youtube implements it.
"""

from pathlib import Path

from pipeline.schema import Script


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
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """CLI: `python -m pipeline.publish.youtube SCRIPT_JSON VIDEO_MP4 OUTPUT_FILE`.

    Parses SCRIPT_JSON with `Script.model_validate_json` (a failure counts as sent=False) and calls
    `upload`. Appends exactly one line to OUTPUT_FILE, which is `$GITHUB_OUTPUT` in the workflow:
    `video_id=<id>` and returns 0, or `sent=true` / `sent=false` and returns 1 with the error on
    stderr.
    """
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
