#!/usr/bin/env python
# -*- mode: python; eol-unix -*-
# File: bin/common_split_makefiles.py
#
"""
Split concatenated Makefile stream (from `make cat`) into individual files.

Example:
    >>> from collections.abc import Iterable
    >>> lines = ["# File: make/00-globals.mk\\n", "all:\\n", "\\t@echo hi\\n"]
    >>> written = common_split_makefiles(lines)
    >>> written[0].name.endswith("00-globals.mk")
    True

This module reads lines from a stream and writes blocks that follow lines of
the form "# File: <path>" into the named file until the next "# File:" line.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path


# --------------------------------------------------------------
# Section: Module-level constants and configuration
# --------------------------------------------------------------
FILE_PATTERN = re.compile(r"^# File:\s+(.+)$")
__all__ = ["common_split_makefiles", "common_split_makefiles_main"]


# --------------------------------------------------------------
# Section: Type definitions and dataclasses
# --------------------------------------------------------------
# (no dataclasses required)


# --------------------------------------------------------------
# Section: Main public API
# --------------------------------------------------------------
def common_split_makefiles(lines: Iterable[str]) -> list[Path]:
    """
    Split a stream of lines into files based on lines matching FILE_PATTERN.

    Args:
        lines: An iterable of input lines (e.g. sys.stdin).

    Returns:
        A list of Path objects for files that were written, in write order.
    """
    written: list[Path] = []
    out_file = None
    try:
        for line in lines:
            match = FILE_PATTERN.match(line)
            if match:
                # close previous file if open
                if out_file is not None:
                    out_file.close()
                    out_file = None
                path = Path(match.group(1)).expanduser()

                # Ensure parent directories exist.
                path.parent.mkdir(parents=True, exist_ok=True)

                # Open the target file for writing using explicit encoding.
                out_file = path.open("w", encoding="utf-8")
                written.append(path)
                print(f"[write] {path}", file=sys.stderr)

                # Write the first line (the # File: ... line) to the new file.
                out_file.write(line)
                continue

            if out_file is not None:
                out_file.write(line)
    finally:
        if out_file is not None:
            out_file.close()

    return written


def common_split_makefiles_main() -> int:
    """
    Entry point for CLI usage. Reads from sys.stdin and writes files.

    Returns:
        Exit code (0 for success, non-zero for filesystem errors).
    """
    try:
        common_split_makefiles(sys.stdin)
    except OSError as exc:
        print(f"Error writing files: {exc}", file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------
# Section: Private implementation details
# --------------------------------------------------------------
# (no additional private helpers required)

if __name__ == "__main__":
    raise SystemExit(common_split_makefiles_main())

# --------------------------------------------------------------
