"""Data card layouts: numbered steps, timeline, place card (task p3-cards). No IO.

Items are (label, value) pairs from a validated scene. Every event lies inside [start, end], uses
ASS layer ASS_LAYER_CARD or above, and every `\\pos` lies inside DATA_PANEL. Text events are
ass_kit.text_event (CARD_STYLE), so long labels wrap inside the panel.
"""


def steps_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """Numbered cards ("1", "2", ...) with each label (and value, if not empty) shown exactly,
    appearing one at a time: item k+1 appears later than item k."""
    raise NotImplementedError


def timeline_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """Dots on a line; each value (a year) and label shown exactly, popping in staggered in
    item order."""
    raise NotImplementedError


def place_events(items: list[tuple[str, str]], start: float, end: float) -> list[str]:
    """A pin with sonar rings, the single item's label (the place) and its value if not empty."""
    raise NotImplementedError
