"""Hashed lock files agree with each other (task p4c-lock-pin).

Dependabot bumped pydantic-core alone in requirements-generate.txt (commit ba7bbd0), but pydantic pins
an exact pydantic-core, so `pip install --require-hashes` failed with ResolutionImpossible. Which
pydantic-core a pydantic release needs is only in its wheel metadata, so offline the tests check that
every package pinned in more than one hashed lock has one version across all of them, and that
Dependabot leaves pydantic-core to pydantic.
"""

from pathlib import Path

import yaml

from tests.test_render_lock import normalise, requirements

ROOT = Path(__file__).resolve().parent.parent
DEPENDABOT = ROOT / ".github" / "dependabot.yml"


def hashed_locks(root: Path) -> list[Path]:
    """Every requirements*.txt at the repo root that pins with --hash (a lock pip installs with
    --require-hashes)."""
    return sorted(p for p in root.glob("requirements*.txt") if "--hash=" in p.read_text(encoding="utf-8"))


def split_pins(locks: list[Path]) -> dict[str, dict[str, str]]:
    """Package -> {lock file name: version} for every package pinned at different versions."""
    seen: dict[str, dict[str, str]] = {}
    for lock in locks:
        for name, version in requirements(lock, hashed=True).items():
            seen.setdefault(name, {})[lock.name] = version
    return {name: files for name, files in seen.items() if len(set(files.values())) > 1}


def test_generate_and_render_locks_are_both_checked() -> None:
    names = {p.name for p in hashed_locks(ROOT)}
    assert {"requirements-generate.txt", "requirements-render.txt"} <= names


def test_pydantic_core_is_pinned_in_both_light_and_render_locks() -> None:
    for name in ("requirements-generate.txt", "requirements-render.txt"):
        assert "pydantic-core" in requirements(ROOT / name, hashed=True), f"{name} lost pydantic-core"


def test_shared_packages_have_one_version_across_hashed_locks() -> None:
    split = split_pins(hashed_locks(ROOT))
    assert not split, f"packages pinned at different versions across hashed locks: {split}"


def test_the_check_flags_a_package_bumped_in_one_lock_only(tmp_path: Path) -> None:
    line = "{} \\\n    --hash=sha256:" + "a" * 64 + "\n"
    (tmp_path / "requirements-a.txt").write_text(
        line.format("pydantic==2.14.3") + line.format("pydantic-core==2.50.4"), encoding="utf-8")
    (tmp_path / "requirements-b.txt").write_text(
        line.format("pydantic==2.14.3") + line.format("Pydantic_Core==2.50.5"), encoding="utf-8")
    (tmp_path / "requirements-c.txt").write_text("pydantic-core==9.9.9\n", encoding="utf-8")
    locks = hashed_locks(tmp_path)
    assert [p.name for p in locks] == ["requirements-a.txt", "requirements-b.txt"]
    assert split_pins(locks) == {
        "pydantic-core": {"requirements-a.txt": "2.50.4", "requirements-b.txt": "2.50.5"}}


def test_dependabot_never_bumps_pydantic_core_on_its_own() -> None:
    config = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    pip = [u for u in config["updates"] if u.get("package-ecosystem") == "pip"]
    assert pip, "dependabot.yml has no pip entry"
    for update in pip:
        ignored = {normalise(i.get("dependency-name", "")) for i in update.get("ignore") or []}
        assert "pydantic-core" in ignored, f"pip update for {update.get('directory')} may bump pydantic-core"


def test_acceptance() -> None:
    test_generate_and_render_locks_are_both_checked()
    test_pydantic_core_is_pinned_in_both_light_and_render_locks()
    test_shared_packages_have_one_version_across_hashed_locks()
    test_dependabot_never_bumps_pydantic_core_on_its_own()
