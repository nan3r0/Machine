"""Phase 3 slice 1 numbers and the host asset (task p3-contracts).

Expected values come from .harness/handoffs/p3-plan.md, p3-spike.md, the owner's decisions of
2026-11-25 and 2026-11-26 and the approved host.yaml, never from code under test.
"""

import hashlib
from pathlib import Path
from typing import get_args

import yaml

from pipeline import constants as c
from pipeline.schema import Template
from pipeline.visuals import art

ROOT = Path(__file__).resolve().parent.parent
HOST = ROOT / "assets" / "character" / "host.yaml"


def host_box() -> tuple[float, float, float, float]:
    """Screen left, top, right, bottom of the host's art box at its placement, read from the YAML."""
    raw = yaml.safe_load(HOST.read_text(encoding="utf-8"))
    gx, gy = raw["anchors"]["ground"]
    width, height = raw["size"]["width"], raw["size"]["height"]
    left = c.HOST_GROUND_X - gx * c.HOST_SCALE
    top = c.HOST_GROUND_Y - gy * c.HOST_SCALE
    return left, top, left + width * c.HOST_SCALE, top + height * c.HOST_SCALE


def max_outline() -> int:
    return max(shape.outline for shape in art.load_host(HOST).all_shapes())


def test_ids_are_the_approved_lists() -> None:
    assert c.SET_IDS == ("night_street", "desert_rail", "lamp_room", "shore_night", "forest", "archive")
    assert c.POSES == ("talk", "wave", "point", "surprised", "think", "shrug")
    assert c.CAMERA_MOVES == ("push_in", "pan_left", "pan_right", "still")
    assert c.HOST_BACKDROP_SET not in c.SET_IDS
    assert c.DEFAULT_POSE == "talk" and c.DEFAULT_CAMERA == "push_in"
    assert {c.HOST_INTRO_POSE, c.HOST_OUTRO_POSE} <= set(c.POSES)
    assert set(c.DEFAULT_SET) == set(get_args(Template))
    assert set(c.DEFAULT_SET.values()) <= set(c.SET_IDS)


def test_host_timing_matches_the_owner_addendum() -> None:
    assert 3.0 <= c.HOST_INTRO_MAX_S <= 5.0
    assert 0 < c.HOST_OUTRO_MAX_S <= 5.0
    assert c.SCENE_FADE_S == 0.3
    assert c.SCENE_FADE_S <= c.HOST_TRANSITION_S <= 1.0
    assert c.SCENE_TAIL_S >= c.MAX_SILENCE_S


def test_camera_numbers_from_the_spike() -> None:
    assert c.SET_DEPTHS == ("far", "mid", "near")
    assert c.DRIFT_PX_PER_S == {"far": 6.0, "mid": 14.0, "near": 30.0}
    for speeds in (c.DRIFT_PX_PER_S, c.PAN_PX_PER_S):
        assert speeds["far"] < speeds["mid"] < speeds["near"], "deeper layers drift less"
    assert all(c.PAN_PX_PER_S[d] > c.DRIFT_PX_PER_S[d] for d in c.SET_DEPTHS)
    assert c.SET_LAYER_MARGIN_PX == 120
    assert c.PUSH_IN_SCALE == 1.08
    assert c.SET_LAYERS == (2, 4) and c.SET_SHAPES_MAX == 25
    assert (c.BLINK_S, c.BLINK_EVERY_S, c.BLINK_FIRST_S) == (0.2, 3.6, 2.2)
    assert (c.BOB_PX, c.ARM_SWING_DEG, c.IDLE_HALF_CYCLE_S) == (10, 15.0, 0.4)
    assert c.COUNTER_STEPS * c.COUNTER_STEP_S <= c.HOST_INTRO_MAX_S


def test_ass_layers_go_back_to_front() -> None:
    order = [c.ASS_LAYER_SET, c.ASS_LAYER_DIM, c.ASS_LAYER_CARD, c.ASS_LAYER_HOST, c.ASS_LAYER_FADE]
    assert order == sorted(set(order))
    assert c.ASS_LAYER_SET + c.SET_LAYERS[1] <= c.ASS_LAYER_DIM
    assert c.ASS_LAYER_HOST + 19 < c.ASS_LAYER_FADE, "host art layers are 0 to 19"


