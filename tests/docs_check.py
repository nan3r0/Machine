"""CI docs check: fails when the docs drift from each other or from the repo. Locked.

Usage: python tests/docs_check.py [repo-root]

Prints one line per problem and exits 1 if there are any (HARNESS.md section 10, Stage 0). Checks:
- every task in .harness/status.yaml `done` has a task YAML, is marked done in the workflow.md
  Phase 1 status table, and has a handoff with a filled `## Docs` section ("none" counts)
- every task id marked done in that table is in .harness/status.yaml
- every backticked `tests/...` path in the workflow.md criterion-to-test map exists, and every
  `path::name` names a test function in that file
- every task id in the CLAUDE.md `## Status` section has a task YAML
- every lessons.md entry under `## Entries` fills each field of the `## Entry format` template
"""

import ast
import re
import sys
from pathlib import Path
from typing import Any

import yaml

TASK_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Task ids as they appear in prose: p1-contracts, h-rotation-hook.
TASK_ID_IN_TEXT = re.compile(r"\b(?:p\d+|h)-[a-z0-9]+(?:-[a-z0-9]+)*\b")
TEST_REF = re.compile(r"`(tests/[^`]+)`")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def load_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data


def section(lines: list[str], heading: str) -> list[str] | None:
    """Lines under `heading` up to the next heading of the same or higher level; None if absent."""
    level = heading.split(" ")[0]
    if heading not in lines:
        return None
    start = lines.index(heading) + 1
    for i in range(start, len(lines)):
        marker = lines[i].split(" ")[0]
        if marker and set(marker) == {"#"} and len(marker) <= len(level):
            return lines[start:i]
    return lines[start:]


def table_rows(lines: list[str]) -> list[list[str]]:
    """Cells of each markdown table body row, header and separator rows skipped."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines if line.startswith("|")]
    return rows[2:]


def task_ids(root: Path) -> set[str]:
    return {str(load_yaml(p).get("id")) for p in (root / ".harness" / "tasks").glob("**/*.yaml")}


def workflow_done(workflow: list[str]) -> set[str]:
    rows = table_rows(section(workflow, "### Phase 1 status") or [])
    return {r[0].strip("`") for r in rows if TASK_ID.match(r[0].strip("`")) and r[1].startswith("done")}


def status_problems(done: list[str], known: set[str], in_workflow: set[str]) -> list[str]:
    found = []
    for task in done:
        if task not in known:
            found.append(f".harness/status.yaml: done task {task} has no task YAML in .harness/tasks/")
        if task not in in_workflow:
            found.append(f".harness/status.yaml: done task {task} is not marked done in the workflow.md "
                         "Phase 1 status table")
    for task in sorted(in_workflow - set(done)):
        found.append(f"workflow.md: task {task} is marked done in the Phase 1 status table but not in "
                     ".harness/status.yaml")
    return found


def function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def map_problems(root: Path, workflow: list[str]) -> list[str]:
    found = []
    for line in section(workflow, "### Criterion to test map") or []:
        for ref in TEST_REF.findall(line):
            path, _, name = ref.partition("::")
            prefix = f"workflow.md: criterion-to-test map names {ref}, which"
            if not (root / path).is_file():
                found.append(f"{prefix} does not exist")
            elif name and name not in function_names(root / path):
                found.append(f"{prefix} has no such test function")
    return found


def claude_status_problems(claude: list[str], known: set[str]) -> list[str]:
    named = TASK_ID_IN_TEXT.findall("\n".join(section(claude, "## Status") or []))
    return [f"CLAUDE.md: the Status section names task {task}, which has no task YAML"
            for task in dict.fromkeys(named) if task not in known]


def handoff_problems(root: Path, done: list[str]) -> list[str]:
    found = []
    for task in done:
        rel = f".harness/handoffs/{task}.md"
        if not (root / rel).is_file():
            found.append(f"done task {task} has no handoff at {rel}")
            continue
        docs = section(read_lines(root / rel), "## Docs")
        if docs is None:
            found.append(f"{rel}: no ## Docs section")
        elif not any(line.strip() for line in docs):
            found.append(f"{rel}: ## Docs section is empty")
    return found


def lessons_problems(lessons: list[str]) -> list[str]:
    template = section(lessons, "## Entry format") or []
    fields = [line.split(":")[0] for line in template if ":" in line and not line.startswith("#")]
    found = []
    entries = section(lessons, "## Entries") or []
    for i, line in enumerate(entries):
        if not line.startswith("### "):
            continue
        body = section(entries[i:], line) or []
        for field in fields:
            if not any(b.startswith(f"{field}:") and b[len(field) + 1:].strip() for b in body):
                found.append(f"lessons.md: entry '{line[4:]}' lacks the field '{field}'")
    return found


def problems(root: Path) -> list[str]:
    known = task_ids(root)
    done = [str(t) for t in load_yaml(root / ".harness" / "status.yaml").get("done") or []]
    workflow = read_lines(root / "workflow.md")
    return [
        *status_problems(done, known, workflow_done(workflow)),
        *map_problems(root, workflow),
        *claude_status_problems(read_lines(root / "CLAUDE.md"), known),
        *handoff_problems(root, done),
        *lessons_problems(read_lines(root / "lessons.md")),
    ]


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    found = problems(root)
    for message in found:
        print(message)
    print(f"docs check failed: {len(found)} problems" if found else "docs check passed")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
