# File: python/plib_/base/context_managers.py
"""
Context managers for managing system paths and rendering contexts.

Provides:
- sys_path_prepended: Temporarily prepends a directory to sys.path.
- CycleGuardContext: Prevents direct object cycles in recursive rendering.
- KWArgsContext: Manages stack-based rendering keyword argument context.
- module_context: Loads a Python module from a file in isolation.
"""

import contextlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, ClassVar, NamedTuple


@contextmanager
def sys_path_prepended(path: str) -> Iterator[None]:
    """
    Context manager to temporarily prepend a directory to sys.path.

    Ensures the directory is first in sys.path for the context's duration,
    and restores the original sys.path state afterward.

    :param path: Directory path to prepend.
    :yield: None
    """
    sys.path.insert(0, path)
    try:
        yield
    finally:
        # Only remove the prepended path if it is still at the front (robustness for nested contexts)
        if sys.path and sys.path[0] == path:
            sys.path.pop(0)


class CycleGuardSeenItem(NamedTuple):
    """
    Represents an object identity+type for use in cycle detection.

    :param obj_id: The id() of the object.
    :param obj_type: The type of the object.
    """

    obj_id: int
    obj_type: type


class CycleGuardContext:
    """
    Maintains a stack to track objects during recursive rendering, preventing direct cycles.

    This is intended for use with xdumps or other recursive renderers to avoid infinite recursion.
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

    Useful for passing context like indent, compact, and separators through recursive
    rendering operations (such as xdumps or custom pretty-printers).
    """

    _xargs_stack: ClassVar[list[dict[str, Any]]] = []

    @classmethod
    @contextlib.contextmanager
    def set_kwargs(cls, **kwargs: Any) -> Iterator[None]:
        """
        Push kwargs onto the stack for use within the context.

        :param kwargs: Keyword arguments to be made available to recursive rendering code.
        :yield: None
        :raises RuntimeError: If popping from an empty stack.
        """
        cls._xargs_stack.append(kwargs)
        try:
            yield
        finally:
            if not cls._xargs_stack:
                raise RuntimeError(f"{cls.__name__} stack is empty. Cannot pop.")
            cls._xargs_stack.pop()

    @classmethod
    def get_kwargs(cls) -> dict[str, Any]:
        """
        Return the most recent rendering kwargs context.

        :return: The topmost context dict of rendering kwargs.
        :rtype: dict[str, Any]
        :raises RuntimeError: If stack is empty.
        """
        if not cls._xargs_stack:
            raise RuntimeError(f"{cls.__name__} stack is empty.")
        return cls._xargs_stack[-1]


# End of file: src/mstair/common/base/context_managers.py
