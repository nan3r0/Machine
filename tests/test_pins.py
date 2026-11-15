"""Model weight pins in constants.py are well formed. Owned by no task, so always runs."""

import re

from pipeline import constants


def test_voice_repo_revision_is_a_commit_sha() -> None:
    assert re.fullmatch(r"[0-9a-f]{40}", constants.VOICE_REPO_REVISION)


def test_every_voice_file_has_a_sha256() -> None:
    assert {"config.json", "kokoro-v1_0.pth", f"voices/{constants.VOICE_NAME}.pt"} <= set(
        constants.VOICE_FILE_SHA256)
    for path, digest in constants.VOICE_FILE_SHA256.items():
        assert re.fullmatch(r"[0-9a-f]{64}", digest), path
