# Copilot Behavior Check for TODO.md

# Purpose: Enforce deterministic, step-based execution for weak LLMs

rules:

-   name: "Respect TODO.md Workflow"
    description: |
    Always follow the TODO.md structure exactly.
    Never reorder, merge, or invent checklist items.
    Only modify items explicitly marked with @copilot instructions.
    Each edit must complete exactly one step and mark it [-] or [x].
    Never infer new context or create TODOs automatically.

-   name: "Preserve Checklists"
    description: |
    Maintain markdown checklist formatting.
    Never replace [ ], [-], or [x] with other symbols or text.
    Keep existing formatting and indentation exactly.

-   name: "Execution Safety"
    description: |
    Before any code change, ensure virtual environment is activated.
    Always use explicit commands: - PowerShell: .venv/Scripts/Activate.ps1 - Bash: source .venv/Scripts/activate
    Never delete files outside the current stage directory.

-   name: "Output Discipline"
    description: |
    When responding, Copilot must only: 1. Perform or describe the action requested by @copilot 2. Update the checklist accordingly 3. Stop immediately after completion
    Do not explain background theory or reformat the document.

-   name: "Minimal Context Mode"
    description: |
    Treat each step as independent.
    Do not assume persistent memory or project state.
    Rely only on what is visible in the current file.
