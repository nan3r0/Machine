"""The host's lip flap follows the voice's loudness (task p3b-host-lipsync).

Owner 2026-11-27: closed in silence and between syllables, a few mouth shapes, changing at about
syllable rate, never held open long. The levels below stand in for voice_levels(voice.wav): one
value per MOUTH_WINDOW_S. The word timings are deliberately off the sound, as aligner timings
can be: the first word starts before the sound and the last word ends 0.5 s into silence.
"""

import re

import pytest

from pipeline import constants as c
from pipeline.schema import WordTiming
from pipeline.visuals import character
from tests.visuals.ass_parse import Event, drawing, events, visible
from tests.visuals.test_character import HOST, WORDS, part_key

W = c.MOUTH_WINDOW_S
SYLLABLES = 16
LOUD = (0.4, 0.6, 0.9, 1.0)
SPEECH = (0.48, 0.48 + SYLLABLES * 6 * W)  # each syllable: 4 windows loud, 2 windows dip
VOWEL = (6.0, 7.0)  # one sustained loud vowel
END = 8.5


def windows(seconds: float, level: float) -> list[float]:
    return [level] * round(seconds / W)


LEVELS = windows(SPEECH[0], 0.0)
for k in range(SYLLABLES):
    LEVELS += windows(4 * W, LOUD[k % len(LOUD)]) + windows(2 * W, 0.05)
LEVELS += windows(VOWEL[0] - SPEECH[1], 0.0) + windows(VOWEL[1] - VOWEL[0], 0.9)
LEVELS += windows(0.8, 0.0) + windows(0.12, 1.0)  # a click at 7.8 s, after the narration
TIMINGS = [WordTiming(word=f"w{i}", start=0.3 + 0.64 * i, end=0.3 + 0.64 * (i + 1)) for i in range(6)]
TIMINGS.append(WordTiming(word="late", start=VOWEL[0], end=VOWEL[1] + 0.5))
STEPS = [k * 0.01 + 0.005 for k in range(round(END * 100))]


def mouths(evs: list[Event]) -> list[str]:
    """The one mouth key shown at each STEPS time."""
    keys = [part_key(HOST.mouths, visible(evs, t)) for t in STEPS]
    assert all(len(k) == 1 for k in keys), "exactly one mouth at a time"
    return [k[0] for k in keys]


def host(pose: str = "talk", levels: list[float] | None = LEVELS,
         timings: list[WordTiming] = TIMINGS) -> list[str]:
    return mouths(events(character.host_events(HOST, 0.0, END, pose, timings, levels=levels)))


def is_open(key: str) -> bool:
    return key not in c.HOST_CLOSED_MOUTHS


def runs(keys: list[str]) -> list[tuple[float, float, str]]:
    """(start, end, key) of each stretch of equal keys over STEPS."""
    out: list[tuple[float, float, str]] = []
    for t, key in zip(STEPS, keys, strict=True):
        if out and out[-1][2] == key:
            out[-1] = (out[-1][0], t + 0.005, key)
        else:
            out.append((t - 0.005, t + 0.005, key))
    return out


def open_onsets(keys: list[str], lo: float, hi: float) -> int:
    return sum(
        1 for i in range(1, len(keys))
        if lo <= STEPS[i] < hi and is_open(keys[i]) and not is_open(keys[i - 1])
    )


def at(keys: list[str], lo: float, hi: float) -> list[str]:
    return [k for t, k in zip(STEPS, keys, strict=True) if lo <= t < hi]


@pytest.mark.parametrize("pose", c.POSES)
def test_closed_in_silence_and_outside_the_narration(pose: str) -> None:
    keys = host(pose)
    margin = c.MOUTH_HOLD_S + W  # an open mouth may finish its hold after the sound stops
    for lo, hi in ((0.0, SPEECH[0]), (SPEECH[1] + margin, VOWEL[0]), (VOWEL[1] + margin, END)):
        assert not any(is_open(k) for k in at(keys, lo, hi)), (pose, lo, hi)
    closed = HOST.poses[pose].mouth if HOST.poses[pose].mouth in c.HOST_CLOSED_MOUTHS else "rest"
    assert set(at(keys, SPEECH[1] + margin, VOWEL[0])) == {closed}, pose


def test_closes_between_syllables_at_their_rate() -> None:
    keys = host()
    onsets = open_onsets(keys, SPEECH[0] - W, SPEECH[1])
    assert SYLLABLES - 2 <= onsets <= SYLLABLES + 1, onsets
    rate = onsets / (SPEECH[1] - SPEECH[0])
    assert 3.0 <= rate <= 8.0, f"{rate:.1f} openings a second"


def test_never_open_past_the_cap() -> None:
    keys = host()
    longest = max(e - s for s, e, k in runs([str(is_open(k)) for k in keys]) if k == "True")
    assert longest <= c.MOUTH_OPEN_MAX_S + 0.02, f"open for {longest:.2f} s"
    vowel = at(keys, VOWEL[0], VOWEL[1])
    assert sum(map(is_open, vowel)) >= len(vowel) / 2, "a long vowel keeps the mouth mostly open"
    assert open_onsets(keys, VOWEL[0], VOWEL[1]) >= 3, "and flaps it rather than holding it"


