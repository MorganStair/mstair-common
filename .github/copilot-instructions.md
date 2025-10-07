# mstair-common – AI Implementation Guide

Primary mission: provide shared utilities that downstream projects pull in via a VCS dependency (`mstair-common @ git+https://github.com/MorganStair/mstair-common.git@main`) rather than as a standalone app.

## Architecture quick tour

- This repo owns the regular package `mstair` and re-exports `mstair.common`; the root package now has an `__init__.py` so downstream tooling treats the distribution like a standard library.
- Downstream apps consume it via VCS dependencies, e.g. `mstair-common @ git+https://github.com/MorganStair/mstair-common.git@main` under `[project].dependencies` in their `pyproject.toml`.
- `mstair.common.base` groups import-safe utilities (filesystem, env detection, string helpers). When adding helpers keep them side-effect free because high level code imports `base.*` at module import time.
- `mstair.common.xlogging` delivers the logging stack: `CoreLogger`, environment-driven level config (`logger_util`), and formatters. Prefer `create_logger(__name__)` from `logger_factory`.
- `mstair.common.xdumps` renders structured diagnostics; `xdumps()` plus `CUSTOMIZER` helpers keep logs readable and protect against recursion.
- `format_helpers.format_source_code` wraps Ruff for formatting via stdin to respect repo-level config; tests mock `subprocess.run` (`test_format_helpers.py`).
- Tests live alongside packages under `src/.../test_*.py`; pytest config in `pyproject.toml` limits discovery to these folders.

## Logging + diagnostics patterns

- Always initialize module loggers via `create_logger(__name__)`; core logger automatically respects env overrides (see `LOG_LEVEL*` parsing in `xlogging/logger_util.py`).
- Use `CoreLogger.prefix_with()` for scoped prefixes instead of string concatenation.
- For structured messages pass complex objects directly; `CoreLogger.log()` will route through `xdumps` so you get safe reprs without manual `json.dumps`.
- When adding new log levels or formatting tweaks, update both `logger_constants.py` and the pytests in `xlogging/test_logger_util.py`.

## Formatting, typing, and style

- Ruff is the single source of truth: run `python -m ruff check --fix` and `python -m ruff format`. Respect CRLF endings enforced in `ruff.toml`.
- Keep the `# End of file:` sentinel comment that closes every module; `tokenize_helpers.CodeRegions` relies on it when splitting sources.
- Type checking is strict (`mypy.ini`, `pyrightconfig.json`); prefer precise typing and reuse aliases from `base/types.py`.
- Keep source modules under `src/mstair/common/`; both `src/mstair/py.typed` and `src/mstair/common/py.typed` ship with the wheel so Pyright/Pylance pick up inline types without separate stub wheels.

## Developer workflows

- Python 3.13 is required (`[project] requires-python`); create the venv with `make venv-reset` or activate `.venv` before running tools.
- Typical edit loop:
  1. Install: `pip install -e .[dev,test]` (Make target `build` handles activation).
  2. Lint/format: `python -m ruff check --fix` then `python -m ruff format`.
  3. Type check: `python -m mypy src`.
  4. Tests: `pytest` (uses `-q --maxfail=5` defaults).
- If you regenerate stubs, write them directly into `src/mstair/common/*.pyi` (or prefer inline annotations) so they ship with the package.
- `makefile-rules.mak` forces `bash` from Git for Windows; run `make` commands from an environment where that shell is available.

## Current status

- Editable installs and built wheels now ship the same layout (`mstair/__init__.py`, `py.typed`, inline annotations). Pyright/Pylance consume inline types directly; only generate `.pyi` stubs if you have a concrete reason to keep them, and commit them under `src/mstair/common/` if you do.

## Coding cues & gotchas

- Reuse `normalize_helpers.normalize_lines` when manipulating source snippets; downstream tooling expects trimmed CRLF-aware output.
- `base.config` uses thread-local flags; prefer context managers like `analysis_mode_context()` over manually toggling globals.
- When dealing with filesystem paths, favor helpers in `base.fs_helpers` (`fs_safe_relpath`, `fs_find_project_root`) to keep Windows compatibility.
- Git metadata helpers (`base.git_helpers.RepoMetadata`) cache expensive calls—clean up context-sensitive values via the provided context manager instead of re-querying Git directly.
- Tests expect logging and xdumps to avoid real subprocess/network calls; follow the mocking patterns in existing tests when adding new behaviors.
