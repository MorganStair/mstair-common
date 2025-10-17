# File: makefile.mak

# ----------------------------------------------------------
# Set Variables, rules, and functions:
#   SHELL, PROJECT_DIR, CACHE_DIR, MYPY_CACHE_DIR, MYPYPATH, VENV_BIN,
#   _activate, _clear_screen, _begin, _end, ...
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
	@$(_fn_make); fn_make mkinit; fn_make stubs
	@set -x; touch $@
	@$(_end)

# ----------------------------------------------------------
# Phony targets for development tasks
# ----------------------------------------------------------

.PHONY: mkinit
mkinit: ## Regenerate __init__.py files for package src/mstair/common
	@${_begin}
	@${_activate}; set -x; mkinit src/mstair/common --inplace --relative --nomods --noattrs --recursive
	@${_end}

# ----------------------------------------------------------
# Phony targets for stub generation
# ----------------------------------------------------------

.PHONY: stubs
PACKAGES := $(shell cat $(TYPINGS_TXT) 2>/dev/null || true)
PACKAGES_DOT_STUB := $(addsuffix .stub,$(PACKAGES))

.PHONY: $(PACKAGES_DOT_STUB)
$(PACKAGES_DOT_STUB): %.stub: $(CACHE_DIR)/typings/%/__init__.pyi
	@:

stubs: $(PACKAGES_DOT_STUB) ## Generate stubs for packages listed in .typings.txt
	@$(_end)

%.stub: $(CACHE_DIR)/typings/%/__init__.pyi
	@:

.NOTINTERMEDIATE: $(CACHE_DIR)/typings/%/__init__.pyi

define _stubgen
	( set -x; stubgen -p "$(1)" -o "$(2)" --include-private -q 2>/dev/null >/dev/null; ); \
	if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then \
		( set -x; stubgen -p "$(1)" -o "$(2)" --include-private -q --no-import --ignore-errors 2>/dev/null >/dev/null; ); \
	fi; \
	if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then \
		printf "\n*** stubgen '$(1)' failed ***\n\n" >&2; exit 1; \
	fi
endef

define _awk_insert_line
	awk -v new_line='$(2)' ' \
		BEGIN { new_line_seen = 0 } \
		{ \
			gsub(/\r/, ""); \
			if ($$0 ~ /^[[:space:]]*$$/) next; \
			if (!seen[$$0]++) print; \
			if ($$0 == new_line) new_line_seen = 1; \
		} \
		END { if (!new_line_seen) print new_line; } \
	' '$(1)'
endef

$(CACHE_DIR)/typings/%/__init__.pyi:
	@$(_begin)
	@$(_activate); \
	$(call _stubgen,$*,$(CACHE_DIR)/typings)
	@set -x; \
	$(call _awk_insert_line,$(TYPINGS_TXT),$*) | tee "$(TYPINGS_TXT).tmp"
	@set -x; mv "$(TYPINGS_TXT).tmp" "$(TYPINGS_TXT)"
	@$(_end)

# ----------------------------------------------------------
# Phony targets for other development tasks
# ----------------------------------------------------------

.PHONY: docs
docs: .venv/.install # Generate documentation in docs/
	@: No documentation to generate yet

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
	@$(_end)

.PHONY: all
all: install stubs docs dist test lint ## Run all steps
	@$(_end)

# ----------------------------------------------------------
# Helper/convenience targets
# ----------------------------------------------------------

.PHONY: clear
clear:
	@$(_clear_screen) # Helper to clear the screen

.PHONY: help-docs-serve
help-docs-serve: docs # Helper to generate and serve documentation locally
	@$(_activate); set -x; python -m http.server 8000 --directory docs/
	@$(_end)

.PHONY: help-git-crlf
help-git-crlf: # Helper to set Git line ending handling
	@set -x; git config --global core.autocrlf false
	@set -x; git config --global core.eol crlf

# ----------------------------------------------------------
# Implicit rules
# ----------------------------------------------------------

$(TYPINGS_TXT): # Ensure the typings file exists
	@touch $@

# End of file: makefile.mak
