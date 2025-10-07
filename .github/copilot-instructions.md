# mstair-common – AI Implementation Guide

Primary mission: provide shared utilities that downstream projects pull in via a VCS dependency (`mstair-common @ git+https://github.com/MorganStair/mstair-common.git@main`) rather than as a standalone app.

## Architecture quick tour

- This repo contributes the PEP 420 namespace package `mstair.common`; the namespace root (`src/mstair/`) intentionally has no `__init__.py` (see `pyproject.toml` comments).
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
- Namespace packaging means new modules must live under `src/mstair/common/`; add `py.typed` entries only within this subpackage.

## Developer workflows

- Python 3.13 is required (`[project] requires-python`); create the venv with `make venv-reset` or activate `.venv` before running tools.
- Typical edit loop:
  1. Install: `pip install -e .[dev,test]` (Make target `build` handles activation).
  2. Lint/format: `python -m ruff check --fix` then `python -m ruff format`.
  3. Type check: `python -m mypy src`.
  4. Tests: `pytest` (uses `-q --maxfail=5` defaults).
- Generate stubs when touching external deps via `make stubs`; results land in `.cache/typings` and are used by Pyright.
- `makefile-rules.mak` forces `bash` from Git for Windows; run `make` commands from an environment where that shell is available.

## Current status

- Blocking issue: downstream editable installs (`pip install -e .`) give consumers the `mstair.common` sources but not the generated stubs, so Pyright/Pylance resolves types as `Any`. Packaging strategy for the `.cache/typings` output (e.g., syncing into `src/mstair/common` or shipping a stub wheel) is the top priority to unblock dependent apps.

## Coding cues & gotchas

- Reuse `normalize_helpers.normalize_lines` when manipulating source snippets; downstream tooling expects trimmed CRLF-aware output.
- `base.config` uses thread-local flags; prefer context managers like `analysis_mode_context()` over manually toggling globals.
- When dealing with filesystem paths, favor helpers in `base.fs_helpers` (`fs_safe_relpath`, `fs_find_project_root`) to keep Windows compatibility.
- Git metadata helpers (`base.git_helpers.RepoMetadata`) cache expensive calls—clean up context-sensitive values via the provided context manager instead of re-querying Git directly.
- Tests expect logging and xdumps to avoid real subprocess/network calls; follow the mocking patterns in existing tests when adding new behaviors.
