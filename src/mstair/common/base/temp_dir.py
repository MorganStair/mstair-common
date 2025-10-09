# File: python/plib_/base/tmpdir_helpers.py
"""
TempDir: Temporary directory helper with automatic file copying support.
"""

import shutil
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory


class TempDir(TemporaryDirectory[str]):
    """
    Temporary directory with automatic file copying support.

    Extends `tempfile.TemporaryDirectory` with validation and copying of files
    into the temporary directory, plus pathlib.Path integration.

    Attributes:
        src_dir (Path): Source directory from which files are copied.
        rel_paths (list[Path]): Relative paths of files to copy from `src_dir`.
        subdir (Path): Optional subdirectory within the temp directory for copied files.
        name (str): Absolute path to the temporary directory (inherited from TemporaryDirectory).
        path (Path): Absolute path to the temporary directory (as a `Path`).
        copied_files (list[Path]): Paths to the files copied into the temporary directory.
    """

    src_dir: Path
    rel_paths: list[Path]
    subdir: Path

    def __init__(
        self,
        src_dir: str | Path | None = None,
        rel_paths: Sequence[str | Path] | None = None,
        subdir: str | Path | None = None,
        *,
        dir: str | Path | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
        ignore_cleanup_errors: bool = False,
        delete: bool = True,
    ) -> None:
        """
        Initialize temporary directory with optional file copying.

        Examples:
        ```
        with TempDir() as temp_dir:
            # temp_dir.path is a Path to the temp directory, like "/tmp/tmpabc123"
        with TempDir(
            src_dir="source_files",
            rel_paths=["file1.txt", "subdir2/file2.txt"],
            subdir="subdir1",
            dir="/custom",
        ) as temp_dir:
            # temp_dir.path is a Path to the temp directory, like "/custom/tmpabc123"
            # temp_dir.path contains "subdir1/file1.txt" and "subdir1/subdir2/file2.txt"
        ```

        :param src_dir: Source directory containing files (defaults to current directory)
        :param rel_paths: Files to copy (relative paths only)
        :param subdir: Optional subdirectory within temp dir for copied files
        :param dir: Parent directory for temporary directory, default is system tempdir
        :param prefix: Prefix for temporary directory name
        :param suffix: Suffix for temporary directory name
        :param ignore_cleanup_errors: Suppress cleanup exceptions
        :param delete: Whether to delete directory on exit
        :raises ValueError: If any absolute paths are provided in rel_paths
        :raises FileNotFoundError: If any source files don't exist
        """
        self.rel_paths = [Path(f) for f in (rel_paths or [])]
        self.src_dir = Path(src_dir) if src_dir else Path.cwd()
        self.subdir = Path(subdir) if subdir else Path()

        # Validate source files
        if abs_paths := [f for f in self.rel_paths if f.is_absolute()]:
            raise ValueError(f"Only relative paths allowed in rel_paths: {abs_paths}")
        if missing_files := [f for f in self.rel_paths if not (self.src_dir / f).exists()]:
            raise FileNotFoundError(f"Files not found in {self.src_dir}: {missing_files}")

        # Create the temporary directory
        super().__init__(
            suffix=suffix,
            prefix=prefix,
            dir=dir,
            ignore_cleanup_errors=ignore_cleanup_errors,
            delete=delete,
        )

        # Copy files into the temporary directory
        for _rel_path in self.rel_paths:
            _src_path = self.src_dir / _rel_path
            _dst_path = self.path / self.subdir / _rel_path
            _dst_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(_src_path, _dst_path)
            except Exception as e:
                raise type(e)(f"Failed to copy {_src_path} -> {_dst_path}") from e

    def cleanup(self) -> None:
        """Delete the temporary directory and its contents."""
        super().cleanup()

    @property
    def copied_files(self) -> list[Path]:
        """List of files copied into the temporary directory (absolute Paths)."""
        return [self.path / self.subdir / f for f in self.rel_paths]

    @property
    def path(self) -> Path:
        """Return temporary directory as a Path object."""
        return Path(self.name)

    def __enter__(self) -> "TempDir":
        """Enter context manager, returning this instance."""
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and clean up temporary directory."""
        return super().__exit__(exc_type, exc_val, exc_tb)


# End of file: src/mstair/common/base/temp_dir.py
