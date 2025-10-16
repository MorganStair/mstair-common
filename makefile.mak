# File: makefile.mak

# ----------------------------------------------------------
# Set Variables, rules, and functions:
#   SHELL, PROJECT_DIR, CACHE_DIR, MYPY_CACHE_DIR, MYPYPATH, VENV_BIN,
#   _activate, _clear_screen, _begin, _end, _stubgen, etc.
# ----------------------------------------------------------
include makefile-rules.mak

# ----------------------------------------------------------
# Variables for the makefile targets
# ----------------------------------------------------------

TYPINGS_TXT := .typings.txt

# ----------------------------------------------------------
# Zero effect targets
# ----------------------------------------------------------

.PHONY: help
.DEFAULT_GOAL := help
help: ## List available Makefile targets
	@printf "Valid targets:\n"
	@grep -hE '^[-a-zA-Z0-9_./]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ----------------------------------------------------------
# Cleanup
# ----------------------------------------------------------

.PHONY: clean
clean: clear ## Remove build artifacts and egg-info directories (not the virtual environment)
	@$(_begin)
	@set -x; rm -rf build dist uploads
	@find . -name .venv -prune -o -type d -name "*.egg-info" \
		-exec $${SHELL} -x -c 'rm -rf "$@"' _ {} +
	@$(_end)

.PHONY: virgin
virgin: clean ## Remove virtual environment, log files, temp files, and .cache directory
	@$(_begin)
	@set -x; rm -rf .venv *.log *.tmp
	@set -x; rm -rf $(CACHE_DIR)
	@$(_end)

# ----------------------------------------------------------
# Touch targets for virtual environment management
# ----------------------------------------------------------

.PHONY: venv
venv: .venv ## Create a virtual environment in .venv
.venv:
	@$(_begin)
	@set -x; python -m venv ".venv"
	@set -x; mv -n $(VENV_BIN)/activate $(VENV_BIN)/activate-original
	@set -x; mv -n $(VENV_BIN)/Activate.ps1 $(VENV_BIN)/ActivateOriginal.ps1
	@set -x; mv -n $(VENV_BIN)/activate.bat $(VENV_BIN)/activate-original.bat
	@set -x; mv -n $(VENV_BIN)/activate.fish $(VENV_BIN)/activate-original.fish
	@set -x; cp -n scripts/venv-shims/* $(VENV_BIN)/
	@set -x; cp -n scripts/sitecustomize.py .venv/Lib/site-packages/
	@$(_activate); set -x; python -m ensurepip --upgrade | /usr/bin/grep -vE '^(Looking in|Requirement already)' || true
	@$(_activate); set -x; pip install -q --upgrade pip setuptools wheel
	@$(_end)

# 	@$(_activate); { set -x; python -m ensurepip --upgrade || exit 1; } | /usr/bin/grep -vE '(Looking in|Requirement already)' || true

.PHONY: check
check:
	@$(_clear_screen)
	@$(_begin)
	@$(_activate); set -x; python --version
	@$(_end)

.PHONY: install
install: .venv/.install; @: ## Install packages and custom wrappers in .venv
.venv/.install: .venv
	@$(_begin)
	@$(_activate); set -x; pip install -q -e .[dev,test]
	@set -x; make --no-print-directory stubs
	@set -x; touch $@
	@$(_end)

# ----------------------------------------------------------
# Phony targets for development tasks
# ----------------------------------------------------------

.PHONY: stubs
stubs: $(CACHE_DIR)/.stubs; @:  ## Generate stubs for packages listed in .typings.txt
$(CACHE_DIR)/.stubs: $(TYPINGS_TXT) # install calls "make stubs", so this can not depend on install
	@$(_begin)
	@{ cat "$(TYPINGS_TXT)" 2>/dev/null || true; } | \
		tr -d '\r' | \
		grep -v '^[[:space:]]*$$' | \
		while IFS= read -r package; do \
			( set -x; $(MAKE) --no-print-directory "$(CACHE_DIR)/typings/$${package}/__init__.pyi"; ); \
		done
	@set -x; touch "$(CACHE_DIR)/.stubs"
	@$(_end)

.PHONY: docs
docs: .venv/.install ## Generate documentation in docs/
	@$(_begin)
	@$(_activate); set -x; python -m mstair.rentals.rentals_docgen --output docs/ --format markdown
	@$(_activate); set -x; rentals --config rentals.example.toml
	@$(_activate); set -x; rentals --help > docs/rentals-help.txt
	@$(_end)

dist: .venv/.install ## Build the source and wheel packages
	@$(_begin)
	@$(_activate); set -x; python -m build -C--quiet
	@$(_end)

.PHONY: lint
lint: .venv/.install $(CACHE_DIR)/.stubs ## Run linters
	@$(_begin)
	@$(_activate); set -x; ruff check .
	@$(_activate); set -x; mypy --config-file=mypy.ini
	@$(_end)

.PHONY: test
test: .venv/.install ## Run test suites and validate documentation generation
	@$(_begin)
	@$(_activate); set -x; pytest -v
	@$(_activate); set -x; python -m mstair.rentals.rentals_docgen --output docs/ --format markdown --validate-only
	@$(_end)

.PHONY: all
all: stubs docs dist test lint ## Run all steps
	@$(_end)

# ----------------------------------------------------------
# Helper/convenience targets
# ----------------------------------------------------------

.PHONY: clear
	@$(_clear_screen) # Helper to clear the screen

.PHONY: help-docs-serve
help-docs-serve: docs # Helper to generate and serve documentation locally
	@$(_begin)
	@$(_activate); set -x; python -m http.server 8000 --directory docs/
	@$(_end)

.PHONY: help-git-crlf
help-git-crlf: # Helper to set Git line ending handling
	@$(_begin)
	@set -x; git config --global core.autocrlf false
	@set -x; git config --global core.eol crlf
	@$(_end)

# ----------------------------------------------------------
# Implicit rules
# ----------------------------------------------------------

%.stub: $(CACHE_DIR)/typings/%/__init__.pyi; @: # Generate package stubs and add it to .typings.txt

.NOTINTERMEDIATE: $(CACHE_DIR)/typings/%/__init__.pyi

$(CACHE_DIR)/typings/%/__init__.pyi: # Implicit rule to generate the stubs for a package
	@$(_begin)
	@$(_activate); $(call _stubgen,$*,$(CACHE_DIR)/typings)
	@touch $(TYPINGS_TXT)
	@set -x; sed -i 'a $*' $(TYPINGS_TXT) && sort -u $(TYPINGS_TXT) -o $(TYPINGS_TXT)
	@dos2unix $(TYPINGS_TXT) 2>/dev/null || true
	@sed -i '/^[[:space:]]*$$/d' $(TYPINGS_TXT)
	@$(_end)

$(TYPINGS_TXT): ; @: # Ensure the typings file exists
	@touch $@
	@dos2unix $@ 2>/dev/null || true
	@sed -i '/^[[:space:]]*$$/d' $@

# End of file: makefile.mak
