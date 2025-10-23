"""
Provides a single wrapper around Ruff for formatting and import sorting.
Uses stdin/stdout approach with --stdin-filename to preserve project context.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mstair.common.base.string_helpers import text_checksum
from mstair.common.xlogging.logger_factory import create_logger


_LOG = create_logger(__name__)


def format_source_code(
    *,
    text: str,
    target: Path,
    timeout: float = 10.0,
) -> str:
    """
    Format and sort imports in Python source code using Ruff.

    Runs `ruff check --select I --fix` (import sort) and `ruff format`
    via stdin with --stdin-filename to preserve project context.

    :param text: Python source text
    :param target: Source file path for context and config resolution
    :param timeout: Timeout in seconds
    :return: Formatted source code string
    """
    _LOG.trace("\n  target=%s", target)
    original = text
    result = text
    try:
        # Run Ruff check with import sorting and auto-fix
        proc = _run_ruff_command(
            *("check", "--select", "I", "--fix"),
            input=result,
            timeout=timeout,
            target=target,
        )
        if _ruff_not_available(proc):
            _LOG.warning("Ruff not available\n  target: %s", target)
            return original
        elif proc.returncode in {0, 1} and proc.stdout:
            result = proc.stdout
            _LOG.debug(f"{text_checksum(result)=}")
        else:
            _LOG.warning(
                "ruff check import sort failed rc=%s: %s",
                proc.returncode,
                proc.stderr.strip() if proc.stderr else "no error output",
            )

        # Run Ruff format
        proc = _run_ruff_command("format", target=target, input=result, timeout=timeout)

        if proc.returncode == 0 and proc.stdout:
            result = proc.stdout
            _LOG.debug(f"After format {text_checksum(result)=}")
        else:
            if _ruff_not_available(proc=proc):
                _LOG.warning("Ruff not available - returning original source")
                return original
            _LOG.warning(
                "ruff format failed rc=%s: %s",
                proc.returncode,
                proc.stderr.strip() if proc.stderr else "no error output",
            )

        # Preserve original line endings
        if ("\r\n" in original) and ("\r\n" not in result):
            result = result.replace("\n", "\r\n")
        elif ("\r\n" not in original) and ("\r\n" in result):
            result = result.replace("\r\n", "\n")

    except subprocess.TimeoutExpired:
        _LOG.warning("Ruff timed out for %s", target)
    except FileNotFoundError:
        _LOG.warning("Ruff not found - returning original source")
    except Exception as exc:
        _LOG.warning("Unexpected error in Ruff for %s: %s", target, exc)

    _LOG.debug(f"Final {text_checksum(result)=}")
    return result


def _run_ruff_command(
    *args: str,
    input: str | None = None,
    timeout: float | None = None,
    target: Path,
) -> subprocess.CompletedProcess[str]:
    """
    Run a Ruff command with the given arguments and input.

    :param args: Arguments to pass to Ruff
    :param input: Input text to pass via stdin
    :param timeout: Timeout in seconds
    :param target: Target file path for context
    :return: CompletedProcess instance
    """
    cmd = [sys.executable, "-m", "ruff", *args, "--stdin-filename", target.resolve().as_posix(), "-"]
    _LOG.debug("%s", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        input=input.replace("\r\n", "\n").replace("\r", "\n") if input is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if input is not None and proc.stdout and "\r\n" in input:
        proc.stdout = proc.stdout.replace("\n", "\r\n")
    return proc


def _ruff_not_available(proc: subprocess.CompletedProcess[str]) -> bool:
    """Check for missing Ruff tool based on stderr."""
    if proc.returncode in {0, 1}:
        return False
    stderr = proc.stderr if proc else ""
    if not stderr:
        return False
    msg = stderr.lower()
    return any(
        marker in msg
        for marker in (
            "no module named ruff",
            "module 'ruff' not found",
            "could not find ruff",
            "ruff: command not found",
        )
    )
