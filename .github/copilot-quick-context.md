# copilot-quick-context.md
# Minimal guide for inline Copilot (weak model safe)

Purpose: quick operational hints for editing `mstair.common` utilities.
Keep this file under 200 lines and never cross-reference other markdowns.
Copilot reads this to orient itself when lacking full context.

---

## Project Summary
- Library name: `mstair.common` — shared helpers, not an app.
- Entry point: `src/mstair/common/`
- Root package: `mstair` re-exports `mstair.common`.
- Supported Python: 3.13+
- Windows paths common; prefer helpers in `base.fs_helpers`.

---

## Edit Rules
1. **Always activate environment first**
   ```powershell
   .venv/Scripts/Activate.ps1
   ```
2. **Do not create new directories or top-level packages.**
3. **Keep changes local** to the edited module.
4. **Preserve imports and `# End of file:` sentinel** at bottom of every source file.
5. **Never remove `py.typed` or edit packaging metadata** unless TODO.md directs it.

---

## Lint & Type Commands
Use exactly these commands before marking a step `[x]` in `TODO.md`:

```bash
python -m ruff check --fix
python -m ruff format
mypy src
pytest
```

(Shortcuts: `make lint`, `make typecheck`, `make test`.)

---

## Test Expectations
- All tests live under `src/**/test_*.py`.
- Avoid real subprocess or network calls.
- Monkeypatch, caplog, or use helpers from:
  - `xlogging/test_logger_util.py`
  - `common/test_format_helpers.py`

---

## Logging Helpers
- Create loggers via:
  ```python
  from mstair.common.xlogging.logger_factory import create_logger
  logger = create_logger(__name__)
  ```
- Root logger auto-configures; do **not** attach handlers manually.
- For diagnostics, inspect `xlogging/logger_util.py`.

---

## Formatting Helpers
- Use:
  ```python
  from mstair.common.format_helpers import format_source_code
  ```
  to format and sort imports.
- Maintain a trailing newline and `# End of file:` comment.

---

## Behavioral Notes
- `base/` modules: safe for import anywhere; no side effects.
- `xlogging/`: logging stack, safe for multithreaded use.
- `xdumps/`: safe object serialization for logs.

---

## Copilot Behavior
- Follow checklist in `TODO.md` step-by-step.
- Never summarize or refactor broadly.
- When unsure, respond:
  > “Need human guidance — unclear TODO step.”
- Limit reasoning to visible code and these rules.

---

## Reference
For detailed guidance (for humans or strong models),
see `.github/ai-agent-guide.md` outside this file’s context.

# End of file: copilot-quick-context.md
