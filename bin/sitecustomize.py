#!/usr/bin/env python
# -*- mode: python; eol-unix -*-
"""
Ensures that Git for Windows is always available on PATH inside this virtual environment.
This fixes pip install errors like:
    ERROR: Cannot find command 'git' - do you have 'git' installed and in your PATH?

Usage:
    Copy this file into .venv/Lib/site-packages/.
"""

import os
from pathlib import Path


def _ensure_git_in_path() -> None:
    """Prepend the Windows Git cmd directory to PATH if missing."""
    git_dir = Path(r"C:\\Program Files\\Git\\cmd")
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if str(git_dir) not in path_parts and git_dir.exists():
        os.environ["PATH"] = os.pathsep.join([str(git_dir), *path_parts])


_ensure_git_in_path()
