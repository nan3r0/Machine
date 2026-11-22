"""R15: the YouTube upload client (task p4-youtube, contract in pipeline/publish/youtube.py).

No network: a fake OpenerDirector.open answers (tests/publish/youtube_fakes.py), except the
redirect tests, which use two HTTP servers on 127.0.0.1 because a fake opener would skip the
redirect handling under test. Expected values come from the contract and the plan, never from the
code under test.
"""

import http.server
import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.publish import youtube
from pipeline.publish.youtube import UploadError
from pipeline.schema import Script
from tests.publish.youtube_fakes import (
    ACCESS,
    SESSION,
    VIDEO_ID,
    Answer,
    FakeOpen,
    header_map,
    http_error,
    session,
    token,
    video,
)
from tests.script.scripts import make_script

CLIENT_ID = "1234567890-fakeclient.apps.googleusercontent.com"
CLIENT_SECRET = "GOCSPX-FAKE-client-secret-0123456789"
REFRESH = "1//0FAKE-refresh-token-abcdefghijklmnop"
SECRETS = (CLIENT_SECRET, REFRESH, ACCESS)
UPLOAD_ID = "xa298sd_f"
ENV = {"YOUTUBE_CLIENT_ID": CLIENT_ID, "YOUTUBE_CLIENT_SECRET": CLIENT_SECRET,
       "YOUTUBE_REFRESH_TOKEN": REFRESH}
PROXY_VARS = ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "no_proxy", "NO_PROXY"]


@pytest.fixture(autouse=True)
def credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    for name in PROXY_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mp4(tmp_path: Path) -> Path:
    path = tmp_path / "final.mp4"
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x01" * constants.MIN_FILE_BYTES)
    return path


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeOpen:
    fake = FakeOpen(*outcomes)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    return fake


def script() -> Script:
    return make_script(id="the-bloop")


def failure(monkeypatch: pytest.MonkeyPatch, mp4: Path, *outcomes: Any) -> tuple[UploadError, FakeOpen]:
    fake = install(monkeypatch, *outcomes)
    with pytest.raises(UploadError) as caught:
        youtube.upload(script(), mp4)
    return caught.value, fake


