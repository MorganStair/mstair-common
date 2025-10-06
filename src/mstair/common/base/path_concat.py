# File: python/plib_/base/path_concat.py

from pathlib import Path


def path_concat(path: Path | str, *strings: str) -> Path:
    """Append string(s) to the filename portion of a Path object."""
    if isinstance(path, str):
        path = Path(path)
    for string in strings:
        path = path.with_name(path.name + string)
    return path


# End of file: python/plib_/base/path_concat.py
