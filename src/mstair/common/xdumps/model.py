# File: python/plib_/xdumps/model.py
"""
Structured emission model for formatting nested Python containers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from functools import total_ordering
from types import NoneType
from typing import Any, ClassVar, Final, Self

from mstair.common.base.types import MISSING


__all__ = [
    "Delimiters",
    "KindT",
    "Kind",
    "Token",
    "XTokenCustomization",
]


class Delimiters:
    """Punctuation for formatting structured containers."""

    open: str
    close: str
    itemsep: str
    kvsep: str

    def __init__(
        self,
        open: str,
        close: str,
        itemsep: str = ",",
        kvsep: str = ":",
    ) -> None:
        self.open = open
        self.close = close
        self.itemsep = itemsep
        self.kvsep = kvsep

    def __repr__(self) -> str:
        tup: tuple[str, str, str, str] = (self.open, self.close, self.itemsep, self.kvsep)
        p = f"{tup=}"[4:]  # Skip the "tup=" prefix
        return p

    @classmethod
    def for_object(
        cls, obj: Any, indent: int | None, separators: tuple[str, str] | None
    ) -> Delimiters | None:
        if obj is None or obj is MISSING:
            return None
        return cls.for_type(type(obj), indent=indent, separators=separators)  # pyright: ignore[reportUnknownArgumentType]

    @classmethod
    def for_type(
        cls, typ: type, indent: int | None, separators: tuple[str, str] | None
    ) -> Delimiters | None:
        """
        Return Delimiters for a container type, mirroring Python's json encoding defaults.

        This method implements the separator logic described in the standard library's
        `json` package (`json.encoder.JSONEncoder.__init__` and `json.dumps`):
        - The `separators` tuple defines the exact literal strings inserted between items (item_separator)
        and between keys and values (key_separator).
        - If `separators` is explicitly provided, it is always used as-is.
        - If `separators` is not provided:
            * If `indent` is None (compact mode), the defaults are (', ', ': ').
            * If `indent` is not None (pretty-print mode, including 0), the defaults are (',', ': ').
        - All whitespace after commas and colons in the output is determined solely by the chosen
        separator tuple. No additional spaces are inserted elsewhere.
        - Newlines and indentation for pretty-printed output are inserted by the pretty-printer logic
        in the encoder (see `json.encoder._make_iterencode`), not as part of the separator.

        References:
            - https://github.com/python/cpython/blob/main/Lib/json/encoder.py (JSONEncoder.__init__, _make_iterencode)
            - https://github.com/python/cpython/blob/main/Lib/json/__init__.py (json.dumps)

        :param typ: The type for which delimiters are being selected.
        :param indent: Indentation level, or None for compact output.
        :param separators: Separators to use, or None for defaults.
        :return Delimiters | None: The delimiters instance, or None for atomic types.
        """
        if typ in (str, bytes, int, float, bool, NoneType):
            return None

        if separators is not None:
            _separators = separators
        elif indent is None:
            _separators = (", ", ": ")
        else:
            _separators = (",", ": ")

        if issubclass(typ, Mapping):
            return cls("{", "}", *_separators)
        if issubclass(typ, tuple):
            return cls("(", ")", *_separators)
        if issubclass(typ, Sequence):
            return cls("[", "]", *_separators)
        if issubclass(typ, set):
            return cls("{", "}", *_separators)
        return None

    def __or__(self, other: Self | str | dict | tuple | list) -> Delimiters:  # type: ignore
        """
        Merge this Delimiters with another, giving precedence to the other's fields.

        Allows merging with another Delimiters or a compatible input form.
        """
        if self is other:
            return self
        if not isinstance(other, Delimiters):
            _other = Delimiters(**Delimiters.normalized_args(other))
        else:
            _other = other

        return Delimiters(
            open=_other.open or self.open,
            close=_other.close or self.close,
            itemsep=_other.itemsep or self.itemsep,
            kvsep=_other.kvsep or self.kvsep,
        )

    @staticmethod
    def normalized_args(input: Any) -> dict[str, str]:
        def _from_type(typ: type) -> tuple[str, str, str, str]:
            delimiters_by_type: Final[dict[type, Delimiters]] = {
                list: Delimiters("[", "]"),
                tuple: Delimiters("(", ")"),
                set: Delimiters("{", "}"),
                frozenset: Delimiters("{", "}"),
                dict: Delimiters("{", "}"),
            }
            p = delimiters_by_type.get(typ)
            if not p:
                raise TypeError(f"Unsupported container type: {typ}")
            return (p.open, p.close, p.itemsep, p.kvsep)

        def _from_str(s: str) -> tuple[str, str, str, str]:
            if len(s) == 2:
                return s[0], s[1], ",", ":"
            if len(s) == 4:
                return s[0], s[1], s[2], s[3]
            raise TypeError("Delimiters string input must be 2 or 4 characters")

        def _from_seq(seq) -> tuple[str, str, str, str]:  # type: ignore
            if len(seq) == 2:  # type: ignore
                return seq[0], seq[1], ",", ":"
            if len(seq) == 4:  # type: ignore
                return seq[0], seq[1], seq[2], seq[3]
            raise TypeError("Delimiters tuple/list must have 2 or 4 elements")

        def _from_dict(d: dict[str, str]) -> tuple[str, str, str, str]:  # type: ignore
            allowed = {"open", "close", "itemsep", "kvsep"}
            extra = set(d) - allowed  # type: ignore
            if extra:
                raise ValueError(f"Invalid keys in Delimiters input: {extra}")
            if "open" not in d or "close" not in d:
                raise TypeError("Delimiters dict input must include 'open' and 'close' keys")
            return d["open"], d["close"], d.get("itemsep", ","), d.get("kvsep", ":")

        if isinstance(input, type):
            return dict(zip(["open", "close", "itemsep", "kvsep"], _from_type(input), strict=False))
        if isinstance(input, str):
            return dict(zip(["open", "close", "itemsep", "kvsep"], _from_str(input), strict=False))
        if isinstance(input, (list, tuple)):
            return dict(zip(["open", "close", "itemsep", "kvsep"], _from_seq(input), strict=False))
        if isinstance(input, dict):
            return dict(zip(["open", "close", "itemsep", "kvsep"], _from_dict(input), strict=False))

        raise TypeError(f"Unsupported input type for Delimiters: {type(input).__name__}")


@total_ordering
class KindT:
    """Determines the contract for structural constraints, enforced by Token during initialization."""

    _order: int
    """Unique identifier used for sorting and comparison."""

    name: str
    """Name of the kind, used for debugging and display."""

    def __init__(self, name: str, order: int) -> None:
        """
        Initialize an instance with a given name.

        :param name: Name of the kind, must be one of the predefined names.
        :param order: Unique order number for sorting kinds.
        :raises ValueError: If the name is not recognized.
        """
        self.name = name
        self._order = order

    NUM_INSTANCES: ClassVar[int] = 0
    """Class variable used to assign a unique order numbers to each instance."""

    def __lt__(self, other: Self) -> bool:
        return self._order < other._order

    def __eq__(self, other: object) -> bool:
        return isinstance(other, KindT) and self._order == other._order

    def __hash__(self) -> int:
        return hash(self._order)

    def __format__(self, format_spec: str) -> str:
        return format(self.name, format_spec)

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class Kind:
    """Static namespace for all defined KindT token categories."""

    OPEN = KindT("OPEN", 1)
    VALUE = KindT("VALUE", 3)
    KV_SEP = KindT("KV_SEP", 4)
    ITEM_SEP = KindT("ITEM_SEP", 5)
    CLOSE = KindT("CLOSE", 6)

    @classmethod
    def all(cls) -> list[KindT]:
        """
        Return all KindT constants defined on the class, in declaration order.
        """
        return [
            v
            for k, v in vars(cls).items()
            if isinstance(v, KindT) and not k.startswith("_") and k.isupper()
        ]


class Token:
    """A contextualized token for structural emission."""

    kind: KindT
    """The kind of token, defining its role in the structure."""

    value_: Any
    """The value of this token, if applicable. Defaults to MISSING if not set."""

    is_kvv: bool
    """Flag indicating if this token is a value in a mapping (dict) context."""

    customization: XTokenCustomization | None
    """Optional customization for this token, affecting how it is tokenized and rendered."""

    parent: Token | None
    """The parent token in the structure, or None if this is a root token."""

    def __init__(
        self,
        *,
        kind: KindT,
        value_: Any = MISSING,
        is_kvv: bool = False,
        parent: Token | None = None,
        customization: XTokenCustomization | None = None,
    ) -> None:
        self.kind = kind
        self.value_ = value_
        self.is_kvv = is_kvv
        self.parent = parent
        self.customization = customization
        if self.kind not in Kind.all():
            raise ValueError(f"Invalid token kind: {self.kind.name}")
        if self.kind is not Kind.VALUE and self.value_ is not MISSING:
            raise ValueError(
                f"Token of kind {self.kind.name} cannot have a value set: {self.value_!r}"
            )
        if self.kind is not Kind.VALUE and not self.parent:
            raise ValueError(f"Token of kind {self.kind.name} must have a parent token set.")

    @classmethod
    def OPEN(cls, parent: Token | None = None, is_kvv: bool = False) -> Token:
        """Create an OPEN token."""
        return Token(kind=Kind.OPEN, parent=parent, is_kvv=is_kvv)

    @classmethod
    def CLOSE(cls, parent: Token | None = None, is_kvv: bool = False) -> Token:
        """Create a CLOSE token."""
        return Token(kind=Kind.CLOSE, parent=parent, is_kvv=is_kvv)

    @classmethod
    def ITEM_SEP(cls, parent: Token | None = None, is_kvv: bool = False) -> Token:
        """Create an ITEM_SEP token."""
        return Token(kind=Kind.ITEM_SEP, parent=parent, is_kvv=is_kvv)

    @classmethod
    def KV_SEP(cls, parent: Token | None = None, is_kvv: bool = False) -> Token:
        """Create a KV_SEP token."""
        return Token(kind=Kind.KV_SEP, parent=parent, is_kvv=is_kvv)

    @classmethod
    def VALUE(
        cls,
        value: Any,
        parent: Token | None,
        customization: XTokenCustomization | None = None,
        is_kvv: bool = False,
    ) -> Token:
        """Create a Token from a structured value."""
        assert not isinstance(value, Token), "Cannot create a Token from another Token"
        token = Token(
            kind=Kind.VALUE, value_=value, is_kvv=is_kvv, parent=parent, customization=customization
        )
        return token

    @property
    def depth(self) -> int:
        """Calculate the depth of this token in the structure."""
        if self.parent:
            return self.parent.depth + 1
        return 0

    def delimiters(self, indent: int | None, separators: tuple[str, str] | None) -> Delimiters:
        """
        Return the applicable Delimiters for this token.

        - For VALUE tokens:
            * Use custom delimiters from customization if present.
            * Otherwise, use Delimiters.for_object(self.value).
        - For all other token kinds:
            * Inherit delimiters from the parent token.

        This property is always resolved, climbing up the parent chain as needed.
        Raises:
            AssertionError: If no delimiters can be found.
        """
        token = self
        while True:
            if token.kind is Kind.VALUE:
                if token.customization and token.customization.delimiters:
                    delimiters = token.customization.delimiters
                else:
                    delimiters = Delimiters.for_object(
                        token.value, indent=indent, separators=separators
                    )
            else:
                assert token.parent is not None, "Non-value tokens must have a parent"
                delimiters = token.parent.delimiters(indent=indent, separators=separators)
            if delimiters is not None:
                return delimiters
            if token.parent is None:
                break
            token = token.parent
        raise AssertionError(f"Missing delimiters for token: {self!r}")

    @property
    def value(self) -> Any:
        value: Any
        if self.customization and self.customization.override:
            value = self.customization.value
        else:
            value = self.value_
        return value

    @property
    def is_container(self) -> bool:
        """Check if this token represents a container type (mapping, sequence, or set)."""
        return self.is_mapping or self.is_sequence or self.is_set

    @property
    def is_mapping(self) -> bool:
        """Check if this token represents a mapping (dict)."""
        return isinstance(self.value, Mapping)

    @property
    def is_sequence(self) -> bool:
        """Check if this token represents a sequence (list, tuple)."""
        value: Any = self.value
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes))

    @property
    def is_set(self) -> bool:
        """Check if this token represents a set."""
        return isinstance(self.value, Set)


class XTokenCustomization:
    """
    Returned by a customizer function to change how a value is tokenized and rendered.

    :param delimiters: Customize the delimiters for this value (only relevant for containers).
    :param suppress: If True, the value is omitted from the output entirely.
    :param value: Custom value to use instead of the original value.
    :param raw_string: If True, the string value is emitted as-is without quoting or escaping.
    """

    delimiters: Delimiters | None = None
    """Customize the delimiters for this value (only relevant for containers)."""

    suppress: bool
    """If True, the value is omitted from the output entirely."""

    value: Any = MISSING
    """Custom value to use instead of the original value."""

    raw_string: bool
    """If True, the string value is emitted as-is without quoting or escaping."""

    raw_key_strings: bool
    """If True, key strings are emitted as-is without quoting or escaping."""

    source_type: type | None
    """Record provenance. This customization was applied to a value of this type."""

    continue_chain: bool
    """If True, continue applying further customizers to the (possibly modified) value."""

    @property
    def override(self) -> bool:
        """Check if this customization overrides the original value."""
        return self.value is not MISSING

    def __init__(
        self,
        *,
        delimiters: Delimiters | None = None,
        suppress: bool = False,
        value: Any = MISSING,
        raw_string: bool = False,
        raw_key_strings: bool = False,
        source_type: type | None = None,
        continue_chain: bool = True,
    ) -> None:
        self.delimiters = delimiters
        self.suppress = suppress
        self.value = value
        self.raw_string = raw_string
        self.raw_key_strings = raw_key_strings
        self.source_type = source_type
        self.continue_chain = continue_chain

    def __repr__(self) -> str:
        return (
            f"XTokenCustomization("
            f"delimiters={self.delimiters!r}, "
            f"suppress={self.suppress}, "
            f"value={'MISSING' if self.value is MISSING else type(self.value).__name__}, "
            f"raw_string={self.raw_string}, "
            f"raw_key_strings={self.raw_key_strings}, "
            f"source_type={self.source_type.__name__ if self.source_type else None}, "
            f"continue_chain={self.continue_chain})"
        )


# End of file: python/plib_/xdumps/model.py
