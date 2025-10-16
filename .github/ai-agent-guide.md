# mstair-common – guide for AI copilots

Purpose: shared utilities consumed via VCS dependency, not a standalone app. Root package `mstair` re-exports `mstair.common` (see `src/mstair/__init__.py`).

## Working style expectations

-   Always stage changes with unit intent; run `python -m ruff check --fix`, `python -m ruff format`, and `mypy src` before proposing a patch. `make lint` and `make typecheck` mirror these if you prefer the makefile targets.
-   Run `pytest` locally for behavioural changes; add targeted tests under `src/**/test_*.py` when you touch logic.
-   Avoid network or long-running subprocess calls inside tests—prefer monkeypatching and the patterns from `xlogging/test_logger_util.py` and `src/mstair/common/test_format_helpers.py`.
-   Windows paths are common; lean on helpers in `mstair.common.base.fs_helpers` instead of manual `os.path` handling.

## Big picture

-   Packages: `base/` (side-effect-free helpers), `xlogging/` (CoreLogger + env config), `xdumps/` (safe object rendering), plus formatting/tokenization helpers under `src/mstair/common/`.
-   Keep `base.*` import-safe; high-level code imports these at module import time. Use thread-local flags/context managers from `base.config`.
-   Modules end with a `# End of file:` sentinel; `tokenize_helpers.CodeRegions` relies on it when splitting sources.

## Repository map

-   `src/mstair/`: public package surface (`__init__.py` re-exports `mstair.common`).
-   `src/mstair/common/base`: generic helpers, safe to import anywhere.
-   `src/mstair/common/xlogging`: logging stack, includes `logger_factory` and formatters.
-   `src/mstair/common/xdumps`: safe object rendering and customizers.
-   `.cache/`, `.pytest_cache/`: generated; treat as opaque.
-   `tools/`: auxiliary scripts invoked from make targets; avoid altering unless requested.

## Developer loop (Python 3.13)

-   Install editable: pip install -e .[dev,test] (or `make build`).
-   Lint/format: python -m ruff check --fix; python -m ruff format. Use `make lint` for both steps.
-   Type check: mypy src (strict per `mypy.ini`, stubPath `.cache/typings` in `pyrightconfig.json`). Shortcut: `make typecheck`.
-   Tests: pytest (quiet, maxfail=5 from `pyproject.toml`; tests live under `src/**/test_*.py`). For fast focus, pass `-k` expressions.
-   Stubs (optional): `make stubs` writes to `.cache/typings`; ship inline types + `py.typed` in `src/mstair/` and `src/mstair/common/`.

## Logging and diagnostics (xlogging + xdumps)

-   Create loggers via `from mstair.common.xlogging.logger_factory import create_logger`; `logger = create_logger(__name__)`.
-   Levels via env: `LOG_LEVELS="pkg.*:DEBUG; root=INFO"`, `LOG_LEVEL_ROOT=WARNING`, `LOG_LEVEL_MYAPP_CORE=ERROR` (see `xlogging/logger_util.py` for precedence: exact > ancestor > glob > default > fallback). Tests: `xlogging/test_logger_util.py`.
-   CoreLogger features: `logger.prefix_with("init")`, `logger.construct(Type, "id", {"k": 1})`, `logger.exception(...)` adds stack info. Don’t attach handlers to per-module loggers; root is initialized idempotently and uses `CoreFormatter`.
-   Pass complex objects directly; CoreLogger serializes non-primitives via `xdumps()` with cycle-safe, width/depth-limited formatting. Customizers in `xdumps/customizer_registry.py` (e.g., `CUSTOMIZER.max_container_width/depth`, `wrap_derived_class_instances`, `libpath_path_as_posix`).

## Formatting and tokenization

-   Use `mstair.common.format_helpers.format_source_code(text=str, target=Path)` to ruff-sort imports and format via stdin with `--stdin-filename` (preserves original line endings). Tests: `test_format_helpers.py` monkeypatch `subprocess.run`.
-   Normalize textual snippets with `base.normalize_helpers.normalize_lines(...)` to trim and keep line ending awareness.
-   `tokenize_helpers.CodeRegions.regions_from_code()` splits header/docstring/body/footer; footer is the first trailing comment block starting at `# End of file:` line.
-   When adding new modules, include a trailing comment block that starts with `# End of file:` and keep a terminating newline so tokenization stays reliable.

## Conventions and helpers

-   Filesystem: prefer `base.fs_helpers` (`fs_find_project_root`, `fs_safe_relpath`, `fs_load_dotenv`, redirection/context helpers) for Windows compatibility.
-   Environment/context: use `base.config.analysis_mode_context()` to suppress side effects; `in_test_mode()/in_desktop_mode()/in_lambda()` are thread-local overrideable.
-   Tests should avoid real subprocess/network I/O; follow patterns in `xlogging/test_logger_util.py` and `test_format_helpers.py` (monkeypatch, caplog).

## Troubleshooting tips

-   Ruff, mypy, and pytest respect the repo’s root; run them from the project root or via `make` to pick up config files (`ruff.toml`, `mypy.ini`, `pyproject.toml`).
-   If formatting via `format_source_code` fails, ensure the `python -m ruff` tooling is installed in the active environment; helpers expect the executable on `PATH`.
-   For logging issues, inspect `mstair.common.xlogging.logger_util` to trace level resolution order (exact > ancestor > glob > default > fallback).
-   If type stubs go stale, clear `.cache/typings` and regenerate with `make stubs`.

If anything above is unclear or missing for your task, tell me what you're implementing and I'll extend these rules with concrete pointers to the relevant modules.
