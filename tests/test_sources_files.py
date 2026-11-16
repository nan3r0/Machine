"""R8: the hand-curated sources/ files, and the link from queue/ scripts back to them
(task p2-seed-sources, owner decisions D3 and D4).

The checks are written out here rather than taken from pipeline/script/sources.py, so they hold
even if the loader is wrong.
"""

import re
import string
import unicodedata
from pathlib import Path

import yaml

from pipeline import constants
from pipeline.schema import Script, SourceFile

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
QUEUE = ROOT / "queue"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# 14 seeded mysteries (two weekly batches) plus the Bloop source behind the Phase 1 sample.
MIN_FILES = 15


def load_all() -> dict[str, SourceFile]:
    return {path.stem: SourceFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
            for path in sorted(SOURCES.glob("*.yaml"))}


def normalised(topic: str) -> str:
    """Casefold, drop punctuation, collapse whitespace."""
    kept = "".join(" " if unicodedata.category(c).startswith("P") or c in string.punctuation else c
                   for c in topic.casefold())
    return " ".join(kept.split())


def fact_problems(source: SourceFile) -> list[str]:
    found = []
    if len(source.facts) > constants.FACTS_PER_SOURCE_MAX:
        found.append(f"{len(source.facts)} facts")
    for fact in source.facts:
        if len(fact.text) > constants.FACT_TEXT_MAX_CHARS:
            found.append(f"fact {fact.id} text too long")
        if len(fact.url) > constants.FACT_URL_MAX_CHARS:
            found.append(f"fact {fact.id} url too long")
        lowered = fact.text.lower()
        if "://" in lowered or "www." in lowered or any(c in fact.text for c in "<>`"):
            found.append(f"fact {fact.id} text holds a link or markup")
        if any(unicodedata.category(c) in ("Cc", "Cf", "Co", "Cs") for c in fact.text + fact.url):
            found.append(f"fact {fact.id} holds a control or invisible character")
    return found


def queue_fact_ids() -> dict[str, set[int]]:
    return {path.relative_to(QUEUE).as_posix(): {i for scene in script.scenes for i in scene.source_fact_ids}
            for path in sorted(QUEUE.glob("**/*.json"))
            for script in [Script.model_validate_json(path.read_text(encoding="utf-8"))]}


def test_every_file_parses_and_is_named_by_a_slug() -> None:
    sources = load_all()
    assert len(sources) >= MIN_FILES, f"{len(sources)} source files, need {MIN_FILES}"
    assert [slug for slug in sources if not SLUG.match(slug)] == []
    assert list(SOURCES.glob("*.yml")) == [], "use the .yaml extension"


def test_fact_ids_unique_across_files() -> None:
    ids = [fact.id for source in load_all().values() for fact in source.facts]
    assert len(ids) == len(set(ids)), sorted(i for i in set(ids) if ids.count(i) > 1)


def test_topics_unique_after_normalising() -> None:
    topics = [normalised(source.topic) for source in load_all().values()]
    assert len(topics) == len(set(topics)), sorted(t for t in set(topics) if topics.count(t) > 1)


def test_normalising_ignores_case_and_punctuation() -> None:
    assert normalised("The Bloop: Solved!") == normalised("the  bloop solved")
    assert normalised("“Wow!” signal") == normalised("wow signal")


def test_facts_within_caps_and_plain() -> None:
    assert {slug: fact_problems(s) for slug, s in load_all().items() if fact_problems(s)} == {}


def test_queue_fact_ids_resolve_to_one_source() -> None:
    """Every fact id a queued script cites is in sources/, and all of one script's ids come from a
    single source file (spec.md section 3), so the used-source ledger (D3) is exact."""
    owner = {fact.id: slug for slug, source in load_all().items() for fact in source.facts}
    for script, ids in queue_fact_ids().items():
        assert ids, f"{script} cites no fact"
        assert sorted(ids - owner.keys()) == [], f"{script} cites unknown fact ids"
        assert len({owner[i] for i in ids}) == 1, f"{script} cites more than one source"


def test_acceptance() -> None:
    """At least 15 valid source files with slug names, unique fact ids and topics, facts within
    caps, and every queued script traceable to exactly one source."""
    test_every_file_parses_and_is_named_by_a_slug()
    test_fact_ids_unique_across_files()
    test_topics_unique_after_normalising()
    test_facts_within_caps_and_plain()
    test_queue_fact_ids_resolve_to_one_source()
