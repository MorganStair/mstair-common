# File: src/mstair/common/vscode_settings_diff.py
"""
Compare VS Code user and workspace settings for overlapping keys.

This script compares VS Code's user `settings.json` and a workspace
`.code-workspace` file, listing configuration keys that appear in both.
Optionally, it can display each setting's values side-by-side.

Usage:
    python vscode_settings_diff.py [--user PATH] [--workspace PATH] [--show-values]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import json5


__all__ = [
    "load_jsonc_file",
    "default_user_settings_path",
    "find_workspace_file",
    "compare_settings",
    "main",
]


def load_jsonc_file(path: Path) -> dict[str, Any]:
    """
    Load a JSONC (JSON5) file into a Python dictionary.

    This uses the `json5` package, which supports:
    - Single-line (//) and block (/* ... */) comments
    - Trailing commas
    - Unquoted keys
    - Single-quoted strings

    Args:
        path: Path to the JSONC or JSON5 file.

    Returns:
        A dictionary representing the parsed JSONC file.

    Raises:
        ValueError: If the file does not contain a JSON object.
    """
    with path.open(encoding="utf-8") as f:
        data = json5.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Top-level structure in {path} must be a JSON object.")
    return data


def default_user_settings_path() -> Path:
    """
    Return the default VS Code user settings path for this platform.
    """
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "Code" / "User" / "settings.json"
    return Path.home() / ".config" / "Code" / "User" / "settings.json"


def find_workspace_file(arg: str | None) -> Path:
    """
    Determine the workspace file path.

    - If `arg` is given, use it directly.
    - Otherwise, prefer one matching the current directory name.
    - Fallback to the first `*.code-workspace` file in the CWD.
    """
    if arg:
        return Path(arg).resolve()

    cwd = Path.cwd()
    expected = cwd / f"{cwd.name}.code-workspace"
    if expected.is_file():
        return expected.resolve()

    files = sorted(cwd.glob("*.code-workspace"))
    if not files:
        raise FileNotFoundError("No .code-workspace file found in current directory.")
    return files[0].resolve()


def compare_settings(
    user_settings: dict[str, Any],
    workspace_settings: dict[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    """
    Compare settings between user and workspace configurations.

    Returns:
        (common_keys, only_user_keys, only_workspace_keys)
    """
    user_keys = set(user_settings)
    ws_keys = set(workspace_settings)
    return user_keys & ws_keys, user_keys - ws_keys, ws_keys - user_keys


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="Compare VS Code user and workspace settings.")
    parser.add_argument(
        "--user",
        type=str,
        help="Path to user settings.json (default: platform default)",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        help="Path to .code-workspace file (default: inferred from CWD)",
    )
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="Show user and workspace values for common keys.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """
    Command-line interface entry point.
    """
    args = parse_args(argv)
    user_path = Path(args.user).resolve() if args.user else default_user_settings_path()
    ws_path = find_workspace_file(args.workspace)

    if not user_path.is_file():
        print(f"ERROR: User settings not found: {user_path}", file=sys.stderr)
        return 2
    if not ws_path.is_file():
        print(f"ERROR: Workspace file not found: {ws_path}", file=sys.stderr)
        return 2

    try:
        user_settings = load_jsonc_file(user_path)
        workspace_json = load_jsonc_file(ws_path)
        workspace_settings = workspace_json.get("settings", {})
        if not isinstance(workspace_settings, dict):
            raise ValueError("'settings' section missing or invalid")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: Failed to load settings: {exc}", file=sys.stderr)
        return 3

    common, _only_user, _only_ws = compare_settings(user_settings, workspace_settings)
    print(f"# Common keys ({len(common)}):")
    for key in sorted(common, key=str.lower):
        print(key)

    if args.show_values:
        print("\n# Values for common keys:")
        for key in sorted(common, key=str.lower):
            u_val = user_settings.get(key)
            w_val = workspace_settings.get(key)
            u_str = json.dumps(u_val, ensure_ascii=False, default=repr)
            w_str = json.dumps(w_val, ensure_ascii=False, default=repr)
            print(f"- {key}:\n  user: {u_str}\n  work: {w_str}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# End of file: src/mstair/common/vscode_settings_diff.py
