"""Art assets as data: the host character and the sets (task p3-contracts). Locked contract.

The host is `assets/character/host.yaml` (`HostArt`), each set is `assets/sets/<id>.yaml`
(`SetArt`). Paths are ASS drawing commands (`m`, `l`, `b`) with integer coordinates and exactly one
`m`, so one shape is one closed contour. Colours are RGB hex; the ASS layer converts them to BGR.
Art coordinates are art, like a font; timings and on-screen sizes are in constants.py.
"""

import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.constants import (
    HEIGHT,
    HOST_ART_PATH,
    POSES,
    SET_LAYER_MARGIN_PX,
    SET_LAYERS,
    SET_SHAPES_MAX,
    SETS_DIR,
    WIDTH,
)

ROOT = Path(__file__).resolve().parent.parent.parent
HOST_ANCHORS = ("neck", "shoulder_left", "shoulder_right", "mouth", "ground")
_ARGS = {"m": 2, "l": 2, "b": 6}  # numbers per repeat of each command
RGB = Annotated[str, Field(pattern=r"^[0-9A-F]{6}$")]
Point = tuple[int, int]


def path_points(path: str) -> list[Point]:
    """Every point of an ASS drawing `path`. Raises ValueError unless the path is one `m x y`
    followed by `l` (pairs) and `b` (three pairs) runs of integers."""
    tokens = path.split()
    if len(tokens) < 3 or tokens[0] != "m" or tokens.count("m") != 1:
        raise ValueError(f"path must start with one 'm': {path[:40]!r}")
    numbers: list[int] = []
    command, count = "m", 0
    for token in [*tokens[1:], "end"]:
        if token in _ARGS or token == "end":
            if count == 0 or count % _ARGS[command] or (command == "m" and count != 2):
                raise ValueError(f"'{command}' needs a multiple of {_ARGS[command]} numbers")
            command, count = token, 0
        elif re.fullmatch(r"-?\d+", token):
            numbers.append(int(token))
            count += 1
        else:
            raise ValueError(f"bad path token {token!r}")
    return list(zip(numbers[::2], numbers[1::2], strict=True))


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Shape(_Strict):
    """One filled contour. `layer` orders shapes within the asset (higher on top); `fill` is a
    palette key; `outline` the border width in px; `alpha` ASS hex, "00" opaque."""

    layer: Annotated[int, Field(ge=0, le=19)]
    fill: str
    outline: Annotated[int, Field(ge=0)]
    path: str
    alpha: Annotated[str, Field(pattern=r"^[0-9A-F]{2}$")] = "00"

    @model_validator(mode="after")
    def _path_parses(self) -> "Shape":
        path_points(self.path)
        return self

    def points(self) -> list[Point]:
        return path_points(self.path)


class Size(_Strict):
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]


class Pose(_Strict):
    """A pose: default face part keys plus both arms, drawn per pose."""

    eyes: str
    brows: str
    mouth: str
    arm_left: Annotated[list[Shape], Field(min_length=1)]
    arm_right: Annotated[list[Shape], Field(min_length=1)]


def _check_fills(shapes: list[Shape], palette: dict[str, str], outline_colour: str) -> None:
    if outline_colour not in palette:
        raise ValueError(f"outline_colour {outline_colour!r} is not in the palette")
    missing = sorted({s.fill for s in shapes} - set(palette))
    if missing:
        raise ValueError(f"fills not in the palette: {missing}")


