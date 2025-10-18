#!/usr/bin/env python3
"""
Insert or replace standardized header and footer lines in specified files.

Usage:
    insert_file_headers.py <file1> [<file2> ... | <pattern> ...]

Examples:
    insert_file_headers.py build/*.mk src/**/*.py

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


# --------------------------------------------------------------
# Configuration
# --------------------------------------------------------------
ALLOWED_SUFFIXES = {".mak", ".mk", ".py"}
HEADER_RE = re.compile(r"^#\s*File:\s+.*$")
FOOTER_RE = re.compile(r"^#\s*-{10,}\s*$")
SHEBANG_RE = re.compile(r"^#!")
FOOTER_LINE = "# " + "-" * 62
__all__ = ["process_file", "expand_args", "main"]


# --------------------------------------------------------------
# Core logic
# --------------------------------------------------------------
def process_file(path: Path) -> bool:
    """Insert or replace the header/footer lines in a single file."""
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

    new_lines: list[str] = []
    if shebang_line:
        new_lines.append(shebang_line)
    new_lines.append(f"# File: {path.as_posix()}")
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
    Expand shell-style glob patterns into file paths.
    Supports recursive patterns like **/*.py.
    """
    results: list[Path] = []
    for arg in args:
        p = Path(arg)
        if any(ch in arg for ch in "*?[]"):
            # If pattern includes glob chars, expand relative to current dir
            base = Path.cwd()
            matches = base.glob(arg) if "**" not in arg else base.rglob(arg.replace("**/", ""))
            for m in matches:
                if m.is_file():
                    results.append(m)
        else:
            results.append(p)
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in results:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


# --------------------------------------------------------------
# CLI entry
# --------------------------------------------------------------
def main(argv: Iterable[str] | None = None) -> int:
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
    raise SystemExit(main())

# End of file: insert_file_headers.py
