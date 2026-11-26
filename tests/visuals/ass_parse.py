"""An independent reader of the Dialogue lines the visuals modules write (task p3-contracts)."""

import re
from dataclasses import dataclass

LINE = re.compile(
    r"^Dialogue: (\d+),(\d+):(\d\d):(\d\d)\.(\d\d),(\d+):(\d\d):(\d\d)\.(\d\d),([^,]*),[^,]*,"
    r"(-?\d+),(-?\d+),(-?\d+),[^,]*,(.*)$"
)
NUMBER = r"(-?\d+(?:\.\d+)?)"


@dataclass(frozen=True)
class Event:
    layer: int
    start: float
    end: float
    style: str
    text: str


def _seconds(h: str, m: str, s: str, cs: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100


def parse(line: str) -> Event:
    found = LINE.match(line)
    assert found, f"not a Dialogue line: {line[:80]!r}"
    g = found.groups()
    return Event(int(g[0]), _seconds(*g[1:5]), _seconds(*g[5:9]), g[9], g[13])


def events(text_or_lines: str | list[str]) -> list[Event]:
    lines = text_or_lines.splitlines() if isinstance(text_or_lines, str) else text_or_lines
    return [parse(line) for line in lines if line.startswith("Dialogue:")]


def visible(evs: list[Event], t: float) -> list[Event]:
    return [e for e in evs if e.start <= t < e.end]


def drawing(text: str) -> str | None:
    """The drawing path of a `\\p1` event, or None."""
    found = re.search(r"\\p1[^}]*}([^{]*)", text)
    return found.group(1).strip() if found else None


def pos(text: str) -> tuple[float, float] | None:
    """`\\pos(x,y)`, or the start point of `\\move(x0,y0,x1,y1...)`."""
    found = re.search(rf"\\(?:pos|move)\({NUMBER},{NUMBER}", text)
    return (float(found.group(1)), float(found.group(2))) if found else None


def move(text: str) -> tuple[float, float, float, float] | None:
    found = re.search(rf"\\move\({NUMBER},{NUMBER},{NUMBER},{NUMBER}", text)
    return tuple(float(v) for v in found.groups()) if found else None  # type: ignore[return-value]


def shown_text(text: str) -> str:
    """What libass shows for a text event: override blocks removed, ASS escapes undone."""
    out, i = [], 0
    while i < len(text):
        if text.startswith("\\{", i) or text.startswith("\\}", i):
            out.append(text[i + 1])
            i += 2
        elif text[i] == "{":
            i = text.index("}", i) + 1
        elif text.startswith("\\\u200b", i):
            out.append("\\")
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)
