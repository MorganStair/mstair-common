# File: python/plib_/base/interpolate.py
# Regular expression that matches a placeholder like "{identifier}".

import re
from collections import deque
from collections.abc import Iterable, Mapping


_INTERPOLATE_PLACEHOLDER_RE: re.Pattern[str] = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Candidate sentinel pairs that are unlikely to appear in normal text.
# We'll pick the first pair not present in any input value.
_INTERPOLATE_SENTINELS: list[tuple[str, str]] = [
    ("\ufff0", "\ufff1"),
    ("\ufdd0", "\ufdd1"),
    ("<<LBRACE>>", "<<RBRACE>>"),
    ("__LBRACE__", "__RBRACE__"),
]


def interpolate_all(values_by_key: Mapping[str, object]) -> dict[str, str]:
    """
    Interpolate all `{name}` placeholders using names from the same mapping.

    Each value may reference other keys using `{key}`.
    All values are coerced to strings for interpolation.
    Literal braces are written as `{{` and `}}`.

    :param values_by_key: Mapping of names to values; each value must be stringable.
    :returns: New dict with all values fully interpolated.
    :raises KeyError: If a placeholder refers to a missing key.
    :raises ValueError: If braces are malformed or there is a cyclic dependency.
    """
    # Step 1 - normalize inputs to strings.
    string_values_by_key: dict[str, str] = {k: str(v) for k, v in values_by_key.items()}

    # Step 2 - choose sentinels that do not collide with the data.
    all_texts: list[str] = list(string_values_by_key.values())
    left_sentinel, right_sentinel = _choose_sentinels(all_texts)

    # Step 3 - protect literal braces and validate brace syntax up front.
    protected_values_by_key: dict[str, str] = {}
    for name, text in string_values_by_key.items():
        protected_text: str = _protect_braces(text, left_sentinel, right_sentinel)
        _validate_braces_are_well_formed(protected_text)
        protected_values_by_key[name] = protected_text

    # Step 4 - build dependency sets: key -> set of referenced keys.
    reference_names_by_key: dict[str, set[str]] = {
        name: {m.group(1) for m in _INTERPOLATE_PLACEHOLDER_RE.finditer(text)}
        for name, text in protected_values_by_key.items()
    }

    # Step 5 - fail fast on missing references.
    missing_names: set[str] = {
        ref
        for refs in reference_names_by_key.values()
        for ref in refs
        if ref not in string_values_by_key
    }
    if missing_names:
        missing_list: str = ", ".join(sorted(missing_names))
        raise KeyError(f"Unknown placeholder name(s): {missing_list}")

    # Step 6 - Kahn's algorithm setup (non-recursive evaluation).
    in_degree_by_key: dict[str, int] = {
        name: len(refs) for name, refs in reference_names_by_key.items()
    }
    dependents_by_key: dict[str, set[str]] = {name: set() for name in string_values_by_key}
    for name, refs in reference_names_by_key.items():
        for ref in refs:
            dependents_by_key[ref].add(name)

    # Optional determinism: process ready nodes in sorted name order.
    ready_keys: deque[str] = deque(sorted(name for name, d in in_degree_by_key.items() if d == 0))
    eval_order: list[str] = []
    while ready_keys:
        current_key: str = ready_keys.popleft()
        eval_order.append(current_key)
        for dependent_key in sorted(dependents_by_key[current_key]):
            in_degree_by_key[dependent_key] -= 1
            if in_degree_by_key[dependent_key] == 0:
                ready_keys.append(dependent_key)

    if len(eval_order) != len(string_values_by_key):
        cyclic_keys: list[str] = sorted(k for k, d in in_degree_by_key.items() if d > 0)
        raise ValueError(f"Cyclic interpolation among keys: {', '.join(cyclic_keys)}")

    # Step 7 - expand in topological order.
    resolved_values_by_key: dict[str, str] = {}
    for current_key in eval_order:
        _text: str = protected_values_by_key[current_key]

        def replace_match(match: re.Match[str]) -> str:
            ref_name: str = match.group(1)
            return resolved_values_by_key[ref_name]

        expanded_text: str = _INTERPOLATE_PLACEHOLDER_RE.sub(replace_match, _text)
        resolved_values_by_key[current_key] = expanded_text

    # Step 8 - unprotect literal braces and return a fresh dict.
    final_values_by_key: dict[str, str] = {
        name: _unprotect_braces(text, left_sentinel, right_sentinel)
        for name, text in resolved_values_by_key.items()
    }
    return final_values_by_key


def _choose_sentinels(texts: Iterable[str]) -> tuple[str, str]:
    """Return a pair of sentinel strings not present in any of the texts."""
    joined: str = "||".join(texts)
    for left, right in _INTERPOLATE_SENTINELS:
        if left not in joined and right not in joined:
            return left, right
    # As a last resort, synthesize unique sentinels that cannot collide.
    # We include the length of the corpus to make accidental collisions even less likely.
    return (f"<<L{len(joined)}>>", f"<<R{len(joined)}>>")


def _protect_braces(text: str, left: str, right: str) -> str:
    """Return text with '{{' and '}}' replaced by sentinels to protect literal braces."""
    return text.replace("{{", left).replace("}}", right)


def _unprotect_braces(text: str, left: str, right: str) -> str:
    """Return text with sentinel markers restored to literal '{' and '}' characters."""
    return text.replace(left, "{").replace(right, "}")


def _validate_braces_are_well_formed(text: str) -> None:
    """
    Ensure that, after protecting '{{' and '}}', any '{' starts a valid {name} token
    and that no stray '}' remains, mirroring str.format's strictness.
    """
    i: int = 0
    n: int = len(text)
    while i < n:
        ch: str = text[i]
        if ch == "{":
            m = _INTERPOLATE_PLACEHOLDER_RE.search(text, i)
            if not m:
                # The brace is not starting a valid {name} token.
                raise ValueError(f"Invalid placeholder syntax near index {i}: {text!r}")
            i = m.end()
            continue
        if ch == "}":
            # A solitary '}' is never valid after protection.
            raise ValueError(f"Single '}}' brace not allowed near index {i}: {text!r}")
        i += 1


# End of file: python/plib_/base/interpolate.py
