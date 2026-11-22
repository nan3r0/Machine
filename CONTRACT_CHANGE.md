# Contract change request: p4-daily-workflow

Tests: every claim shell test in `tests/test_daily_publish_workflow.py` that expects the claim to succeed (`test_claim_commits_a_record_before_the_upload`, `test_claim_retries_once_after_a_rejected_push`, and the `claimed()` helper used by the record tests).

Why: review round 1 (`.harness/reviews/p4-daily-workflow-round1.md`) requires the claim to take the script's blob hash from the render job (`needs.render.outputs.script_blob`) and refuse when main's copy differs. The tests call `run_job(..., {"render.script_id": ID})` with no `render.script_blob`, and `run_job` resolves a missing output to an empty string. The claim now refuses an empty or malformed blob, so those tests fail in CI. Accepting an empty blob would reopen the defect, so the workflow stays strict.

What the tests should say:
- Pass `"render.script_blob": git(repo, "hash-object", SCRIPT).strip()` in the outputs of every successful claim run.
- Add a test: a claim run with a blob that differs from main's script exits non-zero and pushes nothing (also after the rebase retry, when main's script changes between the first push and the retry).
- Add a test: record refuses to move a script whose hash differs from the record's `script_sha`.

## Architect ruling (2026-11-22): approved

The tests are wrong against the plan, not merely hard to pass. p4-plan (Ledger, line 147) says the script moves unchanged, so its blob equals the record's `script_sha`: "which approved version was published". The old contract let claim hash main's copy, which can differ from what render and upload used. Binding all four jobs to the rendered blob is what the plan asks for. No workflow defect found in `daily_publish.yml` at 7cc568d.

Not applied yet: this ruling ran in a session launched with `LOOM_TASK=p4-daily-workflow` (implementer role), so `enforce_locks.py` blocked the test edit. Apply the patch below in a session launched with `LOOM_TASK=p4-contracts` (role `test_author`), on this branch, then delete this file. The test file is already in `.harness/locks.yaml`.

### Patch for `tests/test_daily_publish_workflow.py`

1. Module docstring. Replace the outputs bullet's first line and add a bullet at the end:

```
- Job outputs: render `script_id` and `script_blob` (`git hash-object` of the rendered script),
  upload `video_id` and `sent` (`true` or `false`), as the youtube CLI writes them. ...
```
```
- One version end to end (p4-plan, Ledger): claim and upload refuse unless the script's blob equals
  `script_blob`, and claim writes it as `script_sha`; record moves the script only when its blob
  equals the record's `script_sha`. Render runs on main only, so a branch run publishes nothing.
```

2. `test_render_job`: replace the `script_id` outputs assert with

```python
    assert {"script_id", "script_blob"} <= set(job("render").get("outputs") or {})
    assert " ".join(str(job("render").get("if", "")).split()) == "github.ref == 'refs/heads/main'"
```

3. `test_upload_job`: after the `GITHUB_OUTPUT` assert add

```python
    assert OUTPUT_REF.match(str(keyed[0]["env"].get("SCRIPT_BLOB", "")).strip()).groups() == ("render", "script_blob")
    upload_run = str(keyed[0]["run"])
    assert "git hash-object" in upload_run
    assert upload_run.index("git hash-object") < upload_run.index("python -m pipeline.publish.youtube"), \
        "the script version is checked before anything is sent"
```

`OUTPUT_REF` is defined further down at module level; that is fine, since it is only read when the test runs.

4. Helpers, next to `head()`:

```python
def blob(remote: Path) -> str:
    """The approved script's blob on main, as render's `script_blob` output gives it."""
    return git(remote, "rev-parse", f"main:{SCRIPT}").strip()


def claim_outputs(remote: Path) -> dict[str, str]:
    return {"render.script_id": ID, "render.script_blob": blob(remote)}
```

5. `claimed()`: `run_job(..., "claim", claim_outputs(remote))`.

