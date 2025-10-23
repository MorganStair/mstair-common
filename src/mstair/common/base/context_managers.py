# File: python/plib_/base/context_managers.py
"""
Context managers for managing system paths and rendering contexts.

Provides:
- sys_path_prepended: Temporarily prepends a directory to sys.path.
- CycleGuardContext: Prevents direct object cycles in recursive rendering.
- KWArgsContext: Manages stack-based rendering keyword argument context.
- py_module_context: Loads a Python module from a file in isolation.
"""

import contextlib
import importlib.machinery
import importlib.util
import logging
import sys
import traceback
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar, NamedTuple, TextIO

from mstair.common import base


@contextmanager
def py_module_context(
    *,
    project_dir: str | Path,
    rel_module_path: str | Path,
    module_name: str,
    logger: logging.Logger,
) -> Iterator[ModuleType]:
    """
    Context manager that loads and executes a Python module from disk in isolation.

    This temporarily prepends `project_dir` to `sys.path`, executes the module,
    and ensures that any inserted module entries are removed afterward.
    It can be used to dynamically inspect or analyze a module without
    polluting the global interpreter state.

    Example:
        >>> with py_module_context(
        ...     project_dir=".",
        ...     rel_module_path="src/example_module.py",
        ...     module_name="example_module",
        ...     logger=logging.getLogger(__name__),
        ... ) as module:
        ...     assert hasattr(module, "main")

    Raises:
        ImportError: If the module spec cannot be created.
        RuntimeError: If execution fails or produces warnings escalated to errors.
    """
    project_dir, rel_module_path = map(Path, (project_dir, rel_module_path))
    module_path_str = str((project_dir / rel_module_path).resolve())
    escalate_warnings = logger.getEffectiveLevel() < logging.INFO

    with base.config.analysis_mode_context(), sys_path_prepended(str(project_dir.resolve())):
        module_spec = importlib.util.spec_from_file_location(
            name=module_name, location=module_path_str
        )
        if not module_spec or not module_spec.loader:
            raise ImportError(f"Cannot load module spec for {module_path_str}")

        module = importlib.util.module_from_spec(module_spec)
        save_log_level = logger.level
        logger.setLevel(logging.WARNING)

        try:
            yield from _execute_module_with_warnings_escalated_if_logger_level_requires_it(
                module_spec=module_spec,
                module=module,
                escalate_warnings=escalate_warnings,
                logger=logger,
                module_path_str=module_path_str,
            )
        finally:
            # Remove the module and its submodules from sys.modules
            for name in list(sys.modules):
                if name == module_name or name.startswith(f"{module_name}."):
                    sys.modules.pop(name, None)
            logger.setLevel(save_log_level)


@contextmanager
def sys_path_prepended(path: str) -> Iterator[None]:
    """
    Context manager to temporarily prepend a directory to `sys.path`.

    Ensures the directory is first in `sys.path` for the duration of the context
    and restores the original `sys.path` state afterward. This is useful when
    temporarily loading or importing modules from a project-relative location.

    Example:
        >>> with sys_path_prepended("src"):
        ...     import my_local_module

    :param path: Directory path to prepend.
    :yield: None
    """
    sys.path.insert(0, path)
    try:
        yield
    finally:
        # Only remove the prepended path if it is still at the front
        if sys.path and sys.path[0] == path:
            sys.path.pop(0)


class CycleGuardSeenItem(NamedTuple):
    """
    Represents an object identity and type for use in cycle detection.

    Used internally by `CycleGuardContext` to identify whether an object has
    already been visited during recursive rendering or inspection.

    :param obj_id: The id() of the object.
    :param obj_type: The type of the object.
    """

    obj_id: int
    obj_type: type


class CycleGuardContext:
    """
    Maintains a stack to track objects during recursive rendering, preventing direct cycles.

    This is intended for use with recursive structures (such as nested dataclasses
    or object graphs) to avoid infinite recursion in pretty-printing or serialization.

    Example:
        >>> data = {}
        >>> data["self"] = data  # create a direct cycle
        >>> with CycleGuardContext.prevent_cycles(data) as is_cycle:
        ...     if is_cycle:
        ...         print("Cycle detected")
    """

    seen: ClassVar[list[CycleGuardSeenItem]] = []

    @classmethod
    @contextlib.contextmanager
    def prevent_cycles(cls, obj: Any) -> Iterator[bool]:
        """
        Context manager to track and detect direct cycles for the given object.

        Uses (id(obj), type(obj)) pairs to avoid false positives from
        accidental id reuse or extracted data collisions. Uses a stack,
        not a set, to allow multiple branches to visit the same object independently.

        Example:
            >>> items = []
            >>> items.append(items)
            >>> with CycleGuardContext.prevent_cycles(items) as is_cycle:
            ...     assert is_cycle is False
            >>> with CycleGuardContext.prevent_cycles(items) as is_cycle:
            ...     assert is_cycle is True

        :param obj: The object to guard against cycles.
        :yield: True if a cycle is detected, otherwise False.
        """
        obj_id = id(obj)
        obj_type: type = type(obj)  # pyright: ignore[reportUnknownVariableType]
        item = CycleGuardSeenItem(obj_id, obj_type)
        is_cycle = item in cls.seen
        cls.seen.append(item)
        try:
            yield is_cycle
        finally:
            cls.seen.pop()


