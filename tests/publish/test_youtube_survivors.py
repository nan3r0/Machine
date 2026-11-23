"""R15: tests for the YouTube client's mutation survivors (task p4b-youtube-survivors, QA lead ranks
1, 2 and 4 to 9 in .harness/handoffs/p4-qa-lead.md).

No network: a fake OpenerDirector.open answers (tests/publish/youtube_fakes.py), except the PUT
redirect test, which sends the PUT through the real opener to HTTP servers on 127.0.0.1. Expected
values come from the contract in pipeline/publish/youtube.py, the QA lead's list and literals,
never from the code under test (lessons.md 2026-11-16).
"""

import http.client
import http.server
import io
import json
import logging
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

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
    headers,
    http_error,
    session,
    token,
    video,
)
from tests.script.scripts import make_script

CLIENT_ID = "1234567890-fakeclient.apps.googleusercontent.com"
CLIENT_VALUE = "FAKE-client-value-0123456789"
REFRESH = "1//0FAKE-refresh-token-abcdefghijklmnop"
UPLOAD_ID = "xa298sd_f"
ENV = {"YOUTUBE_CLIENT_ID": CLIENT_ID, "YOUTUBE_CLIENT_SECRET": CLIENT_VALUE,
       "YOUTUBE_REFRESH_TOKEN": REFRESH}
PROXY_VARS = ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "no_proxy", "NO_PROXY"]
STEPS = ("token refresh", "upload init", "video upload")
LOGGER = "pipeline.publish.youtube"
# A session URL that passes the host check but carries no upload_id.
SESSION_WITHOUT_ID = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable"


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


def failure(monkeypatch: pytest.MonkeyPatch, mp4: Path, *outcomes: Any,
            the_script: Script | None = None) -> tuple[UploadError, FakeOpen]:
    fake = install(monkeypatch, *outcomes)
    with pytest.raises(UploadError) as caught:
        youtube.upload(the_script or script(), mp4)
    return caught.value, fake


def error_with_body(code: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://www.googleapis.com/", code, "fake error", headers({}),
                                  io.BytesIO(body))


