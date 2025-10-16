# mstair-common
Common libraries initially developed for mstair packages.

## Coding and Testing Practices (Summary)

- **Linting:** Use `make lint`.
- **Formatting:** Use `python -m ruff check --fix` and `python -m ruff format`.
- **Type Checking:** Run `mypy src`.
- **Testing:** Use `make test` after every behavioural changes. Add or update tests under `src/**/test_*.py` when modifying logic. Avoid real network or subprocess calls in tests; use monkeypatching as in `test_format_helpers.py` and `xlogging/test_logger_util.py`.
- **Filesystem:** Prefer helpers in `mstair.common.base.fs_helpers` for Windows compatibility.
- **Logging:** Use `mstair.common.xlogging.logger_factory.create_logger` for loggers. Configure levels via environment variables. See `xlogging/logger_util.py` for details.
- **General:** Start modules with `# File: relative/path\n#\n"""docstring"""`. End modules with `# End of file: ...` for reliable tokenization.

For full contributor and AI assistant guidance, see `.github/ai-agent-guide.md`.
