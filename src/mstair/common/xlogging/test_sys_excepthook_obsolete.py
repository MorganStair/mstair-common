"""
Tests to demonstrate that CoreLogger does not require a custom sys_excepthook
to log exceptions when used as the logging class.

Rationale:
- Applications should log exceptions via logger.exception(...) in except blocks.
- With CoreLogger set as the logging logger class and root initialized, this
  works without touching CoreLogger.sys_excepthook.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest

from mstair.common.xlogging.core_logger import CoreLogger, initialize_root


@pytest.fixture(autouse=False)
def clean_logging(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset root logger and logger class around each test."""
    root = logging.getLogger()
    prev_level = root.level
    prev_handlers = list(root.handlers)
    prev_class = logging.getLoggerClass()
    prev_attr = getattr(root, "_plib_corelogger_initialized", None)

    root.handlers = []
    if hasattr(root, "_plib_corelogger_initialized"):
        delattr(root, "_plib_corelogger_initialized")
    logging.setLoggerClass(logging.Logger)

    yield

    root.handlers = prev_handlers
    root.setLevel(prev_level)
    logging.setLoggerClass(prev_class)
    if prev_attr is not None:
        setattr(root, "_plib_corelogger_initialized", prev_attr)
    elif hasattr(root, "_plib_corelogger_initialized"):
        delattr(root, "_plib_corelogger_initialized")


# End of file: src/mstair/common/xlogging/test_sys_excepthook_obsolete.py
