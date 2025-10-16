import logging

from mstair.common.io.logging_utils import setup_logging


def _reset_logging() -> None:
    # Reset logging configuration to ensure basicConfig applies in subsequent calls
    logging.basicConfig(level=logging.NOTSET, force=True)


def test_setup_logging_default_sets_info_level() -> None:
    _reset_logging()
    setup_logging()
    assert logging.getLogger().getEffectiveLevel() == logging.INFO


def test_setup_logging_verbose_sets_debug_level() -> None:
    _reset_logging()
    setup_logging(verbose=True)
    assert logging.getLogger().getEffectiveLevel() == logging.DEBUG


def test_setup_logging_quiet_sets_error_level() -> None:
    _reset_logging()
    setup_logging(quiet=True)
    assert logging.getLogger().getEffectiveLevel() == logging.ERROR
