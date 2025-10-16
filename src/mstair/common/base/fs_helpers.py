# File: python/plib_/base/fs_helpers.py
"""
File System Helpers
"""

import importlib.resources.abc
import logging
import os
import sys
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from functools import cache
from io import IOBase
from pathlib import Path
from typing import IO, TypeAlias

import dotenv


StrPath: TypeAlias = str | Path

_fs_pyproject_toml_cache: dict[Path, Path | None] = {}


def fs_safe_relpath(path: StrPath, root: Path) -> str:
    """Return a path with '..' segments, or fallback on the full path, instead of raising"""
    p: Path = Path(path).resolve()
    r: Path = root.resolve()
    try:
        return p.relative_to(r, walk_up=True).as_posix()
    except Exception:
        return p.as_posix()


def fs_find_import_root(file_or_dir: StrPath) -> Path:
    """
    Return the parent directory immediately above the top-level package directory.

    Walks upward from the given Python source file or package directory, stopping
    at the first ancestor directory that is not a Python package (i.e. lacks __init__.py).
    This root is the filesystem directory from which the import path should be resolved.

    Example:
    ```
    root = fs_find_module_root(Path("/dir1/dir2/package3/module4.py"))
    print(root)  # Output: /dir1/dir2
    ```

    :param path: Filesystem path to a Python module or package directory.
    :return Path: Filesystem directory above the top-level Python package.
    """

    return _fs_find_import_root_cached(path=str(file_or_dir))


@cache
def _fs_find_import_root_cached(path: str) -> Path:
    """Workaround for @cache interfering with static type checking."""
    current_dir: Path = Path(path).parent if Path(path).is_file() else Path(path)
    while (current_dir / "__init__.py").is_file():
        current_dir = current_dir.parent
    return current_dir


def fs_find_repo_root(
    *,
    filename: str = ".git",
    start_dir: Path | None = None,
) -> Path:
    """
    Return the absolute path of the repository root.

    This function searches for a file named `.git` in the directory tree starting from `start_dir`.
    Given no parameters, it searches for `.git`, starting in the current working directory.

    :param filename: The name of the file to search for, default is ".git".
    :param start_dir: The directory to start searching from, default is the current working directory.
    :return: The absolute path of first `start_dir` parent directory containing `filename`, or `start_dir` if not found.
    """

    _start_dir_path: Path = start_dir or Path(filename).parent
    result_str: str | None = _fs_find_root_cached(
        filename=filename, start_dir_str=_start_dir_path.as_posix()
    )

    # Handle not-found case with fallback logic (not cached)
    if result_str is None:
        result_str = _start_dir_path.resolve().as_posix()

    return Path(result_str)


def fs_find_pyproject_toml(
    *,
    start_dir: Path | None = None,
    strict: bool = False,
    warn: bool = False,
) -> Path | None:
    """
    Return the absolute path of the nearest `pyproject.toml` file.

    :param start_dir: The directory to start searching from, default is the current working directory.
    :param strict: If True, raises `FileNotFoundError` if the file is not found, default is False.
    :param warn: If True, emits a log `warning` if the file is not found, default is False.
    :return: The absolute path of the nearest `pyproject.toml` file.
    :raises FileNotFoundError: If the `filename` is not found and `strict` is True.
    """
    start_dir = start_dir or Path.cwd()
    if start_dir not in _fs_pyproject_toml_cache:
        for dir in [start_dir, *list(start_dir.parents)]:
            if not dir.is_dir():
                continue
            candidate = dir / "pyproject.toml"
            if candidate.is_file():
                _fs_pyproject_toml_cache[start_dir] = candidate
                return candidate

        if strict:
            raise FileNotFoundError(f"No pyproject.toml found for {start_dir}")
        if warn:
            warnings.warn(
                message=f"No pyproject.toml found for {start_dir}.",
                category=UserWarning,
                stacklevel=2,
            )
        _fs_pyproject_toml_cache[start_dir] = None
    return _fs_pyproject_toml_cache[start_dir]


