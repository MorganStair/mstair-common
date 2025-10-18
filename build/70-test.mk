# File: build/70-test.mk

.PHONY: lint
lint: .venv/.install $(STUBS) # Run all linters
        $(_begin)
        $(_activate)
        {
                set -x
                ruff check .
                mypy --config-file=mypy.toml
        }
        $(_end)

.PHONY: test
test: .venv/.install # Run test suites and validate documentation generation
	@$(_begin)
	@$(_activate); set -x; pytest -v
	@$(_end)

.PHONY: tests
tests: test lint ; @: ## Run all tests and linters

# --------------------------------------------------------------
