"""
Tests for CoreLogger behavior vs root level and environment variables.

Confirms that:
- Setting LOG_LEVELS (e.g., TRACE) does not lower the root logger level.
- CoreLogger raises its level to at least the root's effective level.
- Calling initialize_root(level=...) is required to lower the root threshold.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

import pytest

from mstair.common.xlogging import logger_util as lu
from mstair.common.xlogging.core_logger import CoreLogger, initialize_root


@pytest.fixture(autouse=False)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear LOG_LEVEL* vars and reset singleton; do not read .env during tests."""
    monkeypatch.setattr(lu, "fs_load_dotenv", lambda *a, **k: False, raising=False)  # pyright: ignore[reportUnknownLambdaType]

    keys_to_delete = [k for k in os.environ if k.startswith("LOG_LEVEL")]
    for k in keys_to_delete:
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setattr(lu, "_log_level_config_instance", None, raising=False)

    yield

    for k in keys_to_delete:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(lu, "_log_level_config_instance", None, raising=False)


@pytest.fixture(autouse=False)
def clean_logging(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset root logger state (handlers, level, init flag) around tests."""
    root = logging.getLogger()
    prev_level = root.level
    prev_handlers = list(root.handlers)
    prev_attr = getattr(root, "_plib_corelogger_initialized", None)

    # Reset to known baseline
    root.handlers = []
    root.setLevel(logging.WARNING)
    if hasattr(root, "_plib_corelogger_initialized"):
        delattr(root, "_plib_corelogger_initialized")

    yield

    # Restore
    root.handlers = prev_handlers
    root.setLevel(prev_level)
    if prev_attr is not None:
        setattr(root, "_plib_corelogger_initialized", prev_attr)
    elif hasattr(root, "_plib_corelogger_initialized"):
        delattr(root, "_plib_corelogger_initialized")


def test_env_trace_does_not_lower_root_or_logger(
    clean_env: None, clean_logging: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LOG_LEVELS=TRACE alone does not reduce root level or logger level below WARNING."""
    # Root starts at WARNING
    root = logging.getLogger()
    assert root.getEffectiveLevel() == logging.WARNING

    monkeypatch.setenv("LOG_LEVELS", "pkg.*:TRACE")

    # Create logger for pkg.module
    log = CoreLogger("pkg.module")

    # CoreLogger elevates to at least root level; root remains WARNING by default
    assert root.getEffectiveLevel() == logging.WARNING
    assert log.level == logging.WARNING
    assert log.getEffectiveLevel() == logging.WARNING
    assert not log.isEnabledFor(logging.DEBUG)


def test_initialize_root_level_controls_logger_threshold(
    clean_env: None, clean_logging: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """initialize_root(level=...) sets the root threshold; loggers track that floor."""
    monkeypatch.setenv("LOG_LEVELS", "pkg.*:TRACE")  # most verbose desired for the logger

    # Lower the root using the public API
    initialize_root(level="DEBUG")

    root = logging.getLogger()
    assert root.getEffectiveLevel() == logging.DEBUG

    log = CoreLogger("pkg.module")
    # Logger is raised to root floor (DEBUG), not the more verbose TRACE
    assert log.level == logging.DEBUG
    assert log.getEffectiveLevel() == logging.DEBUG
    assert log.isEnabledFor(logging.DEBUG)


# End of file: src/mstair/common/xlogging/test_core_logger_root_level.py
