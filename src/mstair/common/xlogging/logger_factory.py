# File: python/plib_/xlogging/logger_factory.py
"""
Logger factory for creating and configuring CoreLogger instances.

This module provides functions to create loggers with names inferred from the caller's context,
resolve log level configurations from environment variables, and handle logger name conflicts.

It is designed to work with the CoreLogger class defined in mstair.common.xlogging.logger.
"""

import inspect
import logging
import sys
from pathlib import Path

from mstair.common.base import config as cfg
from mstair.common.base.caller_module_name_and_level import caller_module_name_and_level
from mstair.common.xlogging.core_logger import (
    CoreLogger,
)
from mstair.common.xlogging.logger_util import LogLevelConfig


DEFAULT_LOG_LEVEL = logging.WARNING  # Default log level if not specified in environment variables

_LOG: CoreLogger = None  # pyright: ignore[reportAssignmentType]


def create_logger(
    name: str | None,
    *,
    level: int | str | None = None,
    stacklevel: int = 1,
) -> CoreLogger:
    """
    Return a CoreLogger with the specified name.
    """
    logger_name = name or get_caller_logger_name(stacklevel=stacklevel + 1)

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
        fn_name: str = (
            this_frame.f_code.co_name if (this_frame := inspect.currentframe()) else "<unknown>"
        )
        fn_file = Path(__file__).relative_to(Path.cwd()).as_posix()
        debug_or_warning = _LOG.debug if not existing else _LOG.warning
        debug_or_warning(
            "\n  %s: %s() = %s%s",
            fn_file,
            fn_name,
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
    logger: CoreLogger = logging.getLogger(name)  # pyright: ignore[reportAssignmentType]
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


def _logger_resolve_level_for_name(
    name: str,
    requested_level: int | str | None,
    default: int,
) -> int:
    """
    Resolve the effective integer log level for a logger using environment config
    parsed by LogLevelConfig, with support for explicit int/str overrides.

    :param name: Logger name to resolve.
    :param requested_level: Explicit level (int or name) or None to use env config.
    :param default: Fallback level when nothing matches.
    :return: Resolved stdlib logging level integer (custom levels supported).
    """
    # Minimize noise under trace/debuggers.
    if cfg.being_traced():
        return logging.ERROR

    # Explicit integer wins.
    if isinstance(requested_level, int):
        return requested_level

    # Explicit string override (supports custom names).
    if isinstance(requested_level, str):
        level = _parse_level_name_to_int(requested_level)
        return level if level is not None else default

    # No explicit override: use singleton env config
    config = LogLevelConfig.get_instance()
    return config.get_effective_level(name, default=default)


def _parse_level_name_to_int(level_name: str) -> int | None:
    """
    Map level name to integer, supporting custom levels used by CoreLogger.
    """
    name = level_name.strip().upper()
    custom: dict[str, int] = {
        "TRACE": logging.DEBUG - 1,
        "CONSTRUCT": logging.INFO - 1,
        "SUPPRESS": -1,
    }
    if name in custom:
        return custom[name]
    return logging.getLevelNamesMapping().get(name)


# End of file: python/plib_/xlogging/logger_factory.py
