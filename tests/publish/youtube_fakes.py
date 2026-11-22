"""Hand-built YouTube API answers (no live call: no token exists yet, plan Phase 0). The shapes
(the OAuth refresh-token answer with `access_token` and `scope`, the resumable upload `Location`
header, the `videos` resource) are written from the documented API as recalled, not copied from
the docs in this session. The owner's first live run (R17) is their first real check.

Like tests/script/gemini_fakes.py, but each answer also carries HTTP headers, since the init step
reads `Location`."""

import email.message
import io
import json
import urllib.error
import urllib.request
from typing import Any

ACCESS = "ya29.FAKE-access-token-0123456789abcdefghij"
SESSION = ("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable"
           "&upload_id=xa298sd_f&part=snippet,status")
VIDEO_ID = "dQw4w9WgXcQ"


def headers(values: dict[str, str]) -> email.message.Message:
    message = email.message.Message()
    for name, value in values.items():
        message[name] = value
    return message


class Answer:
    """One HTTP answer: status, headers and a body. Works as what OpenerDirector.open returns."""

    def __init__(self, body: Any = b"", status: int = 200, header: dict[str, str] | None = None) -> None:
        self.status = status
        self.code = status
        self.headers = headers(header or {})
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

    def read(self, *args: Any) -> bytes:
        return self._body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> "Answer":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def token(scope: str = "https://www.googleapis.com/auth/youtube.upload", **overrides: Any) -> Answer:
    body = {"access_token": ACCESS, "expires_in": 3599, "scope": scope, "token_type": "Bearer"}
    body.update(overrides)
    return Answer({k: v for k, v in body.items() if v is not None})


def session(location: str | None = SESSION) -> Answer:
    return Answer(b"", header={"Location": location} if location is not None else {})


def video(video_id: Any = VIDEO_ID) -> Answer:
    return Answer({"kind": "youtube#video", "etag": "fake-etag", "id": video_id,
                   "status": {"uploadStatus": "uploaded", "privacyStatus": "public"}})


def http_error(code: int, body: str = '{"error": {"code": 0, "message": "fake"}}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://www.googleapis.com/", code, "fake error", headers({}),
                                  io.BytesIO(body.encode("utf-8")))


class FakeOpen:
    """Replaces urllib.request.OpenerDirector.open (set on the class, so it is called without the
    opener). Each call takes the next outcome: an Answer, or an exception to raise. Records every
    request and its timeout."""

    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[Any] = []

    def __call__(self, request: urllib.request.Request, *args: Any, **kwargs: Any) -> Answer:
        self.requests.append(request)
        self.timeouts.append(kwargs.get("timeout", args[1] if len(args) > 1 else None))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        answer: Answer = outcome
        return answer


def header_map(request: urllib.request.Request) -> dict[str, str]:
    return {name.lower(): value for name, value in request.header_items()}