class UnreadableBody:
    """An error body whose read fails, as a connection dropped mid-body does."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def read(self, *args: Any) -> bytes:
        raise self.error

    def close(self) -> None:
        return None


def before(step: str) -> list[Any]:
    """The good answers that come before `step`."""
    return [token(), session()][:STEPS.index(step)]


# Rank 1: the session URL and its upload_id are secrets at the PUT.

SESSION_ECHOES = [
    pytest.param(SESSION, id="session-url"),
    pytest.param(UPLOAD_ID, id="upload-id"),
    pytest.param(f"upload_id={UPLOAD_ID}&part=snippet", id="upload-id-in-query"),
    pytest.param(urllib.parse.quote(SESSION, safe=""), id="session-url-quoted"),
    pytest.param(json.dumps(SESSION)[1:-1], id="session-url-json-escaped"),
]


@pytest.mark.parametrize("echo", SESSION_ECHOES)
def test_session_url_and_upload_id_are_redacted_at_the_put(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                           echo: str) -> None:
    error, fake = failure(monkeypatch, mp4, token(), session(), http_error(400, f"echo {echo} end"))
    assert error.sent is True and len(fake.requests) == 3
    text = str(error)
    assert UPLOAD_ID not in text
    assert SESSION not in text
    assert urllib.parse.quote(SESSION, safe="") not in text
    assert "[redacted]" in text


def test_all_session_forms_at_once_are_redacted(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    echo = " ".join(param.values[0] for param in SESSION_ECHOES)
    error, _ = failure(monkeypatch, mp4, token(), session(), http_error(500, echo))
    assert error.sent is True
    assert UPLOAD_ID not in str(error) and "[redacted]" in str(error)


def test_session_url_without_upload_id_uploads(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    fake = install(monkeypatch, token(), session(SESSION_WITHOUT_ID), video())
    assert youtube.upload(script(), mp4) == VIDEO_ID
    assert fake.requests[2].full_url == SESSION_WITHOUT_ID
    assert fake.requests[2].get_method() == "PUT"


def test_session_url_without_upload_id_still_redacted_on_failure(monkeypatch: pytest.MonkeyPatch,
                                                                 mp4: Path) -> None:
    error, _ = failure(monkeypatch, mp4, token(), session(SESSION_WITHOUT_ID),
                       http_error(500, f"bad {SESSION_WITHOUT_ID}"))
    assert error.sent is True
    assert SESSION_WITHOUT_ID not in str(error)


# Rank 2: an echoed secret may come back URL-encoded or JSON-escaped.

# A backslash, a quote and a slash, so the URL-encoded and JSON-escaped forms differ from the raw one.
ODD_VALUE = 'FAKE-odd\\value"with/slash-0123'
ODD_VALUE_QUOTED = "FAKE-odd%5Cvalue%22with%2Fslash-0123"
ODD_VALUE_JSON = 'FAKE-odd\\\\value\\"with/slash-0123'


@pytest.mark.parametrize("echo", [ODD_VALUE, ODD_VALUE_QUOTED, ODD_VALUE_JSON],
                         ids=["raw", "url-encoded", "json-escaped"])
@pytest.mark.parametrize("step", STEPS)
def test_secret_forms_are_redacted(monkeypatch: pytest.MonkeyPatch, mp4: Path, step: str,
                                   echo: str) -> None:
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", ODD_VALUE)
    error, _ = failure(monkeypatch, mp4, *before(step), http_error(400, f'{{"echo": "{echo}"}}'))
    text = str(error)
    for form in (ODD_VALUE, ODD_VALUE_QUOTED, ODD_VALUE_JSON, "odd"):
        assert form not in text
    assert "[redacted]" in text


def test_echoed_token_form_body_is_redacted(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    """The token endpoint echoes the very form body it was sent."""
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", ODD_VALUE)
    fake = FakeOpen()

    def echo_form() -> urllib.error.HTTPError:
        data = fake.requests[0].data
        assert isinstance(data, bytes)
        return http_error(400, data.decode("ascii"))

    fake.outcomes.append(echo_form)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    with pytest.raises(UploadError) as caught:
        youtube.upload(script(), mp4)
    text = str(caught.value)
    assert caught.value.sent is False
    assert ODD_VALUE_QUOTED not in text and "odd" not in text
    assert "1%2F%2F0FAKE-refresh" not in text and "0FAKE-refresh" not in text


FORMS = {
    "raw": lambda secret: secret,
    "url-encoded": lambda secret: urllib.parse.quote(secret, safe=""),
    "json-escaped": lambda secret: json.dumps(secret)[1:-1],
}
# Printable ASCII from "!" to "~": no space, so a space filler can never form part of the secret.
SECRET_CHARS = st.characters(min_codepoint=0x21, max_codepoint=0x7E)


@settings(max_examples=200, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(secret=st.text(SECRET_CHARS, min_size=12, max_size=60), prefix=st.integers(0, 260),
       form=st.sampled_from(sorted(FORMS)))
# The raw secret sits inside its own JSON-escaped form here, offset by the doubled backslashes.
@example(secret="\\" * 12 + "x", prefix=0, form="json-escaped")
def test_property_no_secret_form_survives(monkeypatch: pytest.MonkeyPatch, mp4: Path, secret: str,
                                          prefix: int, form: str) -> None:
    """Whatever the secret, the filler length before it and the form it is echoed in, neither the
    form nor its first 12 characters reach the message. 12 is longer than "[redacted]", and the
    filler is spaces, so a correct message can never hold 12 secret characters in a row."""
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", secret)
    echoed = FORMS[form](secret)
    error, _ = failure(monkeypatch, mp4, token(), session(), http_error(500, " " * prefix + echoed))
    excerpt = str(error).split("HTTP 500", 1)[1]
    assert error.sent is True
    assert echoed[:12] not in excerpt
    assert secret[:12] not in excerpt


# Rank 4: the file is read after the token and init requests.

def test_read_failure_after_a_good_stat_sends_no_bytes(monkeypatch: pytest.MonkeyPatch,
                                                       mp4: Path) -> None:
    def refuse(self: Path) -> bytes:
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "read_bytes", refuse)
    error, fake = failure(monkeypatch, mp4, token(), session(), video())
    assert error.sent is False
    assert len(fake.requests) == 2, "the PUT never went out"
    assert "PermissionError" in str(error)
    assert str(mp4) not in str(error)


# Rank 5: crash paths.

@pytest.mark.parametrize(("step", "sent"), list(zip(STEPS, (False, False, True), strict=True)))
def test_bad_status_line_at_each_step(monkeypatch: pytest.MonkeyPatch, mp4: Path, step: str,
                                      sent: bool) -> None:
    error, fake = failure(monkeypatch, mp4, *before(step), http.client.BadStatusLine("garbage"))
    assert error.sent is sent
    assert len(fake.requests) == STEPS.index(step) + 1
    assert step in str(error) and "BadStatusLine" in str(error)


def test_incomplete_read_after_the_put_says_sent(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    error, fake = failure(monkeypatch, mp4, token(), session(), http.client.IncompleteRead(b"{"))
    assert error.sent is True and len(fake.requests) == 3
    assert "IncompleteRead" in str(error)


@pytest.mark.parametrize("read_error", [ConnectionResetError(), http.client.IncompleteRead(b"{")],
                         ids=["os-error", "incomplete-read"])
@pytest.mark.parametrize(("step", "sent"), list(zip(STEPS, (False, False, True), strict=True)))
def test_unreadable_error_body_still_gives_step_and_status(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                           step: str, sent: bool,
                                                           read_error: BaseException) -> None:
    broken = urllib.error.HTTPError("https://www.googleapis.com/", 502, "fake error", headers({}),
                                    UnreadableBody(read_error))  # type: ignore[arg-type]
    error, _ = failure(monkeypatch, mp4, *before(step), broken)
    assert error.sent is sent
    assert str(error).startswith(f"{step} failed: HTTP 502")


@pytest.mark.parametrize(("step", "sent"), list(zip(STEPS, (False, False, True), strict=True)))
def test_non_utf8_error_body(monkeypatch: pytest.MonkeyPatch, mp4: Path, step: str, sent: bool) -> None:
    body = b"\xff\xfe\x80 " + CLIENT_VALUE.encode("ascii") + b" \xc3"
    error, _ = failure(monkeypatch, mp4, *before(step), error_with_body(500, body))
    assert error.sent is sent
    assert str(error).startswith(f"{step} failed: HTTP 500")
    assert CLIENT_VALUE not in str(error) and "[redacted]" in str(error)


DEEP = b"[" * 100_000 + b"]" * 100_000


@pytest.mark.parametrize(("step", "sent"), [("token refresh", False), ("video upload", True)])
def test_deeply_nested_json_answer(monkeypatch: pytest.MonkeyPatch, mp4: Path, step: str,
                                   sent: bool) -> None:
    error, _ = failure(monkeypatch, mp4, *before(step), Answer(DEEP))
    assert error.sent is sent
    assert step in str(error)


# Rank 6: pinned messages and log records.

@pytest.mark.parametrize("code", [400, 403, 500])
@pytest.mark.parametrize("step", STEPS)
def test_http_message_names_step_and_code(monkeypatch: pytest.MonkeyPatch, mp4: Path, step: str,
                                          code: int) -> None:
    error, _ = failure(monkeypatch, mp4, *before(step), http_error(code, "body"))
    assert str(error).startswith(f"{step} failed: HTTP {code}")
    assert error.sent is (step == "video upload")


def test_excerpt_is_at_most_200_characters(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    error, _ = failure(monkeypatch, mp4, token(), session(), http_error(500, "y" * 500))
    text = str(error)
    assert text.endswith("y" * 200)
    assert "y" * 201 not in text


def test_short_body_is_kept_whole(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    error, _ = failure(monkeypatch, mp4, token(), session(), http_error(500, "quota gone"))
    assert str(error).endswith("quota gone")


@pytest.mark.parametrize("step", STEPS)
def test_invalid_grant_hint_only_with_invalid_grant(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                    step: str) -> None:
    hinted, _ = failure(monkeypatch, mp4, *before(step), http_error(400, '{"error": "invalid_grant"}'))
    plain, _ = failure(monkeypatch, mp4, *before(step), http_error(400, '{"error": "invalid_client"}'))
    assert "revoked" in str(hinted) and "refresh token" in str(hinted)
    assert "revoked" not in str(plain) and "refresh token" not in str(plain)


@pytest.mark.parametrize("step", STEPS)
@pytest.mark.parametrize(("outcome", "name"), [
    pytest.param(partial(urllib.error.URLError, ConnectionRefusedError()), "ConnectionRefusedError",
                 id="url-error"),
    pytest.param(partial(urllib.error.URLError, TimeoutError()), "TimeoutError", id="url-timeout"),
    pytest.param(ConnectionResetError, "ConnectionResetError", id="os-error"),
    pytest.param(TimeoutError, "TimeoutError", id="timeout"),
])
def test_network_errors_name_the_type(monkeypatch: pytest.MonkeyPatch, mp4: Path, step: str,
                                      outcome: Any, name: str) -> None:
    error, _ = failure(monkeypatch, mp4, *before(step), outcome)
    assert str(error) == f"{step} failed: {name}"


def records(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == LOGGER]


def test_log_records_of_a_good_upload(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                      caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    install(monkeypatch, token(), session(), video())
    youtube.upload(script(), mp4)
    assert records(caplog) == ["token refresh: HTTP 200", "upload init: HTTP 200",
                               "video upload: HTTP 200", f"uploaded video {VIDEO_ID}"]
    assert all(record.levelno == logging.INFO for record in caplog.records if record.name == LOGGER)


def test_log_records_of_a_failed_init(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                      caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    failure(monkeypatch, mp4, token(), http_error(403, f"{ACCESS} {CLIENT_VALUE}"))
    assert records(caplog) == ["token refresh: HTTP 200", "upload init: HTTP 403"]


# Rank 7: a redirect at the PUT, through the real opener.

class Server:
    """Answers every request with `status` and an optional Location header; records each hit."""

    def __init__(self, status: int, location: str = "") -> None:
        self.hits: list[str] = []
        hits = self.hits

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_PUT(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                hits.append(self.command)
                payload = json.dumps({"id": VIDEO_ID}).encode("utf-8")
                self.send_response(status)
                if location:
                    self.send_header("Location", location)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = do_PUT

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


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_put_redirect_is_refused(monkeypatch: pytest.MonkeyPatch, mp4: Path, servers: list[Server],
                                 code: int) -> None:
    """The token and init answers are faked; the PUT, sent to the real session URL, is re-pointed
    at a local server and goes through the real OpenerDirector.open, so the client's own redirect
    handling is what runs."""
    target = Server(200)
    servers.append(target)
    redirect = Server(code, location=target.url)
    servers.append(redirect)
    real_open = urllib.request.OpenerDirector.open
    fake = FakeOpen(token(), session())

    def open_(self: urllib.request.OpenerDirector, request: urllib.request.Request,
              *args: Any, **kwargs: Any) -> Any:
        if request.get_method() != "PUT":
            return fake(request, *args, **kwargs)
        assert request.full_url == SESSION, "the PUT goes to the session URL"
        request.full_url = redirect.url
        return real_open(self, request, *args, **kwargs)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", open_)
    with pytest.raises(UploadError) as caught:
        youtube.upload(script(), mp4)
    assert caught.value.sent is True
    assert redirect.hits == ["PUT"]
    assert target.hits == [], "the video and the token reached the redirect target"


# Rank 8: the CLI entry point reads sys.argv.

def write_script(tmp_path: Path) -> Path:
    path = tmp_path / "the-bloop.json"
    path.write_text(script().model_dump_json(), encoding="utf-8")
    return path


@pytest.mark.parametrize(("outcomes", "code", "line"), [
    pytest.param([token(), session(), video()], 0, f"video_id={VIDEO_ID}", id="uploaded"),
    pytest.param([partial(http_error, 500)], 1, "sent=false", id="token-failed"),
    pytest.param([token(), session(), partial(http_error, 500)], 1, "sent=true", id="put-failed"),
])
def test_main_reads_sys_argv(monkeypatch: pytest.MonkeyPatch, mp4: Path, tmp_path: Path,
                             outcomes: list[Any], code: int, line: str) -> None:
    output = tmp_path / "github_output"
    monkeypatch.setattr(sys, "argv", ["youtube.py", str(write_script(tmp_path)), str(mp4), str(output)])
    install(monkeypatch, *[outcome() if callable(outcome) else outcome for outcome in outcomes])
    assert youtube.main() == code
    assert output.read_text(encoding="utf-8") == f"{line}\n"


# Rank 9: host-check edges, video id edges and unicode metadata.

@pytest.mark.parametrize("location", [
    pytest.param("https://[www.googleapis.com/x", id="unclosed-bracket"),
    pytest.param("https://www.googleapis.com:80/upload?upload_id=x", id="port-80"),
    pytest.param("https://www.googleapis.com:/upload?upload_id=x", id="empty-port"),
    pytest.param("HTTP://www.googleapis.com/upload?upload_id=x", id="uppercase-http"),
])
def test_session_url_edges_refused(monkeypatch: pytest.MonkeyPatch, mp4: Path, location: str) -> None:
    error, fake = failure(monkeypatch, mp4, token(), session(location))
    assert error.sent is False and len(fake.requests) == 2


@pytest.mark.parametrize("location", [
    pytest.param("https://www.googleapis.com:443/upload/youtube/v3/videos?upload_id=x", id="port-443"),
    pytest.param("https://WWW.GOOGLEAPIS.COM/upload/youtube/v3/videos?upload_id=x", id="uppercase-host"),
])
def test_session_url_edges_allowed(monkeypatch: pytest.MonkeyPatch, mp4: Path, location: str) -> None:
    fake = install(monkeypatch, token(), session(location), video())
    assert youtube.upload(script(), mp4) == VIDEO_ID
    assert fake.requests[2].full_url == location


@pytest.mark.parametrize("video_id", [
    pytest.param(VIDEO_ID + "A", id="twelve-characters"),
    pytest.param(VIDEO_ID + "\n", id="trailing-newline"),
    pytest.param("\n" + VIDEO_ID, id="leading-newline"),
    pytest.param(VIDEO_ID[:5] + "\n" + VIDEO_ID[6:], id="inner-newline"),
    pytest.param("", id="empty"),
])
def test_bad_video_id_says_sent(monkeypatch: pytest.MonkeyPatch, mp4: Path, video_id: str) -> None:
    error, fake = failure(monkeypatch, mp4, token(), session(), video(video_id))
    assert error.sent is True and len(fake.requests) == 3


@pytest.mark.parametrize("video_id", ["a" * 11, "_-_-_-_-_-_", "Z9z9Z9z9Z9z"])
def test_every_allowed_video_id_character(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                          video_id: str) -> None:
    install(monkeypatch, token(), session(), video(video_id))
    assert youtube.upload(script(), mp4) == video_id


def test_unicode_metadata_reaches_the_init_body(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    unicode_script = make_script(id="the-bloop",
                                 title="The ocean sound nobody could explain, résolu à Zürich",
                                 description="Source: NOAA Océan Service, “Ocean Facts”.\n#mystère",
                                 tags=["mystères", "océan", "science"])
    fake = install(monkeypatch, token(), session(), video())
    assert youtube.upload(unicode_script, mp4) == VIDEO_ID
    data = fake.requests[1].data
    assert isinstance(data, bytes)
    snippet = json.loads(data.decode("utf-8"))["snippet"]
    assert snippet["title"] == "The ocean sound nobody could explain, résolu à Zürich"
    assert snippet["description"].startswith("Source: NOAA Océan Service, “Ocean Facts”.\n#mystère")
    assert snippet["tags"] == ["mystères", "océan", "science"]


def test_acceptance(monkeypatch: pytest.MonkeyPatch, mp4: Path, tmp_path: Path,
                    caplog: pytest.LogCaptureFixture) -> None:
    """QA lead ranks 1, 2 and 4 to 9: session URL and secret forms redacted, a read failure after
    the stat sends nothing, step and status in every message, exact log records, a session URL
    without upload_id uploads, the CLI reads sys.argv."""
    for param in SESSION_ECHOES:
        test_session_url_and_upload_id_are_redacted_at_the_put(monkeypatch, mp4, *param.values)
    test_session_url_without_upload_id_uploads(monkeypatch, mp4)
    for step in STEPS:
        test_secret_forms_are_redacted(monkeypatch, mp4, step, ODD_VALUE_JSON)
        test_secret_forms_are_redacted(monkeypatch, mp4, step, ODD_VALUE_QUOTED)
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", CLIENT_VALUE)
    for step in STEPS:
        test_http_message_names_step_and_code(monkeypatch, mp4, step, 500)
    caplog.clear()
    test_log_records_of_a_good_upload(monkeypatch, mp4, caplog)
    test_main_reads_sys_argv(monkeypatch, mp4, tmp_path, [token(), session(), video()], 0,
                             f"video_id={VIDEO_ID}")
    # Last, since it leaves Path.read_bytes patched for the rest of this test.
    test_read_failure_after_a_good_stat_sends_no_bytes(monkeypatch, mp4)
