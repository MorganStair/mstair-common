# File: python/plib_/base/git_helpers.py
"""
Git Helpers Module

Provides utility functions for interacting with Git repositories, including fetching user email,
repository paths, and branch information.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, fields, is_dataclass
from functools import cache, cached_property
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse

import git
import git.exc
from git import Head
from git.objects.commit import Commit


__all__ = [
    "git_repo",
    "git_repo_basedir",
    "git_repo_owner_fullname",
    "git_repo_owner_email",
    "is_main_branch",
    "sync_branches",
    "RepoContext",
    "git_default_author",
    "RepoMetadata",
]


def git_repo(start_dir: Path | str = ".") -> git.Repo:
    """
    Locate and return the Git repository containing the specified directory.

    Args:
        start_dir (Path | str): The directory to start searching from. Defaults to the current directory.

    Returns:
        git.Repo: The Git repository object representing the found repository.
    """
    return _git_repo_cache_impl(start=str(start_dir))


@cache
def _git_repo_cache_impl(*, start: str):
    return git.Repo(start, search_parent_directories=True)


def git_repo_basedir(start: str | Path = ".") -> str:
    """
    Return the repository base path for the specified directory or raise an exception.

    :param start: The directory or file path to start the search from, default is ".".
    :raise InvalidGitRepositoryError: If the specified directory is not inside a Git repository.
    :returns: The repository base path.

    Usage:
        REPO_BASE = git_repo_basedir()
    """
    result = _git_repo_basedir_cache_impl(start=str(start))
    return result


@cache
def _git_repo_basedir_cache_impl(*, start: str):
    start_path = Path(start or ".").resolve()
    if start_path.is_file():
        start_path = start_path.parent

    try:
        repo: git.Repo = git_repo(start_path.as_posix())
        result = str(repo.git.rev_parse("--show-toplevel")).replace("\\", "/")
    except git.exc.InvalidGitRepositoryError as _e:
        raise git.exc.InvalidGitRepositoryError(f'"{start}" is not inside a Git repository.') from _e
    return result


@cache
def git_repo_owner_fullname(repo_dir: str | Path = ".", default: str = "Unknown Author") -> str:
    """Return the git repo owner name."""
    repo = git_repo(repo_dir)
    user_name = str(repo.config_reader().get_value("user", "name", default))
    return user_name


@cache
def git_repo_owner_email(repo_dir: str | Path = ".", default: str = "unknown@example.com") -> str:
    """Return the git repo owner email."""
    repo = git_repo(repo_dir)
    user_email = str(repo.config_reader().get_value("user", "email", default))
    return user_email


def is_main_branch(branch: Head) -> bool:
    """
    Checks if the given branch's commit is a root commit (i.e., has no parents).
    This does not check the branch name (e.g., 'main' or 'master').
    """
    _branch_commit: Commit = branch.commit
    if not _branch_commit:
        raise ValueError(f"Orphan branch error: {branch.name=} has no associated commit")
    return len(_branch_commit.parents) == 0


def sync_branches(repo: git.Repo) -> None:
    """Fetch updates for 'main' and the current branch without switching branches."""
    remote = repo.remote(name="origin")
    remote.fetch()
    if "main" in repo.heads:
        repo.git.fetch("origin", "main")
    current_branch = repo.active_branch.name
    if current_branch != "main":
        repo.git.fetch("origin", current_branch)


class RepoContext:
    """Provides a global context for accessing the current Git repository path."""

    _stack: ClassVar[list[Path]] = []
    _warned = False

    @classmethod
    @contextmanager
    def set(cls, path: str | Path) -> Iterator[None]:
        """
        Context manager to temporarily set the repository path. It pushes the given path to the stack and
        restores the previous path when exited.
        :param path: The path to the repository.
        :return: A context manager that yields control to the caller.
        """
        _path = Path(path).resolve()
        if not _path.exists():
            raise ValueError(f"Repository path does not exist: {_path}")
        cls._stack.append(_path)
        try:
            yield
        finally:
            if len(cls._stack) == 0:
                raise RuntimeError(f"{cls.__name__} stack is empty. Cannot pop.")
            cls._stack.pop()

    @classmethod
    def root(cls) -> str:
        """
        Retrieve the current repository working tree dir (i.e. the root).

        :raise RuntimeError: If no repository has been set.
        :raise ValueError: If the stored path no longer exists.
        """
        _tree_dir = cls.repo().working_tree_dir
        assert isinstance(_tree_dir, str | os.PathLike), (
            f"Invalid repository {_tree_dir=} ({type(_tree_dir)})"
        )
        _path: Path = Path(_tree_dir).resolve()
        return str(_path)

    @classmethod
    def repo(cls) -> git.Repo:
        """
        Retrieve the current repository object.

        :raise RuntimeError: If no repository has been set.
        """
        return git.Repo(cls._get_active_path(), search_parent_directories=True)

    @classmethod
    def _get_active_path(cls) -> Path:
        """
        Retrieve the current repository path.

        :raise RuntimeError: If no repository has been set.
        :raise ValueError: If the stored path no longer exists.
        """
        if len(cls._stack) == 0:
            _path = Path(".").resolve()
            return _path
        if not cls._stack[-1].exists():
            raise ValueError(f"Repository path does not exist: {cls._stack[-1]}")
        return cls._stack[-1]


def git_default_author() -> str:
    """Return the default author string using the repository owner's fullname and email."""
    fullname = git_repo_owner_fullname()
    email = git_repo_owner_email()
    return f"{fullname} <{email}>"


