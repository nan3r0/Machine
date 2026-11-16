"""Checks a script must pass before it is voiced or published (CSO P1-3, phase review N5).

Task p2-validate. Pure function, no IO. Numbers come from pipeline/constants.py.
"""

from pipeline.schema import Script


def problems(script: Script) -> list[str]:
    """Every reason `script` may not be published, one short line each naming the field
    (for example "title: 104 characters, at most 100"). Empty means the script is fine.

    Rules:
    - Word count of `script.narration_words()` inside `TIKTOK_WORDS` (inclusive), and
      `len(script.narration_text())` at most `NARRATION_MAX_CHARS`.
    - At most `SCENES_MAX` scenes.
    - Title at most `TITLE_MAX_CHARS` characters, description at most `DESCRIPTION_MAX_CHARS`, at
      most `TAGS_MAX` tags, each non-blank and at most `TAG_MAX_CHARS`, `TAGS_TOTAL_MAX_CHARS` summed.
    - Spoken and published fields (title, description, every tag, hook, every scene's narration and
      on_screen_text, loop_line) contain no URL: no `://` and no `www.` (any case).
    - The same fields contain no `<` or `>` (YouTube rejects them in titles and descriptions, and in
      the PR body they could hide text as HTML), no control character (Unicode category Cc, except a
      newline in the description), and no format, private-use or surrogate character (Cf, Co, Cs:
      bidi controls and zero-width characters).
    """
    raise NotImplementedError
