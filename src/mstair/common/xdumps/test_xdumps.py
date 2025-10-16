# File: python/plib_/xdumps/test_xdumps.py
"""
Refactored unit tests for xdumps: one test per major rendering story.

This module validates that the `xdumps` function correctly renders:

- Flat containers with basic primitives
- Extended built-in types like Decimal, Fraction, timedelta
- Exception and HTTP response types
- Dataclasses with uninitialized fields
- Unrenderable objects with fallback rendering

All tests use compact mode and controlled separators for normalized output.
"""

import array
import dataclasses
import json
from collections import OrderedDict, defaultdict, deque
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from typing import Any, NamedTuple

import pytest

from mstair.common.xdumps.customizer_registry import (
    CustomizerRegistry,
    XRawString,
    get_customizer,
)
from mstair.common.xdumps.model import Token, XTokenCustomization
from mstair.common.xdumps.token_stream import TokenStream
from mstair.common.xdumps.xdumps_api import xdumps


# == Fixtures ==


@dataclasses.dataclass
class D:
    x: int
    y: int = dataclasses.field(init=False)


@pytest.fixture
def kwargs_for_compact() -> dict[str, Any]:
    """Common rendering args for compact, normalized output."""
    return {"indent": None, "literals": ("null", "true", "false")}


@pytest.fixture
def value_with_extended_types() -> dict[str, Any]:
    """Esoteric stdlib types to validate custom rendering."""
    return {
        "td": timedelta(days=1, hours=2, minutes=3, seconds=4),
        "dec": Decimal("12.34"),
        "frac": Fraction(3, 4),
        "exc": ValueError("problem"),
    }


@pytest.fixture
def customizer_for_decimals() -> Callable[[Any, int], str | None]:
    """Test customizer that renders Decimals explicitly."""

    def render(value: Any, depth: int) -> str | None:
        if isinstance(value, Decimal):
            return f"Decimal({value})"
        return None

    return render


@pytest.fixture
def value_with_partial_dataclass() -> Any:
    """Dataclass with a missing init=False field."""

    @dataclasses.dataclass
    class D:
        x: int
        y: int = dataclasses.field(init=False)

    return D(x=42)


@pytest.fixture
def value_with_unrenderable_object() -> Any:
    """Object whose __str__ returns a fixed broken string."""

    class U:
        def __str__(self) -> str:
            return "<bad>"

    return U()


@pytest.fixture
def value_with_width_and_depth() -> dict[str, Any]:
    """Nested structure with enough breadth and depth to test max_items and max_depth."""
    return {
        "a": [1, 2],
        "b": {"c": 3, "d": 4},
        "e": (5, 6, 7),
    }


@pytest.fixture
def value_with_container_variants() -> dict[str, Any]:
    """Diverse built-in containers with at least 2 items for width tests."""

    class Point(NamedTuple):
        x: int
        y: int

    return {
        "ordered_dict": OrderedDict([("x", 1), ("y", 2), ("z", 3)]),
        "default_dict": defaultdict(int, {"a": 1, "b": 2}),
        "deque_obj": deque([4, 5, 6]),
        "frozenset_obj": frozenset({1, 2, 3}),
        "namedtuple_obj": Point(9, 10),
        "range_obj": range(3),
        "array_obj": array.array("i", [7, 8, 9]),
    }


# == Unit Tests for xdumps ==


@pytest.mark.unit
def test_containers_flatten_correctly(kwargs_for_compact: dict[str, Any]) -> None:
    """
    Verify that dictionaries and lists are rendered into compact, flat strings.

    This ensures proper separator handling and value placement for common structures.
    """
    obj = {"x": [1, 2], "y": {"a": True}}
    result = xdumps(obj, **kwargs_for_compact)
    assert '"x": [1, 2]' in result
    assert '"y": {"a": true}' in result


