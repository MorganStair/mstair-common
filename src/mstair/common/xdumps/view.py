"""
Visual formatting for structured object rendering.

This module provides rendering logic for depth-aware formatting
and type-specific stringification. It includes:

- `Formatter`: Applies indentation to TokenEmissionContext emissions.
- `Renderer`: Registry for type-specific render functions.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from typing import Any, Final

from mstair.common.base.config import in_desktop_mode
from mstair.common.base.constants import DEFAULT_INDENT
from mstair.common.base.types import CALCULATE, Sentinel
from mstair.common.xdumps import model


# No exports that would be used outside of the package.
__all__ = [
    "TokenFormatter",
]

type _AtomRendererFunction = Callable[[Any], str]
type _TokenFormatterFunction = Callable[[model.Token], str]


def _atom_render_timedelta(obj: timedelta) -> str:
    """Render a timedelta object as a human-readable string."""
    seconds = int(obj.total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    chunks: list[str] = []
    if days:
        chunks.append(f"{days}d:")
    if hours or chunks:
        chunks.append(f"{hours}h:")
    if minutes or chunks:
        chunks.append(f"{minutes:02}m:")
    chunks.append(f"{seconds:02}s")
    return "".join(chunks)


def _atom_render_decimal(obj: Decimal) -> str:
    """Render a Decimal object as a string, preserving precision."""
    try:
        return str(int(obj)) if obj == obj.to_integral_value() else str(float(obj))
    except Exception:
        return str(obj)


def _atom_render_unknown(x: Any) -> str:
    """Render an unknown type as a string representation."""
    t = type(x)
    try:
        return t.__name__ + "<" + str(x) + ">"
    except Exception as e:
        return f"<unrenderable {t.__name__}: {e}>"


_ATOMIC_RENDERERS: Final[dict[type, _AtomRendererFunction]] = {
    bytes: lambda x: x.decode("utf-8", errors="ignore") if x else "",
    str: str,
    int: str,
    float: str,
    type: lambda x: f"<type:{x.__name__}>",
    Fraction: lambda x: f"{x.numerator}/{x.denominator}",
    Decimal: _atom_render_decimal,
    timedelta: _atom_render_timedelta,
}


@dataclass(kw_only=True)
class TokenFormatter:
    """
    Applies indentation and formatting rules to Token emissions.
    """

    indent: Any = CALCULATE
    """Number of spaces for indentation, or None for compact mode."""

    separators: tuple[str, str] | None = None
    """Optional tuple of separators for JSON-like formatting."""

    literals: tuple[str, str, str] = ("None", "True", "False")
    """String representations for None, True, and False values."""

    escape_unicode: bool = True
    """If True, escape non-ASCII characters in output strings."""

    _token_formatters: dict[model.KindT, _TokenFormatterFunction] = field(init=False, repr=False)
    """Registry of token kind to formatting functions, initialized in __post_init__."""

    def __post_init__(self) -> None:
        """Initialize the token formatters based on the indent and separators settings."""
        if self.indent is CALCULATE:
            self.indent = DEFAULT_INDENT if in_desktop_mode() else None

        self._token_formatters: dict[model.KindT, _TokenFormatterFunction] = {
            model.Kind.OPEN: self._token_format_open,
            model.Kind.CLOSE: self._token_format_close,
            model.Kind.ITEM_SEP: self._token_format_item_sep,
            model.Kind.KV_SEP: self._token_format_kv_sep,
            model.Kind.VALUE: self._format_value,
        }

    def token_format(self, token: model.Token) -> str:
        """Call the appropriate formatter method for a given token."""
        chunk = ""
        try:
            chunk = self._token_formatters[token.kind](token)
        except KeyError as e:
            raise ValueError(f"Unsupported token kind for rendering: {token.kind}") from e
        return chunk

    def _token_format_open(self, token: model.Token) -> str:
        """Render an OPEN token, with trailing newline if the container is non-empty."""
        chunk = self.get_indentation(token) + token.delimiters(self.indent, self.separators).open
        if self.indent is not None and token.parent and token.parent.value:
            chunk += "\n"
        return chunk

    def _token_format_close(self, token: model.Token) -> str:
        """Render a CLOSE token, with leading newline if the container is non-empty."""
        chunk = ""
        if self.indent is not None and token.parent and token.parent.value:
            chunk = "\n" + self.get_indentation(token)
        chunk += token.delimiters(self.indent, self.separators).close
        return chunk

    def _token_format_item_sep(self, token: model.Token) -> str:
        """Render an ITEM_SEP token, with a trailing newline or space based on the indent setting."""
        if self.indent == 0:
            chunk = token.delimiters(self.indent, self.separators).itemsep + " "
        elif self.indent is not None:
            chunk = token.delimiters(self.indent, self.separators).itemsep + "\n"
        else:
            chunk = token.delimiters(self.indent, self.separators).itemsep
        return chunk

    def _token_format_kv_sep(self, token: model.Token) -> str:
        chunk = token.delimiters(self.indent, self.separators).kvsep
        return chunk

    def _format_value(self, token: model.Token) -> str:
        """
        Render VALUE tokens, respecting XTokenCustomization.
        """
        # Handle raw_string at this level: unquoted, no escaping
        if token.customization and token.customization.raw_string:
            chunk = str(token.value)
        else:
            chunk = self.stringify_atom(token.value)
        # Only indent atoms (not containers)
        if not token.is_container:
            chunk = self.get_indentation(token) + chunk
        return chunk

    def get_indentation(self, token: model.Token) -> str:
        rshift: int = 0
        if isinstance(self.indent, int) and self.indent > 0 and not token.is_kvv:
            if token.kind is model.Kind.VALUE:
                rshift = token.depth * self.indent
            elif token.kind is model.Kind.OPEN:
                if token.parent is not None:
                    rshift = token.parent.depth * self.indent
                else:
                    rshift = 0  # Root: no indent
            elif token.kind is model.Kind.CLOSE:
                if token.parent is not None:
                    rshift = token.parent.depth * self.indent
                else:
                    rshift = 0  # Root: no indent
        return " " * rshift

    def stringify_atom(self, atom: Any) -> str:
        if isinstance(atom, type(None)):
            chunk = self.literals[0]  # 'null'
        elif atom is True:
            chunk = self.literals[1]  # 'true'
        elif atom is False:
            chunk = self.literals[2]  # 'false'
        elif isinstance(atom, Sentinel):
            chunk = str(atom)  # 'MISSING' or 'CALCULATE'
        elif type(atom) in {str, int, float}:
            chunk = json.dumps(atom)
        else:
            renderer: _AtomRendererFunction = next(
                (
                    _ATOMIC_RENDERERS[_mro]
                    for _mro in type(atom).__mro__
                    if _mro in _ATOMIC_RENDERERS
                ),
                _atom_render_unknown,
            )
            value = renderer(atom)
            chunk = json.dumps(value)
        return chunk
