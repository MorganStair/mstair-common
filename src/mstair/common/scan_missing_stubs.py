# File: src/mstair/common/scan_missing_stubs.py
"""
Scan the codebase for third-party imports that lack inline types or generated stubs.

Usage: invoked via `make stubs-missing`.

Rules:
- Only consider non-stdlib, non-local packages.
- Skip modules that already have generated stubs under .cache/typings.
- Skip modules that ship inline types (py.typed or .pyi origins).
- Only report modules that are importable in the current environment.

Requires: Python 3.11+ for sys.stdlib_module_names and Path.walk().
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from tomllib import loads

from mstair.common.base.fs_helpers import fs_find_pyproject_toml, is_stdlib_module_name
from mstair.common.base.mapping_helpers import mapping_attr_at_keypath
from mstair.common.xlogging.logger_factory import create_logger


_LOG = create_logger(__name__)

WHERE_KEYPATH = "tool.setuptools.packages.find.where"
INCLUDE_KEYPATH = "tool.setuptools.packages.find.include"


def main(_argv: list[str]) -> int:
    """
    Entry point for scanning and printing third-party modules missing stubs.

    Usage:
        $ python tools/scan_missing_stubs.py

    :param argv: Command-line arguments (unused).
    :return: Exit code (0 for success).
    """
    pyproject: Path | None = fs_find_pyproject_toml()
    if pyproject is None or not pyproject.is_file():
        print("Error: Could not find pyproject.toml", file=sys.stderr)
        return 1

    toml = loads(pyproject.read_text(encoding="utf-8"))
    where: list[str] = mapping_attr_at_keypath(toml, WHERE_KEYPATH, pyproject.as_posix(), list)
    include: list[str] = mapping_attr_at_keypath(toml, INCLUDE_KEYPATH, pyproject.as_posix(), list)

    files: Iterator[Path] = _find_pyfiles(
        root=pyproject.parent,
        where=where,
        include=include,
    )
    imports: Iterator[str] = _find_top_level_imports_in_pyfiles(files)
    candidates = {
        n
        for n in imports
        if n and not is_stdlib_module_name(n) and n not in {"mstair", "pytest", "typing", "pathlib"}
    }
    typings_dir: Path = Path(os.getenv("CACHE_DIR", pyproject.parent / ".cache")) / "typings"
    for module_name in sorted(candidates):
        if _has_typings_stub(package_name=module_name, typings_dir=typings_dir):
            continue
        if _has_pytyped_or_pyi(module_name=module_name):
            continue
        if importlib.util.find_spec(name=module_name) is None:
            continue
        print(module_name)
    return 0


def _find_pyfiles(root: Path, where: list[str], include: list[str]) -> Iterator[Path]:
    """
    Return Python source files based on [tool.setuptools.packages.find] in pyproject.toml.
    """

    # Modern Pythonic traversal (3.12+ Path.walk)
    seen: set[Path] = set()
    for topdir in where:
        for inc in include:
            inc_path: Path = root / topdir / inc
            if inc_path.is_dir():
                for dirpath, _dirs, files in inc_path.walk():
                    python_files = {dirpath / f for f in files if f.endswith(".py")} - seen
                    if python_files:
                        yield from python_files
                        seen |= python_files


def _find_top_level_imports_in_pyfiles(files: Iterable[Path]) -> Iterator[str]:
    """
    Find unique top-level imported module names from given source files.

    :param files: Iterable of Python source file paths.
    :yields: Iterator of unique top-level module names.
    """
    names: set[str] = set()
    for f in files:
        try:
            tree: ast.Module = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                import_names: set[str] = {a.name.split(".", 1)[0] for a in node.names if a.name}
                yield from import_names - names
                names |= import_names
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".", 1)[0])


def _has_typings_stub(*, package_name: str, typings_dir: Path) -> bool:
    """
    Return True if package has generated stub (.pyi) files under typings_dir.
    """
    pkg = typings_dir / package_name
    if not pkg.exists():
        return False
    if (pkg / "__init__.pyi").is_file():
        return True
    return any(p.suffix == ".pyi" for p in pkg.rglob("*.pyi"))


def _has_pytyped_or_pyi(*, module_name: str) -> bool:
    """
    Return True if the given module has inline or external typing information.

    Recognizes:
    - Inline typing via a `py.typed` marker (PEP 561)
    - Stub-only packages named `types-<module>` (from typeshed)
    - Modules implemented as `.pyi` files
    """
    # 1. Inline py.typed marker
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError):
        spec = None
        _LOG.debug(f"Module not found: {module_name}")
    _LOG.debug(f"Module found: {module_name}")

    if spec and spec.submodule_search_locations:
        if any(Path(p, "py.typed").is_file() for p in spec.submodule_search_locations or []):
            _LOG.debug(f"Found py.typed for {module_name} in {spec.submodule_search_locations}")
            return True
        _LOG.debug(f"No py.typed found for {module_name} in {spec.submodule_search_locations}")

    # 2. Stub-only package (types-<name>)
    try:
        stub_spec = importlib.util.find_spec(f"types-{module_name}")
        if stub_spec is not None:
            _LOG.debug(f"Found stub-only package: types-{module_name}")
            return True
    except (ImportError, ModuleNotFoundError):
        _LOG.debug(f"No stub-only package found: types-{module_name}")
        pass

    # 3. Direct .pyi origin
    if (
        spec is not None
        and spec.origin is not None
        and isinstance(spec.origin, str)
        and spec.origin.endswith(".pyi")
    ):
        _LOG.debug(f"Module {module_name} is a .pyi file: {spec.origin}")
        return True

    # Fallback: no typing info found
    _LOG.debug(f"No typing info found for module: {module_name}")
    return False


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# End of file: src/mstair/common/scan_missing_stubs.py
