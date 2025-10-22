# File: make/70-test.mk

.PHONY : test-lint
test-lint : .venv/.install ## Run all linters
	$(_begin)
	$(_activate)
	(	set -x
		ruff check .
		mypy --config-file=mypy.ini
	)
	$(_end)

.PHONY : test-pytest
test-pytest : .venv/.install ## Run test suites and validate documentation generation
	@$(_begin)
	@$(_activate)
	(	set -x
		pytest -v
	)
	@$(_end)

.PHONY : test
test : .venv/.test
.venv/.test : .venv/.install test-pytest test-lint ## Run all tests and linters
	@(	set -x
		touch .venv/.test
	)

# --------------------------------------------------------------
