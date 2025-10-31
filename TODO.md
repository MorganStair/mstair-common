<!-- version: 2025-10-16-a -->

# TODO.md — Copilot Execution Version (GPT‑4.1 Safe)

This file is formatted for **GitHub Copilot** (GPT‑4.1 and weaker variants).
It removes inline @mentions to improve patch reliability. Each actionable step includes a comment tag `<!-- @copilot-action:... -->`.

---

## ✅ Step Markers

- `[x]` → Done (implemented and verified)
- `[-]` → In Progress (currently being changed or tested)
- `[ ]` → Not Started (no change yet)

Never invent new markers.

---

## 🔁 Copilot Workflow Rules

1. Read all unchecked `[ ]` steps and summarize what must be done.
2. Mark a step as `[-]` when starting work.
3. After completing and testing, mark `[x]`.
4. If a change affects APIs or user‑visible behavior, increment the patch version in `pyproject.toml` (e.g., `1.2.3 → 1.2.4`).
5. Always activate the environment first.

```powershell
.venv/Scripts/Activate.ps1
```

---

## Namespaces and Packaging Compliance

- [ ] Update `setup.py` to use `find_namespace_packages(where="src")` <!-- @copilot-action:edit -->

- [ ] Confirm `find_namespace_packages(where="src")` used in setup <!-- @copilot-action:verify -->


## Refactor and API Cleanup Plan

**Recommendation:**

- Keep root setup in a “config” module (public), not as CoreLogger methods. Provide a thin alias for ergonomics:
  - Public: `setup_root(level=...)`, `setup_root_from_env(app_name=...)`
  - Internals: `_initialize_root`, `_initialize_root_from_environment` (private)
  - Optionally export classmethod aliases that delegate to config, but mark them as convenience only.
- Reduce CoreLogger “bloat”:
  - Keep: `findCaller` override (core), `prefix_with` context manager (useful), `trace/construct` custom levels (if used; otherwise consider deprecating CONSTRUCT)
  - Consider moving or deprecating: `rebind_stream` (move to utility or document a recipe), `sys_excepthook` property (move to “extras” utility or keep documented but not front-and-center)
  - Tighten kwargs guardrails (already done) and keep `log()` minimal; avoid adding helpers that drift beyond structured logging.
- Rename to reflect environment auto-config:
  - Package: `xlogging` → `envlog` or `logenv` (emphasizes environment-driven config). Keep `xlogging` as a compat alias for a deprecation window.
  - Modules:
    - `core_logger.py` → `logger.py`
    - `logger_formatter.py` → `formatter.py`
    - `logger_util.py` → `config.py`
    - `logger_factory.py` → `factory.py` (or fold into logger.py as `get_logger`)
    - `frame_analyzer.py` → `_frames.py` (private)
    - `constants.py` stays public
  - Public API (clean):
    ```python
    from mstair.common.envlog import (
        CoreLogger, CoreFormatter,
        get_logger, setup_root, setup_root_from_env,
        LogLevelConfig, TRACE, CONSTRUCT, SUPPRESS,
    )
    ```
- Simplify and consolidate:
  - Fold factory into logger (`get_logger`) unless you need separate indirection.
  - Merge color formatting into formatter as an optional style or subclass; avoid an extra top-level module if behavior is small.
  - Keep `LOG_LEVELS` and `LOG_ROOT_LEVELS` DSLs but document clearly that only the latter drives the root threshold (via `setup_root_from_env`).
- Back-compat and migration:
  - Add deprecation-friendly shims (old names import new) for one minor release.
  - Update `__init__.py` to export the cleaner API; stop exporting tests from the package.
  - Add short “How to use” docstrings at the top of `logger.py` and `config.py` with 2–3-line examples.

**Net outcome:**

- CoreLogger stays lean and focused.
- Bootstrap lives in config as explicit, data-driven, and opt-in.
- Names and layout match logging developers’ expectations while preserving your environment-first design.

---

## Quick Command Reminders

- Activate env: `.venv/Scripts/Activate.ps1`
- Lint: `python -m ruff check --fix`
- Format: `python -m ruff format`
- Typecheck: `mypy src`
- Test: `pytest`

---

## Notes for Copilot

- Use ASCII characters only. No Unicode, no emojis, no long dashes, etc.
- Never modify unrelated files.
- Always work in `src/mstair/common/`.
- Preserve formatting and anchors.
- Do not re‑explain PEP 420; compliance is satisfied when all tasks `[x]`.

# End of file: TODO.md