def test_no_flicker() -> None:
    keys = host()
    for s, e, key in runs(keys)[1:-1]:
        assert e - s >= c.MOUTH_HOLD_S - 0.011, (s, e, key)


def test_louder_opens_wider() -> None:
    keys = host()
    shown = {k for k in at(keys, SPEECH[0], SPEECH[1]) if is_open(k)}
    assert shown <= set(HOST.talking_mouths) - {"rest"} and len(shown) >= 2, shown
    wide = next(key for level, key in c.MOUTH_SHAPES if 0.9 >= level)
    assert {k for k in at(keys, VOWEL[0] + 0.1, VOWEL[1]) if is_open(k)} == {wide}


def test_without_levels_the_word_spans_drive_the_flap() -> None:
    keys = host(levels=None, timings=WORDS)
    for w in WORDS:
        assert any(is_open(k) for k in at(keys, w.start, w.end)), w
    longest = max(e - s for s, e, k in runs([str(is_open(k)) for k in keys]) if k == "True")
    assert longest <= c.MOUTH_OPEN_MAX_S + 0.02, f"open for {longest:.2f} s"
    margin = c.MOUTH_HOLD_S + W
    pause = (WORDS[7].end + margin, WORDS[8].start)
    for lo, hi in ((0.0, WORDS[0].start - W), pause, (WORDS[-1].end + margin, END)):
        assert not any(is_open(k) for k in at(keys, lo, hi)), (lo, hi)


def bob_y(e: Event, t: float) -> float:
    found = re.search(r"\\move\((-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\)", e.text)
    assert found, e.text
    y0, y1 = float(found.group(2)), float(found.group(4))
    return y0 + (y1 - y0) * (t - e.start) / (e.end - e.start)


def test_every_shape_at_one_bob_height() -> None:
    evs = events(character.host_events(HOST, 0.0, END, "talk", TIMINGS, levels=LEVELS))
    for t in STEPS[::7]:
        ys = [bob_y(e, t) for e in visible(evs, t)]
        assert max(ys) - min(ys) <= 0.6, t


def test_mouth_events_do_not_recut_the_body() -> None:
    """Body shapes change event only on bob half-cycles and blinks, so a flap costs a few events."""
    text = character.host_events(HOST, 0.0, END, "talk", TIMINGS, levels=LEVELS)
    body = HOST.body[0].path
    cuts = len([line for line in text if body in line])
    blinks = int((END - c.BLINK_FIRST_S) / c.BLINK_EVERY_S) + 1
    assert cuts <= END / c.IDLE_HALF_CYCLE_S + 2 * blinks + 3, cuts


def test_repeatable() -> None:
    once = character.host_events(HOST, 0.0, END, "wave", TIMINGS, levels=LEVELS)
    assert once == character.host_events(HOST, 0.0, END, "wave", TIMINGS, levels=list(LEVELS))


def test_scene_start_off_the_centisecond_grid() -> None:
    """Aligner times carry 3 decimals; the mouth must still show exactly once, never a 0 s event."""
    evs = events(character.host_events(HOST, 1.201, 5.0, "talk", TIMINGS, levels=LEVELS))
    mouth_paths = {s.path for shapes in HOST.mouths.values() for s in shapes}
    mouth_evs = [e for e in evs if drawing(e.text) in mouth_paths]
    assert mouth_evs and all(e.end > e.start for e in mouth_evs)
    for t in (1.205, 1.215, *STEPS[121:500:7]):
        assert len(part_key(HOST.mouths, visible(evs, t))) == 1, t


def test_shape_change_just_before_the_cap_still_closes_on_time() -> None:
    """A wide-to-o change one window before MOUTH_OPEN_MAX_S must not hold the mouth open longer."""
    cap = round(c.MOUTH_OPEN_MAX_S / W)
    levels = windows(0.4, 0.0) + windows((cap - 1) * W, 0.9) + windows(1.0, 0.6)
    keys = host(levels=levels, timings=[WordTiming(word="long", start=0.0, end=2.0)])
    assert {"wide", "o"} <= set(keys), "the mouth changes shape while open"
    longest = max(e - s for s, e, k in runs([str(is_open(k)) for k in keys]) if k == "True")
    assert longest <= c.MOUTH_OPEN_MAX_S + 0.02, f"open for {longest:.2f} s"
    for s, e, key in runs(keys)[1:-1]:
        assert e - s >= c.MOUTH_HOLD_S - 0.011, (s, e, key)


def test_acceptance() -> None:
    for pose in ("talk", "wave", "surprised"):
        test_closed_in_silence_and_outside_the_narration(pose)
    test_closes_between_syllables_at_their_rate()
    test_never_open_past_the_cap()
    test_no_flicker()
    test_without_levels_the_word_spans_drive_the_flap()
    test_every_shape_at_one_bob_height()
