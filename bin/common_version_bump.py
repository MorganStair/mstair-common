#!/usr/bin/env python
# -*- mode: python; eol-unix -*-
"""
Create the next-version changelog entry and update the project version.

Example:
    $ python bin/common_version_bump.py
    $ python bin/common_version_bump.py 1.2.4

Details:
    - Reads current version from `pyproject.toml` `[project].version`.
    - If `next_version` is omitted, increments the last numeric component
      of the current version (e.g., 1.2.3 -> 1.2.4).
    - Locates the commit where the current version was introduced.
    - Collects commit messages for changes under `./src` since that commit.
    - Prepends a new entry to `CHANGELOG.md` and updates `pyproject.toml`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path
from typing import Final


# --------------------------------------------------------------
# Section: Module-level constants and configuration
# --------------------------------------------------------------
PYPROJECT: Final[Path] = Path("pyproject.toml")
CHANGELOG: Final[Path] = Path("CHANGELOG.md")

# --------------------------------------------------------------
# Section: Type definitions and dataclasses
# --------------------------------------------------------------
# (none)

# --------------------------------------------------------------
# Section: Main public API
# --------------------------------------------------------------


__all__ = [
    "common_version_bump_main",
    "read_current_version",
    "bump_version",
    "find_version_commit",
    "collect_commit_messages_since",
    "prepend_changelog_entry",
    "update_pyproject_version",
    "_maybe_reset_inits",
]


def common_version_bump_main(argv: list[str]) -> int:
    """Generate a changelog entry and bump the project version.

    Args:
        argv: Command-line arguments excluding program name.

    Returns:
        Process exit status code.
    """
    parser = argparse.ArgumentParser(description="Generate CHANGELOG entry from src commits.")
    parser.add_argument(
        "next_version", nargs="?", help="Next version string. If omitted, bumps current version."
    )
    args = parser.parse_args(argv)

    _ensure_git_repo()
    current_version = read_current_version()
    next_version = args.next_version or bump_version(current_version)

    last_version_hash = find_version_commit(current_version)
    commit_messages = collect_commit_messages_since(last_version_hash)
    if commit_messages:
        combined = "; ".join(commit_messages)
    else:
        base = last_version_hash[:7] if last_version_hash else "<start>"
        combined = f"No changes in src since {base}."

    prepend_changelog_entry(version=next_version, combined_comment=combined)
    print(f"Current version: {current_version}")
    print(f"Next version:    {next_version}")
    if last_version_hash:
        print(f"Last version at: {last_version_hash}")
    else:
        print("Last version commit not found; used full history.")
    print(f"CHANGELOG updated: {CHANGELOG}")
    try:
        updated = update_pyproject_version(new_version=next_version)
        if updated:
            print("pyproject.toml version updated")
        else:
            print("pyproject.toml already at requested version; no change")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Warning: failed to update pyproject.toml: {exc}", file=sys.stderr)
    # Delegate updating __init__ files' __version__ to common_reset_inits.py
    _maybe_reset_inits()
    return 0


def read_current_version(path: str | Path | None = None) -> str:
    """Return the `[project].version` value from a `pyproject.toml`.

    Args:
        path: Path to the `pyproject.toml` file.

    Returns:
        The version string found in the `[project]` section.
    """
    # Allow callers or tests to override the project file at runtime by
    # passing an explicit path or by monkeypatching the module-level PYPROJECT.
    p = Path(path) if path is not None else Path(PYPROJECT)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")
    in_project = False
    with p.open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                in_project = line.lower() == "[project]"
                continue
            if in_project:
                match = re.match(r"^version\s*=\s*(['\"])([^'\"]+)\1", line)
                if match:
                    return match.group(2)
    raise ValueError("project.version not found in pyproject.toml")


def bump_version(version: str) -> str:
    """Return `version` with its last numeric component incremented.

    If no numeric component exists, appends `.1`.
    """
    parts = version.split(".")
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].isdigit():
            parts[i] = str(int(parts[i]) + 1)
            return ".".join(parts)
    return version + ".1"


def find_version_commit(version: str) -> str | None:
    """Return the commit hash that introduced the given project version.

    First searches using `-S` with the exact version line, then falls back to
    a regex `-G` search. Returns `None` if no commit is found.
    """
    needle = f'version = "{version}"'
    try:
        out = _run_git(["log", "-n", "1", "-S", needle, "--pretty=%H", "--", str(PYPROJECT)])
        if out:
            return out.splitlines()[0].strip()
    except RuntimeError:
        pass
    try:
        regex = rf"^\s*version\s*=\s*\"{re.escape(version)}\""
        out = _run_git(["log", "-n", "1", "-G", regex, "--pretty=%H", "--", str(PYPROJECT)])
        if out:
            return out.splitlines()[0].strip()
    except RuntimeError:
        pass
    return None


def collect_commit_messages_since(base_commit: str | None) -> list[str]:
    """Return commit subjects for changes under `./src` or `./bin` since `base_commit`.

    Args:
        base_commit: The baseline commit hash (exclusive). If `None`, uses the
            repository start.

    Returns:
        A list of commit subject lines (most recent first).
    """
    rev_range = [] if not base_commit else [f"{base_commit}..HEAD"]
    args = ["log", "--no-merges", "--pretty=%s", *rev_range, "--", "src", "bin", "pyproject.toml"]
    try:
        out = _run_git(args)
    except RuntimeError:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def prepend_changelog_entry(
    *,
    version: str,
    combined_comment: str,
    path: str | Path | None = None,
) -> None:
    """Prepend a simple changelog entry for `version`.

    Args:
        version: The next project version string.
        combined_comment: The combined summary of recent commits.
        path: The changelog file to update (default: `CHANGELOG.md`).
    """
    date = _dt.date.today().isoformat()
    header = f"## {version} - {date}\n"
    body = f"- {combined_comment}\n\n"
    entry = header + body
    # Use the provided path, or fall back to the module-level CHANGELOG value.
    p = Path(path) if path is not None else Path(CHANGELOG)
    existing = p.read_text(encoding="utf-8") if p.exists() else ""
    p.write_text(entry + existing, encoding="utf-8", newline="\n")


def update_pyproject_version(
    new_version: str,
    path: str | Path | None = None,
) -> bool:
    """Update `[project].version` in `pyproject.toml` to `new_version`.

    Preserves existing quoting style and trailing content on the version line.

    Args:
        new_version: The version to write.
        path: Path to the `pyproject.toml` file.

    Returns:
        True if the file was changed; False if it already had `new_version`.
    """
    # Use provided path or fall back to the module-level PYPROJECT value so
    # tests that monkeypatch PYPROJECT are supported.
    p = Path(path) if path is not None else Path(PYPROJECT)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found")

    lines = p.read_text(encoding="utf-8").splitlines()

    in_project = False
    changed = False
    for i, raw in enumerate(lines):
        line = raw
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped.lower() == "[project]"
            continue
        if not in_project:
            continue

        match = re.match(
            r"^(?P<indent>\s*)version\s*=\s*(?P<q>['\"])(?P<val>[^'\"]+)(?P=q)(?P<rest>.*)$",
            line,
        )
        if match:
            if match.group("val") == new_version:
                return False
            new_line = f"{match.group('indent')}version = {match.group('q')}{new_version}{match.group('q')}{match.group('rest')}"
            lines[i] = new_line
            changed = True
            break

    if not changed:
        raise ValueError("project.version line not found to update in pyproject.toml")

    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return True


# --------------------------------------------------------------
# Section: Private implementation details
# --------------------------------------------------------------


def _run_git(args: list[str]) -> str:
    """Run a `git` command and return stdout with trailing whitespace trimmed."""
    cmd = ["git", *args]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"git command failed: {' '.join(cmd)}\n{exc.output.decode(errors='replace')}"
        ) from exc
    return out.decode().rstrip()


def _ensure_git_repo() -> None:
    """Raise `RuntimeError` if not inside a git work tree."""
    try:
        inside = _run_git(["rev-parse", "--is-inside-work-tree"]).strip()
    except RuntimeError as exc:
        raise RuntimeError("Not a git repository (cannot run git).") from exc
    if inside.lower() != "true":
        raise RuntimeError("Not inside a git work tree.")


def _maybe_reset_inits() -> None:
    """Run bin/common_reset_inits.py to sync __version__ in __init__.py files.

    Runs only when both `src/` and `bin/common_reset_inits.py` exist in CWD.
    Any failure is reported as a warning but does not abort the bump.
    """
    src = Path("src")
    reset_script = Path("bin/common_reset_inits.py")
    if not (src.exists() and src.is_dir() and reset_script.exists() and reset_script.is_file()):
        return
    try:
        subprocess.run([sys.executable, str(reset_script)], check=True)
    except Exception as exc:  # noqa: BLE001 - best-effort delegation
        print(f"Warning: failed to update __init__ versions via {reset_script}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(common_version_bump_main(sys.argv[1:]))

# End of file: bin/common_version_bump.py
