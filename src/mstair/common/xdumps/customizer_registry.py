# File: python/plib_/xdumps/customizer_registry.py

from __future__ import annotations

import contextlib
import dataclasses
import logging
import pathlib
from collections.abc import Callable, Mapping, Sequence, Set
from typing import Any, final

from mstair.common.xdumps.model import Delimiters, XTokenCustomization


__all__ = [
    "CustomizerRegistry",
    "CUSTOMIZER",
    "XCustomizerFunction",
    "XRawString",
]

XCustomizerFunction = Callable[[Any, int], XTokenCustomization | str | None]
"""
A callable that customizes the rendering of a value during structured dumping.

:param value: The value to customize.
:param depth: The current depth within the data structure.
:return: An XTokenCustomization object for full control, a `str` for unquoted text, or `None` to defer to the next customizer.
:rtype: XTokenCustomization | str | None

:notes:
    Customizers are called recursively at every node. Returning None lets
    other customizers or the default logic handle the value.
"""


@final
class CUSTOMIZER:
    """A namespace class for customizer functions."""

    def __new__(cls, *_a: object, **_k: object) -> None:
        raise TypeError(f"{cls.__name__} is a namespace, not instantiable")

    @staticmethod
    def libpath_path_as_posix() -> XCustomizerFunction:
        """
        Create a customizer that renders pathlib.Path objects as POSIX-style strings.

        :return XCustomizerFunction: A customizer suitable for use with xdumps().
        """

        def _libpath_path_as_posix_customizer(
            value: object, _depth: int
        ) -> XTokenCustomization | str | None:
            if isinstance(value, pathlib.Path):
                return repr(value.as_posix())
            return None

        return _libpath_path_as_posix_customizer

    @staticmethod
    def max_container_depth(*, max_depth: int) -> XCustomizerFunction | None:
        """
        Create a customizer that limits the depth of nested structures in output.

        - If max_depth < 0, the customizer is disabled (returns None).
        - If max_depth >= 0, containers deeper than max_depth are replaced with an ellipsis ("...").
        """
        if max_depth < 0:
            return None  # disable when negative

        def _max_container_depth_customizer(value: Any, depth: int) -> XTokenCustomization | None:
            if depth > max_depth:
                return XTokenCustomization(value="...", raw_string=True)
            return None

        return _max_container_depth_customizer

    # File: src/plib_/pott/customizer_registry.py

    @staticmethod
    def max_container_width(*, max_width: int) -> XCustomizerFunction | None:
        """
        Create a customizer that limits the number of items displayed in collections and dataclasses.

        - If max_width < 0, the customizer is disabled (returns None).
        - If max_width == 0, the entire container is replaced with an ellipsis ("...").
        - If max_width > 0, containers larger than max_width are truncated with a trailing ellipsis.
        """
        if max_width < 0:
            return None  # disable when negative

        def _max_container_width_customizer(value: Any, _depth: int) -> XTokenCustomization | None:
            result: XTokenCustomization | None = None

            if isinstance(value, (str, bytes)):
                return None

            # Replace entire container with ellipsis if width == 0
            if max_width == 0 and (
                isinstance(value, (Mapping, Sequence, Set)) or dataclasses.is_dataclass(value)
            ):
                if dataclasses.is_dataclass(value):
                    delimiters = Delimiters(open=type(value).__name__ + "(", close=")", kvsep="=")
                else:
                    delimiters = Delimiters.for_object(value, indent=None, separators=None)

                return XTokenCustomization(
                    value="...",
                    raw_string=True,
                    delimiters=delimiters,
                )

            # Truncate mappings
            if isinstance(value, Mapping) and len(value) > max_width:
                keys: list[Any] = list(value)[:max_width]
                new_map: dict[Any, Any] = {k: value[k] for k in keys}
                new_map[XRawString("...")] = XRawString("...")
                result = XTokenCustomization(value=new_map)

            # Truncate dataclasses by turning them into dicts
            if result is None and dataclasses.is_dataclass(value):
                fields: tuple[dataclasses.Field[Any], ...] = dataclasses.fields(value)
                if len(fields) > max_width:
                    display_dict: dict[str | XRawString, Any] = {
                        f.name: getattr(value, f.name)
                        for f in fields[:max_width]
                        if hasattr(value, f.name)
                    }
                    display_dict[XRawString("...")] = XRawString("...")
                    result = XTokenCustomization(value=display_dict)

            # Truncate sequences (excluding str/bytes)
            if result is None and isinstance(value, Sequence) and len(value) > max_width:
                truncated: list[Any] = [*list(value[:max_width]), XRawString("...")]
                result = XTokenCustomization(
                    value=truncated if isinstance(value, list) else tuple(truncated)
                )

            # Truncate sets
            if result is None and isinstance(value, Set) and len(value) > max_width:
                truncated_set: set[Any] = set(list(value)[:max_width])
                truncated_set.add(XRawString("..."))
                result = XTokenCustomization(value=truncated_set)

            return result

        return _max_container_width_customizer

    @staticmethod
    def wrap_derived_class_instances(
        build_format_kwargs: Callable[[Any], Mapping[str, Any] | None] | None = None,
        open_fmt: str = "{__name__}(",
        close_fmt: str = ")",
        max_strlen: int = 1024,
    ) -> XCustomizerFunction:
        """
        Returns a customizer that wraps derived class instances with custom delimiters.

        Args:
            build_format_kwargs (Callable[[Any], Mapping[str, Any] | None] | None, optional):
                A function that receives a value and returns a dictionary of keyword arguments
                for formatting `open_fmt` and `close_fmt`. If None, a default implementation is used.
                The default skips built-in types and returns a dict of safe-to-format attributes
                from the type of the value, including: __name__, __module__, __qualname__, __doc__,
                __bases__, and __mro__. Complex attributes are converted to truncated strings
                (up to max_strlen).

            open_fmt (str, optional): Format string for the opening delimiter. Defaults to "{__name__}(".
            close_fmt (str, optional): Format string for the closing delimiter. Defaults to ")".
            max_strlen (int, optional): Maximum length for string representations. Defaults to 1024.

        Returns:
            XCustomizerFunction: A customizer function suitable for use with xdumps().

        Algorithm:
            - For each value, call build_format_kwargs (or the default) to obtain formatting arguments.
            - If build_format_kwargs returns None, the customizer does nothing for that value.
            - Otherwise, the customizer uses open_fmt and close_fmt, formatted with the returned arguments,
              to wrap the value with custom delimiters.
            - The default build_format_kwargs:
                * Skips values whose type is a built-in.
                * Collects type attributes (__name__, __module__, __qualname__, __doc__, __bases__, __mro__).
                * Converts non-primitive attributes to truncated strings (up to max_strlen).
        """

        def _value_to_dict(value: Any) -> Mapping[str, Any] | None:
            """
            Extract type attributes robustly, handling edge cases.
            """
            type_attrs: dict[str, Any] = {}
            try:
                t = type(value)
                if t.__module__ == "builtins":
                    return None
                type_attrs.update(t.__dict__)
            except Exception:
                return None
            essential_attrs = [
                "__name__",
                "__qualname__",
                "__module__",
                "__doc__",
                "__bases__",
                "__mro__",
            ]
            for attr in essential_attrs:
                try:
                    attr_value = getattr(t, attr, None)
                    if attr_value is not None:
                        type_attrs[attr] = attr_value
                except (AttributeError, TypeError):
                    continue

            attr_keys = list(type_attrs.keys())
            for key in attr_keys:
                try:
                    val = type_attrs[key]
                    if isinstance(val, (str, int, float, bool, type(None))):
                        pass
                    elif isinstance(val, (tuple, list)) and all(
                        isinstance(x, (str, int, float, bool)) for x in val
                    ):
                        pass
                    else:
                        str_val = str(val)
                        str_val_trimmed = str_val[:_MAX_STRLEN]
                        if str_val_trimmed and str_val_trimmed != str_val:
                            type_attrs[key] = str_val_trimmed
                except Exception:
                    continue
            return type_attrs if type_attrs else None

        def _wrap_derived_class_instances_customizer(value: Any, _depth: int):
            format_args: Mapping[str, Any] | None = _FORMAT_ARGS_FN(value)
            if format_args is None:
                return None
            with contextlib.suppress(Exception):
                return XTokenCustomization(
                    delimiters=Delimiters(
                        open=_OPEN_FMT.format(**format_args),
                        close=_CLOSE_FMT.format(**format_args),
                    ),
                    value=value,
                )

        # Define closures in all caps so they stand out
        _FORMAT_ARGS_FN: Callable[[Any], Mapping[str, Any] | None] = (
            build_format_kwargs or _value_to_dict
        )
        _OPEN_FMT: str = open_fmt
        _CLOSE_FMT: str = close_fmt
        _MAX_STRLEN: int = max_strlen

        return _wrap_derived_class_instances_customizer