def test_captions_in_the_lower_half_inside_the_locked_range() -> None:
    assert c.HEIGHT / 2 < c.CAPTION_POS_Y <= c.SAFE_BOTTOM_PX - 2 * c.CAPTION_FONT_SIZE
    assert c.CAPTION_BAND_TOP_PX == c.CAPTION_POS_Y - 2 * c.CAPTION_FONT_SIZE


def test_host_is_in_frame_and_clear_of_the_captions() -> None:
    left, top, right, bottom = host_box()
    assert top - c.BOB_PX >= c.SAFE_TOP_PX, "head clear of the top UI zone, bob included"
    assert c.SAFE_LEFT_PX <= left and right <= c.SAFE_RIGHT_PX, "clear of the right UI zone"
    assert bottom + max_outline() <= c.CAPTION_BAND_TOP_PX, "feet and shadow above two caption lines"


def test_data_panel_is_inside_the_safe_zone_above_the_captions() -> None:
    left, top, right, bottom = c.DATA_PANEL
    assert c.SAFE_LEFT_PX <= left < right <= c.SAFE_RIGHT_PX
    assert c.SAFE_TOP_PX <= top < bottom <= c.CAPTION_BAND_TOP_PX
    assert c.CARD_FONT_SIZE * 2 <= right - left


def test_item_caps_fit_one_full_scene() -> None:
    per_item = c.VISUAL_LABEL_MAX_CHARS + c.VISUAL_VALUE_MAX_CHARS
    assert c.VISUAL_ITEMS_MAX == 4
    assert c.VISUAL_ITEMS_MAX * per_item <= c.VISUAL_TEXT_MAX_CHARS
    assert c.VISUAL_VALUE_MAX_CHARS >= len("1,000,000")


def test_seven_scripts_at_every_cap_fit_the_pr_body() -> None:
    """Extends tests/script/test_batch.py::test_body_at_every_cap_fits. Phase 2 worst case: 6920
    characters of fields a script (titles 200, narration 1500, facts 2600, description 1000, tags
    300, 11 flags 1320), and the body built from them measured 51441 for 7 scripts on 2026-11-26.
    Phase 3 adds per scene a same-line set and pose code span, and per data scene up to
    VISUAL_ITEMS_MAX label and value spans plus one exact-check flag."""
    span = 4  # "` " and " `" around a span with no backtick in it
    measured_phase2 = 51_441
    longest_set = max(len(s) for s in c.SET_IDS)
    longest_pose = max(len(p) for p in c.POSES)
    per_scene = 3 + 2 * span + longest_set + longest_pose
    items = c.VISUAL_DATA_SCENES_MAX * c.VISUAL_ITEMS_MAX
    flag = c.REASON_MAX_CHARS + 20  # "- Scene n: " and a span
    per_script = (c.SCENES_MAX * per_scene + c.VISUAL_TEXT_MAX_CHARS + items * 2 * (span + 2)
                  + c.VISUAL_DATA_SCENES_MAX * flag)
    total = measured_phase2 + c.SCRIPTS_PER_BATCH * per_script
    assert total <= c.PR_BODY_MAX_CHARS, f"{total} characters"


def test_render_budget_and_strip() -> None:
    assert c.RENDER_BUDGET_S == c.COMPOSE_TIMEOUT_S / 2
    assert (c.GOLDEN_STRIP_FRAMES, c.GOLDEN_STRIP_STEP_S) == (8, 0.25)


def test_host_asset_is_the_approved_file() -> None:
    """The licence row hashes the committed LF file; a Windows checkout may hold CRLF."""
    digest = hashlib.sha256(HOST.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert digest in (ROOT / "assets" / "LICENSES.md").read_text(encoding="utf-8")


def test_host_asset_validates() -> None:
    host = art.load_host(HOST)
    assert set(host.poses) == set(c.POSES)
    assert set(host.talking_mouths) - {"rest"}, "lip sync needs an open mouth"
    assert host.anchors["ground"] == (279, 802)


def test_acceptance() -> None:
    test_ids_are_the_approved_lists()
    test_host_timing_matches_the_owner_addendum()
    test_camera_numbers_from_the_spike()
    test_ass_layers_go_back_to_front()
    test_captions_in_the_lower_half_inside_the_locked_range()
    test_host_is_in_frame_and_clear_of_the_captions()
    test_data_panel_is_inside_the_safe_zone_above_the_captions()
    test_item_caps_fit_one_full_scene()
    test_seven_scripts_at_every_cap_fit_the_pr_body()
    test_render_budget_and_strip()
    test_host_asset_is_the_approved_file()
    test_host_asset_validates()
