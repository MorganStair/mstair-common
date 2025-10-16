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

# 🧩 Conversion: True Namespace Package `mstair.common`

Follow stages in order. Stop after any failed test.

---

<!-- stage:1 -->
## Stage 1 — Directory and File Layout

 - [x] Code is in `src/mstair/common/`
 - [x] Delete `src/mstair/__init__.py` (namespace must have no init) <!-- @copilot-action:delete -->
 - [ ] Run all tests to confirm imports still work <!-- @copilot-action:test -->
 - [x] Confirm `src/mstair/common/__init__.py` exists (regular package)
 - [x] Confirm `py.typed` exists in both `src/mstair/` and `src/mstair/common/`

---

<!-- stage:2 -->
## Stage 2 — Packaging Metadata

- [ ] Update `setup.py` to use `find_namespace_packages(where="src")` <!-- @copilot-action:edit -->
- [x] Confirm `package_dir={"": "src"}` in `setup.py` or `pyproject.toml`
- [x] Confirm `MANIFEST.in` includes `py.typed`

---

<!-- stage:3 -->
## Stage 3 — Type Checking

- [x] Confirm `py.typed` in `src/mstair/common/`
- [x] Confirm `mypy.ini` or `pyrightconfig.json` exist

---

<!-- stage:4 -->
## Stage 4 — Tests & Linting

- [x] Ensure test files exist: `src/mstair/common/test_*.py`
- [x] Confirm configs exist for `ruff`, `mypy`, and `pyright`

---

<!-- stage:5 -->
## Stage 5 — Namespace Compliance

- [ ] Ensure no `__init__.py` exists in `src/mstair/` <!-- @copilot-action:verify -->
- [x] Confirm `src/mstair/common/__init__.py` exists

---

<!-- stage:6 -->
## Stage 6 — Distribution Setup

- [ ] Confirm `find_namespace_packages(where="src")` used in setup <!-- @copilot-action:verify -->
- [x] Confirm `mstair_common.egg-info/` directory exists

---

## 📊 Completion Criteria

Task is complete when:
- All `[ ]` steps are `[x]`
- Tests and packaging succeed
- Version patch incremented if user‑visible changes occurred

---

## Quick Command Reminders

- Activate env: `.venv/Scripts/Activate.ps1`
- Lint: `python -m ruff check --fix`
- Format: `python -m ruff format`
- Typecheck: `mypy src`
- Test: `pytest`

---

## Notes for Copilot

- Never modify unrelated files.
- Always work in `src/mstair/common/`.
- Preserve formatting and anchors.
- Do not re‑explain PEP 420; compliance is satisfied when all tasks `[x]`.

# End of file: TODO.md
