#!/usr/bin/env python3
"""
Insert or replace standardized header and footer lines in specified files.

Usage:
    insert_file_headers.py <file1> [<file2> ...]

Each file will be updated *in place* if its extension is allowed (.mak, .mk, .py).

Behavior:
    • The first non-shebang line will become "# File: <path>".
    • Any existing header "# File: ..." or footer line of dashes is replaced.
    • The shebang (#!) line, if present, is preserved at the top.
    • Exactly one blank line will appear before the footer.
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
__all__ = ["process_file", "main"]


# --------------------------------------------------------------
# Core logic
# --------------------------------------------------------------
def process_file(path: Path) -> bool:
    """
    Insert or replace the header/footer lines in a single file.

    Args:
        path: Path to the file to modify.

    Returns:
        True if modified successfully, False if skipped or error.
    """
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

    # Remove existing header/footer if present
    if lines and HEADER_RE.match(lines[0]):
        lines.pop(0)
    if lines and FOOTER_RE.match(lines[-1]):
        lines.pop(-1)

    # Remove any trailing blank lines before reappending the footer
    while lines and not lines[-1].strip():
        lines.pop(-1)

    # Reassemble
    new_lines: list[str] = []
    if shebang_line:
        new_lines.append(shebang_line)
    new_lines.append(f"# File: {path.as_posix()}")
    new_lines.extend(lines)
    new_lines.append("")  # ensure exactly one blank line before footer
    new_lines.append(FOOTER_LINE)

    try:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"[error] {path}: {exc}", file=sys.stderr)
        return False

    print(f"[update] {path}", file=sys.stderr)
    return True


# --------------------------------------------------------------
# CLI entry
# --------------------------------------------------------------
def main(argv: Iterable[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Usage: insert_file_headers.py <file1> [<file2> ...]", file=sys.stderr)
        return 1

    success = True
    for arg in argv:
        path = Path(arg)
        if not process_file(path):
            success = False
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())

# End of file: insert_file_headers.py
