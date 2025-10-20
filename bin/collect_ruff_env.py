# File: collect_ruff_env.py
"""
Collect VSCode Ruff settings, Ruff configuration, CLI version, and platform details.

This script uses `json5` to parse VSCode settings.json (which supports comments),
detects the active Ruff CLI version, and prints OS/platform information.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import json5


def get_ruff_version() -> str:
    """Return the version string of the installed Ruff CLI."""
    try:
        result = subprocess.run(
            ["ruff", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "ruff executable not found"
    except subprocess.CalledProcessError as exc:
        return f"ruff --version failed: {exc}"


def get_platform_info() -> str:
    """Return detailed platform information."""
    os_name = platform.system()
    release = platform.release()
    version = platform.version()
    arch = platform.machine()
    return f"{os_name} {release} ({version}), arch={arch}"


def find_vscode_settings() -> dict[str, Any]:
    """Locate and parse VSCode settings.json with Ruff-related keys using json5."""
    candidates: list[Path] = []
    home = Path.home()

    # Windows stable and variants
    candidates.append(home / "AppData" / "Roaming" / "Code" / "User" / "settings.json")
    candidates.append(home / "AppData" / "Roaming" / "Code - Insiders" / "User" / "settings.json")
    # Portable and workspace-local
    candidates.append(Path.cwd() / "data" / "user-data" / "User" / "settings.json")
    candidates.append(Path.cwd() / ".vscode" / "settings.json")
    # Linux and macOS
    candidates.append(home / ".config" / "Code" / "User" / "settings.json")
    candidates.append(home / "Library" / "Application Support" / "Code" / "User" / "settings.json")

    for path in candidates:
        if not path.exists():
            continue
        try:
            raw: Any = json5.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                print(f"# Unexpected JSON in {path}: got {type(raw).__name__}", file=sys.stderr)
                continue
            data = cast(dict[str, Any], raw)
            return {k: v for k, v in data.items() if "ruff" in k.lower()}
        except Exception as exc:
            print(f"# Warning: Could not read {path}: {exc}", file=sys.stderr)
    return {}


def find_ruff_config() -> dict[str, Any]:
    """Locate Ruff configuration file (ruff.toml or pyproject.toml) and print its contents."""
    cwd = Path.cwd()
    candidates = [cwd / "ruff.toml", cwd / ".ruff.toml", cwd / "pyproject.toml"]
    for path in candidates:
        if path.exists():
            print(f"# Found config: {path}")
            try:
                print(path.read_text(encoding="utf-8"))
                return {"path": str(path)}
            except Exception as exc:
                print(f"# Warning: Could not read {path}: {exc}", file=sys.stderr)
    print("# No Ruff configuration file found.")
    return {}


def collect_ruff_env_main() -> None:
    """Main entry point."""
    print("# === Ruff Environment Summary ===")

    # Platform and Ruff CLI version
    print(f"# Platform: {get_platform_info()}")
    print(f"# Ruff CLI version: {get_ruff_version()}")

    # VSCode and Ruff configuration
    settings = find_vscode_settings()
    config = find_ruff_config()

    print("\n# --- VSCode Ruff-related settings ---")
    if settings:
        for key, value in settings.items():
            print(f"{key}: {value!r}")
    else:
        print("(no Ruff-related settings found)")

    print("\n# --- Ruff configuration path ---")
    print(config.get("path", "(not found)"))

    print("\n# === End of Summary ===")


if __name__ == "__main__":
    collect_ruff_env_main()

# End of file: collect_ruff_env.py
