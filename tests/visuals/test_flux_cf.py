"""Locked tests for pipeline/visuals/flux_cf.py (task p3c-flux-client, .harness/handoffs/p3c-plan.md).

The envelope is Cloudflare's documented REST shape; no live call is made. A fake replaces
OpenerDirector.open, so any opener the module builds is covered.
"""

import base64
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from pipeline import constants as c
from pipeline.visuals import flux_cf
from tests.script.gemini_fakes import FakeUrlopen, http_error

FAKE_KEY = "fake-bearer-value-for-tests"
ACCOUNT = "0123456789abcdef0123456789abcdef"
QUOTA_BODY = json.dumps({"success": False, "errors": [{"code": 4006, "message":
                         "you have used up your daily free allocation of 10,000 neurons"}]})


def jpeg(width: int = 1024, height: int = 1024, sof: int = 0xC0) -> bytes:
    """A minimal JPEG header: SOI, APP0, a DHT segment, the SOF, then EOI. No pixels."""
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    dht = b"\xff\xc4\x00\x05\x00\x01\x02"
    frame = (bytes([0xFF, sof]) + b"\x00\x11\x08" + height.to_bytes(2, "big")
             + width.to_bytes(2, "big") + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01")
    return b"\xff\xd8" + app0 + dht + frame + b"\xff\xda\x00\x02" + b"\x00" * 64 + b"\xff\xd9"


def envelope(image: bytes | None = None, success: bool = True) -> dict[str, Any]:
    picture = base64.b64encode(jpeg() if image is None else image).decode("ascii")
    return {"success": success, "errors": [], "messages": [], "result": {"image": picture}}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", FAKE_KEY)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT)


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []
    monkeypatch.setattr("time.sleep", waits.append)
    return waits


def install(monkeypatch: pytest.MonkeyPatch, *outcomes: Any) -> FakeUrlopen:
    fake = FakeUrlopen(*outcomes)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake)
    return fake


def failure(monkeypatch: pytest.MonkeyPatch, *outcomes: Any,
            error: type[Exception] = flux_cf.FluxError) -> tuple[str, FakeUrlopen]:
    fake = install(monkeypatch, *outcomes)
    with pytest.raises(error) as caught:
        flux_cf.generate_image("a lighthouse on a cliff at night")
    assert FAKE_KEY not in str(caught.value)
    return str(caught.value), fake


def test_request_shape(env: None, sleeps: list[float], monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, envelope())
    assert flux_cf.generate_image("a whale under dark water") == jpeg()
    (request,) = fake.requests
    assert request.full_url == c.FLUX_ENDPOINT.format(account_id=ACCOUNT)
    assert request.full_url.startswith("https://api.cloudflare.com/")
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == f"Bearer {FAKE_KEY}"
    assert FAKE_KEY not in request.full_url
    body = json.loads(request.data)  # type: ignore[arg-type]
    assert body == {"prompt": c.FLUX_STYLE_PREFIX + "a whale under dark water", "steps": c.FLUX_STEPS}
    assert fake.timeouts == [c.FLUX_TIMEOUT_S]
    assert sleeps == []


