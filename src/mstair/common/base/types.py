# File: python/plib_/base/types.py

import contextlib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, is_dataclass
from decimal import Decimal
from fractions import Fraction
from os import PathLike
from typing import (
    Any,
    Final,
    Self,
    TypeAlias,
    TypeVar,
    Union,  # pyright: ignore[reportDeprecated]
    cast,
    get_args,
    get_origin,
    overload,
)


# ---------- Static typing aliases (for annotations) ----------

BufferLikeTypes: TypeAlias = range | bytes | bytearray | memoryview
MappingTypes: TypeAlias = dict[Any, Any]
SequenceTypes: TypeAlias = list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any]
PrimitiveNonStringTypes: TypeAlias = int | float | complex | bool | Decimal | Fraction | None
PrimitiveTypes: TypeAlias = PrimitiveNonStringTypes | str
ContainerTypes: TypeAlias = SequenceTypes | MappingTypes
BuiltinTypes: TypeAlias = ContainerTypes | PrimitiveTypes | BufferLikeTypes
JSONSerializableTypes: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None
StrPath: TypeAlias = str | PathLike[str]

# ---------- Runtime tuples (for isinstance/issubclass) ----------

BUFFER_LIKE_TYPES: Final[tuple[type, ...]] = (range, bytes, bytearray, memoryview)
MAPPING_TYPES: Final[tuple[type, ...]] = (dict,)
SEQUENCE_TYPES: Final[tuple[type, ...]] = (list, tuple, set, frozenset)
PRIMITIVE_NON_STRING_TYPES: Final[tuple[type, ...]] = (
    int,
    float,
    complex,
    bool,
    Decimal,
    Fraction,
    type(None),
)
PRIMITIVE_TYPES: Final[tuple[type, ...]] = (*PRIMITIVE_NON_STRING_TYPES, str)
CONTAINER_TYPES: Final[tuple[type, ...]] = SEQUENCE_TYPES + MAPPING_TYPES
BUILTIN_TYPES: Final[tuple[type, ...]] = CONTAINER_TYPES + PRIMITIVE_TYPES + BUFFER_LIKE_TYPES
JSON_SERIALIZABLE_TYPES: Final[tuple[type, ...]] = (dict, list, str, int, float, bool, type(None))
STR_PATH_TYPES: Final[tuple[type, ...]] = (str, PathLike)

C = TypeVar("C", bound=object)
T = TypeVar("T")


@dataclass(slots=True)
class classproperty_cm[C: object, T]:
    """Descriptor that turns a @classmethod into a class-level property."""

    _cm: Callable[[type[C]], T]

    @overload
    def __get__(self, instance: None, owner: type[C]) -> T: ...
    @overload
    def __get__(self, instance: object, owner: type[C]) -> T: ...
    def __get__(self, instance: object, owner: type[C]) -> T:
        del instance
        bound: Callable[[], T] = self._cm.__get__(owner, owner)
        return bound()


def is_hashable(value: Any) -> bool:
    """Check if a value is hashable."""
    try:
        hash(value)
    except TypeError:
        return False
    return True


def istype(obj: object, *types: object) -> bool:
    """
    Enhanced isinstance() supporting PEP 604 (X | Y), Unions, and single types.

    Accepts a list of types and/or typing.Union expressions and evaluates whether
    the object matches any included type.

    :param obj: Object to check
    :param types: One or more types or Union expressions
    :return: True if obj matches any of the resolved types
    """
    if not types:
        raise ValueError("At least one type must be provided")

    for t in types:
        origin = get_origin(t)
        args = get_args(t)

        # Union[X, Y] or X | Y
        if origin is Union and args:  # pyright: ignore[reportDeprecated]
            if isinstance(obj, args):
                return True
        # Fallback for raw types or generics like list[int]
        elif isinstance(t, type):
            if isinstance(obj, t):
                return True
        # Graceful fallback for unsupported things (e.g., Callable[[int], str])
        elif origin is not None and isinstance(origin, type) and isinstance(obj, origin):
            return True

    return False


def dict_intersection(d: dict[Any, Any], *keys: str) -> dict[Any, Any]:
    """
    Return a new dictionary including only the given keys.

    :param d: The input dictionary.
    :param *keys: Keys to include from `d`.
    :return dict: A shallow copy of `d` with specified keys.
    """
    return {k: v for k, v in d.items() if k in keys}


