from speekify.config import MAX_STEPS, MIN_STEPS


def test_supertonic_steps_range_matches_documented_typical_bounds() -> None:
    assert MIN_STEPS == 1
    assert MAX_STEPS == 100