def test_upload_sends_the_three_requests(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    fake = install(monkeypatch, token(), session(), video())
    assert youtube.upload(script(), mp4) == VIDEO_ID
    refresh, init, put = fake.requests
    assert refresh.full_url == constants.YOUTUBE_TOKEN_ENDPOINT and refresh.get_method() == "POST"
    assert header_map(refresh)["content-type"] == "application/x-www-form-urlencoded"
    assert isinstance(refresh.data, bytes)
    assert dict(urllib.parse.parse_qsl(refresh.data.decode("ascii"), strict_parsing=True)) == {
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "refresh_token": REFRESH,
        "grant_type": "refresh_token"}
    split = urllib.parse.urlsplit(init.full_url)
    assert f"{split.scheme}://{split.netloc}{split.path}" == constants.YOUTUBE_UPLOAD_ENDPOINT
    query = urllib.parse.parse_qs(split.query, strict_parsing=True)
    assert query["uploadType"] == ["resumable"]
    # The exact part list is pinned in test_youtube_placement.py.
    assert {"snippet", "status"} <= set(",".join(query["part"]).split(","))
    assert init.get_method() == "POST"
    sent = header_map(init)
    assert sent["authorization"] == f"Bearer {ACCESS}"
    assert sent["content-type"] == "application/json; charset=UTF-8"
    assert sent["x-upload-content-length"] == str(mp4.stat().st_size)
    assert sent["x-upload-content-type"] == "video/mp4"
    assert put.full_url == SESSION and put.get_method() == "PUT"
    assert header_map(put)["authorization"] == f"Bearer {ACCESS}"
    assert header_map(put)["content-type"] == "video/mp4"
    assert put.data == mp4.read_bytes()
    assert fake.timeouts == [constants.YOUTUBE_CONNECT_TIMEOUT_S, constants.YOUTUBE_CONNECT_TIMEOUT_S,
                             constants.YOUTUBE_UPLOAD_TIMEOUT_S]


def test_metadata_comes_from_the_script_plus_the_fixed_flags(monkeypatch: pytest.MonkeyPatch,
                                                             mp4: Path) -> None:
    fake = install(monkeypatch, token(), session(), video())
    youtube.upload(script(), mp4)
    init = fake.requests[1]
    assert isinstance(init.data, bytes)
    expected = script()
    body = json.loads(init.data)
    # The exact whole body is pinned in test_youtube_placement.py.
    assert body["snippet"] == {"title": expected.title,
                               "description": f"{expected.description}\n\n{constants.YOUTUBE_CREDIT_LINE}",
                               "tags": expected.tags, "categoryId": "27"}
    assert body["status"] == {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                              "containsSyntheticMedia": True}


def test_flags_are_read_from_constants_at_call_time(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    monkeypatch.setattr(constants, "YOUTUBE_SYNTHETIC_MEDIA", False)
    monkeypatch.setattr(constants, "YOUTUBE_CATEGORY_ID", "22")
    fake = install(monkeypatch, token(), session(), video())
    youtube.upload(script(), mp4)
    assert isinstance(fake.requests[1].data, bytes)
    body = json.loads(fake.requests[1].data)
    assert body["status"]["containsSyntheticMedia"] is False and body["snippet"]["categoryId"] == "22"


@pytest.mark.parametrize("name", sorted(ENV))
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_credential_fails_before_any_request(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                     name: str, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    error, fake = failure(monkeypatch, mp4)
    assert error.sent is False and name in str(error)
    assert fake.requests == []


def test_invalid_script_fails_before_any_request(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    fake = install(monkeypatch)
    with pytest.raises(UploadError) as caught:
        youtube.upload(make_script(title="See example.com for the answer"), mp4)
    assert caught.value.sent is False and "title" in str(caught.value)
    assert fake.requests == []


@pytest.mark.parametrize("case", ["missing", "too-small", "too-big"])
def test_bad_video_file_fails_before_any_request(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                 case: str) -> None:
    if case == "missing":
        mp4.unlink()
    elif case == "too-small":
        mp4.write_bytes(b"\x01" * (constants.MIN_FILE_BYTES - 1))
    else:
        monkeypatch.setattr(constants, "MAX_FILE_BYTES", mp4.stat().st_size - 1)
    error, fake = failure(monkeypatch, mp4)
    assert error.sent is False
    assert fake.requests == []


def test_size_bounds_are_inclusive(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    mp4.write_bytes(b"\x01" * constants.MIN_FILE_BYTES)
    monkeypatch.setattr(constants, "MAX_FILE_BYTES", constants.MIN_FILE_BYTES)
    install(monkeypatch, token(), session(), video())
    assert youtube.upload(script(), mp4) == VIDEO_ID


def test_revoked_refresh_token_says_so(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    body = '{"error": "invalid_grant", "error_description": "Token has been expired or revoked."}'
    error, fake = failure(monkeypatch, mp4, http_error(400, body))
    assert error.sent is False and len(fake.requests) == 1
    assert "refresh token" in str(error).lower()


TOKEN_FAILURES = [
    pytest.param(partial(http_error, 401), id="http-401"),
    pytest.param(partial(http_error, 500), id="http-500"),
    pytest.param(partial(http_error, 302), id="http-302"),
    pytest.param(TimeoutError(), id="timeout"),
    pytest.param(urllib.error.URLError(TimeoutError()), id="url-timeout"),
    pytest.param(urllib.error.URLError(ConnectionRefusedError()), id="url-error"),
    pytest.param(ConnectionResetError(), id="os-error"),
    pytest.param(Answer(b"not json"), id="not-json"),
    pytest.param(Answer(b"[]"), id="not-an-object"),
    pytest.param(token(access_token=None), id="no-access-token"),
    pytest.param(token(access_token=""), id="blank-access-token"),
    pytest.param(token(access_token=7), id="access-token-not-a-string"),
    pytest.param(token(scope=None), id="no-scope"),
    pytest.param(token(scope="https://www.googleapis.com/auth/youtube"), id="other-scope"),
    pytest.param(token(scope="https://www.googleapis.com/auth/youtube.upload "
                             "https://www.googleapis.com/auth/youtube"), id="broader-scope"),
]


@pytest.mark.parametrize("outcome", TOKEN_FAILURES)
def test_token_failure_sends_nothing(monkeypatch: pytest.MonkeyPatch, mp4: Path, outcome: Any) -> None:
    error, fake = failure(monkeypatch, mp4, outcome)
    assert error.sent is False
    assert len(fake.requests) == 1, "no request follows a failed token refresh"


INIT_FAILURES = [
    pytest.param(partial(http_error, 400), id="http-400"),
    pytest.param(partial(http_error, 403), id="http-403-quota"),
    pytest.param(partial(http_error, 503), id="http-503"),
    pytest.param(partial(http_error, 308), id="http-308"),
    pytest.param(TimeoutError(), id="timeout"),
    pytest.param(urllib.error.URLError(OSError()), id="url-error"),
    pytest.param(session(None), id="no-location"),
    pytest.param(session(""), id="empty-location"),
    pytest.param(session(SESSION.replace("https://", "http://")), id="http-session"),
    pytest.param(session("https://evil.example/upload?upload_id=x"), id="other-host"),
    pytest.param(session("https://www.googleapis.com.evil.example/upload"), id="suffix-host"),
    pytest.param(session("https://www.googleapis.com@evil.example/upload"), id="userinfo-host"),
    pytest.param(session("https://user@www.googleapis.com/upload"), id="userinfo"),
    pytest.param(session("https://www.googleapis.com:8443/upload"), id="other-port"),
    pytest.param(session("https://googleapis.com/upload"), id="parent-domain"),
    pytest.param(session("/upload/youtube/v3/videos?upload_id=x"), id="relative"),
]


@pytest.mark.parametrize("outcome", INIT_FAILURES)
def test_init_failure_sends_nothing(monkeypatch: pytest.MonkeyPatch, mp4: Path, outcome: Any) -> None:
    error, fake = failure(monkeypatch, mp4, token(), outcome)
    assert error.sent is False
    assert len(fake.requests) == 2, "the video bytes, and the token with them, never left"


PUT_FAILURES = [
    pytest.param(partial(http_error, 400), id="http-400"),
    pytest.param(partial(http_error, 500), id="http-500"),
    pytest.param(partial(http_error, 301), id="http-301"),
    pytest.param(TimeoutError(), id="timeout"),
    pytest.param(urllib.error.URLError(TimeoutError()), id="url-timeout"),
    pytest.param(ConnectionResetError(), id="os-error"),
    pytest.param(Answer(b"<html>"), id="not-json"),
    pytest.param(video(None), id="no-id"),
    pytest.param(video("dQw4w9WgXc"), id="id-too-short"),
    pytest.param(video("dQw4w9WgX/Q"), id="id-bad-char"),
    pytest.param(video(12345678901), id="id-not-a-string"),
]


@pytest.mark.parametrize("outcome", PUT_FAILURES)
def test_failure_after_the_bytes_left_says_sent(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                outcome: Any) -> None:
    error, fake = failure(monkeypatch, mp4, token(), session(), outcome)
    assert error.sent is True
    assert len(fake.requests) == 3, "no retry inside a run"


def test_no_secret_in_errors_or_logs(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                     caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    echo = " ".join(SECRETS)
    messages = []
    # Before the refresh answers, the client cannot know the access token, so that step echoes the
    # two stored secrets only.
    for outcomes in ([http_error(400, f"{CLIENT_SECRET} {REFRESH}")], [token(), http_error(401, echo)],
                     [token(), session(), http_error(500, echo)]):
        error, _ = failure(monkeypatch, mp4, *outcomes)
        messages.append(str(error))
    install(monkeypatch, token(), session(), video())
    youtube.upload(script(), mp4)
    assert UPLOAD_ID in SESSION
    for text in [*messages, caplog.text]:
        for secret in (*SECRETS, UPLOAD_ID):
            assert secret not in text


def test_access_token_is_masked_before_init(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    failure(monkeypatch, mp4, token(), partial(http_error, 500))
    assert f"::add-mask::{ACCESS}" in capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("offset", range(0, 400, 9))
def test_redacted_before_clipping(monkeypatch: pytest.MonkeyPatch, mp4: Path, offset: int) -> None:
    """A secret cut in half by the excerpt limit must not survive as a prefix."""
    error, _ = failure(monkeypatch, mp4, token(), session(), http_error(500, "x" * offset + CLIENT_SECRET))
    assert CLIENT_SECRET[:12] not in str(error)


class Server:
    """Answers every POST and PUT with `status`, an optional Location header and a JSON body, and
    records the headers of each request it receives."""

    def __init__(self, status: int, location: str = "", body: Any = None) -> None:
        self.hits: list[dict[str, str]] = []
        hits = self.hits
        payload = json.dumps(body if body is not None else {}).encode("utf-8")

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                hits.append({name.lower(): value for name, value in self.headers.items()})
                self.send_response(status)
                if location:
                    self.send_header("Location", location)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_PUT = do_GET = do_POST

            def log_message(self, *args: Any) -> None:
                return None

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/endpoint"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def servers() -> Iterator[list[Server]]:
    started: list[Server] = []
    yield started
    for server in started:
        server.close()


@pytest.mark.parametrize("step", ["token", "init"])
@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_redirect_is_refused(monkeypatch: pytest.MonkeyPatch, mp4: Path, servers: list[Server],
                             step: str, code: int) -> None:
    target = Server(200, body={"access_token": ACCESS, "scope": constants.YOUTUBE_SCOPE, "id": VIDEO_ID})
    servers.append(target)
    redirect = Server(code, location=target.url)
    servers.append(redirect)
    if step == "token":
        monkeypatch.setattr(constants, "YOUTUBE_TOKEN_ENDPOINT", redirect.url)
    else:
        good = Server(200, body={"access_token": ACCESS, "scope": constants.YOUTUBE_SCOPE})
        servers.append(good)
        monkeypatch.setattr(constants, "YOUTUBE_TOKEN_ENDPOINT", good.url)
        monkeypatch.setattr(constants, "YOUTUBE_UPLOAD_ENDPOINT", redirect.url)
    with pytest.raises(UploadError) as caught:
        youtube.upload(script(), mp4)
    assert caught.value.sent is False
    assert len(redirect.hits) == 1
    assert target.hits == [], "a request, and with it a secret or the token, reached the redirect target"


def write_script(tmp_path: Path) -> Path:
    path = tmp_path / "the-bloop.json"
    path.write_text(script().model_dump_json(), encoding="utf-8")
    return path


def test_cli_appends_the_video_id(monkeypatch: pytest.MonkeyPatch, mp4: Path, tmp_path: Path) -> None:
    output = tmp_path / "github_output"
    output.write_text("earlier=1\n", encoding="utf-8")
    install(monkeypatch, token(), session(), video())
    assert youtube.main([str(write_script(tmp_path)), str(mp4), str(output)]) == 0
    assert output.read_text(encoding="utf-8") == f"earlier=1\nvideo_id={VIDEO_ID}\n"


@pytest.mark.parametrize(("outcomes", "line"), [
    pytest.param([partial(http_error, 500)], "sent=false", id="token-failed"),
    pytest.param([token(), session(), partial(http_error, 500)], "sent=true", id="put-failed"),
])
def test_cli_reports_sent_and_fails(monkeypatch: pytest.MonkeyPatch, mp4: Path, tmp_path: Path,
                                    capsys: pytest.CaptureFixture[str], outcomes: list[Any],
                                    line: str) -> None:
    output = tmp_path / "github_output"
    install(monkeypatch, *outcomes)
    assert youtube.main([str(write_script(tmp_path)), str(mp4), str(output)]) == 1
    assert output.read_text(encoding="utf-8") == f"{line}\n"
    assert capsys.readouterr().err.strip(), "the reason goes to stderr"


def test_cli_unreadable_script_sends_nothing(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                             tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"id": "bad"}', encoding="utf-8")
    output = tmp_path / "github_output"
    fake = install(monkeypatch)
    assert youtube.main([str(bad), str(mp4), str(output)]) == 1
    assert output.read_text(encoding="utf-8") == "sent=false\n"
    assert fake.requests == []


def test_acceptance(monkeypatch: pytest.MonkeyPatch, mp4: Path, tmp_path: Path) -> None:
    """R15.1 to R15.4: token refresh, resumable init with the script's metadata, the credit line and
    the three flags, then one PUT; the session URL must be https on the allowed host; failures say
    whether bytes were sent; the CLI writes one output line."""
    test_upload_sends_the_three_requests(monkeypatch, mp4)
    test_metadata_comes_from_the_script_plus_the_fixed_flags(monkeypatch, mp4)
    error, _ = failure(monkeypatch, mp4, token(), session("https://evil.example/upload"))
    assert error.sent is False
    error, _ = failure(monkeypatch, mp4, token(), session(), http_error(500))
    assert error.sent is True
    test_cli_appends_the_video_id(monkeypatch, mp4, tmp_path)
