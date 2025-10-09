# File: python/plib_/base/config.py
"""
Environment and execution context detection utilities.

This module provides utilities for checking and modifying the current
execution context, such as whether the program is running in AWS Lambda,
in test mode, desktop mode, or under static analysis. It uses thread-local
storage so that overrides and context-sensitive flags are isolated per thread.

Exports:
- analysis_mode_context(): context manager for analysis mode.
- in_analysis_mode(): check if analysis mode is active.
- in_lambda(): check or override whether code is running in AWS Lambda.
- in_test_mode(): check or override whether code is in test mode.
- in_desktop_mode(): check or override whether code is in desktop mode.
- being_traced(): check if Python tracing/debugging is active.

Typical uses:
- Adjusting behavior in test, analysis, or cloud contexts.
- Avoiding side effects (like I/O) during analysis or testing.
- Supporting dependency injection or mocking via context-aware flags.
"""

from __future__ import annotations

import inspect
import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache


_tls = threading.local()


@dataclass
class TLSAttrs:
    """Thread-local flags for environment context."""

    in_code_analyzer: bool = False
    in_lambda_override: bool | None = None
    in_test_mode_override: bool | None = None
    in_desktop_mode_override: bool | None = None


def _get_tls() -> TLSAttrs:
    """Return the current thread's TLSAttrs instance, initializing if needed."""
    try:
        return _tls.state
    except AttributeError:
        _tls.state = TLSAttrs()
        return _tls.state


@contextmanager
def analysis_mode_context() -> Iterator[None]:
    """
    Context manager to enable code analysis mode temporarily.

    Restores the previous value on exit. Nested contexts are supported.
    """
    tls = _get_tls()
    previous_state = tls.in_code_analyzer
    tls.in_code_analyzer = True
    try:
        yield
    finally:
        tls.in_code_analyzer = previous_state


def in_analysis_mode() -> bool:
    """
    Check if code analysis mode is active on this thread.

    :return: True if analysis mode is active, False otherwise.
    """
    return _get_tls().in_code_analyzer


def in_lambda(
    *,
    unset_override: bool = False,
    override: bool | None = None,
) -> bool:
    """
    Check if running in an AWS Lambda environment, with optional override.

    Uses Lambda-specific environment variables unless explicitly overridden.

    :param unset_override: If True, clears any prior override for this thread.
    :param override: If True or False, sets the override for this thread.
    :return: True if in Lambda context, False otherwise.
    """
    tls = _get_tls()
    if unset_override:
        tls.in_lambda_override = None
    if override is not None:
        tls.in_lambda_override = override
        return override
    if tls.in_lambda_override is not None:
        return tls.in_lambda_override
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("LAMBDA_RUNTIME_DIR"))


def in_test_mode(
    *,
    unset_override: bool = False,
    override: bool | None = None,
) -> bool:
    """
    Check if running in test mode, with optional override.

    Test mode is disabled when in analysis mode.

    Detection order:
      1. Analysis mode check (always False).
      2. Explicit override (thread-local).
      3. Presence of pytest/unittest in sys.modules.
      4. Known environment variables (e.g. PYTEST_CURRENT_TEST, CI).

    :param unset_override: If True, clears any prior override for this thread.
    :param override: If True or False, sets the override for this thread.
    :return: True if test mode is active, False otherwise.
    """
    if in_analysis_mode():
        return False

    tls = _get_tls()
    if unset_override:
        tls.in_test_mode_override = None
    if override is not None:
        tls.in_test_mode_override = override
        return override
    if tls.in_test_mode_override is not None:
        return tls.in_test_mode_override
    if "pytest" in sys.modules or "unittest" in sys.modules:
        return True

    env = os.environ
    if (
        any(env.get(k) for k in ("PYTEST_CURRENT_TEST", "PYTEST_RUNNING", "UNITTEST_RUNNING"))
        or env.get("CI") == "true"
        or env.get("APP_TEST_MODE") == "1"
    ):
        return True

    return False


def in_desktop_mode(
    *,
    unset_override: bool = False,
    override: bool | None = None,
) -> bool:
    """
    Determine if output should be formatted for interactive display.

    Rules:
      - Explicit override wins.
      - Returns True in test mode.
      - Returns False in analysis or Lambda environments.
      - Otherwise True.

    :param unset_override: If True, clears any prior override for this thread.
    :param override: If True or False, sets the override for this thread.
    :return: True if desktop mode is active, False otherwise.
    """
    tls = _get_tls()
    if unset_override:
        tls.in_desktop_mode_override = None
    if override is not None:
        tls.in_desktop_mode_override = override
        return override
    if tls.in_desktop_mode_override is not None:
        return tls.in_desktop_mode_override

    if in_test_mode():
        return True
    if in_analysis_mode():
        return False
    return not in_lambda()


@cache
def _is_traced() -> bool:
    """Return True if sys tracing or profiling hooks are active."""
    return sys.gettrace() is not None or sys.getprofile() is not None


@cache
def _has_pycallgraph_stack() -> bool:
    """Return True if any frame in the call stack originates from pycallgraph."""
    return any("pycallgraph" in (frame.filename or "") for frame in inspect.stack())


def being_traced() -> bool:
    """
    Check if Python tracing/debugging/call graphing is active.

    Includes:
      - sys tracing or profiling hooks
      - stack inspection for 'pycallgraph'
    """
    return _is_traced() or _has_pycallgraph_stack()


# End of file: src/mstair/common/base/config.py
