#!/usr/bin/env python
# -*- mode: python; eol-unix -*-
"""
Reset and normalize all __init__.py files in the mstair source tree.

This script ensures each package under ``src/mstair/`` has a proper __init__.py
with the expected header structure. It performs the following steps:

1. Create missing __init__.py files.
2. Ensure a package docstring exists at the top.
3. Ensure AUTOGEN_INIT comment markers are present.
4. Remove any __all__ definitions.
5. For ``*.*`` packages, insert or update the __version__ dunder
   based on the version in pyproject.toml.
6. Finally, run mkinit and Ruff to rebuild and format the package structure.

Example:
    $ python bin/common_reset_inits.py
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import time
import tomllib
from collections.abc import Iterator
from pathlib import Path


# -----------------------------------------------------------------------------
# Module constants and configuration
# -----------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOG: logging.Logger = logging.getLogger(__name__)

_SRC: Path = Path("src").resolve()

_INIT_DOCSTRING_TEMPLATE: str = '"""\npackage: {package}\n"""'
_AUTOGEN_BLOCK: str = "# <AUTOGEN_INIT>\npass\n# </AUTOGEN_INIT>\n"
_VERSION_PATTERN: re.Pattern[str] = re.compile(r"^__version__\s*=\s*['\"](.+?)['\"]", re.MULTILINE)
_ALL_PATTERN: re.Pattern[str] = re.compile(r"^\s*__all__\s*=\s*\[[^\]]*\]\s*$", re.MULTILINE)
_DOCSTRING_PATTERN: re.Pattern[str] = re.compile(r'^\s*""".*?"""', re.DOTALL)


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------


def _ensure_docstring(content: str, package: str) -> str:
    """Insert a package docstring if missing."""
    if not _DOCSTRING_PATTERN.search(content):
        doc = _INIT_DOCSTRING_TEMPLATE.format(package=package)
        return f"{doc}\n\n{content.lstrip()}"
    return content


def _ensure_autogen_markers(content: str) -> str:
    """Insert AUTOGEN markers if missing."""
    if "# <AUTOGEN_INIT>" not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += _AUTOGEN_BLOCK
    return content


def _remove_all_definitions(content: str) -> str:
    """Remove __all__ definitions."""
    return _ALL_PATTERN.sub("", content)


def _set_or_update_version(content: str, version: str) -> str:
    """Insert or update the __version__ dunder."""
    if _VERSION_PATTERN.search(content):
        return _VERSION_PATTERN.sub(f'__version__ = "{version}"', content)
    if not content.endswith("\n"):
        content += "\n"
    return f'{content}\n__version__ = "{version}"\n'


def _read_pyproject_version(pyproject_path: Path) -> str:
    """Read and validate the project version from pyproject.toml."""
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    try:
        version = pyproject["project"]["version"]
    except KeyError as exc:
        _LOG.error("Missing 'project.version' in pyproject.toml")
        raise SystemExit(1) from exc

    if not isinstance(version, str):
        _LOG.error("Version in pyproject.toml is not a string: %r", version)
        raise SystemExit(1)

    if not re.match(r"^\d+\.\d+\.\d+(?:[a-zA-Z0-9.\-]*)?$", version):
        _LOG.error("Version string does not match expected format: %s", version)
        raise SystemExit(1)

    return version


# -----------------------------------------------------------------------------
# Core processing
# -----------------------------------------------------------------------------


def _process_init_file(
    init_path: Path,
    package_fqn: str,
    version: str | None,
) -> bool:
    """
    Ensure a single __init__.py file has the correct structure.

    Returns True if the file was modified.
    """
    if not init_path.exists():
        init_path.touch()
    original_content: str = init_path.read_text(encoding="utf-8") if init_path.exists() else ""
    content: str = original_content

    # Apply non-destructive edits
    content = _ensure_docstring(content, package_fqn)
    content = _ensure_autogen_markers(content)
    content = _remove_all_definitions(content)

    # Apply version only for second-level packages
    if version is not None and len(package_fqn.split(".")) == 2:
        content = _set_or_update_version(content, version)

    # Normalize trailing newlines
    content = content.rstrip() + "\n"

    if content != original_content:
        _LOG.info("Updating %s", init_path)
        init_path.write_text(content, encoding="utf-8")
        return True

    _LOG.debug("No changes needed for %s", init_path)
    return False


def _run_subprocess(cmd: list[str]) -> None:
    """Run a subprocess command and exit on failure."""
    _LOG.info("> %s", " ".join(cmd))
    time.sleep(0.2)
    subprocess.run(cmd, check=True)


def common_reset_inits_main(argv: list[str] | None = None) -> None:
    """
    Reset and normalize all __init__.py files in the mstair package tree.

    This function may be safely re-run; it only modifies what is missing
    or inconsistent with the desired package initialization structure.
    """
    parser = argparse.ArgumentParser(description="Reset and normalize mstair __init__.py files.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show planned changes without modifying files."
    )
    parser.add_argument(
        "--clean", "-c", action="store_true", help="Remove all existing __init__.py files first."
    )
    args = parser.parse_args(argv)

    pyproject_path: Path = _SRC.parent / "pyproject.toml"
    version_string: str = _read_pyproject_version(pyproject_path)
    src_subdirs = (d for d in _SRC.iterdir() if d.is_dir())
    top_package_dirs: list[Path] = []

    for package_dir in recurse_package_paths(*src_subdirs):
        _LOG.info("Processing: %s", package_dir.as_posix())
        package_tree = package_dir.relative_to(_SRC).parts
        package_fqn = ".".join(package_tree)
        package_init_path = package_dir / "__init__.py"
        if args.clean and package_init_path.exists():
            _LOG.info("Removing existing __init__.py: %s", package_init_path.as_posix())
            package_init_path.unlink()
        _process_init_file(
            package_init_path,
            package_fqn,
            version_string if len(package_tree) == 2 else None,
        )
        if len(package_tree) == 1:
            top_package_dirs.append(package_dir)

    for top_package_dir in top_package_dirs:
        _LOG.info("Reprocessing top-level package: %s", top_package_dir.as_posix())
        mkinit_cmd: list[str] = [
            "mkinit",
            top_package_dir.as_posix(),
            "--inplace",
            "--noattrs",
            "--recursive",
        ]
        _LOG.info("mkinit_cmd:\n> %s", " ".join(mkinit_cmd))
        _run_subprocess(mkinit_cmd)

    if args.dry_run:
        _LOG.info("Dry run complete. No changes written.")
        return

    _run_subprocess(["ruff", "check", _SRC.as_posix(), "--fix"])
    _run_subprocess(["ruff", "format", _SRC.as_posix()])


def recurse_package_paths(*package_paths: Path) -> Iterator[Path]:
    """Recursively yield package directories."""
    queue: list[Path] = [*package_paths]
    while queue:
        path = queue.pop()
        if re.fullmatch(r"[a-z_][a-z0-9_]*[a-z0-9]", path.name):
            yield path
        for _subdir in path.iterdir():
            if _subdir.is_dir():
                queue.append(_subdir)


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    try:
        common_reset_inits_main()
    except subprocess.CalledProcessError as exc:
        _LOG.error("Subprocess failed: %s", exc)
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        _LOG.warning("Interrupted by user.")
        sys.exit(130)

# End of file: bin/common_reset_inits.py
