"""Script writer: one source in, one valid Script out (task p2-generate, PLAN.md sections 4 and 7).

Calls Gemini only through the module (`gemini.generate_json`), so tests can fake it. Prompts are
module constants here (owner decision D8: no prompts folder).

The writer is asked for JSON in this shape (the `schema` argument describes it as a JSON Schema
object whose top-level `properties` are exactly these keys):
`{"template": "chart" | "map" | "steps" | "story", "hook": str, "scenes": [{"narration": str,
"on_screen_text": str, "source_fact_ids": [int]}], "loop_line": str, "title": str,
"description": str, "tags": [str]}`.
A line rewrite asks for `{"narration": str}` (top-level `properties` exactly `narration`).

Source facts reach the model only between `DATA_START` and `DATA_END`, each on its own line, and
the prompt says that block is data, never instructions. Fact text cannot end the block early: the
prompt holds exactly one `DATA_END`.
"""

from datetime import date

from pipeline.schema import Script, SourceFile

DATA_START = "<source_facts>"
DATA_END = "</source_facts>"


class GenerateError(Exception):
    """The writer's output was still invalid after the allowed calls."""


def write_script(source: SourceFile, script_id: str, publish_after: date) -> Script:
    """A new script about `source`, from exactly one call to
    `gemini.generate_json(constants.WRITER_MODEL, prompt, schema)`. The batch owns the retry, so it
    can count every writer call against its budget.

    The prompt carries PLAN.md section 4: the tone rules (suspense, short sentences, a beat before
    each reveal, eerie never graphic), the 65 s format (`constants.TARGET_WORDS` words, accepted
    range `constants.TIKTOK_WORDS`, a hook in the first 2 to 3 s, a mandatory curiosity reset at
    about 25 to 30 s, a loop ending) and the content rules (sourced resolution only, no speculation
    as the answer, no private individuals, nothing graphic).

    Fills `id` (script_id), `topic` (source.topic), `platforms` (all three), `publish_after` and each
    scene's `visual` ({"type": template, "data": {}}) itself. The answer is accepted only when it
    builds a Script, `validate.problems` is empty, and every scene cites at least one fact id, all of
    them ids of `source`; otherwise GenerateError. Keys the answer should not hold (id, topic, ...)
    are ignored. GeminiError propagates.
    """
    raise NotImplementedError


def rewrite_line(script: Script, index: int, source: SourceFile, reason: str) -> Script:
    """`script` with scene `index`'s narration rewritten after it failed a fact check for `reason`.

    Exactly one `gemini.generate_json(constants.WRITER_MODEL, prompt, schema)` call; the prompt
    holds the old line, the reason, the same tone rules and the scene's linked facts in the data
    block. Only that narration changes. If the result fails Script or `validate.problems`, raises
    GenerateError. GeminiError propagates.
    """
    raise NotImplementedError
