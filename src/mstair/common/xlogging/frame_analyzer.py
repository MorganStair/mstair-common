# File: python/plib_/xlogging/frame_analyzer.py
"""
Module: mstair.common.xlogging.frame_analyzer

Utilities for analyzing stack frames for logging purposes.
"""

from __future__ import annotations

import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from types import CodeType, FrameType
from typing import Any


def f_code_filename_relative(f_code_filename: str | Path) -> str:
    path = Path(f_code_filename)
    _rpath = ""
    with suppress(Exception):
        _rpath = path.relative_to(sys.path[0])
    if not _rpath:
        with suppress(Exception):
            _rpath = path.relative_to(Path.cwd())
    if not _rpath:
        _rpath = path.absolute()
    return _rpath.as_posix()


@dataclass
class StackFrameInfo:
    frame: FrameType
    """The actual frame object from which this info was extracted."""

    stack_position: int
    """The level of the frame in the call stack."""

    f_locals_self: object | None
    """The value of the 'self' variable in the frame's local scope, if any."""

    f_locals_class_name: str
    """Class name if the frame is a method, otherwise an empty string."""

    f_code_name: str
    """Name of the function or method"""

    f_locals_self_module_name: str
    """Module name where the function is defined."""

    f_code_filename: str
    """Path to source file (script path, import path, "<string>", or "<stdin>")"""

    code_filename_relative: str
    """The relative path from the script directory to the source file."""

    @classmethod
    def from_raw_frame(
        cls,
        *,
        raw_frame: FrameType,
        stack_position: int,
    ) -> StackFrameInfo:
        """
        Create a LoggerFrameInfo instance from a frame object.
        Robust to interpreter teardown and strictly typed.
        """

        def _get_code_attr(code: CodeType | None, attr: str, default: str = "") -> str:
            val = getattr(code, attr, default)
            return val if isinstance(val, str) else default

        def _get_class_name(locals_: dict[str, Any]) -> str:
            if (zelf := locals_.get("self")) and hasattr(zelf, "__class__"):
                return type(zelf).__name__
            if (cls_obj := locals_.get("cls")) and hasattr(cls_obj, "__name__"):
                return cls_obj.__name__
            return ""

        def _get_module(locals_: dict[str, Any], globals_: dict[str, Any]) -> str:
            if (zelf := locals_.get("self")) and isinstance(getattr(zelf, "__module__", None), str):
                return zelf.__module__
            name: str = globals_.get("__name__", "<unknown>")
            return name

        _f_code: CodeType | None = getattr(raw_frame, "f_code", None)
        _f_locals: dict[str, Any] = getattr(raw_frame, "f_locals", {})
        _f_globals: dict[str, Any] = getattr(raw_frame, "f_globals", {})
        _f_code_filename = _get_code_attr(_f_code, "co_filename")
        _f_code_name = _get_code_attr(_f_code, "co_name", "<unknown>")

        _f_code_filename_relative = f_code_filename_relative(_f_code_filename)
        return StackFrameInfo(
            f_code_filename=_f_code_filename,
            f_code_name=_f_code_name,
            frame=raw_frame,
            f_locals_class_name=_get_class_name(_f_locals),
            f_locals_self_module_name=_get_module(_f_locals, _f_globals),
            code_filename_relative=_f_code_filename_relative,
            f_locals_self=_f_locals.get("self"),
            stack_position=stack_position,
        )


# End of file: python/plib_/xlogging/frame_analyzer.py