class KWArgsContext:
    """
    Context manager for managing stack-based rendering keyword arguments (kwargs).

    Useful for passing contextual parameters (like indentation, compactness,
    or separators) through recursive rendering operations such as custom
    pretty-printers or serializers.

    Example:
        >>> with KWArgsContext.set_kwargs(indent=2, compact=True):
        ...     assert KWArgsContext.get_kwargs()["indent"] == 2
    """

    xargs_stack: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    @contextlib.contextmanager
    def set_kwargs(cls, **kwargs: Any) -> Iterator[None]:
        """
        Push kwargs onto the stack for use within the context.

        This enables temporarily overriding rendering parameters
        during nested or recursive formatting operations.

        Example:
            >>> with KWArgsContext.set_kwargs(indent=4):
            ...     process_data()

        :param kwargs: Keyword arguments to be made available to recursive rendering code.
        :yield: None
        :raises RuntimeError: If popping from an empty stack.
        """
        cls.xargs_stack.append(kwargs)
        try:
            yield
        finally:
            if not cls.xargs_stack:
                raise RuntimeError(f"{cls.__name__} stack is empty. Cannot pop.")
            cls.xargs_stack.pop()

    @classmethod
    def get_kwargs(cls) -> dict[str, Any]:
        """
        Return the most recent rendering kwargs context.

        This retrieves the topmost dictionary on the stack, allowing
        nested rendering logic to access the active parameters.

        Example:
            >>> with KWArgsContext.set_kwargs(indent=2):
            ...     print(KWArgsContext.get_kwargs()["indent"])  # 2

        :return: The topmost context dict of rendering kwargs.
        :rtype: dict[str, Any]
        :raises RuntimeError: If stack is empty.
        """
        if not cls.xargs_stack:
            raise RuntimeError(f"{cls.__name__} stack is empty.")
        return cls.xargs_stack[-1]


def _execute_module_with_warnings_escalated_if_logger_level_requires_it(
    *,
    module_spec: importlib.machinery.ModuleSpec,
    module: ModuleType,
    escalate_warnings: bool,
    logger: logging.Logger,
    module_path_str: str,
) -> Iterator[ModuleType]:
    """
    Execute a module specification while optionally escalating warnings to exceptions.

    This helper is used internally by `py_module_context`. When `escalate_warnings`
    is True, warnings are converted into exceptions so that test or analysis runs
    fail fast on problematic code.

    Example:
        This function is not typically called directly, but via `py_module_context`.
        It ensures consistent logging, warning escalation, and exception wrapping.

    :param module_spec: The importlib module specification for the target file.
    :param module: The module object to execute.
    :param escalate_warnings: Whether to treat warnings as exceptions.
    :param logger: Logger for emitting diagnostic output.
    :param module_path_str: The path of the module being executed.
    :yield: The executed module.
    :raises RuntimeError: If execution fails or warnings escalate to exceptions.
    """

    def warning_to_exception(
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file: TextIO | None = None,
        line: str | None = None,
    ) -> None:
        """Convert any warning into a raised exception, preserving context."""
        raise category(f"{filename}:{lineno}: {message}")

    loader = module_spec.loader
    assert loader is not None

    if escalate_warnings:
        with warnings.catch_warnings(record=True) as caught_warnings:
            old_showwarning = warnings.showwarning
            try:
                warnings.showwarning = warning_to_exception
                warnings.simplefilter("error")
                loader.exec_module(module)
            except Exception as e:
                tb = traceback.format_exc()
                msg = f"{e.__class__.__name__} loading path={module_path_str!r}: {e}\n{tb}"
                logger.error(msg, exc_info=e)
                raise RuntimeError(msg) from e
            finally:
                warnings.showwarning = old_showwarning

            for warning in caught_warnings:
                logger.warning(str(warning.message), stacklevel=2)

            yield module
    else:
        try:
            loader.exec_module(module)
            yield module
        except Exception as e:
            tb = traceback.format_exc()
            msg = f"{e.__class__.__name__} loading path={module_path_str!r}: {e}\n{tb}"
            logger.error(msg, exc_info=e)
            raise RuntimeError(msg) from e


# End of file: python/plib_/base/context_managers.py
