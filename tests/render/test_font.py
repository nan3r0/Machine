"""The caption font is one static Bold font whose family name libass can match (task p1-font-fix).

libass matches the ASS style's font name against the font's family name (name ID 1). A variable
font whose default instance is Thin reports family "Montserrat Thin", so libass falls back to
another font without any error. These tests read the font tables with the standard library only.
"""

import hashlib
import struct
from pathlib import Path

from pipeline import constants

ROOT = Path(__file__).resolve().parent.parent.parent
FONTS = ROOT / constants.FONTS_DIR
LICENSES = ROOT / "assets" / "LICENSES.md"
FAMILY, SUBFAMILY = 1, 2
BOLD_WEIGHT = 700


def font_file() -> Path:
    fonts = sorted(p for p in FONTS.iterdir() if p.suffix.lower() in {".ttf", ".otf"})
    assert len(fonts) == 1, f"expected exactly one caption font in {FONTS}, found {fonts}"
    return fonts[0]


def tables(data: bytes) -> dict[str, bytes]:
    """Table tag -> table bytes, from the sfnt table directory."""
    (count,) = struct.unpack_from(">H", data, 4)
    found = {}
    for i in range(count):
        tag, _, offset, length = struct.unpack_from(">4sIII", data, 12 + 16 * i)
        found[tag.decode("latin-1")] = data[offset:offset + length]
    return found


def names(table: bytes) -> dict[int, str]:
    """Name ID -> string, preferring Windows Unicode English (3, 1, 0x409) over other records."""
    _, count, strings = struct.unpack_from(">HHH", table, 0)
    found: dict[int, str] = {}
    for i in range(count):
        platform, encoding, language, name_id, length, offset = struct.unpack_from(">6H", table, 6 + 12 * i)
        raw = table[strings + offset:strings + offset + length]
        if (platform, encoding, language) == (3, 1, 0x409):
            found[name_id] = raw.decode("utf-16-be")
        elif platform == 1 and name_id not in found:
            found[name_id] = raw.decode("latin-1")
    return found


def font_tables() -> dict[str, bytes]:
    return tables(font_file().read_bytes())


def test_family_name_matches_the_caption_style() -> None:
    assert names(font_tables()["name"])[FAMILY] == constants.CAPTION_FONT_NAME


def test_style_is_bold() -> None:
    found = font_tables()
    assert names(found["name"])[SUBFAMILY] == "Bold"
    (weight,) = struct.unpack_from(">H", found["OS/2"], 4)
    assert weight == BOLD_WEIGHT


def test_font_is_static() -> None:
    assert "fvar" not in set(font_tables()), "variable font: libass sees only its default instance"


def test_acceptance() -> None:
    """The one caption font is static Montserrat Bold, its OFL text is committed, and
    assets/LICENSES.md lists it with the sha256 of the committed file."""
    found = font_tables()
    assert "fvar" not in set(found)
    assert names(found["name"])[FAMILY] == constants.CAPTION_FONT_NAME
    assert names(found["name"])[SUBFAMILY] == "Bold"
    assert "SIL OPEN FONT LICENSE" in (FONTS / "OFL.txt").read_text(encoding="utf-8").upper()
    licences = LICENSES.read_text(encoding="utf-8")
    path = font_file()
    assert f"fonts/{path.name}" in licences
    assert hashlib.sha256(path.read_bytes()).hexdigest() in licences