@pytest.mark.unit
def test_extended_types_are_rendered(
    value_with_extended_types: dict[str, Any], kwargs_for_compact: dict[str, Any]
) -> None:
    """Confirm that known extended types (timedelta, Decimal, Fraction, Exception) are rendered as strings."""
    result = xdumps(value_with_extended_types, **kwargs_for_compact)
    assert "1d:2h:03m:04s" in result
    assert "12.34" in result
    assert "3/4" in result
    assert "problem" in result


@pytest.mark.unit
def test_partial_dataclass_does_not_crash(
    value_with_partial_dataclass: Any, kwargs_for_compact: dict[str, Any]
) -> None:
    """Validate that dataclasses with uninitialized fields still render safely."""
    result = xdumps(value_with_partial_dataclass, **kwargs_for_compact)
    assert "x" in result
    assert "42" in result


@pytest.mark.unit
def test_unrenderable_object_fallback(
    value_with_unrenderable_object: Any, kwargs_for_compact: dict[str, Any]
) -> None:
    """Ensure that objects with faulty or minimal __str__ implementations fall back gracefully."""
    result = xdumps(value_with_unrenderable_object, **kwargs_for_compact)
    assert "<bad>" in result


@pytest.mark.unit
def test_vs_json_dumps() -> None:
    """
    Compare xdumps output to json.dumps for standard types to ensure consistency.

    This test ensures that xdumps behaves similarly to json.dumps for common structures.
    """

    obj: dict[str, list[int] | dict[str, bool | None]] = {
        "a": [1, 2, 3],
        "b": {"x": True, "y": None},
    }

    @dataclasses.dataclass(frozen=True)
    class DumpCase:
        indent: int | None
        separators: tuple[str, str] | None

    tests: list[DumpCase] = [
        DumpCase(indent=None, separators=None),
        DumpCase(indent=2, separators=(",", ": ")),
        DumpCase(indent=4, separators=(",", ": ")),
        DumpCase(indent=2, separators=(",", ": ")),
    ]

    for test in tests:
        pott_result = xdumps(
            obj,
            indent=test.indent,
            separators=test.separators,
            literals=("null", "true", "false"),
        )
        # Only pass supported arguments to json.dumps
        json_kwargs: dict[str, Any] = {}
        if test.indent is not None:
            json_kwargs["indent"] = test.indent
        if test.separators is not None:
            json_kwargs["separators"] = test.separators
        json_result = json.dumps(obj, **json_kwargs)
        if pott_result != json_result:
            print("")
            print(
                "xdumps with indent={} and separators={}:\n{}".format(
                    test.indent, test.separators, pott_result
                )
            )
            print("json.dumps result:\n{}".format(repr(json_result)))
            print("pott.xdumps result:\n{}".format(repr(pott_result)))
        assert pott_result == json_result


@pytest.mark.unit
def test_customize_value_format(
    customizer_for_decimals: Callable[[Any, int], str | None], kwargs_for_compact: dict[str, Any]
) -> None:
    """Validate that customizers can modify the rendering output as expected."""
    obj = {"dec": Decimal("3.14")}
    result = xdumps(obj, **kwargs_for_compact, customizers=[customizer_for_decimals])
    assert "Decimal(3.14)" in result


@pytest.mark.unit
def test_empty_list_and_dict_render_compactly() -> None:
    """Empty lists and dicts render as [] and {} with no spaces between delimiters, regardless of indentation settings."""
    for indent in (None, 0, 2, 4):
        result = xdumps([], indent=indent, literals=("null", "true", "false"))
        assert result == "[]", f"Empty list with indent={indent} gave: {repr(result)}"

        result = xdumps({}, indent=indent, literals=("null", "true", "false"))
        assert result == "{}", f"Empty dict with indent={indent} gave: {repr(result)}"


