"""R12.3: every script in queue/ is valid and publishable, so a mobile edit of an approval PR is
checked by CI (task p2-validate)."""

from pathlib import Path

from pipeline.schema import Script
from pipeline.script import validate

QUEUE = Path(__file__).resolve().parent.parent / "queue"


def queue_problems(queue: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(queue.glob("**/*.json")):
        script = Script.model_validate_json(path.read_text(encoding="utf-8"))
        problems = validate.problems(script)
        if script.id != path.stem:
            problems.append(f"id {script.id} differs from the file name")
        if problems:
            found[path.relative_to(queue).as_posix()] = problems
    return found


def test_a_bad_queue_file_is_reported(tmp_path: Path) -> None:
    sample = QUEUE / "approved" / "sample-65s.json"
    (tmp_path / "published").mkdir()
    text = sample.read_text(encoding="utf-8").replace('"title": "', '"title": "www.evil.example ', 1)
    (tmp_path / "published" / "sample-65s.json").write_text(text, encoding="utf-8")
    assert list(queue_problems(tmp_path)) == ["published/sample-65s.json"]


def test_acceptance() -> None:
    """Every queue/**/*.json parses as a Script, has no validate problem and is named after its id."""
    assert list(QUEUE.glob("**/*.json")), "queue/ holds no script"
    assert queue_problems(QUEUE) == {}