class HostArt(_Strict):
    """The host character (assets/character/host.yaml). Every point and anchor lies inside `size`,
    origin top-left. Poses are exactly constants.POSES; each names existing face parts.
    `talking_mouths` is the lip-sync cycle, all keys of `mouths`."""

    name: str
    size: Size
    outline_colour: str
    palette: dict[str, RGB]
    anchors: dict[str, Annotated[Point, Field(strict=False)]]  # YAML gives lists
    body: Annotated[list[Shape], Field(min_length=1)]
    eyes: dict[str, list[Shape]]
    brows: dict[str, list[Shape]]
    mouths: dict[str, list[Shape]]
    talking_mouths: Annotated[list[str], Field(min_length=2)]
    poses: dict[str, Pose]

    def all_shapes(self) -> list[Shape]:
        parts = [*self.eyes.values(), *self.brows.values(), *self.mouths.values()]
        arms = [arm for pose in self.poses.values() for arm in (pose.arm_left, pose.arm_right)]
        return [*self.body, *(s for group in [*parts, *arms] for s in group)]

    @model_validator(mode="after")
    def _consistent(self) -> "HostArt":
        if set(self.poses) != set(POSES):
            raise ValueError(f"poses must be exactly {sorted(POSES)}, got {sorted(self.poses)}")
        if set(HOST_ANCHORS) - set(self.anchors):
            raise ValueError(f"anchors must include {HOST_ANCHORS}")
        if "closed" not in self.eyes:
            raise ValueError("eyes must include 'closed' for blinks")
        if set(self.talking_mouths) - set(self.mouths):
            raise ValueError("talking_mouths must name keys of mouths")
        for name, pose in self.poses.items():
            for part, key, table in (("eyes", pose.eyes, self.eyes), ("brows", pose.brows, self.brows),
                                     ("mouth", pose.mouth, self.mouths)):
                if key not in table:
                    raise ValueError(f"pose {name}: {part} {key!r} does not exist")
        shapes = self.all_shapes()
        _check_fills(shapes, self.palette, self.outline_colour)
        points = [p for s in shapes for p in s.points()] + list(self.anchors.values())
        if any(not (0 <= x <= self.size.width and 0 <= y <= self.size.height) for x, y in points):
            raise ValueError("a point or anchor lies outside the art box")
        return self


class SetLayer(_Strict):
    """One flat layer of a set; `depth` sets its drift speed (constants.DRIFT_PX_PER_S)."""

    depth: Literal["far", "mid", "near"]
    shapes: Annotated[list[Shape], Field(min_length=1)]


class SetArt(_Strict):
    """A set (assets/sets/<id>.yaml) in frame coordinates: x from -SET_LAYER_MARGIN_PX to
    WIDTH + SET_LAYER_MARGIN_PX, y from 0 to HEIGHT. SET_LAYERS layers, back to front, with at most
    SET_SHAPES_MAX shapes in total."""

    name: str
    outline_colour: str
    palette: dict[str, RGB]
    layers: list[SetLayer]

    @model_validator(mode="after")
    def _within_caps(self) -> "SetArt":
        low, high = SET_LAYERS
        if not low <= len(self.layers) <= high:
            raise ValueError(f"{len(self.layers)} layers, must be {low} to {high}")
        shapes = [s for layer in self.layers for s in layer.shapes]
        if len(shapes) > SET_SHAPES_MAX:
            raise ValueError(f"{len(shapes)} shapes, at most {SET_SHAPES_MAX}")
        _check_fills(shapes, self.palette, self.outline_colour)
        m = SET_LAYER_MARGIN_PX
        if any(not (-m <= x <= WIDTH + m and 0 <= y <= HEIGHT) for s in shapes for x, y in s.points()):
            raise ValueError("a point lies outside the frame plus its margin")
        return self


def load_host(path: Path = ROOT / HOST_ART_PATH) -> HostArt:
    """Parse and validate the host asset. Raises pydantic.ValidationError or yaml.YAMLError."""
    return HostArt.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_set(set_id: str, sets_dir: Path = ROOT / SETS_DIR) -> SetArt:
    """Parse and validate `<sets_dir>/<set_id>.yaml`; its `name` must equal `set_id`.
    Raises ValueError for a set id that is not a plain lowercase name."""
    if not re.fullmatch(r"[a-z][a-z_]*", set_id):
        raise ValueError(f"bad set id {set_id!r}")
    art = SetArt.model_validate(yaml.safe_load((sets_dir / f"{set_id}.yaml").read_text(encoding="utf-8")))
    if art.name != set_id:
        raise ValueError(f"set file {set_id}.yaml is named {art.name!r}")
    return art