def dict_difference(d: dict[Any, Any], *keys: str) -> dict[Any, Any]:
    """
    Return a new dictionary excluding the given keys.

    :param d: The input dictionary.
    :param *keys: Keys to exclude from `d`.
    :return dict: A shallow copy of `d` with specified keys removed.
    """
    return {k: v for k, v in d.items() if k not in keys}


def object_as_dict(o: Any) -> dict[str, Any] | None:
    """Attempt to convert the object to a dictionary representation."""
    # Try dataclasses.asdict(o)
    o_dict: dict[str, Any] | None = None
    if o_dict is None and is_dataclass(o):
        with contextlib.suppress(Exception):
            o_dict = asdict(cast(Any, o))

    # Try o.to_dict() and o.as_dict()
    if o_dict is None:
        for fn in ("to_dict", "as_dict"):
            o_bound_method = getattr(o, fn, None)
            if callable(o_bound_method):
                with contextlib.suppress(Exception):
                    result = o_bound_method()
                    if isinstance(result, dict) and all(istype(k, str) for k in result):
                        o_dict = result
                        break

    # Try o.__dict__
    if o_dict is None and isinstance(getattr(o, "__dict__", None), dict):
        o_dict = cast(dict[str, Any], o.__dict__)
    return o_dict


class Sentinel:
    """
    Robust singleton base class for sentinel objects such as MISSING and CALCULATE.

    Behaves as a falsy, unique, singleton marker, distinct from None.
    Subclass and override _repr_name and relevant property methods for specialized sentinels.
    """

    __slots__ = ()

    _repr_name: str = "SENTINEL"

    def __repr__(self) -> str:
        return self._repr_name

    def __str__(self) -> str:
        return self._repr_name

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)

    def __reduce__(self) -> tuple[type, tuple[()]]:
        return (type(self), ())

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(
        self,
        _memo: dict[int, object],
    ) -> Self:
        return self

    def __new__(cls) -> Self:
        if hasattr(cls, "_instance"):
            return cls._instance
        cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_missing(self) -> bool:
        """True if this sentinel represents a missing value."""
        return False

    @property
    def is_calculate(self) -> bool:
        """True if this sentinel represents a calculated/dynamic value."""
        return False


class Missing(Sentinel):
    """Singleton indicating a missing or unset value."""

    _repr_name = "MISSING"

    @property
    def is_missing(self) -> bool:
        return True


MISSING: Final[Missing] = Missing()


class Calculate(Sentinel):
    """Singleton indicating a value should be dynamically calculated."""

    _repr_name = "CALCULATE"

    @property
    def is_calculate(self) -> bool:
        return True


CALCULATE: Final[Calculate] = Calculate()


class PeekableIterator[T](Iterator[T]):
    """
    Peekable, bool-able iterator over any iterable (except str/bytes).
    """

    __slots__ = ("_it", "_has_cache", "_cache")

    def __init__(self, iterable: Iterable[T]) -> None:
        """
        Initialize with an iterable. Reject str/bytes.

        :param iterable: Source iterable.
        :raises TypeError: If iterable is str or bytes.
        """

        if isinstance(iterable, (str, bytes)):
            raise TypeError(f"PeekableIterator does not support str or bytes (got {type(iterable)})")
        self._it: Iterator[T] = iter(iterable)
        self._has_cache: bool = False
        self._cache: T | None = None

    def __next__(self) -> T:
        """
        Return next item. Uses cache if peeked.

        :return T: The next item.
        :raises StopIteration: If exhausted.
        """
        if self._has_cache:
            self._has_cache = False
            assert self._cache is not None
            return self._cache
        return next(self._it)

    def is_empty(self) -> bool:
        """
        Return True if another item is available.

        :return bool: True if not exhausted.
        """
        try:
            self.peek()
            return False
        except StopIteration:
            return True

    def peek(self) -> T:
        """
        Return next item without advancing iterator.

        :return T: Next item.
        :raises StopIteration: If exhausted.
        """
        if not self._has_cache:
            self._cache = next(self._it)
            self._has_cache = True
        assert self._cache is not None
        return self._cache


def int_from_string(value: str | None, default: int = 0) -> int:
    """
    Convert a string to an integer, returning a default value if the string is None or empty.

    :param value: The string to convert.
    :param default: The default integer to return if the string is None or empty.
    :return: An integer.
    """
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


# End of file: src/mstair/common/base/types.py
