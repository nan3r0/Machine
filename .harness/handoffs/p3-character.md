# Handoff: p3-character (Implementer)

## Goal
Animate the host as libass events: pose arms, blinks, idle bob, mouth on word timings (`pipeline/visuals/character.py`).

## Status
done. Light tests green; no heavy test covers this task (the render check is p3's own heavy test, CI).

## What changed
- `pipeline/visuals/character.py`: `host_origin()` and `host_events()`.
  - The window is cut at every bob half-cycle, blink edge and word edge (rounded to centiseconds). Each segment emits body, face (eyes, brows, mouth) and both arms through `ass_kit.shape_event`.
  - Bob: triangle wave, one `\move` per segment from the level at its start to the level at its end, so motion is smooth.
  - Wave: right arm adds `\org` at the shoulder anchor and `\frz` swinging +/-ARM_SWING_DEG with `\t`, in step with the bob.
  - Mouth: talking mouths other than "rest", cycled by word index; the pose mouth between words.

## Decisions made
- Segments are cut at every bob half-cycle, so a pose is about 45 events per 0.4 s. The `\move` keeps the motion smooth; the cost is event count (about 2000 for an 8 s window).
- `\org` is set at the segment's mid-bob y, so the pivot is off by at most BOB_PX/2 (under 1.5 px of arm error at the swing angle).
- `host_origin()` takes no argument (locked signature), so it loads the host asset each call.

## Tried and abandoned
none

## Known risks
- Event count: if the heavy render timing test is slow, merge static parts across bob segments or use `\t` for the bob.
- Wave swing direction (sign of `\frz`) was not looked at in a render.

## Next step
CI heavy render once the scene composer (later task) uses `host_events`.

## Docs
none

## Evidence
- ruff clean; mypy --strict pipeline/ clean; pytest 1681 passed, 233 skipped (heavy); tests/visuals/test_character.py 12 passed.
