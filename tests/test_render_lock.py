"""CSO P1-4 heavy half: hash-checked installs in both render paths (task p4b-render-lock, plan
.harness/handoffs/p4b-plan.md, "P1-4 heavy half").

The render job of daily_publish.yml and render.yml install torch and torchaudio from the PyTorch CPU
index alone, from requirements-render-torch.txt, then everything else from PyPI, from
requirements-render.txt, both with --require-hashes. The lock files must carry the pins of
requirements.txt and requirements-heavy.txt at the same versions, so a bump of either source file
fails here until the lock is regenerated. ci.yml keeps its unhashed install (no secret, no publish).
"""

import re
import shlex
from pathlib import Path

from tests import workflow_rules as rules
from tests.test_daily_publish_workflow import job_run

ROOT = Path(__file__).resolve().parent.parent
LIGHT = ROOT / "requirements.txt"
HEAVY = ROOT / "requirements-heavy.txt"
TORCH_LOCK = ROOT / "requirements-render-torch.txt"
RENDER_LOCK = ROOT / "requirements-render.txt"
TORCH = {"torch", "torchaudio"}
CPU_INDEX = "https://download.pytorch.org/whl/cpu"
# pip reads `#` as a comment only at the start of a line or after whitespace; a URL's #sha256 stays.
COMMENT = re.compile(r"(?:^|\s)#.*$")
HASHED = re.compile(r"(?P<req>.+?)(?:\s+--hash=sha256:[0-9a-f]{64})+")
PIN = re.compile(r"([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[A-Za-z0-9_.,-]+\])?==(\S+)")
DIRECT_URL = re.compile(r"([A-Za-z0-9][A-Za-z0-9_.-]*) @ (https://\S+#sha256=[0-9a-f]{64})")
INDEX_OPTIONS = {"-i", "--index-url", "--extra-index-url", "-f", "--find-links", "--no-index"}


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements(path: Path, hashed: bool) -> dict[str, str]:
    """Normalised name -> version, or -> the URL for a direct URL requirement. Every line must be
    `name==version` or a direct URL with #sha256 (and carry sha256 hashes if asked). Option lines
    (--index-url, --find-links and the like) are not requirements, so they fail too."""
    assert path.is_file(), f"{path.name} is missing"
    found: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").replace("\\\n", " ").splitlines():
        line = COMMENT.sub("", raw).strip()
        if not line:
            continue
        if hashed:
            match = HASHED.fullmatch(line)
            assert match, f"{path.name}: '{line}' has no --hash=sha256 of 64 hex characters"
            line = match.group("req").strip()
        pin = PIN.fullmatch(line) or DIRECT_URL.fullmatch(line)
        assert pin, f"{path.name}: '{line}' is not name==version or a direct URL with #sha256"
        name = normalise(pin.group(1))
        assert name not in found, f"{path.name}: {name} is listed twice"
        found[name] = pin.group(2)
    return found


def test_torch_lock_holds_exactly_torch_and_torchaudio_at_the_heavy_versions() -> None:
    heavy = requirements(HEAVY, hashed=False)
    assert requirements(TORCH_LOCK, hashed=True) == {name: heavy[name] for name in TORCH}


def test_render_lock_pins_every_other_requirement_at_the_same_version() -> None:
    expected = {**requirements(LIGHT, hashed=False), **requirements(HEAVY, hashed=False)}
    locked = requirements(RENDER_LOCK, hashed=True)
    for name, version in expected.items():
        if name not in TORCH:
            assert locked.get(name) == version, f"{name}: lock has {locked.get(name)}, sources {version}"
    assert not TORCH & set(locked), "torch comes only from the CPU index, through its own lock"


def pip_installs(run: str) -> list[list[str]]:
    """The arguments after `install` of every pip install in a `run:` text."""
    lines = [shlex.split(line) for line in run.replace("\\\n", " ").splitlines() if "pip install" in line]
    return [words[words.index("install") + 1:] for words in lines]


def requirement_files(args: list[str]) -> list[str]:
    return [args[i + 1] for i, arg in enumerate(args) if arg in ("-r", "--requirement")]


def options(args: list[str]) -> list[str]:
    """Option names, with any `=value` cut off, so `--find-links=x` counts as `--find-links`."""
    return [arg.split("=", 1)[0] for arg in args if arg.startswith("-")]


def assert_hashed_render_install(run: str) -> None:
    """Exactly two installs: torch from the CPU index alone, without its dependencies, then the rest
    from PyPI. Both hash-checked, each from its lock only."""
    installs = pip_installs(run)
    assert len(installs) == 2, f"two pip installs, torch then the rest: {installs}"
    torch, rest = installs
    assert requirement_files(torch) == ["requirements-render-torch.txt"], torch
    assert {"--no-deps", "--require-hashes"} <= set(torch), torch
    assert [o for o in options(torch) if o in INDEX_OPTIONS] == ["--index-url"], "the CPU index alone"
    assert torch[torch.index("--index-url") + 1] == CPU_INDEX, torch
    assert requirement_files(rest) == ["requirements-render.txt"], rest
    assert "--require-hashes" in rest, rest
    assert not INDEX_OPTIONS & set(options(rest)), f"the rest comes from PyPI only: {rest}"
    rules.assert_torch_from_cpu_index_first(run)


def test_daily_render_job_installs_only_from_the_locks() -> None:
    assert_hashed_render_install(job_run("render"))


def test_render_workflow_installs_only_from_the_locks() -> None:
    assert_hashed_render_install(rules.run_text(rules.load("render.yml")))


def test_acceptance() -> None:
    test_torch_lock_holds_exactly_torch_and_torchaudio_at_the_heavy_versions()
    test_render_lock_pins_every_other_requirement_at_the_same_version()
    test_daily_render_job_installs_only_from_the_locks()
    test_render_workflow_installs_only_from_the_locks()