@cache
def _fs_find_root_cached(filename: str, start_dir_str: str) -> str | None:
    """Workaround for @cache interfering with static type checking."""
    start_path = Path(start_dir_str).resolve()
    for dir_path in [start_path, *list(start_path.parents)]:
        if (dir_path / filename).exists():
            return dir_path.as_posix()
    return None


def fs_remove_files(*, root: str, glob: str = "*") -> None:
    """
    Recursively remove files matching the glob pattern under the root directory.

    :param root: The root directory from which to begin the recursive file search.
    :param glob: The glob pattern to remove. Default="*".
    """
    for file in Path(root).rglob(glob):
        if file.is_file():
            file.unlink()


@contextmanager
def fs_redirect_fd(
    from_file: int | IOBase,
    to_file: int | IOBase,
    *,
    enabled: bool = True,
) -> Iterator[None]:
    """
    Redirects a file descriptor or stream to another file or stream.

    Args:
        from_file: The file descriptor or stream to redirect.
        to_file: The file descriptor, stream, or filename to redirect to.
        enabled: Whether to enable the redirection. Default=True.

    Example:
        ```
        with redirect_fd( from_file=sys.stderr, to_file=os.devnull ):
        ```
    """
    if not enabled:
        yield
        return

    def _get_fd(file: int | IOBase, can_open: bool) -> int:
        if isinstance(file, int) and file > 0:
            return int(file)
        _fileno_method = getattr(file, "fileno", None)
        if callable(_fileno_method):
            _fileno = _fileno_method()
            if isinstance(_fileno, int) and _fileno > 0:
                return int(_fileno)
        elif isinstance(file, str):
            if not can_open:
                raise ValueError(f"Invalid {file=}")
            if file in {os.devnull, "NUL", "/dev/null"}:
                if os.name == "nt":
                    return os.open("NUL", os.O_WRONLY)
                return os.open("/dev/null", os.O_WRONLY)
            return os.open(file, os.O_RDWR)
        raise ValueError(f"Invalid {file=}")

    def _safe_sync(fd: int) -> None:
        """Safely flush and sync a file descriptor, ignoring errors."""
        with suppress(OSError):
            os.fsync(fd)

    _from_fd = _get_fd(from_file, can_open=False)
    _to_fd = _get_fd(to_file, can_open=True)
    _safe_sync(_from_fd)
    _saved_from_fd = os.dup(_from_fd)
    os.dup2(_to_fd, _from_fd)
    try:
        yield
    finally:
        _safe_sync(_from_fd)
        os.dup2(_saved_from_fd, _from_fd)
        REDIRECT_TEST = True
        if REDIRECT_TEST:
            _safe_sync(_from_fd)
        else:
            os.close(_saved_from_fd)
        if isinstance(to_file, str):
            os.close(_to_fd)


def is_project_local_file(
    project_dir: str | Path,
    rel_file_path: str | Path,
) -> bool:
    """
    Check if a file path points to a project-local source file.

    The file is project-local if its absolute path is within project_dir and
    not inside typical virtual environment or third-party package subdirectories.

    :param project_dir: Path to the project root directory.
    :param rel_file_path: File path, relative to project_dir.
    :return bool: True if the file is project-local; otherwise, False.
    """
    project_dir, rel_file_path = map(Path, (project_dir, rel_file_path))
    if not rel_file_path:
        return False

    abs_file_path = (project_dir / rel_file_path).resolve()
    abs_file_str = abs_file_path.as_posix().lower()

    # Known third-party or virtual environment path segments
    third_party_segs = (
        "site-packages",
        "dist-packages",
        "venv",
        ".venv",
        "env",
        ".env",
    )
    if any(seg in abs_file_str for seg in third_party_segs):
        return False

    try:
        abs_file_path.relative_to(project_dir.resolve())
        return True
    except ValueError:
        return False


def is_stdlib_module_name(
    module_name: str,
) -> bool:
    """
    Check if the top-level module name is a Python standard library module.

    Uses sys.stdlib_module_names (Python 3.10+). For earlier versions, always returns False.

    :param module_name: Full dotted module name, e.g., "os.path".
    :return bool: True if top-level module is standard library, else False.
    """
    if not module_name:
        return False

    top_level = module_name.split(".", 1)[0]
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if stdlib_names is not None:
        return top_level in stdlib_names
    return False


