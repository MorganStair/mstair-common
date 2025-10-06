# File: tests/test_formatters.py
"""
Tests for Ruff-based formatter wrapper `format_source_code`.

The tests monkeypatch `subprocess.run` to avoid invoking real tools.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from mstair.common.format_helpers import format_source_code


class _Completed:
    """Minimal stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode: int = returncode
        self.stdout: str = stdout
        self.stderr: str = stderr


def test_successful_import_sort_and_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When Ruff succeeds, formatted content should be returned."""
    target_file = tmp_path / "success.py"
    original = "x=1\n"
    changed = "x = 1  # formatted\n"

    calls: list[list[str]] = []

    def fake_run(args: list[str], input: str = "", **_: Any) -> _Completed:
        calls.append(args)
        if "check" in args:
            return _Completed(1, stdout=input)  # check runs, no change
        if "format" in args:
            return _Completed(0, stdout=changed)
        return _Completed(0, stdout=input)

    monkeypatch.setattr("subprocess.run", fake_run)

    out = format_source_code(text=original, target=target_file)

    assert len(calls) == 2
    assert "check" in calls[0] and "--fix" in calls[0]
    assert "format" in calls[1]
    assert out == changed


def test_missing_ruff_returns_original(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    target_file = tmp_path / "missing.py"
    src = "a=3\n"

    def fake_run(*args: object, **kwargs: object) -> _Completed:
        return _Completed(2, stdout="", stderr="No module named ruff")

    monkeypatch.setattr("subprocess.run", fake_run)

    with caplog.at_level(logging.WARNING):
        out = format_source_code(text=src, target=target_file)

    assert out == src
    for rec in caplog.records:
        print(f"  {rec.levelname}: {rec.message}")

    log_messages = [rec.message.lower() for rec in caplog.records]
    assert any("ruff not available" in m for m in log_messages), f"{log_messages=}"


def test_format_failure_returns_check_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If the format step fails, return the check result instead."""
    target_file = tmp_path / "format_fails.py"
    src = "z=4\n"
    check_result = "z = 4  # fixed\n"

    def fake_run(args: list[str], input: str = "", **_: Any) -> _Completed:
        if "check" in args:
            return _Completed(1, stdout=check_result)
        if "format" in args:
            return _Completed(2, stdout="", stderr="Format failed")
        return _Completed(0, stdout=input)

    monkeypatch.setattr("subprocess.run", fake_run)

    out = format_source_code(text=src, target=target_file)

    assert out == check_result


def test_stdin_filename_is_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure --stdin-filename uses absolute paths."""
    absolute_path = tmp_path / "test.py"
    captured: list[str] = []

    def fake_run(args: list[str], input: str = "", **_: Any) -> _Completed:
        if "--stdin-filename" in args:
            idx = args.index("--stdin-filename")
            captured.append(args[idx + 1])
        return _Completed(0, stdout=input)

    monkeypatch.setattr("subprocess.run", fake_run)

    format_source_code(text="x=1\n", target=absolute_path)

    assert captured
    for filename in captured:
        assert Path(filename) == absolute_path


# End of file: python/tests/test_formatters.py
