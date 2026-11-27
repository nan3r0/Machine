"""The host character (task p3-character): mouth on word timings, blinks, every pose, same anchor."""

import pytest

from pipeline import constants as c
from pipeline.schema import WordTiming
from pipeline.visuals import art, character
from tests.visuals.ass_parse import Event, drawing, events, pos, visible

HOST = art.load_host()
# Words 0.5 to 0.9, 1.0 to 1.4, ... with a 0.1 s gap, then a long pause from 4.5 to 6.0.
WORDS = [WordTiming(word=f"w{i}", start=0.5 + 0.5 * i, end=0.9 + 0.5 * i) for i in range(8)]
WORDS.append(WordTiming(word="late", start=6.0, end=6.4))


def part_key(table: dict[str, list[art.Shape]], shown: list[Event]) -> list[str]:
    paths = {drawing(e.text) for e in shown}
    return [
        key
        for key, shapes in table.items()
        if all(s.path in paths for s in shapes)
        and not any(
            s.path in paths
            for k, other in table.items()
            if k != key
            for s in other
            if s.path not in {x.path for x in shapes}
        )
    ]


def host(pose: str = "talk", start: float = 0.0, end: float = 8.0) -> list[Event]:
    return events(character.host_events(HOST, start, end, pose, WORDS))


def test_events_stay_in_the_window_and_host_layers() -> None:
    evs = host(start=1.0, end=7.0)
    assert evs and all(1.0 <= e.start <= e.end <= 7.0 for e in evs)
    assert all(c.ASS_LAYER_HOST <= e.layer <= c.ASS_LAYER_HOST + 19 for e in evs)


def test_mouth_talks_on_words_and_rests_between() -> None:
    evs = host()
    for word in WORDS:
        # The mouth flaps inside a word (p3b-host-lipsync), so it need not be open at the midpoint.
        steps = [word.start + k * 0.01 + 0.005 for k in range(round((word.end - word.start) * 100))]
        keys = [part_key(HOST.mouths, visible(evs, t)) for t in steps]
        assert all(len(k) == 1 for k in keys), word
        assert any(k[0] in HOST.talking_mouths and k[0] != "rest" for k in keys), word
    assert part_key(HOST.mouths, visible(evs, 5.2)) == [HOST.poses["talk"].mouth]


def test_blinks_on_the_fixed_pattern() -> None:
    evs = host(start=1.0, end=9.0)
    for k in range(2):
        blink = 1.0 + c.BLINK_FIRST_S + k * c.BLINK_EVERY_S + c.BLINK_S / 2
        assert part_key(HOST.eyes, visible(evs, blink)) == ["closed"]
    assert part_key(HOST.eyes, visible(evs, 1.0 + c.BLINK_FIRST_S - 0.3)) == ["open"]


@pytest.mark.parametrize("pose", c.POSES)
def test_every_pose_shows_body_and_its_arms(pose: str) -> None:
    shown = {drawing(e.text) for e in visible(host(pose), 3.05)}
    spec = HOST.poses[pose]
    assert {s.path for s in HOST.body} <= shown
    if pose != "wave":  # the waving arm rotates, so its path may be drawn under a \frz
        assert {s.path for s in [*spec.arm_left, *spec.arm_right]} <= shown


def test_same_anchor_in_every_scene() -> None:
    ox, oy = character.host_origin()
    gx, gy = HOST.anchors["ground"]
    assert ox == pytest.approx(c.HOST_GROUND_X - gx * c.HOST_SCALE)
    assert oy == pytest.approx(c.HOST_GROUND_Y - gy * c.HOST_SCALE)
    ys = set()
    for start in (0.0, 13.7, 42.1):
        for e in host(start=start, end=start + 3.0):
            x, y = pos(e.text) or (None, None)
            assert x == pytest.approx(ox, abs=0.5)
            assert oy - c.BOB_PX - 0.5 <= y <= oy + 0.5  # type: ignore[operator]
            ys.add(round(y, 1))  # type: ignore[arg-type]
    assert len(ys) > 1, "the idle bob moves the host"


def test_repeatable_and_bad_pose_raises() -> None:
    assert character.host_events(HOST, 0, 5, "think", WORDS) == character.host_events(
        HOST, 0, 5, "think", WORDS
    )
    with pytest.raises(ValueError):
        character.host_events(HOST, 0, 5, "dance", WORDS)


def test_acceptance() -> None:
    test_events_stay_in_the_window_and_host_layers()
    test_mouth_talks_on_words_and_rests_between()
    test_blinks_on_the_fixed_pattern()
    for pose in c.POSES:
        test_every_pose_shows_body_and_its_arms(pose)
    test_same_anchor_in_every_scene()
