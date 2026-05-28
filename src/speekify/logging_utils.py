from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

from speekify.config import LOG_DIR, LOG_FILE_NAME

LOGGER_NAME = "speekify"
DEFAULT_LOG_RETENTION_DAYS = 14
LOG_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S,%f"
LOG_TIMESTAMP_LENGTH = len("2026-05-28 11:02:01,503")
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
    retention_days: int | None = DEFAULT_LOG_RETENTION_DAYS,
    now: datetime | None = None,
) -> tuple[logging.Logger, Path]:
    quiet_third_party_model_logs()

    resolved_path = get_log_path(log_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    pruned_line_count = prune_log_file(
        resolved_path,
        retention_days=retention_days,
        now=now,
    )

    logger = logging.getLogger(LOGGER_NAME)
    log_level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(log_level)
    logger.propagate = False

    target = str(resolved_path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == target:
            handler.setLevel(log_level)
            logger.info(
                "Logger configured path=%s level=%s retention_days=%s pruned_lines=%s",
                resolved_path,
                logging.getLevelName(log_level),
                retention_days,
                pruned_line_count,
            )
            return logger, resolved_path

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler = logging.FileHandler(resolved_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(
        "Logger configured path=%s level=%s retention_days=%s pruned_lines=%s",
        resolved_path,
        logging.getLevelName(log_level),
        retention_days,
        pruned_line_count,
    )
    return logger, resolved_path


def prune_log_file(
    log_path: Path,
    *,
    retention_days: int | None = DEFAULT_LOG_RETENTION_DAYS,
    now: datetime | None = None,
) -> int:
    if retention_days is None or not log_path.exists():
        return 0
    if retention_days < 1:
        raise ValueError("Log retention must be at least 1 day.")

    cutoff = (now or datetime.now()) - timedelta(days=retention_days)
    retained_lines: list[str] = []
    removed_line_count = 0
    retain_current_record = True

    for line in log_path.read_text(encoding="utf-8").splitlines(keepends=True):
        timestamp = _parse_log_timestamp(line)
        if timestamp is not None:
            retain_current_record = timestamp >= cutoff

        if retain_current_record:
            retained_lines.append(line)
        else:
            removed_line_count += 1

    if removed_line_count:
        log_path.write_text("".join(retained_lines), encoding="utf-8")
    return removed_line_count


def _parse_log_timestamp(line: str) -> datetime | None:
    delimiter = line[LOG_TIMESTAMP_LENGTH : LOG_TIMESTAMP_LENGTH + 3]
    if len(line) <= LOG_TIMESTAMP_LENGTH or delimiter != " | ":
        return None

    try:
        return datetime.strptime(line[:LOG_TIMESTAMP_LENGTH], LOG_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def quiet_third_party_model_logs() -> None:
    for logger_name in QUIET_THIRD_PARTY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    try:
        from huggingface_hub.utils import logging as hub_logging
    except ImportError:  # pragma: no cover - dependency is optional in unit tests.
        return

    hub_logging.set_verbosity_error()
