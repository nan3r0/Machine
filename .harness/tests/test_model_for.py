import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model_for import model_for, role_from_review_out, shadow_model

OPUS, SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
CONFIG = f"""profile: {{profile}}
roles:
  reviewer: {OPUS}
  visual_qa: {OPUS}
  security_reviewer: {OPUS}
  implementer: {SONNET}
specialist_reviews:
  security: ["pipeline/publish/**", "**/auth*", ".github/workflows/**"]
profiles:
  trial-lean:
    roles:
      reviewer: {SONNET}
      visual_qa: {SONNET}
    shadow_review_every: 1
"""


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def make(profile: str = "trial-lean") -> Path:
        (tmp_path / ".harness" / "reviews").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".harness" / "tasks" / "p9").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".harness" / "config.yaml").write_text(CONFIG.format(profile=profile), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        return tmp_path
    return make


def task(root: Path, task_id: str, role: str, files: list[str] | None) -> None:
    (root / ".harness" / "tasks" / "p9" / f"{task_id}.yaml").write_text(
        f"id: {task_id}\nrole: {role}\n", encoding="utf-8")
    if files is not None:
        diff = "".join(f"diff --git a/{f} b/{f}\n+x\n" for f in files)
        (root / ".harness" / "reviews" / f"{task_id}.diff").write_text(diff, encoding="utf-8")


def test_baseline_profile_changes_nothing(root) -> None:
    r = root("baseline")
    task(r, "t1", "implementer", ["pipeline/render/x.py"])
    assert model_for("reviewer", ".harness/reviews/t1-g2.json", r) == OPUS
    assert model_for("visual_qa", ".harness/reviews/t1-vq.json", r) == OPUS
    assert shadow_model("reviewer", ".harness/reviews/t1-g2.json", r) == ""


def test_trial_downgrades_ordinary_gate2(root) -> None:
    r = root()
    task(r, "t1", "implementer", ["pipeline/render/x.py"])
    assert model_for("reviewer", ".harness/reviews/t1-g2.json", r) == SONNET
    assert model_for("visual_qa", ".harness/reviews/t1-vq.json", r) == SONNET


@pytest.mark.parametrize("path", ["pipeline/publish/youtube.py", "auth.py", "pipeline/x/auth_flow.py",
                                  ".github/workflows/ci.yml"])
def test_security_paths_keep_opus_gate2(root, path: str) -> None:
    r = root()
    task(r, "t1", "implementer", ["pipeline/render/x.py", path])
    assert model_for("reviewer", ".harness/reviews/t1-g2.json", r) == OPUS


def test_tests_and_contracts_tasks_keep_opus(root) -> None:
    r = root()
    task(r, "t1", "test_author", ["tests/test_x.py"])
    assert model_for("reviewer", ".harness/reviews/t1-g2.json", r) == OPUS


def test_missing_diff_keeps_opus(root) -> None:
    r = root()
    task(r, "t1", "implementer", None)
    assert model_for("reviewer", ".harness/reviews/t1-g2.json", r) == OPUS


def test_roles_not_in_profile_are_unchanged(root) -> None:
    r = root()
    assert model_for("security_reviewer", ".harness/reviews/t1-sec.json", r) == OPUS
    assert model_for("implementer", None, r) == SONNET


def test_shadow_only_for_downgraded_reviews(root) -> None:
    r = root()
    task(r, "t1", "implementer", ["pipeline/render/x.py"])
    task(r, "t2", "implementer", ["pipeline/publish/y.py"])
    assert shadow_model("reviewer", ".harness/reviews/t1-g2.json", r) == OPUS
    assert shadow_model("reviewer", ".harness/reviews/t2-g2.json", r) == ""


def test_unknown_profile_fails_loudly(root) -> None:
    r = root("nope")
    with pytest.raises(SystemExit):
        model_for("reviewer", None, r)


@pytest.mark.parametrize("name,role", [("p1-compose-g2.json", "reviewer"), ("p1-align.json", "reviewer"),
                                       ("p1-compose-sec.json", "security_reviewer"),
                                       ("p1-qa-vq.json", "visual_qa"), ("p1-captions-ass-vqa.json", "visual_qa")])
def test_role_from_existing_review_names(name: str, role: str) -> None:
    assert role_from_review_out(name) == role
