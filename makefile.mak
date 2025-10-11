# File: makefile.mak

include makefile-rules.mak

# .ONESHELL:
TYPINGS_TXT	= .typings.txt
TYPINGS_DIR	= $(call asposix,$(CACHE_DIR)/typings)

# ----------------------------------------------------------
# Default target: list available targets
# ----------------------------------------------------------

.PHONY: default
default:  ## List available Makefile targets
	@printf "Valid targets:\n"
	@grep -hE '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ----------------------------------------------------------
# Virtual environment and package management
# ----------------------------------------------------------

.PHONY: venv-reset
venv-reset: ## Recreate .venv from scratch, reinstall dependencies
	$(_begin)
	rm -rf .venv
	python -m ensurepip --upgrade
	python -m venv .venv
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate && {
	  python -m pip install --upgrade pip setuptools wheel pip-tools; \
	  pip install -e .[dev,test]; \
	}
	$(_end)

.PHONY: venv-ensure
venv-ensure: ## Ensure .venv exists (create if missing)
	$(_begin)
	[ -d ".venv" ] || python -m venv .venv
	$(_end)

build: venv-ensure ## Install current package in editable mode into .venv
	$(_begin)
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate && { \
	  pip install -e .[dev,test]; \
	}
	$(_end)

package: venv-ensure ## Build distribution artifacts (wheel and sdist)
	$(_begin)
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate && {
	  python -m build; \
	}
	$(_end)

setup: venv-ensure build stubs ## Full developer environment setup
	$(_end)

# ----------------------------------------------------------
# Type stubs generation
# ----------------------------------------------------------

.PHONY: stubs
stubs:	$(TYPINGS_TXT) ## Generate type stubs for packages listed in $(TYPINGS_TXT)
	$(_begin)
	set -x
	{ test -s "$(TYPINGS_TXT)" && cat "$(TYPINGS_TXT)"; } | \
	  tr -d '\r' | \
	  grep -v '^[[:space:]]*$$' | \
	  while IFS= read -r package; do \
	    $(MAKE) --no-print-directory "$${package}.stub"; \
	  done
	$(_end)

%.stub: $(TYPINGS_DIR)/%/__init__.pyi ## Generate type stubs for package $*
	$(_end)

.NOTINTERMEDIATE: $(TYPINGS_DIR)/%/__init__.pyi

$(TYPINGS_DIR)/%/__init__.pyi:
	$(_begin)
	source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate && { \
	  pip install --upgrade pip setuptools wheel; \
	  pip install mypy; \
	}
	[ ! -f "$(VIRTUAL_ENV)/Lib/site-packages/$*/__init__.pyi" ] || \
	  { printf "\n*** '$*' includes stubs ***\n\n" >&2; exit 1; }; \
	source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate && \
	  $(call STUBGEN_RUN,$*,$(TYPINGS_DIR))
	: "$(TYPINGS_TXT)"; \
	  { test -f "$$_" && cat "$$_"; printf "%s\n" "$*"; } \
	  | tr -d '\r' | grep -v '^$$' | sort | uniq >| "$$_";
	$(_end)

# ----------------------------------------------------------
# Cleanup
# ----------------------------------------------------------

.PHONY: clear
clear:
	$(_clear_screen)

.PHONY: clean
clean:: clear ## Remove generated stubs and cache directory
	$(_begin)
	rm -rf "$(TYPINGS_DIR)"
	$(_end)

.PHONY: virgin
virgin:: clean
	$(_begin)
	rm -rf .venv
	rm -rf "$(CACHE_DIR)"
	rm -rf "$(MYPY_CACHE_DIR)"
	rm -rf build
	rm -rf dist
	rm -rf uploads
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	$(_end)

.PHONY: windows-init
windows-init: ## Initialize Windows environment (run once)
	$(_begin)
	git config --global core.autocrlf false
	git config --global core.eol crlf
	$(_end)

# End of file: makefile.mak