class CustomizerRegistry:
    """Maintains an ordered, mutable registry of customizer functions."""

    customizers: list[XCustomizerFunction]
    """The list of customizer functions to apply in order."""

    def __init__(self, *, customizers: list[XCustomizerFunction] | None = None) -> None:
        """
        Initialize the registry with an optional initial list of customizers.

        :param customizers: An optional sequence of customizer functions to register first.
        """
        self.customizers = []
        self.reset()
        for idx, fn in enumerate(customizers or []):
            self.register(fn, idx=idx)

    def customize(self, value: Any, depth: int, **kwargs: Any) -> XTokenCustomization | None:
        """
        Apply all registered customizers in order to `value`.

        - If a customizer returns a str, wrap it in XTokenCustomization(raw_string=True)
          and stop (strings cannot merge).
        - If a customizer returns XTokenCustomization:
            * If continue_chain is False, return it immediately.
            * If continue_chain is True, merge it with the current result and continue.
        - If none apply, return None.
        """

        def _get_fn_location(customizer: Callable[..., Any]) -> str:
            file_str: str = (
                getattr(customizer, "__code__", None) and customizer.__code__.co_filename
            ) or "?"
            line_str: str = (
                getattr(customizer, "__code__", None) and str(customizer.__code__.co_firstlineno)
            ) or "?"
            function_str: str = (
                getattr(customizer, "__name__", None) and customizer.__name__ + "()"
            ) or "?"
            return f"{file_str}:{line_str} {function_str}"

        merged: XTokenCustomization | None = None
        i = 0
        LOG = logging.getLogger()
        while i < len(self.customizers):
            customizer = self.customizers[i]
            try:
                result: XTokenCustomization | str | None = customizer(value, depth, **kwargs)
                i += 1
            except Exception as exc:
                self.customizers.pop(i)
                customizer_location = _get_fn_location(customizer)
                LOG.error(
                    f"\n{customizer_location} removed for raising an exception given {value=!r}, {depth=}\n"
                )
                LOG.exception("Exception details:", exc_info=exc)
                continue

            if result is None:
                continue

            # If customizer returned a raw str -> stop
            if isinstance(result, str):
                return XTokenCustomization(value=result, raw_string=True, continue_chain=False)

            # If customizer returned XTokenCustomization
            if merged is None:
                merged = result
            else:
                if result.delimiters:
                    merged.delimiters = result.delimiters
                if result.override:
                    merged.value = result.value
                if result.raw_key_strings:
                    merged.raw_key_strings = True
                if result.raw_string:
                    merged.raw_string = True
                if result.source_type:
                    merged.source_type = result.source_type
                # keep merged.continue_chain as True unless result disables it
                if not result.continue_chain:
                    merged.continue_chain = False

            # stop if this customization disables chaining
            if isinstance(result, XTokenCustomization) and not result.continue_chain:
                return merged

        value_repr: str = "<error>"
        with contextlib.suppress(Exception):
            value_repr = repr(value)
        _merged_repr: str = "<error>"
        with contextlib.suppress(Exception):
            _merged_repr = repr(merged)

        LOG.debug(f"customize: {value_repr=} depth={depth} merged={_merged_repr}")
        return merged

    def reset(self) -> None:
        """
        Reset and (re)register the default set of built-in customizers.
        """
        self.customizers.clear()
        self.register(self._customize_raw_string)
        self.register(self._customize_exception)
        self.register(self._customize_dataclass)
        self.register(self._customize_path)

    def register(self, func: XCustomizerFunction, idx: int = 0) -> XCustomizerFunction:
        """
        Decorator to register a customizer function with highest priority.

        For example, to make exceptions render as a ExceptionType('msg'):
        ```
        @register_customizer_function
        def customize_exception(e: Exception) -> XTokenCustomization | None:
            return f"{type(e).__name__}({e})" if isinstance(e, Exception) else None
        ```
        """
        if func in self.customizers:
            del self.customizers[self.customizers.index(func)]
        self.customizers.insert(idx, func)
        return func

    @staticmethod
    def _customize_raw_string(value: Any, depth: int) -> XTokenCustomization | str | None:
        """Returns an XTokenCustomization that renders the value as a raw string."""
        if isinstance(value, XRawString):
            return XTokenCustomization(value=str(value), raw_string=True)
        return None

    @staticmethod
    def _customize_exception(value: Any, depth: int) -> XTokenCustomization | str | None:
        """Returns an XTokenCustomization that flattens the exception into a dict."""
        if isinstance(value, Exception):
            return XTokenCustomization(
                delimiters=Delimiters(open=type(value).__name__ + "(", close=")", kvsep=":"),
                value=dict(
                    message=str(value),
                    args=value.args,
                ),
            )
        return None

    @staticmethod
    def _customize_dataclass(
        value: Any, depth: int, *, strict: bool = False
    ) -> XTokenCustomization | str | None:
        """
        Returns an XTokenCustomization that customizes the formatting of dataclass instances for tokenization.

        - Uses the class name followed by '(' as the opening delimiter.
        - Uses ')' as the closing delimiter.
        - Uses '=' as the key-value separator.
        - Renders field names as unquoted raw strings.
        - Only includes fields with repr=True.
        - Skips fields that are not yet initialized (avoids AttributeError) unless strict=True.
        - If strict=True, raises AttributeError immediately on uninitialized fields.
        """

        # Only customize dataclass instances that are not already customized
        if not dataclasses.is_dataclass(value):
            return None

        LOG = logging.getLogger()
        new_dict: dict[str | XRawString, Any] = {}
        for orig_field in dataclasses.fields(value):
            if not orig_field.repr:
                continue
            if not hasattr(value, orig_field.name):
                if strict:
                    raise AttributeError(
                        f"Uninitialized field {orig_field.name!r} in dataclass {type(value).__name__}"
                    )
                LOG.warning("Skipping uninitialized field: %s", orig_field.name)
                continue
            try:
                new_dict[orig_field.name] = getattr(value, orig_field.name)
                LOG.debug(
                    "Added field %s (type=%s)",
                    orig_field.name,
                    type(new_dict[orig_field.name]).__name__,
                )
            except AttributeError as e:
                if strict:
                    raise
                LOG.error("Failed getattr for %s: %s", orig_field.name, e)
                continue

        LOG.debug("Returning customization new_dict=%r", new_dict)
        result = XTokenCustomization(
            delimiters=Delimiters(open=type(value).__name__ + "(", close=")", kvsep="="),
            value=new_dict,
            raw_key_strings=True,
            source_type=type(value),
        )
        LOG.debug("Built XTokenCustomization: %r", result)
        return result

    @staticmethod
    def _customize_path(value: Any, depth: int) -> XTokenCustomization | str | None:
        """Returns an XTokenCustomization that renders Path objects as raw strings."""
        if isinstance(value, pathlib.Path):
            return repr(value.as_posix())
        return None


class XRawString(str):
    """A custom string type that gets rendered as a raw (i.e. unquoted) string."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"


# End of file: python/plib_/xdumps/customizer_registry.py
