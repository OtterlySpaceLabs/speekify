from pathlib import Path

try:
	from supertonic.config import AVAILABLE_LANGUAGES as SUPERTONIC_AVAILABLE_LANGUAGES
	from supertonic.config import UNKNOWN_LANGUAGE as SUPERTONIC_UNKNOWN_LANGUAGE
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
	SUPERTONIC_AVAILABLE_LANGUAGES = [
		"en",
		"ko",
		"ja",
		"ar",
		"bg",
		"cs",
		"da",
		"de",
		"el",
		"es",
		"et",
		"fi",
		"fr",
		"hi",
		"hr",
		"hu",
		"id",
		"it",
		"lt",
		"lv",
		"nl",
		"pl",
		"pt",
		"ro",
		"ru",
		"sk",
		"sl",
		"sv",
		"tr",
		"uk",
		"vi",
		"na",
	]
	SUPERTONIC_UNKNOWN_LANGUAGE = "na"

OUTPUT_DIR = Path("output")
LOG_DIR = Path("logs")
LOG_FILE_NAME = "speekify.log"
MODEL_NAME = "supertonic-3"
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-en-fr"
TRANSLATION_CHUNK_TOKEN_LIMIT = 128
DEFAULT_VOICE = "M1"
DEFAULT_TTS_LANG = "en"
DEFAULT_TRANSLATION_TARGET_LANG = "fr"
DEFAULT_SPEED = 1.05
DEFAULT_STEPS = 8
DEFAULT_SILENCE_DURATION = 0.3
TRANSLATION_CHUNK_SIZE = 2_000
MIN_SPEED = 0.7
MAX_SPEED = 2.0
MIN_STEPS = 1
MAX_STEPS = 100
MIN_URL_TEXT_LENGTH = 80
UNKNOWN_TTS_LANGUAGE = SUPERTONIC_UNKNOWN_LANGUAGE
SUPPORTED_TTS_LANGUAGES = tuple(str(code) for code in SUPERTONIC_AVAILABLE_LANGUAGES)

VOICE_NAMES = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
