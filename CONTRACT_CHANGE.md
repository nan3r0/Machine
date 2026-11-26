# CONTRACT_CHANGE: tests/visuals/test_charts.py (task p3-charts, review round 1)

Request: add a regression test to the locked `tests/visuals/test_charts.py`. The existing tests check no ASS override tags, so a bug where the tags were plain strings with single backslashes (`"\an5"` turns `\a` into BEL, `\f` into form feed, `\t` into TAB) passed all of them. PLAN.md needs the bars to grow, labels left aligned and pop-ins, so libass must receive real tags.

Proposed test (fails on the round 1 code, passes on the fix). `evs` is the raw dialogue lines:

```python
@pytest.mark.parametrize(
    ("layout", "items", "tags"),
    [
        (charts.counter_events, [("Kilometres apart", "3,219")], ["\\an5"]),
        (charts.bars_events, [("Bloop", "3,219"), ("Whale", "0")], ["\\an4", "\\an7", "\\fscx1", "\\t("]),
    ],
)
def test_override_tags_are_real_tags(layout: object, items: list[tuple[str, str]], tags: list[str]) -> None:
    lines = layout(items, 5.0, 12.0)  # type: ignore[operator]
    assert not any(ord(ch) < 0x20 for line in lines for ch in line), "control byte in an event"
    joined = "".join(lines)
    assert all(tag in joined for tag in tags)
```
