"""Hashed lock files agree with each other (tasks p4c-lock-pin, p4c-lock-pin-2, p4c-lock-pin-4,
p4c-lock-pin-5).

pip installs a hashed lock only if every pin satisfies what the other pins require, or it fails with
ResolutionImpossible. Dependabot broke that by bumping one package without the one that constrains
it: pydantic-core alone (commit ba7bbd0), then pydantic alone (PR #151) while an ignore held
pydantic-core back, thinc (PR #150) and curated-transformers (PR #152) past what spaCy allows, and
rfc3986 (PR #161) past what csvw allows, srsly (PR #169) past what spaCy allows, and num2words
(PR #158) to a release that needs docopt, which no lock pins.
The tests check that every package pinned in more than one hashed lock has one version across all
of them, that pins satisfy the known requirements in CONSTRAINTS, and that Dependabot bumps pydantic
and pydantic-core together and leaves the capped pins' majors alone. pip's hash mode also needs
every line pinned with == and hashed.
"""

from pathlib import Path

import yaml
from packaging.specifiers import SpecifierSet

from tests.test_render_lock import normalise, requirements

ROOT = Path(__file__).resolve().parent.parent
DEPENDABOT = ROOT / ".github" / "dependabot.yml"

# (package, version, dependency, specifier): that release requires the dependency within the
# specifier. Each row is copied from the `Requires-Dist:` line in that wheel's METADATA on PyPI,
# since an offline test cannot read it. Bumping a listed package needs its new row.
CONSTRAINTS = [
    ("pydantic", "2.14.3", "pydantic-core", "==2.50.4"),  # pydantic-2.14.3 wheel METADATA
    ("pydantic", "2.14.4", "pydantic-core", "==2.50.5"),  # pydantic-2.14.4 wheel METADATA
    ("spacy", "3.8.18", "thinc", ">=8.3.12,<8.4.0"),  # spacy-3.8.18 wheel METADATA
    # spacy_curated_transformers-0.3.1 wheel METADATA
    ("spacy-curated-transformers", "0.3.1", "curated-transformers", ">=0.1.0,<0.2.0"),
    ("csvw", "4.2.0", "rfc3986", "<2"),  # csvw-4.2.0 wheel METADATA
    ("spacy", "3.8.18", "srsly", ">=2.5.3,<3.0.0"),  # spacy-3.8.18 wheel METADATA
]

# Dependabot may not take these past a major: spaCy or csvw caps them, and they are only transitive pins.
CAPPED = ("thinc", "curated-transformers", "rfc3986", "srsly")


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


def constraint_problems(locks: list[Path]) -> list[str]:
    """One message per lock pin that breaks a CONSTRAINTS row, or per pinned package version that
    CONSTRAINTS lists other versions of but not this one."""
    problems = []
    for lock in locks:
        pins = requirements(lock, hashed=True)
        for package in sorted({row[0] for row in CONSTRAINTS} & pins.keys()):
            rows = [row for row in CONSTRAINTS if row[0] == package and row[1] == pins[package]]
            if not rows:
                problems.append(
                    f"{lock.name}: {package} {pins[package]} has no row in CONSTRAINTS "
                    "(tests/test_lock_consistency.py); add one from that wheel's METADATA Requires-Dist")
            for _, version, dependency, spec in rows:
                pinned = pins.get(dependency)
                if pinned is None or pinned not in SpecifierSet(spec):
                    problems.append(
                        f"{lock.name}: {package} {version} requires {dependency}{spec}, lock pins {pinned}")
    return problems


def write_lock(path: Path, *pins: str) -> None:
    path.write_text("".join(f"{pin} \\\n    --hash=sha256:{'a' * 64}\n" for pin in pins), encoding="utf-8")


def pip_updates() -> list[dict]:
    config = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    pip = [u for u in config["updates"] if u.get("package-ecosystem") == "pip"]
    assert pip, "dependabot.yml has no pip entry"
    return pip


def test_generate_and_render_locks_are_both_checked() -> None:
    names = {p.name for p in hashed_locks(ROOT)}
    assert {"requirements-generate.txt", "requirements-render.txt"} <= names


def test_pydantic_core_is_pinned_in_both_light_and_render_locks() -> None:
    for name in ("requirements-generate.txt", "requirements-render.txt"):
        pins = requirements(ROOT / name, hashed=True)
        assert {"pydantic", "pydantic-core"} <= pins.keys(), f"{name} lost pydantic or pydantic-core"


def test_render_lock_pins_the_capping_packages_and_what_they_cap() -> None:
    pins = requirements(ROOT / "requirements-render.txt", hashed=True)
    assert {"spacy", "spacy-curated-transformers", "csvw", *CAPPED} <= pins.keys()


