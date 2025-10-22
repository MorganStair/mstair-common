# .github/copilot-instructions.md — project edit protocol

## Purpose

Defines how automated or AI-based edits must behave in this repository.
Formatting and code style are governed by [`.github/CODING_STANDARDS.md`](CODING_STANDARDS.md).

---

## Editing discipline

-   Treat each edit as **stateless**; rely only on visible file text.
-   Apply **small, targeted patches** with clear purpose.
-   Never reformat, reorder, or restyle files unless the change demands it.
-   Preserve spacing, indentation, comments, and blank lines.
-   Keep `# File:` and `# End of file:` markers intact.
-   Reload the file before editing if a patch fails or the version header changed.

---

## Environment

Use the provided `makefile.mak` and project virtual environment.

### Activate the environment before running any non-make command

| Shell      | Command                                |
| ---------- | -------------------------------------- |
| PowerShell | `.venv/Scripts/CommonActivate.ps1`     |
| Bash       | `source .venv/Scripts/common-activate` |

---

### Run individual tests after small changes

```powershell
.venv\Scripts\Activate.ps1; pytest -k "<test_name>"
```

---

### Run the full test suite after completing a feature or fix

(The makefile handles environment activation automatically.)

```powershell
make all
```

All tests must complete **without warnings** before continuing.

---

## Behavioral rules

-   Reference `CODING_STANDARDS.md` for structure, typing, and docstring rules.
-   Default: **Python 3.13+, ASCII-only source**.
-   Use **absolute imports** only, ordered stdlib → third-party → local.
-   Avoid clever abstractions; correctness and clarity first.
-   Do not modify or delete files outside the edit target.
-   Never inject summaries, banners, or metadata into Markdown or Python files.

---

## Multi-step edits

For multi-file or sequential edits:

1. State the planned change briefly.
2. Apply only the necessary modifications.
3. Report concise progress (no long summaries).
4. Stop and request confirmation on large or destructive edits.

---

## Safety

-   Preserve all anchors, code fences, and list structure in Markdown.
-   Never normalize whitespace globally.
-   Keep outputs deterministic, plain ASCII, and import-safe.
-   No dynamic imports, broad exceptions, or implicit globals.