@pytest.mark.unit
def test_empty_and_nested_compact_rendering() -> None:
    """
    Structured containers (list, dict, tuple, set) render with correct spacing and delimiters.
    - Lists/dicts: match json.dumps
    - Tuples: use () delimiters
    - Sets: use {} for non-empty, '{}' for empty
    """
    cases: dict[str, Any] = {
        "empty list": {"input": [], "expected": {None: "[]", 2: "[]", 4: "[]"}},
        "empty dict": {"input": {}, "expected": {None: "{}", 2: "{}", 4: "{}"}},
        "empty tuple": {"input": (), "expected": {None: "()", 2: "()", 4: "()"}},
        "empty set": {"input": set(), "expected": {None: "{}", 2: "{}", 4: "{}"}},
        "nested empty list/dict": {
            "input": [[], {}],
            "expected": {None: "[[], {}]", 2: "[\n  [],\n  {}\n]", 4: "[\n    [],\n    {}\n]"},
        },
        "nested empty tuple": {
            "input": [()],
            "expected": {None: "[()]", 2: "[\n  ()\n]", 4: "[\n    ()\n]"},
        },
        "nested empty set": {
            "input": [set()],
            "expected": {None: "[{}]", 2: "[\n  {}\n]", 4: "[\n    {}\n]"},
        },
        "set of tuples": {
            "input": {()},
            "expected": {None: "{()}", 2: "{\n  ()\n}", 4: "{\n    ()\n}"},
        },
        "tuple of sets": {
            "input": ({()},),
            "expected": {
                None: "({()})",
                2: "(\n  {\n    ()\n  }\n)",
                4: "(\n    {\n        ()\n    }\n)",
            },
        },
    }

    for label, case in cases.items():
        inp = case["input"]
        for indent, expected in case["expected"].items():
            result = xdumps(inp, indent=indent, literals=("null", "true", "false"))
            assert f"{result!r}" == f"{expected!r}", (
                f"{label!r} failed for indent={indent}: {result!r} != {expected!r}"
            )


@pytest.mark.unit
def test_xdumps_max_width_1_and_depth_1(
    value_with_width_and_depth: Any, kwargs_for_compact: dict[str, Any]
) -> None:
    """Verify that max_items=1 (width) and max_depth=1 (depth) work independently as intended."""
    result = xdumps(value_with_width_and_depth, max_width=1, max_depth=999, **kwargs_for_compact)
    assert "..." in result
    assert "[1, ...]" in result or "(5, ...)" in result

    result = xdumps(value_with_width_and_depth, max_width=999, max_depth=1, **kwargs_for_compact)
    assert result.count("...") >= 2
    assert "a" in result and "b" in result and "e" in result


@pytest.mark.unit
def test_xdumps_max_width_zero_all_ellipsis(
    value_with_width_and_depth: Any, kwargs_for_compact: dict[str, Any]
) -> None:
    """With max_items=0, all containers are replaced with an ellipsis."""
    result = xdumps(value_with_width_and_depth, max_width=0, **kwargs_for_compact)
    assert result.strip() in {"{...}", '{"...": "..."}'} or "..." in result
    assert result.count("...") >= 1


@pytest.mark.unit
def test_xdumps_width_and_depth_both_1(
    value_with_width_and_depth: Any, kwargs_for_compact: dict[str, Any]
) -> None:
    """If max_items=1 and max_depth=1, both constraints are applied simultaneously."""
    result = xdumps(value_with_width_and_depth, max_width=1, max_depth=1, **kwargs_for_compact)
    assert result.count("...") >= 2


def test_customizer_applied_for_partial_dataclass(value_with_partial_dataclass: Any) -> None:
    reg = CustomizerRegistry()
    result: XTokenCustomization | None = reg.customize(value_with_partial_dataclass, depth=0)
    assert result is not None, "Expected dataclass customizer to fire"
    result_value = result.value
    assert isinstance(result_value, dict)
    value_dict: dict[str, Any] = result.value
    assert "x" in value_dict
    assert "y" not in value_dict


