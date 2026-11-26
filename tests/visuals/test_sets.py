"""Set layers (task p3-sets): drift within the margin, deeper layers drift less, push-in centred,
fade at each scene start."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pipeline import constants as c
from pipeline.visuals import sets
from pipeline.visuals.art import SetArt
from tests.visuals.ass_parse import drawing, events, move

ART = SetArt.model_validate(
    {
        "name": "fixture",
        "outline_colour": "ink",
        "palette": {"ink": "000000", "sky": "223344"},
        "layers": [
            {
                "depth": "far",
                "shapes": [
                    {
                        "layer": 0,
                        "fill": "sky",
                        "outline": 0,
                        "path": "m -120 0 l 1200 0 l 1200 900 l -120 900",
                    }
                ],
            },
            {
                "depth": "near",
                "shapes": [
                    {"layer": 1, "fill": "ink", "outline": 2, "path": "m 0 1000 l 500 1000 l 500 1900"},
                    {"layer": 1, "fill": "ink", "outline": 0, "path": "m 600 1000 l 900 1000 l 900 1900"},
                ],
            },
        ],
    }
)
SHAPE_PATHS = {s.path for layer in ART.layers for s in layer.shapes}


@given(st.sampled_from(c.SET_DEPTHS), st.sampled_from(c.CAMERA_MOVES), st.floats(0, 120))
def test_drift_never_exceeds_the_margin(depth: str, camera: str, seconds: float) -> None:
    assert abs(sets.drift_px(depth, camera, seconds)) <= c.SET_LAYER_MARGIN_PX


@given(st.sampled_from(c.CAMERA_MOVES), st.floats(0, 60))
def test_deeper_layers_drift_less(camera: str, seconds: float) -> None:
    far, mid, near = (abs(sets.drift_px(d, camera, seconds)) for d in c.SET_DEPTHS)
    assert far <= mid <= near


def test_drift_direction_and_speed() -> None:
    assert sets.drift_px("mid", "push_in", 2.0) == pytest.approx(-28.0)
    assert sets.drift_px("mid", "pan_right", 2.0) == pytest.approx(-56.0)
    assert sets.drift_px("mid", "pan_left", 2.0) == pytest.approx(56.0)
    assert sets.drift_px("near", "push_in", 20.0) == pytest.approx(-c.SET_LAYER_MARGIN_PX)
    assert sets.drift_px("far", "still", 9.0) == 0
    with pytest.raises(ValueError):
        sets.drift_px("far", "zoom", 1.0)


@pytest.mark.parametrize("camera", c.CAMERA_MOVES)
def test_every_shape_moves_by_its_drift(camera: str) -> None:
    evs = events(sets.set_events(ART, 10.0, 17.0, camera))
    shapes = [e for e in evs if drawing(e.text) in SHAPE_PATHS]
    assert len(shapes) == len(SHAPE_PATHS)
    for e in shapes:
        assert (e.start, e.end) == (10.0, 17.0)
        depth = next(layer.depth for layer in ART.layers if drawing(e.text) in {s.path for s in layer.shapes})
        x0, y0, x1, y1 = move(e.text)  # type: ignore[misc]
        assert x1 - x0 == pytest.approx(sets.drift_px(depth, camera, 7.0), abs=0.5) and y0 == y1
    far = [e.layer for e in shapes if drawing(e.text) in {s.path for s in ART.layers[0].shapes}]
    near = [e.layer for e in shapes if drawing(e.text) in {s.path for s in ART.layers[1].shapes}]
    assert c.ASS_LAYER_SET <= max(far) < min(near) < c.ASS_LAYER_DIM


def test_push_in_is_centred_and_other_cameras_do_not_scale() -> None:
    scale = f"\\fscx{c.PUSH_IN_SCALE * 100:g}"
    for e in events(sets.set_events(ART, 0, 7, "push_in")):
        if drawing(e.text) in SHAPE_PATHS:
            assert f"\\org({c.WIDTH // 2},{c.HEIGHT // 2})" in e.text and "\\t(" in e.text and scale in e.text
    for camera in ("still", "pan_left", "pan_right"):
        assert not any("\\t(" in e.text for e in events(sets.set_events(ART, 0, 7, camera)))


def test_fade_at_scene_start_and_dim() -> None:
    evs = events(sets.set_events(ART, 4.0, 9.0, "still", dim=True, fade_in=c.SCENE_FADE_S))
    fades = [e for e in evs if e.layer == c.ASS_LAYER_FADE]
    assert len(fades) == 1 and fades[0].start == 4.0 and "\\fad(0,300)" in fades[0].text
    dims = [e for e in evs if e.layer == c.ASS_LAYER_DIM]
    assert len(dims) == 1 and f"\\1a&H{c.SET_DIM_ALPHA}&" in dims[0].text
    assert not any(
        e.layer in (c.ASS_LAYER_FADE, c.ASS_LAYER_DIM) for e in events(sets.set_events(ART, 0, 5, "still"))
    )


def test_acceptance() -> None:
    test_drift_direction_and_speed()
    for camera in c.CAMERA_MOVES:
        test_every_shape_moves_by_its_drift(camera)
    test_push_in_is_centred_and_other_cameras_do_not_scale()
    test_fade_at_scene_start_and_dim()
