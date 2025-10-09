# File: python/plib_/base/mapping_helpers.py
"""
Helpers for accessing and modifying nested mappings (e.g., dicts) via key paths.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def mapping_attr_at_keypath[T](
    map: Mapping[str, Any], keypath: str, origin: str, expected_type: type[T]
) -> T:
    """
    Retrieve a nested value from a mapping using a dot-separated keypath.

    :param map: Root mapping (e.g., a parsed TOML or JSON dictionary).
    :param keypath: Dot-separated lookup path, e.g. "tool.setuptools.packages.find.include".
    :param origin: Identifier for the mapping (used in diagnostic messages).
    :param expected_type: The expected runtime type of the final value.
    :return: The resolved value of type ``T``.
    :raises: KeyError if any key in the path is missing.
    :raises: TypeError if the resolved value is not of ``expected_type``.
    """
    # try:
    #     result = reduce(lambda acc, key: acc[key], keypath.split("."), map)
    # except KeyError as e:
    #     raise KeyError(f"Missing key '{e.args[0]}' in '{origin}' while resolving '{keypath}'")
    keys = keypath.split(".")
    visited: list[str] = []
    this_origin = origin
    current: Any = map
    for key in keys:
        visited.append(key)
        this_origin = f"{origin}:" + ".".join(visited)
        if not isinstance(current, Mapping) or key not in current:
            raise KeyError(f"Missing key at '{this_origin}'")
        current = current[key]
    if not isinstance(current, expected_type):
        wanted_type = expected_type.__name__
        actual_type = type(current).__name__
        raise TypeError(f"Expected type {wanted_type} at {this_origin} (got {actual_type})")
    return current


# End of file: src/mstair/common/base/mapping_helpers.py
