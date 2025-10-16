# TODO.md Usage Workflow

This file tracks project tasks and compliance steps. Use the following conventions and workflow:

## Step Status Markers
- `[x]` — **Completed**: The step is fully done and verified.
- `[-]` — **In Progress**: Work has started but is not yet complete or fully tested.
- `[ ]` — **Not Started**: No work has begun on this step.

## Workflow
1. **Plan**: List all required steps for the task or migration.
2. **Mark as In Progress**: When you begin work on a step, change `[ ]` to `[-]`.
3. **Test**: For each step, perform relevant tests (unit, integration, or manual checks) to verify correctness. Document the test performed in a comment if needed.
4. **Mark as Completed**: Once a step is fully implemented and tested, change `[-]` to `[x]`.
5. **Version Bumping**: If a completed step changes user-facing behavior, public API, or fixes a bug, increment the bugfix (patch) version in `pyproject.toml` (e.g., from `1.2.3` to `1.2.4`).
6. **Review**: Periodically review the TODO.md to ensure all steps are up to date and accurately marked.

---


# TODO: Convert to True Namespace Package "mstair.common"

This checklist breaks down the conversion into stages and steps, with each step marked as completed `[x]`, in progress `[-]`, or not started `[ ]` based on the current project state.

## Stage 1: Directory and File Structure
- [x] Source code is under `src/mstair/common/`
- [ ] Remove `src/mstair/__init__.py` (must be absent for namespace package)
- [ ] Test the codebase and all tests after removing `src/mstair/__init__.py` to ensure nothing breaks
- [x] Ensure `src/mstair/common/__init__.py` exists (regular package, not namespace)
- [x] Ensure `py.typed` exists in both `src/mstair/` and `src/mstair/common/`

## Stage 2: Packaging and Metadata
- [ ] Update `setup.py` to use `find_namespace_packages(where="src")`
- [x] Ensure `package_dir={"": "src"}` is set in `setup.py`/`pyproject.toml`
- [x] Ensure `MANIFEST.in` includes `py.typed`

## Stage 3: Type Checking
- [x] Ensure `py.typed` is present in `src/mstair/common/`
- [x] Ensure type checker configs (`mypy.ini`, `pyrightconfig.json`) exist

## Stage 4: Tests and Linting
- [x] Ensure tests exist in `src/mstair/common/test_*.py`
- [x] Ensure linting/type checking config (ruff, mypy, pyright) exists

## Stage 5: Namespace Package Compliance
- [ ] No `__init__.py` in `src/mstair/` (remove if present)
- [x] `src/mstair/common/__init__.py` present

## Stage 6: Distribution
- [ ] Ensure `setup.py`/`pyproject.toml` is configured for namespace package (explicitly use `find_namespace_packages`)
- [x] `mstair_common.egg-info/` present

---

## Status: Some steps remain to convert this to a true namespace package per PEP 420. See above for required actions.
