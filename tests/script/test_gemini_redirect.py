"""CSO P2-5: the Gemini client never follows a redirect, so the key header cannot reach another
host (task p2-gemini-redirects).

Two real HTTP servers on 127.0.0.1 stand in for the endpoint and for the host a redirect points
at, because a fake opener would skip the redirect handling under test. Nothing leaves the machine.
"""

import http.server
import json
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest

from pipeline import constants
from pipeline.script import gemini
from pipeline.script.gemini import GeminiError
from tests.script.gemini_fakes import as_json, interaction

KEY = "AIzaFAKE-redirect-key-0123456789abcdef"
SCHEMA = {"type": "object", "properties": {"narration": {"type": "string"}}, "required": ["narration"]}
ANSWER = {"narration": "The sound was ice."}
PROXY_VARS = ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]


class Server:
    """Answers every GET and POST with `status`, an optional Location header and a completed
    interaction body, and records the headers of each request it receives."""

    def __init__(self, status: int, location: str = "") -> None:
        self.hits: list[dict[str, str]] = []
        hits = self.hits

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                hits.append({name.lower(): value for name, value in self.headers.items()})
                body = json.dumps(interaction(as_json(ANSWER))).encode("utf-8")
                self.send_response(status)
                if location:
                    self.send_header("Location", location)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST

            def log_message(self, *args: Any) -> None:
                return None

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1beta/interactions"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    calls: list[float] = []
    monkeypatch.setattr(time, "sleep", calls.append)
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    for name in PROXY_VARS:
        monkeypatch.delenv(name, raising=False)
    return calls


@pytest.fixture
def target() -> Iterator[Server]:
    server = Server(200)
    yield server
    server.close()


def call(monkeypatch: pytest.MonkeyPatch, endpoint: str) -> dict[str, Any]:
    monkeypatch.setattr(constants, "GEMINI_ENDPOINT", endpoint)
    return gemini.generate_json(constants.WRITER_MODEL, "Write one line.", SCHEMA)


def assert_redirect_refused(monkeypatch: pytest.MonkeyPatch, sleeps: list[float], target: Server,
                            code: int) -> None:
    redirect = Server(code, location=target.url)
    try:
        with pytest.raises(GeminiError) as caught:
            call(monkeypatch, redirect.url)
    finally:
        redirect.close()
    assert len(redirect.hits) == 1, "a 3xx is not retried"
    assert target.hits == [], "the request, and with it the key header, reached the redirect target"
    assert sleeps == []
    assert str(code) in str(caught.value)
    assert KEY not in str(caught.value)


def assert_direct_call_works(monkeypatch: pytest.MonkeyPatch, target: Server) -> None:
    """Control: the servers work and the client still talks to a plain endpoint."""
    assert call(monkeypatch, target.url) == ANSWER
    assert target.hits[-1]["x-goog-api-key"] == KEY


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_redirect_is_refused(code: int, monkeypatch: pytest.MonkeyPatch, sleeps: list[float],
                             target: Server) -> None:
    assert_redirect_refused(monkeypatch, sleeps, target, code)


def test_direct_endpoint_still_works(monkeypatch: pytest.MonkeyPatch, sleeps: list[float],
                                     target: Server) -> None:
    assert_direct_call_works(monkeypatch, target)


def test_acceptance(monkeypatch: pytest.MonkeyPatch, sleeps: list[float], target: Server) -> None:
    """A 302 to another host raises GeminiError naming the status, sends nothing to that host and is
    not retried; a plain endpoint still answers."""
    assert_redirect_refused(monkeypatch, sleeps, target, 302)
    assert_direct_call_works(monkeypatch, target)
