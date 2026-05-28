import logging

from speekify.logging_utils import configure_logger


def test_configure_logger_quiets_third_party_model_loggers(tmp_path) -> None:
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)

    configure_logger(tmp_path / "speekify.log")

    assert logging.getLogger("huggingface_hub").level == logging.ERROR
    assert logging.getLogger("transformers").level == logging.ERROR