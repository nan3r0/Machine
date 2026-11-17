"""Hand-curated sources and which of them are still unused (task p2-generate, owner decisions D3, D4).

The queue files are the ledger: a source is used once any of its fact ids appears in a script under
queue/ (approved or published). There is no used_facts.json.
"""

from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import ValidationError

from pipeline.schema import Script, SourceFile


def load_sources(directory: Path) -> dict[str, SourceFile]:
    """Every `directory/*.yaml` parsed as a SourceFile, keyed by file stem (the slug), in stem order.
    The slug becomes the script id. An invalid file raises ValueError naming the file."""
    loaded: dict[str, SourceFile] = {}
    for path in sorted(directory.glob("*.yaml"), key=lambda p: p.stem):
        try:
            loaded[path.stem] = SourceFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except (yaml.YAMLError, ValidationError) as error:
            raise ValueError(f"{path.name}: {error}") from error
    return loaded


def unused_sources(sources: Mapping[str, SourceFile], queue_dir: Path) -> dict[str, SourceFile]:
    """The entries of `sources`, in their order, none of whose fact ids appear in the
    `source_fact_ids` of any script in `queue_dir/**/*.json` (approved/ and published/ alike)."""
    used = {
        fact_id
        for path in queue_dir.glob("**/*.json")
        for scene in Script.model_validate_json(path.read_text(encoding="utf-8")).scenes
        for fact_id in scene.source_fact_ids
    }
    return {slug: source for slug, source in sources.items() if used.isdisjoint(f.id for f in source.facts)}
