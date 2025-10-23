from typing import Any


class AccessorMixin:
    """Redirects attribute access through optional `_get_{name}` and `_set_{name}` hooks.

    Features
    --------
    - Reading `obj.{name}` calls `obj._get_{name}()` if defined.
    - Writing `obj.{name} = value` calls `obj._set_{name}(value)` if defined.
    - Attributes without hooks fall back to normal `object.__getattribute__` /
      `object.__setattr__`.
    - Special attributes and dunders (e.g. `__len__`, `__deepcopy__`) are never
      intercepted. For optional protocol dunders like `__deepcopy__` or
      `__reduce_ex__`, if no implementation exists this mixin returns `None`
      instead of raising `AttributeError`, matching the semantics of
      `getattr(obj, "__deepcopy__", None)`.

    Why
    ---
    This mixin allows developers to customize, log, or debug access to specific attributes
    without reimplementing `__getattribute__` and `__setattr__` themselves. It preserves
    Python's data model semantics for special methods while giving fine-grained control.

    Examples
    --------
    Basic usage with hooks:

    >>> class MyClass(AccessorMixin):
    ...     NAME: int = 0
    ...     def _get_NAME(self):
    ...         return f"Value is {object.__getattribute__(self, 'NAME')}"
    ...     def _set_NAME(self, val):
    ...         object.__setattr__(self, 'NAME', val * 2)
    ...
    >>> obj = MyClass()
    >>> obj.NAME = 10        # calls _set_NAME
    >>> obj.NAME             # calls _get_NAME
    'Value is 20'

    Dunders are not intercepted:

    >>> hasattr(obj, "__deepcopy__")  # behaves like getattr(..., None)
    False
    >>> import copy; isinstance(copy.deepcopy(obj), MyClass)
    True

    Notes
    -----
    - Core dunders like `__class__` and `__dict__` always raise if missing;
      they are never replaced with `None`.
    - Hook methods must be callable; if not, normal attribute access is used.
    """

    def __getattribute__(self, name: str) -> Any:
        """Look up an attribute, using a `_get_{name}` hook if available.

        - For dunders:
            - Always defer to `object.__getattribute__`.
            - If missing and known to be optional (e.g. `__deepcopy__`),
              return `None` instead of raising `AttributeError`.
        - For normal attributes:
            - If `_get_{name}` exists and is callable, call it.
            - Otherwise, return the attribute normally.
        """
        if name.startswith("__") and name.endswith("__"):
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                if name in {"__deepcopy__", "__reduce_ex__", "__reduce__"}:
                    return None
                raise

        try:
            getter = object.__getattribute__(self, f"_get_{name}")
        except AttributeError:
            return object.__getattribute__(self, name)
        else:
            if callable(getter):
                return getter()
            return getter

    def __setattr__(self, name: str, value: Any) -> None:
        """Assign to an attribute, using a `_set_{name}` hook if available.

        - For dunders:
            - Always defer directly to `object.__setattr__`.
        - For normal attributes:
            - If `_set_{name}` exists and is callable, call it.
            - Otherwise, assign the attribute normally.
        """
        if name.startswith("__") and name.endswith("__"):
            object.__setattr__(self, name, value)
            return

        try:
            setter = object.__getattribute__(self, f"_set_{name}")
        except AttributeError:
            object.__setattr__(self, name, value)
            return
        else:
            if callable(setter):
                setter(value)
                return
            else:
                object.__setattr__(self, name, value)
                return
