# File: src/mstair/common/xlogging/logger_factory.py
"""
Logger factory for creating and configuring CoreLogger instances.

This module provides functions to create loggers with names inferred from the caller's context,
resolve log level configurations from environment variables, and handle logger name conflicts.

It is designed to work with the CoreLogger class defined in mstair.common.xlogging.logger.
"""

import contextlib
import inspect
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from mstair.common.base.caller_module_name_and_level import caller_module_name_and_level
from mstair.common.xlogging.core_logger import CoreLogger


DEFAULT_LOG_LEVEL = logging.WARNING  # Default log level if not specified in environment variables

_LOG: CoreLogger = None  # type: ignore


def create_logger(
    name: str | None,
    *,
    level: int | str | None = None,
    stacklevel: int = 1,
) -> CoreLogger:
    """
    Return a CoreLogger with a consistent, context-aware name.

    Handles:
    - Normal imports (uses given name)
    - Direct script execution (__main__)
    - Embedded or frozen interpreters (no argv)
    - Anonymous loggers (uses caller-derived name)
    """
    logger_name: str = name or ""

    if logger_name == "__main__":
        arg0 = Path(sys.argv[0]) if sys.argv and sys.argv[0] else None
        if arg0 and arg0.exists():
            logger_name = arg0.stem
        else:  # Invoked via PythonC API or embedded interpreter
            exe = Path(sys.executable or "")
            logger_name = exe.stem if exe.exists() else "embedded_main"

    if not logger_name:
        logger_name = get_caller_logger_name(stacklevel=stacklevel + 1)

    existing = logging.Logger.manager.loggerDict.get(logger_name)

    if isinstance(existing, CoreLogger):
        if level is not None:
            existing.setLevel(level)
        return existing

    # Create (or replace with) CoreLogger
    logger = _get_core_logger_from_logging(logger_name)

    if level is not None:
        logger.setLevel(level)

    if _LOG:
        current_frame = inspect.currentframe()
        current_frame_co_name: str = current_frame.f_code.co_name if current_frame else "<unknown>"
        current_file: Path = Path(__file__)
        with contextlib.suppress(ValueError):
            current_file = current_file.relative_to(Path.cwd())
        debug_or_warning: Callable[..., None] = _LOG.debug if not existing else _LOG.warning
        debug_or_warning(
            "\n  %s: %s() = %s%s",
            current_file.as_posix(),
            current_frame_co_name,
            str(logger),
            " (replacement)" if existing else "",
            stacklevel=stacklevel + 1,
        )
    return logger


def _get_core_logger_from_logging(name: str) -> CoreLogger:
    """
    Create or retrieve a CoreLogger through logging.getLogger().

    Temporarily sets CoreLogger as the logger class to ensure proper integration
    with Python's logging hierarchy (parent relationships, propagation). Without
    this, manually created loggers would have parent=None and break caplog.

    :param name: Logger name.
    :return: CoreLogger instance.
    :raises TypeError: If getLogger() returns wrong type.
    """
    logging_class = logging.getLoggerClass()
    if logging_class is not CoreLogger:
        logging.setLoggerClass(CoreLogger)
    logger: CoreLogger = logging.getLogger(name)  # type: ignore
    if logging_class is not CoreLogger:
        logging.setLoggerClass(logging_class)
    if not isinstance(logger, CoreLogger):
        raise TypeError(f"Failed to create CoreLogger: {logger!r}")
    return logger


def get_caller_logger_name(*, stacklevel: int = 1) -> str:
    """
    Resolve the default logger name based on caller context.
    """
    name = caller_module_name_and_level(stacklevel=stacklevel + 1)[0]
    if not name or name == "__main__":
        executable = sys.argv[0] if sys.argv and sys.argv[0] else sys.executable
        name = Path(executable).stem
    return name


# End of file: src/mstair/common/xlogging/logger_factory.py
