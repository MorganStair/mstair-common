"""
Tests for the common_version_bump helper module.

Example:
    >>> # Run a subset of tests:
    >>> # .venv\\Scripts\\Activate.ps1; pytest -k test_bump_version_basic
"""

from __future__ import annotations

import importlib.util
import os
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import pytest


SCRIPT_PATH = "bin/common_version_bump.py"

STUB_RESET_SCRIPT = r"""#!/usr/bin/env python
from __future__ import annotations
import re
from pathlib import Path

def read_version(p: Path) -> str:
    in_proj = False
    for raw in p.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line.startswith('[') and line.endswith(']'):
            in_proj = line.lower() == '[project]'
            continue
        if in_proj:
            m = re.match(r"^version\s*=\s*(['\"])([^'\"]+)\1", line)
            if m:
                return m.group(2)
    raise SystemExit(2)

def upsert_version(p: Path, version: str) -> None:
    text = p.read_text(encoding='utf-8') if p.exists() else ''
    if re.search(r'^__version__\s*=\s*', text, re.M):
        text = re.sub(r'^__version__\s*=\s*["\'][^"\']+["\']', f'__version__ = "{version}"', text, flags=re.M)
    else:
        text = (text.rstrip() + '\n\n' if text else '') + f'__version__ = "{version}"\n'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

def main() -> None:
    version = read_version(Path('pyproject.toml'))
    for rel in [Path('src/foo/__init__.py'), Path('src/foo/bar/__init__.py')]:
        upsert_version(rel, version)

if __name__ == '__main__':
    main()
"""


def _load_module() -> ModuleType:
    """Load the common_version_bump module from the adjacent file."""
    location: Path = Path(os.environ.get("VIRTUAL_ENV", ".")).resolve().parent / SCRIPT_PATH
    name = location.stem.removesuffix(".py")
    spec: ModuleSpec | None = importlib.util.spec_from_file_location(name=name, location=location)
    if not spec:
        raise ImportError(f"Cannot load module from {location}")
    module: ModuleType = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Provide a loaded module with PYPROJECT and CHANGELOG redirected to a temp workspace."""
    m = _load_module()
    # Redirect default files into a temp workspace for isolation
    monkeypatch.setattr(m, "PYPROJECT", tmp_path / "pyproject.toml", raising=False)
    monkeypatch.setattr(m, "CHANGELOG", tmp_path / "CHANGELOG.md", raising=False)
    monkeypatch.chdir(tmp_path)
    return m


def test_bump_version_basic(mod: ModuleType) -> None:
    """Bumping numeric patch or minor behaves as expected."""
    assert mod.bump_version("1.2.3") == "1.2.4"
    assert mod.bump_version("2.0") == "2.1"


def test_bump_version_no_numeric(mod: ModuleType) -> None:
    """When no numeric part present, append .1."""
    assert mod.bump_version("alpha") == "alpha.1"


def test_read_current_version_success(mod: ModuleType, tmp_path: Path) -> None:
    """read_current_version reads the version from a pyproject.toml file."""
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        name = "pkg"
        version = "1.2.3"
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    assert mod.read_current_version(mod.PYPROJECT) == "1.2.3"


def test_read_current_version_missing_file_raises(mod: ModuleType) -> None:
    """Missing pyproject.toml raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        mod.read_current_version(mod.PYPROJECT)


def test_read_current_version_missing_version_raises(mod: ModuleType, tmp_path: Path) -> None:
    """Missing version key raises ValueError."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mod.read_current_version(mod.PYPROJECT)


def test_update_pyproject_version_updates_and_idempotent(mod: ModuleType, tmp_path: Path) -> None:
    """update_pyproject_version updates the version line and is idempotent."""
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        version = "0.9.9"  # pin
        """.strip()
        + "\n",
        encoding="utf-8",
    )
    assert mod.update_pyproject_version("1.0.0", mod.PYPROJECT) is True
    text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.0.0"  # pin' in text

    # Idempotent second pass
    assert mod.update_pyproject_version("1.0.0", mod.PYPROJECT) is False


