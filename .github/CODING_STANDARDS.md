# CODING_STANDARDS.md — mstair projects

## File layout

Every Python file must follow this structurem, including blank lines:

```python
<placeholder: shebang line for executable scripts only>
"""
<placeholder: module summary on its own line>

<placeholder: brief description with purpose and example>
"""

from __future__ import annotations

<placeholder: stdlib imports>
<placeholder: third-party imports>
<placeholder: local imports (absolute only)>
<placeholder: __all__ definition>

<placeholder: heading for the section below>
<placeholder: module constants and configuration>

<placeholder: heading for the section below>
<placeholder: type definitions and dataclasses>

<placeholder: heading for the section below>
<placeholder: public functions and classes>

<placeholder: heading for the section below>
<placeholder: private helpers with docstrings>

# End of file: <path relative to project root>
```

---

## Typing and signatures

* Full **PEP 484** type annotations everywhere, including private helpers.
* Always include explicit return types.
* Follow Python 3.13 conventions.
* Use `X | None` and `from collections.abc import Iterable, Mapping` over `typing.*` forms.
* Use native `list[str]`, `dict[str, int]`, etc. over `typing.List`, `typing.Dict`.
* Use `Final`, `Literal`, `TypedDict`, or `Protocol` where clearer.
* Declare all class field types explicitly.
* Follow strict mypy rules, like using `object` and protocols instead of bare `Any`.

---

## Documentation and comments

* Names must be phrase-like, **self-documenting**, and descriptive, not abbreviated.
* Use keyword arguments when there are multiple parameters.
* Every public function, class, and module must have a **PEP 257** docstring.
* Use clear, concise **Google-style** or short-section docstrings.
* Comment non-obvious logic only; do not restate what the code already says.
* Use ASCII-only text in all comments and strings.
* Each module docstring should include at least one short usage example.

Example:

```python
def fields_and_values_from_email_header(*, text: str, default: dict[str, str] | None = None) -> dict[str, str]:
    """
    Extract key:value pairs from a raw email header string.

    Example:
        >>> fields_and_values_from_email_header(text="From: Alice <alice@example.com>\nTo: Bob <bob@example.com>")
        {'From': 'Alice <alice@example.com>', 'To': 'Bob <bob@example.com>'}

    Args:
        text: The raw email header text.
        default: Default values for missing keys.

    Returns:
        A dictionary of header fields and their values.
    """
```
## Formatting and layout

* Keep trailing newline, `# File: <path>\n#\n` header, and `# End of file:` footer.
* Order functions by visibility: public before private, and callers before callees.
* Order class members: constants → `__init__` → public → private.

---

## Structural and style constraints

* One clear purpose per module; no mixed responsibilities.
* Avoid circular imports by factoring shared logic into `base/`.
* Use modern constructs: `match`, `Path`, f-strings, `dataclass`.
* Explicit is better than implicit — no magic globals or dynamic imports.
* Never use `try/except ImportError` for optional modules.
* All files, docstrings, and outputs must be **ASCII-only**.
* Prefer `with` statements for resource handling.
* Catch specific exceptions only; never `except Exception:` bare.
* Always specify `encoding="utf-8"` in file I/O.

---

## Class and function design

* Every function or method must start with a one-line docstring summary sentence, even private helpers.
* Keep functions short and single-purpose.
* Use `@staticmethod` when `self` is unused.
* Use clear parameter names; prefer keyword arguments for clarity.
* Minimize side effects; functions should be deterministic.
* Classes should encapsulate one concept only; avoid “utility blobs.”

---

## Example module skeleton

```python
# File: src/mstair/common/example_helpers.py
"""
<placeholder: brief summary of what this module does>

Example:
    >>> result = normalize_path("C:\\Temp")
    >>> print(result)
    'C:/Temp'
"""

from __future__ import annotations
from pathlib import Path

def normalize_path(value: str) -> str:
    """Return a forward-slash normalized path string."""
    return Path(value).as_posix()

# End of file: src/mstair/common/example_helpers.py
```

---

## Minimal aesthetic and safety rules

### Positives:
* Readable plain ASCII everywhere.
* Modern Python 3.13 idioms and well-maintained PyPI packages.
* Restful, deterministic, testable, import-safe design.
* Predictable, explicit structure that is AI and static analyzer friendly.

### Negatives:
* Unicode characters outside ASCII range.
* Obscure, clever, or “magic” code.
* Deeply nested code or excessive indentation.
* Overly long functions or classes.
* Excessive comments or redundant docstrings.
* Unnecessary abstraction layers or cleverness.
