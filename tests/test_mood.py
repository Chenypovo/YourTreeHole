from core.mood import Mood


def test_default_mood_is_50():
    assert Mood().value == 50


def test_adjust_positive_clamps_100():
    m = Mood()
    m.adjust(60)
    assert m.value == 100


def test_adjust_negative_clamps_0():
    m = Mood()
    m.adjust(-80)
    assert m.value == 0


def test_label_happy():
    assert Mood(value=85).label == "happy"


def test_label_calm():
    assert Mood(value=50).label == "calm"


def test_label_sad():
    assert Mood(value=15).label == "sad"


def test_hearts_full():
    assert Mood(value=100).hearts == "♥♥♥♥♥"


def test_hearts_partial():
    assert Mood(value=60).hearts == "♥♥♥♦♦"
