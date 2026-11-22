"""Pick the model for a harness role under the active routing profile (HARNESS.md section 3, TRIAL.md).

    python .harness/model_for.py <role> [--review-out PATH]           # model to use
    python .harness/model_for.py auto --review-out PATH               # role from the review file name
    python .harness/model_for.py <role> --shadow --review-out PATH    # baseline model if a shadow review is due, else nothing

`profile: baseline` (or no `profile` key) means the `roles` block, exactly as before.
Any other profile overrides roles from `profiles.<name>.roles`, with two safety rules for reviews:
a Gate 2 review stays on the baseline model when the task is a contracts/tests task (role test_author
or architect), or when its diff touches a `specialist_reviews.security` path.

Config is read from the main checkout (so the owner flips one line there and every worktree follows),
falling back to the current folder. Run from a worktree or the project root.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import subprocess
from pathlib import Path
from typing import Any

import yaml

REVIEW_SUFFIXES = {"-g2": "reviewer", "-sec": "security_reviewer", "-vq": "visual_qa", "-vqa": "visual_qa"}
KEEP_BASELINE_TASK_ROLES = {"test_author", "architect"}


def main_root() -> Path:
    """The main checkout's root (the parent of git's common dir), else the current folder."""
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        root = Path(out).parent
        if (root / ".harness" / "config.yaml").is_file():
            return root
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.cwd()


def load_config(root: Path) -> dict[str, Any]:
    return yaml.safe_load((root / ".harness" / "config.yaml").read_text(encoding="utf-8")) or {}


def active_profile(cfg: dict[str, Any]) -> str:
    return str(cfg.get("profile") or "baseline")


def profile_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    name = active_profile(cfg)
    if name == "baseline":
        return {}
    profiles = cfg.get("profiles") or {}
    if name not in profiles:
        raise SystemExit(f"profile {name!r} is not defined under profiles: in .harness/config.yaml")
    return profiles[name] or {}


def task_id_from_review_out(review_out: str) -> str:
    stem = Path(review_out).stem
    for suffix in sorted(REVIEW_SUFFIXES, key=len, reverse=True):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def role_from_review_out(review_out: str) -> str:
    stem = Path(review_out).stem
    for suffix in sorted(REVIEW_SUFFIXES, key=len, reverse=True):
        if stem.endswith(suffix):
            return REVIEW_SUFFIXES[suffix]
    return "reviewer"


def task_role(root: Path, task_id: str) -> str | None:
    for path in (root / ".harness" / "tasks").glob("**/*.yaml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if str(data.get("id")) == task_id:
            return str(data.get("role") or "") or None
    return None


def changed_files(task_id: str, roots: list[Path]) -> list[str] | None:
    """Files in the saved review diff, or None if no diff was found (treated as risky)."""
    for root in roots:
        diff = root / ".harness" / "reviews" / f"{task_id}.diff"
        if diff.is_file():
            files = []
            for line in diff.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("diff --git "):
                    files.append(line.rsplit(" b/", 1)[-1].strip())
            return files
    return None


def matches(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]):
            return True
    return False


def model_for(role: str, review_out: str | None = None, root: Path | None = None) -> str:
    root = root or main_root()
    cfg = load_config(root)
    baseline = cfg["roles"][role]
    overrides = profile_settings(cfg).get("roles") or {}
    if role not in overrides:
        return str(baseline)
    if role == "reviewer" and review_out:
        task_id = task_id_from_review_out(review_out)
        if task_role(root, task_id) in KEEP_BASELINE_TASK_ROLES:
            return str(baseline)
        files = changed_files(task_id, [Path.cwd(), root])
        security = (cfg.get("specialist_reviews") or {}).get("security") or []
        if files is None or any(matches(f, security) for f in files):
            return str(baseline)
    return str(overrides[role])


def shadow_model(role: str, review_out: str, root: Path | None = None) -> str:
    """Baseline model when this review was downgraded and is picked for a shadow review, else ''."""
    root = root or main_root()
    cfg = load_config(root)
    every = int(profile_settings(cfg).get("shadow_review_every") or 0)
    baseline = str(cfg["roles"][role])
    if every <= 0 or model_for(role, review_out, root) == baseline:
        return ""
    task_id = task_id_from_review_out(review_out)
    if int(hashlib.sha256(task_id.encode()).hexdigest(), 16) % every != 0:
        return ""
    return baseline


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("role")
    parser.add_argument("--review-out")
    parser.add_argument("--shadow", action="store_true")
    args = parser.parse_args()
    if args.role == "auto":  # review role from the output name: -sec, -vq/-vqa, else Gate 2
        args.role = role_from_review_out(args.review_out or "")
    if args.shadow:
        print(shadow_model(args.role, args.review_out or ""))
    else:
        print(model_for(args.role, args.review_out))
