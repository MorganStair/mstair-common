"""
Shared logging utilities for common I/O operations.

This module provides a single entry point for consistent logging configuration
across all project modules. It standardizes output formatting, log levels, and
stream handling for both command-line tools and library code.

`setup_logging()` can be called early in the application startup to ensure
that all loggers share the same configuration. Output is directed to stdout
and formatted with timestamp, logger name, level, and message text.

Example:
    >>> from mstair.common.io.logging_utils import setup_logging
    >>> import logging
    >>> setup_logging(verbose=True)
    >>> log = logging.getLogger("example")
    >>> log.info("Processing started")
    2025-10-16 14:22:01,845 - example - INFO - Processing started
"""

from __future__ import annotations

import logging
import sys


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure standard logging for project modules.

    Args:
        verbose: Enable verbose (DEBUG) logging output.
        quiet: Suppress most logging output.
    """
    if quiet:
        level = logging.ERROR  # Only show errors in quiet mode
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