6. `test_claim_commits_a_record_before_the_upload` and `test_claim_retries_once_after_a_rejected_push`: pass `claim_outputs(remote)` (in the retry test, compute it before `other` pushes; the script is unchanged so either order works). Keep `expected_sha = git(repo, "hash-object", SCRIPT)`: it checks claim writes the rendered blob as `script_sha`.

7. `test_claim_refuses_a_bad_script_id`: pass `{"render.script_id": bad, "render.script_blob": blob(remote)}`, so the refusal comes from the id check.

8. `test_claim_never_rewrites_or_claims_what_main_does_not_offer`: take `rendered = claim_outputs(remote)` right after `remote_with_script`, before `change_main`, and pass it, so each case fails on the record or missing-script check, not on an empty blob.

9. `test_write_jobs_run_no_git_hooks`: `outputs = {**claim_outputs(remote), "upload.video_id": VIDEO, "upload.sent": ""}`, computed before the hooks are planted.

10. New tests, after `test_claim_never_rewrites_or_claims_what_main_does_not_offer`:

```python
def edit_script(tmp_path: Path, remote: Path) -> None:
    """The owner re-approves a different version of the script on main."""
    change_main(tmp_path, remote, {SCRIPT: show(remote, SCRIPT).encode("utf-8") + b"\n"})


@shell_tools
@pytest.mark.parametrize("bad", ["", "abc", "0" * 39, "0" * 41, "z" * 40, "$(touch pwned)" + "0" * 26])
def test_claim_refuses_a_bad_script_blob(tmp_path: Path, bad: str) -> None:
    remote = remote_with_script(tmp_path)
    base = head(remote)
    repo = checkout(tmp_path, remote, "claim")
    assert run_job(tmp_path, repo, "claim", {"render.script_id": ID, "render.script_blob": bad}) != 0
    assert head(remote) == base
    assert not (repo / "pwned").exists()


@shell_tools
@pytest.mark.parametrize("changed", ["before-the-claim", "during-the-claim"])
def test_claim_refuses_a_script_version_that_was_not_rendered(tmp_path: Path, changed: str) -> None:
    """during-the-claim: the local check passes, the push is rejected, and the rebase brings the
    new version, so only the re-check after `pull --rebase` can refuse."""
    remote = remote_with_script(tmp_path)
    rendered = claim_outputs(remote)
    if changed == "before-the-claim":
        edit_script(tmp_path, remote)
    repo = checkout(tmp_path, remote, "claim")
    if changed == "during-the-claim":
        edit_script(tmp_path, remote)
    base = head(remote)
    assert blob(remote) != rendered["render.script_blob"]
    assert run_job(tmp_path, repo, "claim", rendered) != 0
    assert head(remote) == base and RECORD not in files(remote)
```

And after `test_record_leaves_the_claim_when_the_upload_is_unknown`:

```python
@shell_tools
def test_record_keeps_the_claim_when_the_script_changed(tmp_path: Path) -> None:
    """The ledger never archives a version other than the one claimed and uploaded."""
    remote = claimed(tmp_path)
    claim_sha = PublishRecord.model_validate_json(show(remote, RECORD)).script_sha
    edit_script(tmp_path, remote)
    base, before = head(remote), record_on_main(remote)
    repo = checkout(tmp_path, remote, "record")
    outputs = {"render.script_id": ID, "upload.video_id": VIDEO, "upload.sent": ""}
    assert run_job(tmp_path, repo, "record", outputs) != 0
    assert (head(remote), record_on_main(remote)) == (base, before)
    assert SCRIPT in files(remote) and blob(remote) != claim_sha
```

Note: `edit_script` calls `change_main`, which clones into `tmp_path / "change"`; each test calls it at most once, so the clone name does not collide.

Checked by reading against the workflow at 7cc568d: every new test fails if its guard is removed (bad blob: the regex; before-the-claim: the first hash check; during-the-claim: the re-check after `pull --rebase`, since without it the rebased commit pushes cleanly; record: the `script_sha` comparison, since without it `git mv` succeeds on the changed file). The existing success tests pass against the strict claim once they carry the blob.