def test_dataclass_root_token_uses_override() -> None:
    d = D(x=42)
    ts = TokenStream(d, customizers=[])  # default customizers still included
    it = iter(ts)
    token: Token = next(it)  # root VALUE or OPEN token
    # Inspect whether override fired
    if token.kind.name == "VALUE":
        assert token.customization and token.customization.override
        token_value = token.value
        assert isinstance(token_value, dict)
        assert "x" in token_value
    else:
        # if OPEN, then its parent VALUE token should have override
        parent = token.parent
        assert parent and parent.customization and parent.customization.override
        assert "x" in parent.value


def test_max_width_zero_replaces_entire_mapping() -> None:
    c = get_customizer().max_container_width(max_width=0)
    data = {"a": 1, "b": 2}
    assert c is not None
    result = c(data, 0)
    assert isinstance(result, XTokenCustomization)
    assert result.raw_string
    assert str(result.value) == "..."


def test_max_width_positive_truncates_sequence() -> None:
    c = get_customizer().max_container_width(max_width=2)
    data = [1, 2, 3, 4]
    assert c is not None
    result = c(data, 0)
    assert isinstance(result, XTokenCustomization)
    assert result.value[-1] == XRawString("...")


def test_max_width_positive_truncates_set() -> None:
    c = get_customizer().max_container_width(max_width=1)
    data = {1, 2}
    assert c is not None
    result = c(data, 0)
    assert isinstance(result, XTokenCustomization)
    assert any(isinstance(v, XRawString) and str(v) == "..." for v in result.value)


def test_max_width_dataclass_truncated_fields() -> None:
    c = get_customizer().max_container_width(max_width=0)
    d = D(x=42)
    assert c is not None
    result = c(d, 0)
    assert isinstance(result, XTokenCustomization)
    assert str(result.value) == "..."


def test_max_width_dataclass_partial() -> None:
    c = get_customizer().max_container_width(max_width=1)
    d = D(x=42)
    assert c is not None
    result = c(d, 0)
    assert isinstance(result, XTokenCustomization)
    # should still include "x" and not crash on missing "y"
    assert "x" in result.value


def test_partial_dataclass_tokenstream(value_with_partial_dataclass: Any) -> None:
    ts = TokenStream(value_with_partial_dataclass)
    tokens: list[Token] = ts.tokens()
    root: Token = tokens[0]
    if root.kind.name == "VALUE":
        assert root.customization and root.customization.override
        assert "x" in root.value
        assert "y" not in root.value
    else:
        parent = root.parent
        assert parent and parent.customization and parent.customization.override
        assert "x" in parent.value
        assert "y" not in parent.value


def test_partial_dataclass_customization_provenance(value_with_partial_dataclass: Any) -> None:
    reg = CustomizerRegistry()
    result: XTokenCustomization | None = reg.customize(value_with_partial_dataclass, depth=0)
    assert result and result.source_type and result.source_type.__name__ == "D"


@pytest.mark.unit
def test_xdumps_rshift_applies_global_padding(kwargs_for_compact: dict[str, Any]) -> None:
    """
    Verify that the rshift parameter left-pads all lines by the requested number of spaces.
    """
    obj = {"a": [1, 2]}
    kwargs: dict[str, Any] = {**kwargs_for_compact, "indent": 2, "rshift": 4}
    result = xdumps(obj, **kwargs)
    lines = result.splitlines()
    # Every line should start with exactly 4 spaces
    assert all(line.startswith("    ") for line in lines), f"Unexpected rshift result:\n{result}"
    # Sanity check: removing the padding should match normal xdumps output
    kwargs = {**kwargs_for_compact, "indent": 2, "rshift": 0}
    unshifted = xdumps(obj, **kwargs)
    stripped = "\n".join(line[4:] if line.startswith("    ") else line for line in lines)
    assert stripped == unshifted


# End of file: src/mstair/common/xdumps/test_xdumps.py
