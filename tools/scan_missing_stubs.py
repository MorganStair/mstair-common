# File: tools/scan_missing_stubs.py
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
from collections.abc import Iterable, Iterator, Mapping
from functools import cache, reduce
from pathlib import Path
from tomllib import loads
from typing import Any, TypeVar


T = TypeVar("T")
SRC_KEYPATH = "tool.setuptools.packages.find.src"
INCLUDE_KEYPATH = "tool.setuptools.packages.find.include"


def main(_argv: list[str]) -> int:
    """
    Entry point for scanning and printing third-party modules missing stubs.

    Usage:
        $ python tools/scan_missing_stubs.py

    :param argv: Command-line arguments (unused).
    :return: Exit code (0 for success).
    """
    project_dir: Path = _find_pyproject_toml()
    cache_dir = Path(os.getenv("CACHE_DIR", project_dir / ".cache"))
    typings_dir: Path = cache_dir.joinpath("typings").resolve()
    files: Iterator[Path] = _find_pyfiles(pyproject=project_dir / "pyproject.toml")
    imports: Iterator[str] = _find_top_level_imports_in_pyfiles(files)
    candidates = {
        n
        for n in imports
        if n and not _is_stdlib_module(n) and n not in {"mstair", "pytest", "typing", "pathlib"}
    }

    for module_name in sorted(candidates):
        if _has_typings_stub(package_name=module_name, typings_dir=typings_dir):
            continue
        if _has_pytyped_or_pyi(module_name=module_name):
            continue
        if importlib.util.find_spec(name=module_name) is None:
            continue
        print(module_name)
    return 0


def _is_stdlib_module(name: str) -> bool:
    """
    Check whether a module belongs to the standard library.

    :param name: Module name to check.
    :return: True if the module is part of the standard library, False otherwise.
    """
    std = getattr(sys, "stdlib_module_names", None)
    return bool(std and name in std)


def _find_pyfiles(*, pyproject: Path) -> Iterator[Path]:
    """
    Return Python source files based on [tool.setuptools.packages.find] in pyproject.toml.
    """
    toml: dict[str, Any] = _load_pyproject_toml(pyproject)
    src: str = _get_map_attr_at_keypath(toml, SRC_KEYPATH, pyproject.as_posix(), str)
    include: list[str] = _get_map_attr_at_keypath(toml, INCLUDE_KEYPATH, pyproject.as_posix(), list)
    root: Path = pyproject.parent

    # Modern Pythonic traversal (3.12+ Path.walk)
    seen: set[Path] = set()
    for inc in include:
        inc_path: Path = root / src / inc
        if inc_path.is_dir():
            for dirpath, _dirs, files in inc_path.walk():
                python_files = {dirpath / f for f in files if f.endswith(".py")} - seen
                if python_files:
                    yield from python_files
                    seen |= python_files


@cache
def _load_pyproject_toml(pyproject: Path | None = None) -> dict[str, Any]:
    """
    Load and parse pyproject.toml file.

    :param pyproject: Path to pyproject.toml (if None, will search for it).
    :return: Parsed pyproject.toml as a dictionary.
    """
    pyproject = pyproject or _find_pyproject_toml()
    return loads(pyproject.read_text(encoding="utf-8"))


@cache
def _find_pyproject_toml(start_dir: Path | None = None, name: str = "pyproject.toml") -> Path:
    """
    Return nearest pyproject.toml.

    :param start_dir: Directory to start searching from (defaults to cwd).
    :param name: Filename to search for (defaults to 'pyproject.toml').
    :return: Path to the found pyproject.toml file.
    :raises: FileNotFoundError if no pyproject.toml is found.
    """
    start_dir = start_dir or Path.cwd()
    for dir in (start_dir, *start_dir.parents):
        candidate = dir / name
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Could not find {name} in any parent directory of {start_dir}")


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
    Return True if package provides inline typing (py.typed or .pyi origin).
    """
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError):
        return False
    if spec is None:
        return False

    # Package with py.typed marker
    if spec.submodule_search_locations:
        return any(Path(p, "py.typed").is_file() for p in spec.submodule_search_locations or [])
    # Module implemented as .pyi
    return isinstance(spec.origin, str) and spec.origin.endswith(".pyi")


def _get_map_attr_at_keypath[T](
    map: Mapping[str, Any], keypath: str, origin: str, expected_type: type[T]
) -> T:
    """
    Retrieve a nested value from a mapping using a dot-separated keypath.

    :param map: Root mapping (e.g., a parsed TOML or JSON dictionary).
    :param keypath: Dot-separated lookup path, e.g. "tool.setuptools.packages.find.include".
    :param origin: Identifier for the mapping (used in diagnostic messages).
    :param expected_type: The expected runtime type of the final value.
    :return: The resolved value of type ``T``.
    :raises: KeyError if any key in the path is missing.
    :raises: TypeError if the resolved value is not of ``expected_type``.
    """
    try:
        result = reduce(lambda acc, key: acc[key], keypath.split("."), map)
    except KeyError as e:
        raise KeyError(f"Missing key '{e.args[0]}' in '{origin}' while resolving '{keypath}'") from e
    if not isinstance(result, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__} at '{keypath}' in '{origin}', "
            f"got {type(result).__name__}"
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# End of file: tools/scan_missing_stubs.py
