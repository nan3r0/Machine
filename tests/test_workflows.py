"""R7.1 structure: the render workflow (task p1-actions-workflow). The run itself is checked by hand."""

from pathlib import Path

from tests import workflow_rules as rules

ROOT = Path(__file__).resolve().parent.parent


def test_acceptance() -> None:
    """Manual dispatch with a script input, renders with the CLI, uploads the output."""
    wf = rules.load("render.yml")
    rules.assert_safe(wf)
    dispatch = wf["on"]["workflow_dispatch"]
    script_input = dispatch["inputs"]["script"]
    assert (ROOT / script_input["default"]).exists()
    assert set(wf["on"]) == {"workflow_dispatch"}, "render runs only by hand in Phase 1"
    assert all(job["runs-on"] == "ubuntu-latest" for job in wf["jobs"].values())
    assert "python -m pipeline.render_one" in rules.run_text(wf)


def test_installs_ffmpeg_and_heavy_requirements() -> None:
    text = rules.run_text(rules.load("render.yml"))
    assert "ffmpeg" in text
    plain = "-r requirements.txt" in text and "-r requirements-heavy.txt" in text
    assert plain or "-r requirements-render.txt" in text, "the hashed lock covers both files"


def test_caches_models_and_pip() -> None:
    wf = rules.load("render.yml")
    used = [s.get("uses", "") for s in rules.steps(wf)]
    assert any(u.startswith("actions/cache@") for u in used), "model weights must be cached"
    assert any(u.startswith("actions/setup-python@") for u in used)
    assert "--cache-dir" in rules.run_text(wf)
    rules.assert_model_cache_tracks_pins(wf)


def test_installs_torch_from_cpu_index_only() -> None:
    rules.assert_torch_from_cpu_index_first(rules.run_text(rules.load("render.yml")))


def test_uploads_output_with_short_retention() -> None:
    uploads = [s for s in rules.steps(rules.load("render.yml"))
               if s.get("uses", "").startswith("actions/upload-artifact@")]
    assert uploads
    for step in uploads:
        assert step["with"].get("if-no-files-found") == "error"
        assert 1 <= int(step["with"]["retention-days"]) <= 7


def test_script_input_reaches_the_cli_through_env() -> None:
    wf = rules.load("render.yml")
    render = [s for s in rules.steps(wf) if "pipeline.render_one" in str(s.get("run", ""))]
    assert render
    assert "inputs.script" in str(render[0].get("env", {}))


def test_no_secrets_in_phase_1() -> None:
    assert "secrets." not in (ROOT / ".github" / "workflows" / "render.yml").read_text(encoding="utf-8")
