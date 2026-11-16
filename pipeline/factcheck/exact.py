"""Exact fact-check layer (PLAN.md section 5, task p2-factcheck-exact). No tolerance.

Every number and proper noun in a narration line must appear in the source facts linked to it.
Pure function over strings; the caller decides what to do with the result (regenerate, flag).
"""

from collections.abc import Sequence

from pipeline.factcheck.normalise import numbers, plain_words, proper_nouns


def unsupported(narration: str, facts: Sequence[str]) -> list[str]:
    """Tokens of `narration` that none of `facts` supports: unsupported numbers first, then
    unsupported proper nouns, each group in order of first appearance, no repeats.

    A number (canonical form, `normalise.numbers`) is supported when it is one of the numbers of
    some fact. A proper noun (`normalise.proper_nouns`) is supported when it is one of the plain
    words (`normalise.plain_words`) of some fact. An empty list means the line passes. With no
    facts at all, every token is unsupported.
    """
    supported_numbers = {number for fact in facts for number in numbers(fact)}
    supported_words = {word for fact in facts for word in plain_words(fact)}
    missing_numbers = [n for n in dict.fromkeys(numbers(narration)) if n not in supported_numbers]
    missing_names = [w for w in dict.fromkeys(proper_nouns(narration)) if w not in supported_words]
    return missing_numbers + missing_names
