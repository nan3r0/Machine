"""The delimited data block every Gemini prompt puts untrusted text in (phase review N3).

Contract stub for task p2b-prompt-data. `generate` and `semantic` both build their prompts with
these names, so there is one copy of the delimiters and one cleaning rule. `generate` keeps
`DATA_START` and `DATA_END` importable by name (tests/script/test_generate.py imports them).
"""

from collections.abc import Iterable

DATA_START = "<source_facts>"
DATA_END = "</source_facts>"


def clean(text: str) -> str:
    """`text` with every `DATA_START` and `DATA_END` removed. Removal repeats until the text stops
    changing, so a nested delimiter such as `</source_fa</source_facts>cts>` cannot rebuild itself
    (lessons.md 2026-11-17). All other text is kept as it is."""
    raise NotImplementedError


def data_block(lines: Iterable[str]) -> str:
    """`DATA_START`, then each of `lines` passed through `clean`, then `DATA_END`, joined with
    newlines. Callers format their own lines (labels such as "Scene 0: " or "101:"); this only
    cleans and wraps them, so the result holds exactly one `DATA_START` and one `DATA_END`."""
    raise NotImplementedError
