from speekify.config import (
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_TTS_LANG,
    DEFAULT_VOICE,
    MAX_STEPS,
    MIN_STEPS,
)


def test_default_tts_preset_targets_natural_french_narration() -> None:
    assert DEFAULT_TTS_LANG == "fr"
    assert DEFAULT_VOICE == "M5"
    assert DEFAULT_SPEED == 0.98
    assert DEFAULT_STEPS == 10
    assert DEFAULT_SILENCE_DURATION == 0.25


def test_supertonic_steps_range_matches_documented_typical_bounds() -> None:
    assert MIN_STEPS == 1
    assert MAX_STEPS == 100
