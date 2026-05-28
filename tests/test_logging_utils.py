from datetime import datetime
import logging

from speekify.logging_utils import configure_logger


def test_configure_logger_quiets_third_party_model_loggers(tmp_path) -> None:
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    configure_logger(tmp_path / "speekify.log")

    assert logging.getLogger("huggingface_hub").level == logging.ERROR
    assert logging.getLogger("transformers").level == logging.ERROR


def test_configure_logger_prunes_log_records_older_than_retention(tmp_path) -> None:
    log_path = tmp_path / "speekify.log"
    log_path.write_text(
        "2026-05-10 10:00:00,000 | ERROR | speekify | Old failure\n"
        "Traceback (most recent call last):\n"
        "RuntimeError: old failure\n"
        "2026-05-20 10:00:00,000 | INFO | speekify | Recent event\n"
        "recent continuation\n",
        encoding="utf-8",
    )

    configure_logger(log_path, now=datetime(2026, 5, 28, 12, 0, 0))

    content = log_path.read_text(encoding="utf-8")
    assert "Old failure" not in content
    assert "RuntimeError: old failure" not in content
    assert "Recent event" in content
    assert "recent continuation" in content
    assert "Logger configured" in content
    assert "pruned_lines=3" in content