# TODO.md — Copilot Execution Version (For Weak Models)

This file is formatted for **GitHub Copilot** running weak or limited-context models (GPT-4o-mini, GPT-5-mini, etc.).

Each step has explicit commands and @copilot triggers.
Copilot must **not summarize, skip, or reorder steps**.
Copilot must perform exactly one step at a time.

---

## ✅ Step Markers

- `[x]` → Done (code implemented and verified)
- `[-]` → In Progress (actively editing or testing)
- `[ ]` → Not Started (no change made yet)

Never invent new markers.

---

## 🔁 Copilot Workflow Rules

1. **@copilot plan** — Read all unchecked `[ ]` steps and describe what must be done, one bullet per step.
2. **@copilot start** — Pick one unchecked `[ ]` step and begin implementation.
3. **@copilot test** — After each implementation, run or describe relevant tests.
4. **@copilot verify** — Confirm the step works; if yes, mark `[x]`.
   If not, explain what failed and keep it `[-]`.
5. **@copilot bump** — If the change affects APIs or behavior, increase the **patch version** in `pyproject.toml`.
   Example: `1.2.3 → 1.2.4`.
6. **@copilot review** — Summarize remaining unchecked `[ ]` items once per session.

Copilot must always activate the Python environment first:

```powershell
.venv/Scripts/Activate.ps1
```

---

# 🧩 Conversion: True Namespace Package `mstair.common`

Follow stages in order.
Stop after any failed test.

---

## Stage 1 — Directory and File Layout

- [x] Code is in `src/mstair/common/`
- [ ] @copilot delete `src/mstair/__init__.py` (namespace must have no init)
- [ ] @copilot run all tests to confirm imports still work
- [x] Confirm `src/mstair/common/__init__.py` exists (regular package)
- [x] Confirm `py.typed` exists in both `src/mstair/` and `src/mstair/common/`

---

## Stage 2 — Packaging Metadata

- [ ] @copilot open `setup.py` and ensure this code exists:

  ```python
  packages=find_namespace_packages(where="src")
  ```

- [x] Confirm `package_dir={"": "src"}` in `setup.py` or `pyproject.toml`
- [x] Confirm `MANIFEST.in` includes `py.typed`

---

## Stage 3 — Type Checking

- [x] Confirm `py.typed` in `src/mstair/common/`
- [x] Confirm `mypy.ini` or `pyrightconfig.json` exist

---

## Stage 4 — Tests & Linting

- [x] Ensure test files exist: `src/mstair/common/test_*.py`
- [x] Confirm configs exist for `ruff`, `mypy`, and `pyright`

---

## Stage 5 — Namespace Compliance

- [ ] @copilot verify no `__init__.py` exists in `src/mstair/`
- [x] Confirm `src/mstair/common/__init__.py` exists

---

## Stage 6 — Distribution Setup

- [ ] @copilot confirm `find_namespace_packages(where="src")` used in setup
- [x] Confirm `mstair_common.egg-info/` directory exists

---

## 📊 Completion Criteria

Task is complete when:
- All `[ ]` steps are marked `[x]`
- Tests and packaging succeed
- Version patch is incremented if user-visible changes occurred

---

## Quick Command Reminders

- `@copilot plan` — List next unchecked step.
- `@copilot fix` — Implement that step.
- `@copilot verify` — Run or describe tests.
- `@copilot bump` — Increment patch version if needed.
- `@copilot review` — Show remaining `[ ]` tasks.

---

## Notes for Copilot

- Never modify unrelated files.
- Always work in `src/mstair/common/`.
- Always confirm environment activation.
- Do not re-explain PEP 420 — it is already satisfied once steps are `[x]`.

---

## Status Summary

Some tasks remain:
- Remove `src/mstair/__init__.py`
- Update `setup.py` to use `find_namespace_packages`
- Retest build and confirm import paths

When complete, the project will be a **PEP 420 namespace package**.
