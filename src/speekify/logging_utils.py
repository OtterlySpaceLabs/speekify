from __future__ import annotations

import logging
from pathlib import Path

from speekify.config import LOG_DIR, LOG_FILE_NAME

LOGGER_NAME = "speekify"
QUIET_THIRD_PARTY_LOGGERS = (
    "huggingface_hub",
    "transformers",
)


def get_log_path(log_path: Path | None = None) -> Path:
    return log_path or LOG_DIR / LOG_FILE_NAME


def configure_logger(
    log_path: Path | None = None,
    *,
    verbose: bool = False,
) -> tuple[logging.Logger, Path]:
    quiet_third_party_model_logs()

    resolved_path = get_log_path(log_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    log_level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(log_level)
    logger.propagate = False

    target = str(resolved_path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == target:
            handler.setLevel(log_level)
            return logger, resolved_path

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler = logging.FileHandler(resolved_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger, resolved_path


def quiet_third_party_model_logs() -> None:
    for logger_name in QUIET_THIRD_PARTY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    try:
        from huggingface_hub.utils import logging as hub_logging
    except ImportError:  # pragma: no cover - dependency is optional in unit tests.
        return

    hub_logging.set_verbosity_error()
