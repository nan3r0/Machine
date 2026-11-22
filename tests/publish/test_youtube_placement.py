"""R15: paid product placement declared false on every insert, and the access token character check
(task p4b-youtube, contract by p4b-youtube-contracts; audit F1, QA lead's token note).

Since the API revision of 2026-11-16 an unset `hasPaidProductPlacement` means the video is not
declared free of paid placement, so the init request names the part and sends false. The access
token goes into an HTTP header and a `::add-mask::` workflow command, so anything but printable
ASCII without spaces is refused before either. No network: tests/publish/youtube_fakes.py answers.
Expected values come from the plan (.harness/handoffs/p4b-plan.md), never from the code under test.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from pipeline import constants
from pipeline.publish import youtube
from pipeline.publish.youtube import UploadError
from pipeline.schema import Script
from tests.publish.youtube_fakes import ACCESS, FakeOpen, session, token, video
from tests.script.scripts import make_script

ENV = {"YOUTUBE_CLIENT_ID": "1234567890-fakeclient.apps.googleusercontent.com",
       "YOUTUBE_CLIENT_SECRET": "GOCSPX-FAKE-client-secret-0123456789",
       "YOUTUBE_REFRESH_TOKEN": "1//0FAKE-refresh-token-abcdefghijklmnop"}
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


def init_request(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> urllib.request.Request:
    fake = install(monkeypatch, token(), session(), video())
    youtube.upload(script(), mp4)
    return fake.requests[1]


def test_init_query_names_the_placement_part(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(init_request(monkeypatch, mp4).full_url).query,
                                  strict_parsing=True)
    assert query["uploadType"] == ["resumable"]
    assert len(query["part"]) == 1
    assert query["part"][0].split(",") == ["snippet", "status", "paidProductPlacementDetails"]


def test_init_body_declares_no_paid_placement(monkeypatch: pytest.MonkeyPatch, mp4: Path) -> None:
    init = init_request(monkeypatch, mp4)
    assert isinstance(init.data, bytes)
    body = json.loads(init.data)
    expected = script()
    assert body == {
        "snippet": {"title": expected.title,
                    "description": f"{expected.description}\n\n{constants.YOUTUBE_CREDIT_LINE}",
                    "tags": expected.tags, "categoryId": "27"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},
        "paidProductPlacementDetails": {"hasPaidProductPlacement": False},
    }
    # Dict equality takes 0 for False; the API needs JSON false.
    assert body["paidProductPlacementDetails"]["hasPaidProductPlacement"] is False


BAD_TOKENS = [
    pytest.param(ACCESS[:20] + "\n" + ACCESS[20:], id="embedded-newline"),
    pytest.param(ACCESS + "\n", id="trailing-newline"),
    pytest.param(ACCESS[:20] + " " + ACCESS[20:], id="space"),
    pytest.param(ACCESS[:20] + "\t" + ACCESS[20:], id="tab"),
    pytest.param(ACCESS[:20] + "\r" + ACCESS[20:], id="carriage-return"),
    pytest.param(ACCESS[:20] + "é" + ACCESS[20:], id="non-ascii-letter"),
]


@pytest.mark.parametrize("bad", BAD_TOKENS)
def test_unprintable_access_token_is_refused_before_mask(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                                                         capsys: pytest.CaptureFixture[str],
                                                         bad: str) -> None:
    capsys.readouterr()  # test_acceptance runs the successful uploads first, which print a mask
    # Enough answers for a full upload, so code without the check finishes instead of raising.
    fake = install(monkeypatch, token(access_token=bad), session(), video())
    with pytest.raises(UploadError) as caught:
        youtube.upload(script(), mp4)
    assert caught.value.sent is False
    assert len(fake.requests) == 1, "only the token refresh was sent"
    assert "::add-mask::" not in capsys.readouterr().out
    assert bad not in str(caught.value)


def test_acceptance(monkeypatch: pytest.MonkeyPatch, mp4: Path,
                    capsys: pytest.CaptureFixture[str]) -> None:
    """R15 (F1): the init request names paidProductPlacementDetails and sends
    hasPaidProductPlacement false; an access token outside printable ASCII without spaces is
    refused before the mask line and before the init request."""
    test_init_query_names_the_placement_part(monkeypatch, mp4)
    test_init_body_declares_no_paid_placement(monkeypatch, mp4)
    for param in BAD_TOKENS:
        test_unprintable_access_token_is_refused_before_mask(monkeypatch, mp4, capsys, *param.values)
