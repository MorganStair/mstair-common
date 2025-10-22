#!/usr/bin/env python
# -*- mode: python; eol-unix -*-
"""
Ensure that Git for Windows is available on PATH inside this virtual environment.

This script installs or updates a ``sitecustomize.py`` file within the active
virtual environment (``.venv/Lib/site-packages/``) so that the Git executable
directory (``C:\\Program Files\\Git\\cmd``) is prepended to PATH whenever Python
starts inside that environment. This prevents errors such as:

    ERROR: Cannot find command 'git' - do you have 'git' installed and in your PATH?

Usage:
    python bin/common_sitecustomize_setup.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Content injected into sitecustomize.py
# ---------------------------------------------------------------------------

CONTENT: str = (
    "def _ensure_git_in_path() -> None:\n"
    '    """Prepend the Windows Git cmd directory to PATH if missing."""\n'
    "    import os\n"
    "    from pathlib import Path\n"
    "    git_dir = Path(r'C:\\\\Program Files\\\\Git\\\\cmd')\n"
    "    path_parts = os.environ.get('PATH', '').split(os.pathsep)\n"
    "    if str(git_dir) not in path_parts and git_dir.exists():\n"
    "        os.environ['PATH'] = os.pathsep.join([str(git_dir), *path_parts])\n"
    "\n"
    "_ensure_git_in_path()\n"
)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def sitecustomize_main() -> None:
    """Ensure sitecustomize.py exists in the active virtual environment."""

    venv_dir: str | None = os.environ.get("VIRTUAL_ENV")
    if not venv_dir:
        print("Not inside a virtual environment; no action taken.", file=sys.stderr)
        sys.exit(1)

    site_packages = Path(venv_dir) / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    target_path = site_packages / "sitecustomize.py"

    if target_path.exists():
        try:
            existing = target_path.read_text(encoding="utf-8").replace("\r\n", "\n")
            if "_ensure_git_in_path()" in existing:
                print(f"{target_path} already configured.")
                sys.exit(0)
        except OSError as exc:
            print(f"Warning: could not read {target_path}: {exc}", file=sys.stderr)
            sys.exit(1)

    # Append safely (LF-only, UTF-8)
    try:
        with target_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write("\n" + CONTENT + "\n")
        print(f"Updated {target_path}")
    except OSError as exc:
        print(f"Error writing to {target_path}: {exc}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sitecustomize_main()