def test_shared_packages_have_one_version_across_hashed_locks() -> None:
    split = split_pins(hashed_locks(ROOT))
    assert not split, f"packages pinned at different versions across hashed locks: {split}"


def test_pins_satisfy_the_known_requirements() -> None:
    problems = constraint_problems(hashed_locks(ROOT))
    assert not problems, "lock pins pip cannot resolve:\n" + "\n".join(problems)


def test_the_check_flags_a_package_bumped_in_one_lock_only(tmp_path: Path) -> None:
    write_lock(tmp_path / "requirements-a.txt", "pydantic==2.14.3", "pydantic-core==2.50.4")
    write_lock(tmp_path / "requirements-b.txt", "pydantic==2.14.3", "Pydantic_Core==2.50.5")
    (tmp_path / "requirements-c.txt").write_text("pydantic-core==9.9.9\n", encoding="utf-8")
    locks = hashed_locks(tmp_path)
    assert [p.name for p in locks] == ["requirements-a.txt", "requirements-b.txt"]
    assert split_pins(locks) == {
        "pydantic-core": {"requirements-a.txt": "2.50.4", "requirements-b.txt": "2.50.5"}}


def test_the_check_flags_pins_outside_a_requirement(tmp_path: Path) -> None:
    write_lock(tmp_path / "requirements-ok.txt",
               "pydantic==2.14.4", "pydantic-core==2.50.5", "spacy==3.8.18", "thinc==8.3.14",
               "srsly==2.5.6")
    write_lock(tmp_path / "requirements-core.txt", "pydantic==2.14.4", "pydantic-core==2.50.4")
    write_lock(tmp_path / "requirements-thinc.txt", "spacy==3.8.18", "thinc==10.0.0", "srsly==2.5.6")
    write_lock(tmp_path / "requirements-gone.txt", "spacy==3.8.18", "srsly==2.5.6")
    write_lock(tmp_path / "requirements-new.txt", "pydantic==99.0.0", "pydantic-core==99.0.0")
    write_lock(tmp_path / "requirements-other.txt", "pyyaml==6.0.2")
    problems = constraint_problems(hashed_locks(tmp_path))
    assert [p.split(":")[0] for p in problems] == [
        "requirements-core.txt", "requirements-gone.txt", "requirements-new.txt", "requirements-thinc.txt"]
    assert "add one" in problems[2]


def test_every_hashed_lock_line_is_pinned_and_hashed() -> None:
    for lock in hashed_locks(ROOT):
        assert requirements(lock, hashed=True), f"{lock.name} pins nothing"


def test_num2words_stays_at_0_5_6_unless_docopt_is_pinned() -> None:
    # num2words 0.5.6 has no Requires-Dist; 0.5.14 requires docopt>=0.6.2 (both wheels' METADATA),
    # and docopt ships only an sdist, so render.yml run 45306110415 failed in --require-hashes mode.
    pins = requirements(ROOT / "requirements-render.txt", hashed=True)
    if pins.get("num2words") != "0.5.6":
        assert "docopt" in pins, f"num2words {pins.get('num2words')} needs docopt, which is not pinned"


def test_dependabot_bumps_pydantic_and_pydantic_core_together() -> None:
    for update in pip_updates():
        where = update.get("directory")
        ignored = {normalise(i.get("dependency-name", "")) for i in update.get("ignore") or []}
        assert "pydantic-core" not in ignored, f"pip update for {where} ignores pydantic-core"
        groups = [{normalise(p) for p in g.get("patterns") or []}
                  for g in (update.get("groups") or {}).values()]
        assert any({"pydantic", "pydantic-core"} <= g for g in groups), (
            f"pip update for {where} has no group with both pydantic and pydantic-core")


def test_dependabot_never_takes_capped_pins_past_a_major() -> None:
    for update in pip_updates():
        majors_ignored = {
            normalise(i.get("dependency-name", "")) for i in update.get("ignore") or []
            if "version-update:semver-major" in (i.get("update-types") or ["version-update:semver-major"])}
        missing = set(CAPPED) - majors_ignored
        assert not missing, f"pip update for {update.get('directory')} may bump {sorted(missing)} a major"


def test_acceptance() -> None:
    test_generate_and_render_locks_are_both_checked()
    test_pydantic_core_is_pinned_in_both_light_and_render_locks()
    test_render_lock_pins_the_capping_packages_and_what_they_cap()
    test_shared_packages_have_one_version_across_hashed_locks()
    test_pins_satisfy_the_known_requirements()
    test_dependabot_bumps_pydantic_and_pydantic_core_together()
    test_dependabot_never_takes_capped_pins_past_a_major()
    test_every_hashed_lock_line_is_pinned_and_hashed()
    test_num2words_stays_at_0_5_6_unless_docopt_is_pinned()
