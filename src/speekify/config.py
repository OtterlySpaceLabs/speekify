from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE_NAME = "speekify.log"
MODEL_NAME = "supertonic-3"
TRANSLATION_MODEL_NAME = "Helsinki-NLP/opus-mt-en-fr"
TRANSLATION_CHUNK_TOKEN_LIMIT = 128
TRANSLATION_MAX_LENGTH = 512
DEFAULT_VOICE = "M5"
# Sentinel for "use the document's detected language" (no --lang given).
AUTO_TTS_LANGUAGE = "auto"
DEFAULT_TRANSLATION_TARGET_LANG = "fr"
DEFAULT_SPEED = 0.98
DEFAULT_STEPS = 10
DEFAULT_SILENCE_DURATION = 0.25
TRANSLATION_CHUNK_SIZE = 2_000
MIN_SPEED = 0.7
MAX_SPEED = 2.0
MIN_STEPS = 1
MAX_STEPS = 100
MIN_URL_TEXT_LENGTH = 80
UNKNOWN_TTS_LANGUAGE = "na"
SUPPORTED_TTS_LANGUAGES = (
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
	UNKNOWN_TTS_LANGUAGE,
)

VOICE_NAMES = ("M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5")