def fs_expand_file_paths(
    *,
    dir: str | Path,
    paths: StrPath | list[StrPath],
    filter: Callable[[Path], bool] = Path.is_file,
) -> list[Path]:
    """
    Expand and normalize paths, then filter them based on the provided filter function.

    :param dir: Directory to use as a base for relative paths.
    :param paths: Path or list of paths to expand and normalize.
    :param filter: Function to filter normalized paths, default = files only.
    :return: List of normalized Path objects that pass the filter.
    """
    result: list[Path] = []
    if isinstance(paths, StrPath):
        paths = [paths]

    for p in paths:
        if not isinstance(p, StrPath):
            raise TypeError(f"Expected str or Path, got {type(p).__name__}({p})")
        path: Path = Path(p)
        expanded = (
            path.expanduser()
            if str(path).startswith("~")
            else path
            if path.is_absolute()
            else (Path(dir) / path)
        )
        if filter(expanded):
            result.append(expanded)

    return result


@cache
def fs_read_project_file_cached(
    file_or_resource: Path | importlib.resources.abc.Traversable,
) -> str:
    """
    Cache file or resource content to avoid duplicate reads.

    Supports both real filesystem paths and package resources accessed via
    importlib.resources.

    Args:
        file_or_resource: The Path or Traversable to read.

    Returns:
        The content of the file or resource as a string.

    Example:
        content = fs_read_project_file_cached(candidate)
    """
    if isinstance(file_or_resource, Path):
        return file_or_resource.read_bytes().decode("utf-8")
    elif isinstance(file_or_resource, importlib.resources.abc.Traversable):
        with file_or_resource.open(mode="rb") as f:
            return f.read().decode("utf-8")
    else:
        raise TypeError(
            f"Unsupported type {type(file_or_resource).__name__}; expected Path or Traversable"
        )


def fs_load_dotenv(
    *,
    logger: logging.Logger | None = None,
    dotenv_path: StrPath | None = None,
    stream: IO[str] | None = None,
    verbose: bool = False,
    override: bool = False,
    interpolate: bool = True,
    encoding: str | None = "utf-8",
) -> bool:
    """
    Parse a .env file and then load all the variables found as environment variables.

    :param logger: Logger to use for warnings and info messages, if supplied verbose is enabled.
    :param dotenv_path: Absolute or relative path to .env file.
    :param stream: Text stream (such as `io.StringIO`) with .env content, used if `dotenv_path` is `None`.
    :param verbose: Whether to output a warning the .env file is missing.
    :param override: Whether to override the environment variables with the variables from the `.env` file.
    :param interpolate: Whether to interpolate environment variables in the .env file.
    :return: True if at least one environment variable is set else False

    If both `dotenv_path` and `stream` are `None`, `find_dotenv()` is used to find the
    .env file with it's default parameters. If you need to change the default parameters
    of `find_dotenv()`, you can explicitly call `find_dotenv()` and pass the result
    to this function as `dotenv_path`."""
    if logger is not None and bool(logger):
        dotenv.main.logger = logger
        verbose = True
    return dotenv.load_dotenv(
        dotenv_path=dotenv_path,
        stream=stream,
        verbose=verbose,
        override=override,
        interpolate=interpolate,
        encoding=encoding,
    )


def fs_find_file_in_parents(
    *filename: str,
    start_dir: StrPath | None = None,
) -> Path | None:
    """
    Search for the first occurrence of any specified filename in the current or parent directories.

    :param filename: One or more filenames to search for.
    :param start_dir: Directory to start searching from, defaults to current working directory.
    :return: Path to the found file, or None if not found.
    """
    start_dir = Path(start_dir or ".").resolve()
    if not start_dir.is_dir():
        raise ValueError(f"start_dir {start_dir} is not a directory")

    for dir in [start_dir, *list(start_dir.parents)]:
        for basename in filename:
            candidate = dir / basename
            if candidate.is_file():
                return candidate
    return None


# End of file: src/mstair/common/base/fs_helpers.py
