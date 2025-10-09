# File: python/plib_/base/file_discovery.py
"""
Python File Discovery and Scanning

Handles identification of Python source files to process for metavars header/docstring insertion.
This module supports both file and directory input paths, recursive walking, and skipping of
irrelevant or non-source directories and files.
"""

import fnmatch
from collections.abc import Iterator
from pathlib import Path


IGNORED_DIRS: set[str] = {
    ".assets",
    ".cache",
    ".git",
    ".hg",
    ".mypy_cache",
    ".ruff_cache",
    ".svn",
    ".venv*",
    "__*__",
    "cdk.out",
    "node_modules",
    "typings",
    "venv*",
}

IGNORED_FILES: set[str] = set()


def discover_python_files(
    *,
    dirs_and_files: list[Path],
    ignore_dirs: set[str] | None = None,
    ignore_file_globs: set[str] | None = None,
) -> Iterator[Path]:
    """
    Yield all Python files under the given paths, skipping ignored folders.

    :param dirs_and_files: List of file or directory paths to search
    :yields Path: Python source file paths ending in .py
    """
    ignore_dirs = ignore_dirs or IGNORED_DIRS
    ignore_file_globs = ignore_file_globs or IGNORED_FILES
    for path in dirs_and_files:
        if not isinstance(path, (str, Path)):
            continue
        if path.is_dir() and not _should_skip_dir(path, ignore_dirs):
            yield from _walk_python_files_in_dir(
                path,
                ignore_dir_globs=ignore_dirs,
                ignore_file_globs=ignore_file_globs,
            )
        elif (
            path.is_file()
            and path.suffix == ".py"
            and not any(
                fnmatch.fnmatchcase(
                    path.name.lower(),
                    ignore_file_glob.lower(),
                )
                for ignore_file_glob in ignore_file_globs
            )
        ):
            yield path
        else:
            continue


def _should_skip_dir(dir_path: Path, skip_dir_globs: set[str]) -> bool:
    """
    Check if the directory should be skipped based on ignored patterns.
    :param dir_path: Directory to check
    :return bool: True if the directory should be skipped, False otherwise
    """
    return any(
        fnmatch.fnmatchcase(
            name=_part.lower(),
            pat=_glob.lower(),
        )
        for _glob in skip_dir_globs
        for _part in dir_path.parent.parts
    )


def _walk_python_files_in_dir(
    path: Path,
    ignore_dir_globs: set[str],
    ignore_file_globs: set[str],
) -> Iterator[Path]:
    """
    Discover Python files recursively from a Resolved Root directory using os.walk.
    Skips ignored directories and yields only .py files not matching skip patterns.
    """
    for _dir_path, _dir_names, _file_names in path.walk():
        _dir_names[:] = [
            name
            for name in _dir_names
            if not any(
                fnmatch.fnmatchcase(
                    name.lower(),
                    ignore_dir_glob.lower(),
                )
                for ignore_dir_glob in ignore_dir_globs
            )
        ]

        for filename in _file_names:
            if not filename.endswith(".py"):
                continue
            file_path = _dir_path / filename
            if any(
                fnmatch.fnmatchcase(
                    file_path.name.lower(),
                    ignore_file_glob.lower(),
                )
                for ignore_file_glob in ignore_file_globs
            ):
                continue
            yield file_path


# End of file: src/mstair/common/base/file_discovery.py
