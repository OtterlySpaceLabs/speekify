from __future__ import annotations

import logging
from pathlib import Path

from speekify.config import LOG_DIR, LOG_FILE_NAME

LOGGER_NAME = "speekify"


def get_log_path(log_path: Path | None = None) -> Path:
    return log_path or LOG_DIR / LOG_FILE_NAME


def configure_logger(log_path: Path | None = None) -> tuple[logging.Logger, Path]:
    resolved_path = get_log_path(log_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    target = str(resolved_path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == target:
            return logger, resolved_path

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler = logging.FileHandler(resolved_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger, resolved_path
