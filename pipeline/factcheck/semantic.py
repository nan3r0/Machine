"""Meaning fact-check layer (PLAN.md section 5, task p2-semantic): one checker call per script.

Calls Gemini only through the module (`gemini.generate_json`), so tests can fake it. The checker
is asked for `{"verdicts": [{"index": int, "verdict": "SUPPORTED" | "UNSUPPORTED" | "PARTIAL",
"reason": str, "fact_ids": [int]}]}` (top-level `properties` of the schema exactly `verdicts`).
"""

from collections.abc import Sequence

from pipeline.schema import Fact, LineVerdict, Script


def check_script(script: Script, facts: Sequence[Fact]) -> list[LineVerdict]:
    """One verdict per scene of `script`, in scene order, from exactly one call to
    `gemini.generate_json(constants.CHECKER_MODEL, prompt, schema, constants.CHECKER_TEMPERATURE)`.

    The prompt asks, for each scene, "Does the source reasonably support this statement? Ignore
    rewording. Answer SUPPORTED / UNSUPPORTED / PARTIAL with a one-line reason", and to name the
    supporting fact ids. Each scene's narration goes with its linked facts (the `facts` whose id is
    in its source_fact_ids), all inside a delimited data block.

    A broken answer is never a pass. A scene whose verdict is missing, repeated, malformed or of an
    unknown kind, or that names no fact id or a fact id not linked to that scene, gets UNSUPPORTED
    with a reason saying why. Reasons are clipped to `constants.REASON_MAX_CHARS`. GeminiError
    propagates; the batch decides.
    """
    raise NotImplementedError
