# File: bin/reset_inits.py
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
    $ python bin/reset_inits.py
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import tomllib
from pathlib import Path


# -----------------------------------------------------------------------------
# Module constants and configuration
# -----------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
_LOG: logging.Logger = logging.getLogger(__name__)

_ROOT_DIR: Path = Path("src")
_NAMESPACE_PATHS: list[Path] = [dir for dir in _ROOT_DIR.glob("*") if dir.is_dir()]

_DOCSTRING_TEMPLATE: str = '"""\n{package}\n"""'
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
        doc = _DOCSTRING_TEMPLATE.format(package=package)
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


def _process_init_file(init_path: Path, package_fqn: str, version: str | None) -> bool:
    """
    Ensure a single __init__.py file has the correct structure.

    Returns True if the file was modified.
    """
    original_content: str = init_path.read_text(encoding="utf-8") if init_path.exists() else ""
    content: str = original_content

    # Apply non-destructive edits
    content = _ensure_docstring(content, package_fqn)
    content = _ensure_autogen_markers(content)
    content = _remove_all_definitions(content)

    # Apply version only for mstair.rentals
    if version is not None and package_fqn == "mstair.rentals":
        content = _set_or_update_version(content, version)

    # Normalize trailing newlines
    content = content.rstrip() + "\n"

    if content != original_content:
        init_path.write_text(content, encoding="utf-8")
        _LOG.info("Updated %s", init_path)
        return True

    _LOG.debug("No changes needed for %s", init_path)
    return False


def _run_subprocess(cmd: list[str]) -> None:
    """Run a subprocess command and exit on failure."""
    _LOG.info("> %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def reset_inits_main(argv: list[str] | None = None) -> None:
    """
    Reset and normalize all __init__.py files in the mstair package tree.

    This function may be safely re-run; it only modifies what is missing
    or inconsistent with the desired package initialization structure.
    """
    parser = argparse.ArgumentParser(description="Reset and normalize mstair __init__.py files.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show planned changes without modifying files."
    )
    args = parser.parse_args(argv)

    pyproject_path: Path = _ROOT_DIR.parent / "pyproject.toml"
    version: str = _read_pyproject_version(pyproject_path)

    modified_count: int = 0
    for namespace_path in _NAMESPACE_PATHS:
        _LOG.info("Processing namespace: %s", namespace_path.stem)
        for root_package_in_namespace in (p for p in namespace_path.rglob("*") if p.is_dir()):
            _LOG.info(
                "Processing top level package %s.%s",
                namespace_path.stem,
                root_package_in_namespace.stem,
            )
            relative = root_package_in_namespace.relative_to(_ROOT_DIR)
            package_fqn = ".".join(relative.parts)
            init_path = root_package_in_namespace / "__init__.py"

            if not init_path.exists():
                init_path.touch()
                _LOG.info("Created missing %s", init_path)

            if not args.dry_run:
                if _process_init_file(init_path, package_fqn, version):
                    modified_count += 1

        _LOG.info("Processed all __init__.py files. %d modified.", modified_count)
        _run_subprocess(["mkinit", str(namespace_path), "--noattrs", "--inplace", "--recursive"])

    if args.dry_run:
        _LOG.info("Dry run complete. No changes written.")
        return

    _run_subprocess(["ruff", "check", str(_ROOT_DIR), "--fix"])
    _run_subprocess(["ruff", "format", str(_ROOT_DIR)])


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        reset_inits_main()
    except subprocess.CalledProcessError as exc:
        _LOG.error("Subprocess failed: %s", exc)
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        _LOG.warning("Interrupted by user.")
        sys.exit(130)

# End of file: bin/reset_inits.py
