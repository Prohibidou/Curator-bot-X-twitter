import random
from curator.humanize_math import bezier_path, jittered_delay, dwell_seconds


def test_bezier_endpoints_and_length():
    rng = random.Random(1)
    path = bezier_path((0, 0), (100, 50), steps=20, rng=rng)
    assert len(path) == 20
    assert path[0] == (0, 0)
    assert path[-1] == (100, 50)


def test_bezier_is_curved_not_straight():
    rng = random.Random(2)
    path = bezier_path((0, 0), (100, 0), steps=50, rng=rng)
    assert any(p[1] != 0 for p in path)


def test_jittered_delay_within_bounds():
    rng = random.Random(3)
    for _ in range(100):
        d = jittered_delay(1.0, 5.0, rng)
        assert 1.0 <= d <= 5.0


def test_dwell_scales_and_has_minimum():
    assert dwell_seconds("") >= 0.4
    assert dwell_seconds("word " * 100) > dwell_seconds("word")
