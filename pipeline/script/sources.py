"""Hand-curated sources and which of them are still unused (task p2-generate, owner decisions D3, D4).

The queue files are the ledger: a source is used once any of its fact ids appears in a script under
queue/ (approved or published). There is no used_facts.json.
"""

from collections.abc import Mapping
from pathlib import Path

from pipeline.schema import SourceFile


def load_sources(directory: Path) -> dict[str, SourceFile]:
    """Every `directory/*.yaml` parsed as a SourceFile, keyed by file stem (the slug), in stem order.
    The slug becomes the script id. An invalid file raises ValueError naming the file."""
    raise NotImplementedError


def unused_sources(sources: Mapping[str, SourceFile], queue_dir: Path) -> dict[str, SourceFile]:
    """The entries of `sources`, in their order, none of whose fact ids appear in the
    `source_fact_ids` of any script in `queue_dir/**/*.json` (approved/ and published/ alike)."""
    raise NotImplementedError
