"""ci.yml triggers and concurrency (task p2d-ci-triggers, CSO P1-5).

The Actions allowance ran out on 2026-11-21: every push to a PR branch ran the check job twice,
once for `push` and once for `pull_request`. The check now runs once per PR update, once per
push to main and on pushes to scripts/<day> branches, and a newer PR update cancels the run it
supersedes.
"""

from typing import Any

from tests import workflow_rules as rules


def ci() -> dict[str, Any]:
    return rules.load("ci.yml")


def test_push_runs_only_on_main_and_script_prs() -> None:
    """A task or docs branch gets its CI from the pull_request event. scripts/** stays on push: that
    PR is opened with GITHUB_TOKEN, whose pull_request runs wait for approval, and GitHub's docs do
    not say whether the owner's own edit commits on it escape that (R12.3)."""
    push = ci()["on"]["push"]
    assert set(push) == {"branches"}
    assert sorted(push["branches"]) == ["main", "scripts/**"]


def test_every_pull_request_runs_with_no_filter() -> None:
    """No branch or path filter: docs-only PRs still need the docs check and the status-driven tests,
    and the owner's mobile edits on a scripts/<day> PR still get CI (R12.3)."""
    on = ci()["on"]
    assert "pull_request" in on
    assert on["pull_request"] is None or not {"branches", "branches-ignore", "paths", "paths-ignore"} & set(
        on["pull_request"])


def test_manual_dispatch_is_kept_and_reports_stay_manual() -> None:
    wf = ci()
    assert "workflow_dispatch" in wf["on"]
    assert wf["jobs"]["reports"]["if"] == "github.event_name == 'workflow_dispatch'"
    assert "if" not in wf["jobs"]["check"], "check runs on every trigger, dispatch included"


def test_set_of_triggers_is_exact() -> None:
    assert set(ci()["on"]) == {"push", "pull_request", "workflow_dispatch"}


def test_concurrency_cancels_superseded_pr_runs_only() -> None:
    """A PR's runs share one group and a newer one cancels the older. Every other run gets a group
    of its own (its run id), because GitHub cancels a pending run in the same group even without
    cancel-in-progress: main pushes and the reports dispatch must never replace each other."""
    concurrency = ci()["concurrency"]
    group = str(concurrency["group"])
    assert "github.event.pull_request.number" in group
    assert "github.run_id" in group
    cancel = concurrency["cancel-in-progress"]
    assert cancel is True or str(cancel).replace(" ", "") == "${{github.event_name=='pull_request'}}"


def test_acceptance() -> None:
    """Triggers, concurrency and every existing guard hold together."""
    wf = ci()
    rules.assert_safe(wf)
    test_push_runs_only_on_main_and_script_prs()
    test_every_pull_request_runs_with_no_filter()
    test_manual_dispatch_is_kept_and_reports_stay_manual()
    test_concurrency_cancels_superseded_pr_runs_only()
    check = wf["jobs"]["check"]
    assert check["env"]["BRANCH"] == "${{ github.head_ref || github.ref_name }}"
    assert check["env"]["BASE_REF"] == "${{ github.base_ref }}"
    assert check["steps"][0]["with"]["fetch-depth"] == 0
