# File: src/mstair/common/update_pyproject_version.py
"""
Increment pyproject.toml [project.version] if the repo has uncommitted or unpushed changes.

Intended for use in build or release automation, ensuring that downstream
pip installs see a version change whenever the source tree has been modified.

Usage:
    python src/mstair/common/update_pyproject_version.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from git import Repo


INCLUDE_KEYPATH = "tool.setuptools.packages.find.include"
SRC_KEYPATH = "tool.setuptools.packages.find.src"
VERSION_KEYPATH = "project.version"


def get_repo(path: Path) -> Repo:
    """Return a GitPython Repo rooted at or above the given path."""
    try:
        return Repo(path, search_parent_directories=True)
    except Exception as exc:
        sys.exit(f"[ERROR] Not a git repository: {path}\n{exc}")


def repo_has_changes(repo: Repo) -> bool:
    """
    Return True if the repository has any uncommitted or unpushed changes.
    This includes:
        - modified or untracked files
        - commits ahead of the remote
    """
    if repo.is_dirty(untracked_files=True):
        return True
    try:
        head = repo.head.commit
        tracking = repo.active_branch.tracking_branch()
        if tracking is None:
            return False
        return bool(head.hexsha != tracking.commit.hexsha)
    except Exception:
        # Detached HEAD or no remote tracking
        return False


def increment_patch(version: str) -> str:
    """Return version with its final numeric segment incremented."""
    match = re.match(r"^(\d+(?:\.\d+)*)(.*)$", version.strip())
    if not match:
        raise ValueError(f"Invalid version format: {version!r}")
    numeric, suffix = match.groups()
    parts = [int(p) for p in numeric.split(".")]
    parts[-1] += 1
    return ".".join(map(str, parts)) + suffix


def bump_pyproject_version(pyproject_path: Path) -> str | None:
    """
    If the git repo has changes and the version has not yet been bumped,
    increment the patch component of [project.version] in pyproject.toml.

    :return: New version string if updated, else None.
    """
    repo = get_repo(pyproject_path.parent)
    if not repo_has_changes(repo):
        return None

    text = pyproject_path.read_text(encoding="utf-8")
    pattern = re.compile(r'(^\s*version\s*=\s*["\'])([\d\w.\-]+)(["\'])', re.MULTILINE)

    match = pattern.search(text)
    if not match:
        raise RuntimeError("No [project.version] entry found in pyproject.toml")

    current = match.group(2)
    new_version = increment_patch(current)

    if new_version == current:
        return None

    new_text = pattern.sub(rf"\1{new_version}\3", text, count=1)
    pyproject_path.write_text(new_text, encoding="utf-8")
    print(f"[INFO] Bumped version: {current} → {new_version}")
    return new_version


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    pyproject = Path(argv[0] if argv else "pyproject.toml").resolve()
    if not pyproject.is_file():
        sys.exit(f"[ERROR] No pyproject.toml at {pyproject}")
    bump_pyproject_version(pyproject)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# End of file: src/mstair/common/update_pyproject_version.py