@dataclass(slots=True, kw_only=True)
class RepoMetadata:
    """
    Efficient repository metadata with batched git operations.

    Caches expensive operations and derives multiple properties from them.
    """

    _start_dir: str = "."

    def __init__(self, start_dir: str | Path = ".") -> None:
        self._start_dir = Path(start_dir).resolve().as_posix()

    def __repr__(self) -> str:
        """String representation of the repository metadata."""
        return "{class_name}( {public_attrs} )".format(
            class_name=self.__class__.__name__,
            public_attrs=str(self.to_dict()),
        )

    @cached_property
    def _repo(self) -> git.Repo:
        """Get the git repository object."""
        return git.Repo(self._start_dir, search_parent_directories=True)

    @cached_property
    def _config(self) -> dict[str, str]:
        """Cache git config values in one read."""
        config: dict[str, str] = {}
        try:
            reader = self._repo.config_reader()
            with suppress(Exception):
                config["user.name"] = str(reader.get_value("user", "name"))
            with suppress(Exception):
                config["user.email"] = str(reader.get_value("user", "email"))
        except Exception:
            pass
        return config

    @cached_property
    def _remotes(self) -> dict[str, str]:
        """Cache all remote URLs in one operation."""
        return {remote.name: str(remote.url) for remote in self._repo.remotes}

    @cached_property
    def _branch_info(self) -> dict[str, Any]:
        """Cache branch information in one operation."""
        info: dict[str, Any] = {"current": None, "head_detached": False}
        try:
            if self._repo.head.is_detached:
                info["head_detached"] = True
            else:
                info["current"] = str(self._repo.active_branch.name)
        except Exception:
            pass
        return info

    @cached_property
    def _path_info(self) -> dict[str, str | None]:
        """Cache path information."""
        info: dict[str, str | None] = {}
        working_dir = self._repo.working_dir
        git_dir = self._repo.git_dir

        info["working_dir"] = str(working_dir) if working_dir else None
        info["git_dir"] = str(git_dir) if git_dir else None

        if info["working_dir"]:
            info["name"] = Path(info["working_dir"]).name
        else:
            info["name"] = None
        return info

    # === Derived properties from cached data ===

    @property
    def name(self) -> str | None:
        """Repository name from directory."""
        return self._path_info["name"]

    @property
    def working_dir(self) -> str | None:
        """Repository working directory."""
        return self._path_info["working_dir"]

    @property
    def git_dir(self) -> str:
        """Git directory path."""
        git_dir = self._path_info["git_dir"]
        return git_dir if git_dir is not None else str(self._repo.git_dir)

    @property
    def origin_url(self) -> str | None:
        """Origin remote URL."""
        return self._remotes.get("origin")

    @property
    def remotes(self) -> dict[str, str]:
        """All remote URLs."""
        return self._remotes.copy()  # Return copy to prevent mutation

    @property
    def current_branch(self) -> str | None:
        """Current branch name."""
        return self._branch_info["current"]

    @property
    def is_head_detached(self) -> bool:
        """Whether HEAD is detached."""
        return self._branch_info["head_detached"]

    @property
    def user_name(self) -> str | None:
        """Git user name from config."""
        return self._config.get("user.name")

    @property
    def user_email(self) -> str | None:
        """Git user email from config."""
        return self._config.get("user.email")

    @cached_property
    def owner(self) -> str | None:
        """Repository owner parsed from origin URL."""
        origin_url = self.origin_url
        if not origin_url:
            return None
        ssh_match = re.search(r"git@[^:]+:([^/]+)/", origin_url)
        if ssh_match:
            return ssh_match.group(1)
        # eg. HTTPS: https://github.com/owner/repo.git
        if origin_url.startswith(("https://", "http://")):
            parsed = urlparse(origin_url)
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[0]

        return None

    @cached_property
    def web_url(self) -> str | None:
        """Web URL for repository."""
        origin = self.origin_url
        if not origin:
            return None

        # Convert SSH to HTTPS
        ssh_match = re.search(r"git@([^:]+):([^/]+)/(.+?)(?:\.git)?$", origin)
        if ssh_match:
            host, owner, repo = ssh_match.groups()
            return f"https://{host}/{owner}/{repo}"

        # Clean up HTTPS
        if origin.startswith(("https://", "http://")):
            return origin.replace(".git", "") if origin.endswith(".git") else origin

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert repository metadata to a dictionary."""
        _public_attr_names = [
            _name for _name in _attr_names_from_class(self.__class__) if not _name.startswith("_")
        ]
        _public_attrs_dict: dict[str, Any] = {
            _name: getattr(self, _name) for _name in _public_attr_names
        }
        return _public_attrs_dict


def _attr_names_from_class(
    class_: type[object], *, include_inherited: bool = False
) -> tuple[str, ...]:
    """
    Return public attribute/property names in a stable, definition order.

    :param class_: The class to inspect (must be a class type).
    :param include_inherited: If True, scan base classes (MRO) as well.
    :return: Tuple of public names suitable for dict/str serialization.
    """
    _field_names: list[str] = [f.name for f in fields(class_)] if is_dataclass(class_) else []
    _class_defs = (
        [c for c in reversed(class_.__mro__) if hasattr(c, "__dict__")]
        if include_inherited
        else [class_]
        if hasattr(class_, "__dict__")
        else []
    )
    _property_names: list[str] = [
        _attr_name
        for _class_def in _class_defs
        for _attr_name, _attr_def in _class_def.__dict__.items()
        if isinstance(_attr_def, (property, cached_property))
    ]
    _deduped_attr_names = {*_field_names, *_property_names}
    return tuple(_deduped_attr_names)


# End of file: python/plib_/base/git_helpers.py