@pytest.mark.parametrize("name", ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"])
@pytest.mark.parametrize("value", [None, "  "])
def test_missing_secret_fails_before_any_request(env: None, monkeypatch: pytest.MonkeyPatch,
                                                 name: str, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    message, fake = failure(monkeypatch)
    assert name in message
    assert fake.requests == []


@pytest.mark.parametrize("account", ["0123456789ABCDEF0123456789ABCDEF", "0123456789abcdef",
                                     "0123456789abcdef0123456789abcde/", "../../zones/1234567890ab"])
def test_odd_account_id_fails_before_any_request(env: None, monkeypatch: pytest.MonkeyPatch,
                                                 account: str) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", account)
    _, fake = failure(monkeypatch)
    assert fake.requests == []


def test_prompt_limits(env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch)
    room = c.FLUX_PROMPT_MAX_CHARS - len(c.FLUX_STYLE_PREFIX)
    for prompt in ("", "   ", "x" * (room + 1)):
        with pytest.raises(flux_cf.FluxError):
            flux_cf.generate_image(prompt)
    assert fake.requests == []
    install(monkeypatch, envelope())
    assert flux_cf.generate_image("x" * room) == jpeg()


@pytest.mark.parametrize("first", [http_error(429), http_error(500), http_error(503), TimeoutError()])
def test_one_retry_after_a_transient_failure(env: None, sleeps: list[float],
                                             monkeypatch: pytest.MonkeyPatch, first: Exception) -> None:
    fake = install(monkeypatch, first, envelope())
    before = flux_cf.requests_sent
    assert flux_cf.generate_image("fog over a harbour") == jpeg()
    assert len(fake.requests) == 2
    assert flux_cf.requests_sent - before == 2
    assert sleeps == [c.FLUX_RETRY_WAIT_S]


def test_two_transient_failures_give_up(env: None, sleeps: list[float],
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    message, fake = failure(monkeypatch, http_error(503), http_error(502))
    assert len(fake.requests) == 2
    assert "502" in message
    assert sleeps == [c.FLUX_RETRY_WAIT_S]


@pytest.mark.parametrize("body", [QUOTA_BODY, '{"errors": [{"code": 4006}]}',
                                  "You have used up your DAILY FREE ALLOCATION"])
def test_daily_quota_is_never_retried(env: None, sleeps: list[float],
                                      monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    _, fake = failure(monkeypatch, http_error(429, body), error=flux_cf.FluxQuotaError)
    assert len(fake.requests) == 1
    assert sleeps == []


def test_quota_on_the_retry(env: None, sleeps: list[float], monkeypatch: pytest.MonkeyPatch) -> None:
    _, fake = failure(monkeypatch, http_error(500), http_error(429, QUOTA_BODY),
                      error=flux_cf.FluxQuotaError)
    assert len(fake.requests) == 2


@pytest.mark.parametrize("code", [301, 302, 307, 400, 401, 403, 404])
def test_no_retry_on_redirect_or_client_error(env: None, sleeps: list[float],
                                              monkeypatch: pytest.MonkeyPatch, code: int) -> None:
    message, fake = failure(monkeypatch, http_error(code, f'{{"echo": "{FAKE_KEY}"}}'))
    assert len(fake.requests) == 1
    assert str(code) in message
    assert sleeps == []


def test_send_error_names_the_type_only(env: None, sleeps: list[float],
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    message, fake = failure(monkeypatch, OSError(f"reset while sending Bearer {FAKE_KEY}"))
    assert "OSError" in message
    assert len(fake.requests) == 1


def test_a_redirect_is_never_followed(env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The real opener, not the fake: a 302 handed to its redirect handler must not be followed."""
    calls: list[urllib.request.Request] = []
    followed: list[Any] = []

    def redirected(self: urllib.request.OpenerDirector, request: urllib.request.Request,
                   *args: Any, **kwargs: Any) -> Any:
        calls.append(request)
        for handler in self.handlers:
            if isinstance(handler, urllib.request.HTTPRedirectHandler):
                moved = handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/")
                if moved is not None:
                    followed.append(moved)
        raise urllib.error.HTTPError(request.full_url, 302, "Found", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", redirected)
    with pytest.raises(flux_cf.FluxError):
        flux_cf.generate_image("a dark forest path")
    assert len(calls) == 1
    assert followed == []


@pytest.mark.parametrize("outcome", [
    b"not json",
    b"[1, 2]",
    envelope(success=False),
    {"success": True, "result": {}},
    {"success": True, "result": {"image": 7}},
    {"success": True, "result": {"image": "@@not base64@@"}},
    envelope(image=b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
    envelope(image=jpeg(100, 100)),
])
def test_bad_answers_are_errors(env: None, sleeps: list[float], monkeypatch: pytest.MonkeyPatch,
                                outcome: Any) -> None:
    _, fake = failure(monkeypatch, outcome)
    assert len(fake.requests) == 1


def test_oversized_body_is_an_error(env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    failure(monkeypatch, b"{" + b" " * c.FLUX_RESPONSE_MAX_BYTES + b"}")


@pytest.mark.parametrize("sof", [0xC0, 0xC1, 0xC2])
def test_image_size_reads_the_frame_header(sof: int) -> None:
    assert flux_cf.image_size(jpeg(768, 1344, sof)) == (768, 1344)


def test_image_size_bounds_are_inclusive() -> None:
    low, high = c.FLUX_IMAGE_SIDE_PX
    assert flux_cf.image_size(jpeg(low, high)) == (low, high)
    for width, height in ((low - 1, 1024), (1024, high + 1), (0, 0)):
        with pytest.raises(flux_cf.FluxError):
            flux_cf.image_size(jpeg(width, height))


@pytest.mark.parametrize("data", [
    b"",
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
    b"GIF89a" + b"\x00" * 32,
    jpeg()[:30],
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9",
    jpeg() + b"\x00" * c.FLUX_IMAGE_MAX_BYTES,
])
def test_image_size_rejects(data: bytes) -> None:
    with pytest.raises(flux_cf.FluxError):
        flux_cf.image_size(data)


def test_acceptance(env: None, sleeps: list[float], monkeypatch: pytest.MonkeyPatch) -> None:
    """A busy server, then a painting: one retry, the JPEG back, the token only in its header."""
    fake = install(monkeypatch, http_error(503), envelope(jpeg(1024, 1024)))
    image = flux_cf.generate_image("the ocean surface at dusk, a small boat")
    assert flux_cf.image_size(image) == (1024, 1024)
    assert sleeps == [c.FLUX_RETRY_WAIT_S]
    for request in fake.requests:
        assert request.get_header("Authorization") == f"Bearer {FAKE_KEY}"
        assert FAKE_KEY not in request.full_url and FAKE_KEY.encode() not in (request.data or b"")
        assert json.loads(request.data)["prompt"].startswith(c.FLUX_STYLE_PREFIX)  # type: ignore[arg-type]
