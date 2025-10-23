"""
TokenStream: Stateful token emitter for structured object traversal.

This class replaces the recursive `tokenize()` logic with a generator-based
state machine that flattens structured containers (mappings, sequences)
into a stream of layout-aware model.Token objects.
"""

from __future__ import annotations

import contextlib
import logging
import warnings
from collections.abc import Iterator, Mapping, Sequence, Set
from typing import Any, cast

from mstair.common.base.types import PeekableIterator
from mstair.common.xdumps import model
from mstair.common.xdumps.customizer_registry import CustomizerRegistry, XCustomizerFunction


__all__ = [
    "TokenStream",
]


class TokenStream:
    """
    Stateful token emitter for structured object traversal.

    TokenStream generates a stream of Token objects representing the structure of any Python value,
    applying one or more customizers to flatten or specialize emission for complex types.
    """

    value: Any
    """The value being tokenized."""

    customizers: list[XCustomizerFunction]
    """Extra (ordered) customizer functions to apply before the default ones."""

    _private_customizers: CustomizerRegistry
    """Private registry of customizers built from the provided extra_customizers."""

    def __init__(
        self,
        value: Any,
        *,
        customizers: list[XCustomizerFunction] | None = None,
    ) -> None:
        """
        Initialize the TokenStream with a value and optional customizers.

        :param value: The root value to tokenize.
        :param customizers: An optional sequence of customizer functions to register first.
        """
        self.value = value
        self.customizers = customizers or []
        self._private_customizers = CustomizerRegistry()
        for func in self.customizers:
            self._private_customizers.register(func)

    def __iter__(self) -> Iterator[model.Token]:
        """Yields a stream of model.Token objects representing the structure."""

        # Start with the root value
        customization = self._private_customizers.customize(self.value, depth=0)
        root_token = model.Token.VALUE(self.value, None, customization)
        LOG = logging.getLogger(__name__)
        customization_repr: str = "<error>"
        with contextlib.suppress(Exception):
            customization_repr = repr(customization)
        root_token_repr: str = "<error>"
        with contextlib.suppress(Exception):
            root_token_repr = repr(root_token)
        LOG.debug(f"\n  assign: {customization_repr=}\n      to: {root_token_repr=}")

        # If customization suppresses the root token, emit nothing
        if customization and customization.suppress:
            return

        # If customization provides a raw string, emit only that token and stop
        if customization and customization.raw_string:
            yield root_token
            return

        # If customization overrides the value, treat it as the new value for container checks
        effective_value = root_token.value
        if isinstance(effective_value, (Mapping, Sequence, Set)):
            yield model.Token.OPEN(root_token)
            yield from self.emit_container_items(root_token)
            yield model.Token.CLOSE(root_token)
        else:
            yield root_token

    def emit_container_items(self, container_token: model.Token) -> Iterator[model.Token]:
        """
        Yield tokens for children of a container (sequence or mapping) token.

        :param container_token: The container token whose items to emit.
        :yields model.Token: Structural and value tokens for each item.
        """
        if container_token.is_mapping:
            items = PeekableIterator(cast(Mapping[Any, Any], container_token.value).items())
            yield from self._emit_mapping_items(container_token, items)
        elif container_token.is_sequence or container_token.is_set:
            items = PeekableIterator(cast(Sequence[Any] | Set[Any], container_token.value))
            yield from self._emit_sequence_items(container_token, items)
        else:
            raise TypeError(f"{type(container_token.value).__name__} is not a valid container type")

    def tokens(self) -> list[model.Token]:
        """
        Collect and return all tokens from this TokenStream as a list.

        This is primarily intended for testing and debugging so that
        tokenization can be inspected independently of formatting.
        """
        return list(self)

    def _emit_mapping_items(
        self,
        container_token: model.Token,
        items: PeekableIterator[tuple[Any, Any]],
    ) -> Iterator[model.Token]:
        """
        Emit mapping pairs that are not suppressed by a customizer.
        """
        emitted_any = False
        try:
            while not items.is_empty():
                pair = items.peek()
                if self._is_pair_suppressed(pair, container_token):
                    next(items)
                    continue
                if emitted_any:
                    yield model.Token.ITEM_SEP(container_token)
                next(items)
                yield from self.emit_tokens_for_mapping_pair(container_token, pair)
                emitted_any = True
        except StopIteration:
            pass

    def _emit_sequence_items(
        self,
        container_token: model.Token,
        items: PeekableIterator[Any],
    ) -> Iterator[model.Token]:
        """
        Emit values (for sequences or sets) that are not suppressed by a customizer.

        Each value is recursively handled as a container or atom using _emit_value_or_container.

        :param container_token: The parent sequence/set token.
        :param items: Items to emit.
        :yields model.Token: Structural and value tokens for each item.
        """
        emitted_any = False
        try:
            while not items.is_empty():
                value = items.peek()
                if self._is_value_suppressed(value, container_token):
                    next(items)
                    continue
                if emitted_any:
                    yield model.Token.ITEM_SEP(container_token)
                next(items)
                yield from self._emit_value_or_container(value, container_token)
                emitted_any = True
        except StopIteration:
            pass

    def _emit_value_or_container(
        self,
        value: Any,
        parent_token: model.Token,
    ) -> Iterator[model.Token]:
        """
        Emit the value as either a full container (OPEN, items, CLOSE) or as a VALUE token.

        :param value: The value to emit.
        :param parent_token: The parent token for context.
        :yields model.Token: The emitted tokens, possibly descending recursively for containers.
        """
        customization = self._private_customizers.customize(value, depth=parent_token.depth + 1)
        token = model.Token.VALUE(value, parent_token, customization)
        if token.is_container:
            yield model.Token.OPEN(token)
            yield from self.emit_container_items(token)
            yield model.Token.CLOSE(token)
        else:
            yield token

    def _is_pair_suppressed(self, pair: tuple[Any, Any], parent_token: model.Token) -> bool:
        """
        Return True if a mapping pair should be suppressed by a customizer.
        """
        customization = self._private_customizers.customize(pair, depth=parent_token.depth + 1)
        return bool(customization and customization.suppress)

    def _is_value_suppressed(self, value: Any, parent_token: model.Token) -> bool:
        """
        Return True if a value should be suppressed by a customizer.
        """
        customization = self._private_customizers.customize(value, depth=parent_token.depth + 1)
        return bool(customization and customization.suppress)

    def emit_tokens_for_mapping_pair(
        self,
        container_token: model.Token,
        item: tuple[Any, Any],
    ) -> Iterator[model.Token]:
        """Yield tokens for a single key-value pair in a mapping."""
        kv_key, kv_value = item

        # Build the KEY token
        key_customization = self._private_customizers.customize(
            kv_key, depth=container_token.depth + 1
        )
        key_token = model.Token.VALUE(kv_key, container_token, key_customization)
        if key_customization and key_customization.suppress:
            warnings.warn(
                f"Mapping key tokens cannot be suppressed: {kv_key!r} ({type(kv_key).__name__})"
            )

        # If key_token is a container, yield its structure and contents, otherwise yield it directly
        if key_token.is_container:
            yield model.Token.OPEN(key_token)
            yield from self.emit_container_items(key_token)
            yield model.Token.CLOSE(key_token)
        else:
            yield key_token

        # Yield the key:value delimiter
        yield model.Token.KV_SEP(container_token)

        # Build the VALUE token
        value_customization = self._private_customizers.customize(
            kv_value, depth=container_token.depth + 1
        )
        if value_customization and value_customization.suppress:
            warnings.warn(
                f"Mapping value tokens cannot be suppressed: {kv_value!r} ({type(kv_value).__name__})"
            )
        value_token = model.Token.VALUE(kv_value, container_token, value_customization, is_kvv=True)

        # If value_token is a container, yield its structure and contents, otherwise yield it directly
        if value_token.is_container:
            yield model.Token.OPEN(value_token, is_kvv=True)
            yield from self.emit_container_items(value_token)
            yield model.Token.CLOSE(value_token)
        else:
            yield value_token
