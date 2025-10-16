# .copilot-instructions.md — Enhanced for GPT‑4.1 Patch Safety

This configuration ensures reliable TODO.md edits and predictable agent behavior for Copilot GPT‑4.1 and weaker models.

---

rules:

-   name: "Respect TODO.md Workflow"
    description: |
    Follow TODO.md exactly.
    Never reorder or summarize checklist items.
    Perform only the step explicitly referenced.
    Update `[ ]` → `[-]` → `[x]` only.
    Keep Markdown formatting unchanged.

-   name: "Always refresh file before patch"
    description: |
    Before editing TODO.md:
    • Fetch the latest version of the file from disk.
    • Confirm the version header (<!-- version: ... -->) matches.
    • Use the current file state when building patches.
    • Never rely on cached context.

-   name: "Retry on patch mismatch"
    description: |
    If a patch fails due to context mismatch:
    • Re-read the entire file.
    • Retry once with the latest version header.
    • Do not reformat, reorder, or strip whitespace.

-   name: "Preserve Formatting and Comments"
    description: |
    Preserve all HTML comments, anchors, and code fences.
    Maintain indentation and blank lines.
    Never normalize Markdown unless explicitly told to.

-   name: "Patch Safety for TODO.md"
    description: |
    Only modify checklist marker states or text inside action lines.
    Keep everything else intact.
    Do not inject extra @mentions or summaries.

-   name: "Execution Safety"
    description: |
    Always activate the Python environment before running code:
    PowerShell: .venv/Scripts/Activate.ps1
    Bash: source .venv/Scripts/activate
    Never delete files outside the designated stage directory.

-   name: "Minimal Context Mode"
    description: |
    Treat each edit as stateless.
    Use only visible text and this guide for context.
    Do not assume memory across sessions.
