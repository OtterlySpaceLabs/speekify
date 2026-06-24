from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speekify.validation import (
    normalize_language_code,
    normalize_voice_name,
)

CONFIG_ENV_VAR = "SPEEKIFY_CONFIG"


@dataclass(frozen=True)
class UserConfig:
    voice: str | None = None
    custom_style_path: Path | None = None
    language_code: str | None = None
    speed: float | None = None
    steps: int | None = None
    max_chunk_length: int | None = None
    silence_duration: float | None = None
    english_islands: bool | None = None
    english_lexicon_path: Path | None = None
    output_dir: Path | None = None


def default_config_path() -> Path:
    configured_path = os.environ.get(CONFIG_ENV_VAR, "").strip()
    if configured_path:
        return Path(configured_path).expanduser()

    config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base_dir = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base_dir / "speekify" / "config.toml"


def load_user_config(path: Path | None = None) -> UserConfig:
    config_path = path or default_config_path()
    if not config_path.is_file():
        return UserConfig()

    try:
        with config_path.open("rb") as config_file:
            payload = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid Speekify config file {config_path}: {exc}") from exc

    generation = payload.get("generation", payload)
    if not isinstance(generation, dict):
        raise ValueError("Speekify config [generation] section must be a table.")

    return UserConfig(
        voice=_optional_voice(generation.get("voice")),
        custom_style_path=_optional_path(generation.get("custom_style_path")),
        language_code=_optional_language(generation.get("language_code", generation.get("lang"))),
        speed=_optional_float(generation.get("speed"), "speed"),
        steps=_optional_int(generation.get("steps"), "steps"),
        max_chunk_length=_optional_int(generation.get("max_chunk_length"), "max_chunk_length"),
        silence_duration=_optional_float(generation.get("silence_duration"), "silence_duration"),
        english_islands=_optional_bool(generation.get("english_islands"), "english_islands"),
        english_lexicon_path=_optional_path(generation.get("english_lexicon_path")),
        output_dir=_optional_path(generation.get("output_dir")),
    )


def config_value(current_value: Any, default_value: Any, configured_value: Any) -> Any:
    if configured_value is None:
        return current_value
    if current_value == default_value or current_value is None:
        return configured_value
    return current_value


def _optional_voice(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Speekify config voice must be a string.")
    return normalize_voice_name(value)


def _optional_language(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Speekify config language_code must be a string.")
    return normalize_language_code(value)


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Speekify config paths must be strings.")
    return Path(value).expanduser()


def _optional_bool(value: object, name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"Speekify config {name} must be true or false.")
    return value


def _optional_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Speekify config {name} must be an integer.")
    return value


def _optional_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Speekify config {name} must be a number.")
    return float(value)