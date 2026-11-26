"""Every set id has a valid asset within the caps (task p3-sets-art, owner-approved stills)."""

import pytest

from pipeline import constants as c
from pipeline.visuals import art

ALL_SETS = (*c.SET_IDS, c.HOST_BACKDROP_SET)


@pytest.mark.parametrize("set_id", ALL_SETS)
def test_set_asset_is_valid(set_id: str) -> None:
    found = art.load_set(set_id)
    assert c.SET_LAYERS[0] <= len(found.layers) <= c.SET_LAYERS[1]
    assert sum(len(layer.shapes) for layer in found.layers) <= c.SET_SHAPES_MAX
    depths = [c.SET_DEPTHS.index(layer.depth) for layer in found.layers]
    assert depths == sorted(depths), "layers go back to front"


def test_acceptance() -> None:
    for set_id in ALL_SETS:
        test_set_asset_is_valid(set_id)