def test_update_pyproject_version_missing_line_raises(mod: ModuleType, tmp_path: Path) -> None:
    """If no version line present, updating raises ValueError."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mod.update_pyproject_version("1.2.3", mod.PYPROJECT)


def test_find_version_commit_prefers_string_search(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """find_version_commit prefers exact string search (-S)."""

    def fake_run_git(args: list[str]) -> str:
        if "-S" in args:
            return "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)
    assert mod.find_version_commit("1.2.3") == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_find_version_commit_fallback_regex(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If -S fails, find_version_commit falls back to regex (-G)."""

    def fake_run_git(args: list[str]) -> str:
        if "-S" in args:
            return ""  # simulate not found
        if "-G" in args:
            return "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)
    assert mod.find_version_commit("1.2.3") == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def test_find_version_commit_none_on_errors(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Errors from git cause find_version_commit to return None."""

    def fake_run_git(args: list[str]) -> str:
        raise RuntimeError("git failed")

    monkeypatch.setattr(mod, "_run_git", fake_run_git)
    assert mod.find_version_commit("1.2.3") is None


def test_collect_src_commit_messages_since_ranges_and_parsing(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """collect_src_commit_messages_since builds the correct range and parses messages."""
    recorded: dict[str, list[str]] = {}

    def fake_run_git(args: list[str]) -> str:
        recorded["args"] = args
        return "feat: A\n\nfix: B \n"

    monkeypatch.setattr(mod, "_run_git", fake_run_git)
    msgs = mod.collect_commit_messages_since("abc1234")
    assert "abc1234..HEAD" in recorded["args"]
    assert msgs == ["feat: A", "fix: B"]


def test_prepend_changelog_entry_prepends(mod: ModuleType, tmp_path: Path) -> None:
    """prepend_changelog_entry inserts entries at the top preserving existing content."""
    # Start with existing content
    (tmp_path / "CHANGELOG.md").write_text("Existing\n", encoding="utf-8")
    today = __import__("datetime").date.today().isoformat()

    mod.prepend_changelog_entry(version="1.2.3", combined_comment="first")
    mod.prepend_changelog_entry(version="1.2.4", combined_comment="second")

    text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.splitlines()[0] == f"## 1.2.4 - {today}"
    assert f"## 1.2.3 - {today}" in text
    assert text.endswith("Existing\n")


def test_happy_path_bumps_and_writes_files(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() performs a happy-path bump and writes updated files."""
    # Prepare pyproject
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        name = "pkg"
        version = "1.2.3"
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_run_git(args: list[str]) -> str:
        if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
            return "true\n"
        if args[:2] == ["log", "-n"] and "-S" in args and "--pretty=%H" in args:
            return "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
        if args[:1] == ["log"] and "--pretty=%s" in args:
            return "feat: add something\n"
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    rc = mod.common_version_bump_main([])
    assert rc == 0

    # Version bumped
    assert mod.read_current_version(mod.PYPROJECT) == "1.2.4"

    # Changelog created with commit message
    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "feat: add something" in changelog

    out = capsys.readouterr().out
    assert "Current version: 1.2.3" in out
    assert "Next version:    1.2.4" in out


def test_delegates_to_reset_inits_and_updates_inits(
    mod: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """common_version_bump_main() delegates to reset_inits to sync __init__ versions.

    We stub a lightweight reset script under ./bin/common_reset_inits.py that reads the
    bumped version from pyproject and applies it to both top-level and nested packages.
    """
    # Prepare workspace structure
    (tmp_path / "bin").mkdir()
    (tmp_path / "src" / "foo").mkdir(parents=True)
    (tmp_path / "src" / "foo" / "bar").mkdir(parents=True)

    # Initial pyproject with current version
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        name = "pkg"
        version = "1.2.3"
        """.strip()
        + "\n",
        encoding="utf-8",
    )

    # Pre-existing init files
    (tmp_path / "src" / "foo" / "__init__.py").write_text("# top-level init\n", encoding="utf-8")
    (tmp_path / "src" / "foo" / "bar" / "__init__.py").write_text(
        "# nested init\n", encoding="utf-8"
    )

    # Stub reset script that mirrors the delegation behavior expected

    (tmp_path / "bin" / "common_reset_inits.py").write_text(STUB_RESET_SCRIPT, encoding="utf-8")

    # Git stubs
    def fake_run_git(args: list[str]) -> str:
        if args[:2] == ["rev-parse", "--is-inside-work-tree"]:
            return "true\n"
        if args[:2] == ["log", "-n"] and "-S" in args and "--pretty=%H" in args:
            return "cafebabecafebabecafebabecafebabecafebabe\n"
        if args[:1] == ["log"] and "--pretty=%s" in args:
            return "chore: testing delegation\n"
        return ""

    monkeypatch.setattr(mod, "_run_git", fake_run_git)

    # Execute bump without specifying next version (1.2.3 -> 1.2.4)
    rc = mod.common_version_bump_main([])
    assert rc == 0

    # Verify stub ran and updated both init files to bumped version
    top_init = (tmp_path / "src" / "foo" / "__init__.py").read_text(encoding="utf-8")
    nested_init = (tmp_path / "src" / "foo" / "bar" / "__init__.py").read_text(encoding="utf-8")
    assert '__version__ = "1.2.4"' in top_init
    assert '__version__ = "1.2.4"' in nested_init
