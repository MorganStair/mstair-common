# File: python/plib_/xdumps/xdumps_api.py
"""
Structured object visualization for debugging and inspection.

This module defines `dumps()` and `xdumps()`, which generate compact or pretty-printed
textual representations of arbitrary Python objects. Output is designed for **human readability**,
not for serialization or round-tripping.

Compared to `json.dumps()`, this renderer:

- Supports arbitrary Python types, including user-defined classes
- Detects and safely handles cyclic references
- Preserves structure using formatting tokens (e.g., brackets, commas, indentation)
- Avoids quoting rules and escaping constraints of JSON
- Uses dynamic type inspection and registered renderers for extended types
"""

from __future__ import annotations

import inspect
from functools import cache
from typing import Any

from mstair.common.base.config import in_desktop_mode
from mstair.common.base.constants import DEFAULT_INDENT
from mstair.common.base.types import CALCULATE, Calculate
from mstair.common.xdumps.customizer_registry import (
    XCustomizerFunction,
    get_customizer,
)
from mstair.common.xdumps.token_stream import TokenStream
from mstair.common.xdumps.view import TokenFormatter


__all__ = [
    "dumps",
    "xdumps",
    "XDUMPS_VALID_KWARGS",
]


def dumps(value: Any, **kwargs: Any) -> str:
    """
    `json.dumps()`-like variant of xdumps() for API compatibility.

    Args:
        value: The object to render.
        **kwargs: Options forwarded to xdumps().

    Returns:
        str: A string representation of value in JSON-ish style (not valid JSON).
    """
    defaults = dict(
        literals=("null", "true", "false"),
        string_bypass=False,
        indent=None,
    )
    params: dict[str, Any] = {**defaults, **kwargs}
    return xdumps(value, **params)


def xdumps(
    value: Any,
    *,
    indent: int | Calculate | None = CALCULATE,
    separators: tuple[str, str] | None = None,
    escape_unicode: bool = False,
    literals: tuple[str, str, str] = ("None", "True", "False"),
    rshift: int = 0,
    max_width: int = -1,
    max_depth: int = -1,
    customizers: list[XCustomizerFunction] | None = None,
    string_bypass: bool = True,
    **_kwargs: Any,
) -> str:
    """
    Render a structured, human-readable string representation of any Python object.

    Unlike json.dumps(), this can handle arbitrary types, cyclic references, and
    includes pretty-print options for debugging and inspection.

    Args:
        value: The object to render.
        indent: Indentation level (None disables pretty-print).
        separators: Tuple of separators (item, key-value).
        escape_unicode: If True, escapes Unicode characters.
        literals: Replacements for (None, True, False).
        rshift: Pad all lines with rshift spaces.
        string_bypass: If True and value is str, returns it as-is.
        max_container_width: Max items shown in any container type.
        max_container_depth: Max nested depth.
        customizers: Additional customizer functions.
        **_kwargs: Allows callers to pass their own kwargs unfiltered without causing errors.

    Returns:
        str: Human-readable representation of value.
    """
    _customizers: list[XCustomizerFunction] = customizers.copy() if customizers else []
    _customizers.extend(
        _c
        for _c in [
            get_customizer().libpath_path_as_posix(),
            get_customizer().max_container_width(max_width=max_width),
            get_customizer().max_container_depth(max_depth=max_depth),
            get_customizer().wrap_derived_class_instances(),
        ]
        if _c is not None
    )

    if string_bypass and isinstance(value, str):
        text = value
    else:
        _indent = (
            indent
            if isinstance(indent, (int, type(None)))
            else DEFAULT_INDENT
            if in_desktop_mode()
            else None
        )
        _token_stream = TokenStream(
            value,
            customizers=_customizers,
        )
        _formatter = TokenFormatter(
            escape_unicode=escape_unicode,
            indent=_indent,
            separators=separators,
            literals=literals,
        )
        _chunks: list[str] = []
        for _token in _token_stream:
            _chunk = _formatter.token_format(_token)
            _chunks.append(_chunk)
        text = "".join(_chunks)
    if rshift > 0:
        lines = text.splitlines(keepends=True)
        text = "".join(" " * rshift + line for line in lines)
    return text


@cache
def XDUMPS_VALID_KWARGS() -> set[str]:
    """Return the set of valid argument names for xdumps() by inspecting its signature."""
    sig = inspect.signature(xdumps)
    valid_arg_names = {
        param.name
        for param in sig.parameters.values()
        if param.kind
        in {
            param.POSITIONAL_OR_KEYWORD,
            param.KEYWORD_ONLY,
        }
    }
    return valid_arg_names


# End of file: src/mstair/common/xdumps/xdumps_api.py
