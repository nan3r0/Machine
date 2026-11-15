"""R3: forced alignment of the known script text (task p1-align)."""

import wave
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline.schema import WordTiming
from pipeline.voice import align
from pipeline.voice.align import AlignError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
WAV = FIXTURES / "align_sample.wav"
TEXT = (FIXTURES / "align_sample.txt").read_text(encoding="utf-8").strip()


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def assert_valid(timings: list[WordTiming], words: list[str], duration: float) -> None:
    """R3.1 and R3.2 invariants."""
    assert [t.word for t in timings] == words
    for t in timings:
        assert 0 <= t.start <= t.end <= duration
    for before, after in zip(timings, timings[1:], strict=False):
        assert before.start <= after.start
        assert before.end <= after.end


@pytest.mark.heavy
def test_acceptance() -> None:
    """R3.1 and R3.2 on the committed speech fixture."""
    duration = wav_seconds(WAV)
    timings = align.align_words(WAV, TEXT)
    assert_valid(timings, TEXT.split(), duration)
    assert timings[0].start < 2.0
    assert timings[-1].end > duration / 2
    assert timings[-1].end > timings[0].start


@pytest.mark.heavy
def test_unicode_and_punctuation_survive() -> None:
    text = TEXT.replace("dollars.", "dóllars…").replace("Why", "“Why").replace("much?", "much?”")
    timings = align.align_words(WAV, text)
    assert_valid(timings, text.split(), wav_seconds(WAV))


@pytest.mark.heavy
def test_unreadable_audio_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio")
    with pytest.raises(AlignError):
        align.align_words(bad, TEXT)


@pytest.mark.parametrize("text", ["", "   "])
def test_blank_text_raises_before_loading_model(text: str) -> None:
    with pytest.raises(AlignError):
        align.align_words(WAV, text)


def test_pieces_map_one_to_one() -> None:
    words = ["In", "1938,", "a", "pen."]
    pieces = [(" In", 0.1, 0.3), (" 1938,", 0.3, 1.0), (" a", 1.0, 1.1), (" pen.", 1.1, 1.5)]
    timings = align.to_word_timings(words, pieces, 2.0)
    assert [(t.word, t.start, t.end) for t in timings] == [
        ("In", 0.1, 0.3), ("1938,", 0.3, 1.0), ("a", 1.0, 1.1), ("pen.", 1.1, 1.5)]


def test_split_word_spans_its_pieces() -> None:
    words = ["a", "ten-dollar", "pen"]
    pieces = [(" a", 0.0, 0.2), (" ten", 0.2, 0.5), ("-", 0.5, 0.6), ("dollar", 0.6, 1.0), (" pen", 1.0, 1.4)]
    timings = align.to_word_timings(words, pieces, 2.0)
    assert (timings[1].word, timings[1].start, timings[1].end) == ("ten-dollar", 0.2, 1.0)


def test_unicode_words_are_kept_exactly() -> None:
    words = ["Café", "{x}", "naïve\\", "日本"]
    pieces = [(" Café", 0.0, 0.3), (" {x}", 0.3, 0.6), (" naïve\\", 0.6, 0.9), (" 日", 0.9, 1.0), ("本", 1.0, 1.2)]
    timings = align.to_word_timings(words, pieces, 2.0)
    assert [t.word for t in timings] == words
    assert timings[3].end == 1.2


def test_text_mismatch_raises() -> None:
    with pytest.raises(AlignError):
        align.to_word_timings(["a", "pen"], [(" a", 0.0, 0.2), (" pan", 0.2, 0.5)], 1.0)
    with pytest.raises(AlignError):
        align.to_word_timings(["a", "pen"], [(" a", 0.0, 0.2)], 1.0)


def test_bad_piece_times_are_clamped() -> None:
    words = ["one", "two", "three"]
    pieces = [(" one", 0.5, 0.2), (" two", 0.1, 0.9), (" three", 0.9, 5.0)]
    assert_valid(align.to_word_timings(words, pieces, 2.0), words, 2.0)


word = st.text(st.characters(categories=["L", "N", "P", "S"]), min_size=1, max_size=8)


@settings(deadline=None, max_examples=200)
@given(words=st.lists(word, min_size=1, max_size=30), data=st.data())
def test_any_split_and_any_times_give_valid_timings(words: list[str], data: st.DataObject) -> None:
    """Whatever pieces and times the aligner returns, the result keeps the R3 invariants."""
    duration = data.draw(st.floats(min_value=0.1, max_value=120))
    joined = "".join(words)
    cuts = sorted(data.draw(st.sets(st.integers(1, max(1, len(joined) - 1)), max_size=len(joined))))
    bounds = [0, *(c for c in cuts if c < len(joined)), len(joined)]
    times = st.floats(min_value=-1, max_value=duration + 5, allow_nan=False)
    pieces = [(" " + joined[a:b], data.draw(times), data.draw(times)) for a, b in zip(bounds, bounds[1:],
                                                                                     strict=False)]
    assert_valid(align.to_word_timings(words, pieces, duration), words, duration)
