#!/usr/bin/env python3
"""
Insert or replace standardized header and footer lines in specified files.

Usage:
    insert_file_headers.py <file1> [<file2> ... | <pattern> ...]

Examples:
    insert_file_headers.py make/*.mk src/**/*.py

Each file will be updated *in place* if its extension is allowed (.mak, .mk, .py).

Behavior:
    • The first non-shebang line will become "# File: <path>".
    • Any existing header "# File: ..." or footer line of dashes is replaced.
    • The shebang (#!) line, if present, is preserved at the top.
    • Exactly one blank line will appear before the footer.
    • Globs like "*.py" and "**/*.mk" are expanded recursively.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path


__all__ = ["process_file", "expand_args", "insert_file_headers_main"]

# --------------------------------------------------------------
# Configuration
# --------------------------------------------------------------
ALLOWED_SUFFIXES = {".mak", ".mk", ".py"}
HEADER_RE = re.compile(r"^#\s*File:\s+.*$")
FOOTER_RE = re.compile(r"^#\s*-{10,}\s*$")
SHEBANG_RE = re.compile(r"^#!")
FOOTER_LINE = "# " + "-" * 62


# --------------------------------------------------------------
# Core logic
# --------------------------------------------------------------
def process_file(path: Path) -> bool:
    """Insert or replace the header/footer lines in a single file."""
    path = path.resolve()  # always normalize
    if path.suffix not in ALLOWED_SUFFIXES:
        print(f"[skip] {path} (unsupported extension)", file=sys.stderr)
        return False
    if not path.is_file():
        print(f"[skip] {path} (not found or not a file)", file=sys.stderr)
        return False

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"[error] {path}: {exc}", file=sys.stderr)
        return False

    shebang_line: str | None = None
    if lines and SHEBANG_RE.match(lines[0]):
        shebang_line = lines.pop(0)

    if lines and HEADER_RE.match(lines[0]):
        lines.pop(0)
    if lines and FOOTER_RE.match(lines[-1]):
        lines.pop(-1)
    while lines and not lines[-1].strip():
        lines.pop(-1)

    # Try to compute relative path for header display
    try:
        rel_path = path.relative_to(Path.cwd())
        header_path = rel_path.as_posix()
    except ValueError:
        # Fall back to filename only (still relative-looking)
        header_path = path.name

    new_lines: list[str] = []
    if shebang_line:
        new_lines.append(shebang_line)
    new_lines.append(f"# File: {header_path}")
    new_lines.extend(lines)
    new_lines.append("")  # one blank line before footer
    new_lines.append(FOOTER_LINE)

    try:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"[error] {path}: {exc}", file=sys.stderr)
        return False

    print(f"[update] {path}", file=sys.stderr)
    return True


# --------------------------------------------------------------
# Globbing helper
# --------------------------------------------------------------
def expand_args(args: Iterable[str]) -> list[Path]:
    """
    Expand shell-style glob patterns into absolute file paths.
    Supports recursive patterns like **/*.py.
    Filters results by ALLOWED_SUFFIXES.
    """
    results: list[Path] = []

    cwd = Path.cwd()

    for arg in args:
        has_glob = any(ch in arg for ch in "*?[]")
        matches: Iterable[Path]

        if has_glob:
            # Always expand relative to current directory
            if "**" in arg:
                matches = cwd.rglob(arg)
            else:
                matches = cwd.glob(arg)
        else:
            matches = [cwd / arg]

        for m in matches:
            try:
                if m.is_file() and m.suffix in ALLOWED_SUFFIXES:
                    results.append(m.resolve())
            except OSError:
                # Ignore any inaccessible files
                continue

    # Deduplicate while preserving order
    unique: list[Path] = []
    seen: set[Path] = set()
    for p in results:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


# --------------------------------------------------------------
# CLI entry
# --------------------------------------------------------------
def insert_file_headers_main(argv: Iterable[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: insert_file_headers.py <file1|pattern> ...", file=sys.stderr)
        return 1

    paths = expand_args(args)
    if not paths:
        print("[error] No files matched given arguments.", file=sys.stderr)
        return 1

    success = True
    for path in paths:
        if not process_file(path):
            success = False
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(insert_file_headers_main())

# End of file: insert_file_headers.py
