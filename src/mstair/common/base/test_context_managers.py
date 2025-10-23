# File: tests/test_context_managers.py
"""
Unit tests for mstair.common.base.context_managers.

These tests verify context behaviors (stack integrity, sys.path cleanup,
and module loading isolation). They do not depend on private state.
"""

from __future__ import annotations

import logging
import sys
import tempfile
import textwrap
import types
from pathlib import Path

import pytest

from mstair.common.base.context_managers import (
    CycleGuardContext,
    KWArgsContext,
    py_module_context,
    sys_path_prepended,
)


# ----------------------------------------------------------------------
# sys_path_prepended
# ----------------------------------------------------------------------


def test_sys_path_prepended_adds_and_restores(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure sys.path is correctly modified and restored."""
    orig_path = list(sys.path)
    new_path = str(Path.cwd())
    with sys_path_prepended(new_path):
        assert sys.path[0] == new_path
    assert sys.path == orig_path


# ----------------------------------------------------------------------
# CycleGuardContext
# ----------------------------------------------------------------------


def test_cycle_guard_detects_cycle() -> None:
    """Ensure direct self-reference cycles are detected within a single stack."""
    a: dict[str, object] = {}
    a["self"] = a

    # First entry: no cycle yet
    with CycleGuardContext.prevent_cycles(a) as first:
        assert first is False
        # Second entry while still inside -> cycle detected
        with CycleGuardContext.prevent_cycles(a) as second:
            assert second is True

    # After exiting, stack clears; a new entry is not a cycle
    with CycleGuardContext.prevent_cycles(a) as third:
        assert third is False


# ----------------------------------------------------------------------
# KWArgsContext
# ----------------------------------------------------------------------


def test_kwargs_context_push_and_pop() -> None:
    """Ensure kwargs stack pushes and pops correctly."""
    with KWArgsContext.set_kwargs(indent=2):
        assert KWArgsContext.get_kwargs()["indent"] == 2
    with pytest.raises(RuntimeError):
        # Manually empty stack and try to pop again
        KWArgsContext.xargs_stack.clear()
        KWArgsContext.get_kwargs()


def test_kwargs_context_nested() -> None:
    """Ensure nested context stacks work correctly."""
    with KWArgsContext.set_kwargs(level=1):
        assert KWArgsContext.get_kwargs()["level"] == 1
        with KWArgsContext.set_kwargs(level=2):
            assert KWArgsContext.get_kwargs()["level"] == 2
        assert KWArgsContext.get_kwargs()["level"] == 1


# ----------------------------------------------------------------------
# py_module_context
# ----------------------------------------------------------------------


def test_py_module_context_executes_and_cleans() -> None:
    """Ensure a temporary module can be imported and cleaned up."""
    logger = logging.getLogger("test")
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        module_path = project_dir / "demo_module.py"
        module_path.write_text("VALUE = 123\n")

        with py_module_context(
            project_dir=project_dir,
            rel_module_path=module_path,
            module_name="demo_module",
            logger=logger,
        ) as mod:
            assert isinstance(mod, types.ModuleType)
            assert getattr(mod, "VALUE") == 123

        # Confirm it was removed from sys.modules
        assert "demo_module" not in sys.modules


def test_py_module_context_fails_on_bad_path(tmp_path: Path) -> None:
    """Verify RuntimeError is raised for invalid module path."""
    logger = logging.getLogger("test")
    bad_path = tmp_path / "does_not_exist.py"
    with (
        pytest.raises(RuntimeError),
        py_module_context(
            project_dir=tmp_path,
            rel_module_path=bad_path,
            module_name="missing_mod",
            logger=logger,
        ),
    ):
        pass


def test_warning_escalation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify that warnings escalate to errors when logger < INFO."""
    logger = logging.getLogger("test_warning")
    logger.setLevel(logging.DEBUG)

    module_code = textwrap.dedent(
        """
        import warnings
        warnings.warn("deprecated call", DeprecationWarning)
        """
    )
    module_path = tmp_path / "warn_module.py"
    module_path.write_text(module_code)

    with (
        pytest.raises(RuntimeError),
        py_module_context(
            project_dir=tmp_path,
            rel_module_path=module_path,
            module_name="warn_module",
            logger=logger,
        ),
    ):
        pass
