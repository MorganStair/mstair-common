# File: makefile.mak
#
# ----------------------------------------------------------
# Developer automation for mstair-common
# ----------------------------------------------------------
# Highlights:
# - Uses .cache/typings for stubgen output (not packaged)
# - Keeps imports discoverable for IDEs via pyrightconfig.json
# - Provides clean, rebuild, and environment setup targets
# ----------------------------------------------------------

include makefile-rules.mak

# ----------------------------------------------------------
# Default target: list available targets
# ----------------------------------------------------------

.PHONY: default
default:  ## List available Makefile targets
	@set -eu -o pipefail; { \
		printf "\n%s:\n" "$@"; \
		printf "Valid targets:\n"; \
		grep -hE '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-20s\033[0m %s\n", $$1, $$2}'; \
	}

# ----------------------------------------------------------
# Virtual environment and package management
# ----------------------------------------------------------

.PHONY: venv-reset
venv-reset: ## Recreate .venv from scratch, reinstall dependencies
	@printf "\n%s:\n" "$@"
	set -ex
	rm -rf .venv
	python -m ensurepip --upgrade
	python -m venv .venv
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate
	python -m pip install --upgrade pip setuptools wheel pip-tools
	pip install -e .[dev,test]
	@printf "\n[done] virgin virtual environment built successfully\n"

venv-ensure: ## Ensure .venv exists (create if missing)
	@printf "\n%s:\n" "$@"
	set -ex
	if [ ! -d ".venv" ]; then \
		echo "Creating missing virtual environment (.venv)..."; \
		python -m venv .venv; \
	fi
	@printf "[ok] .venv is present and usable.\n"

build: venv-ensure ## Install current package in editable mode into .venv
	@printf "\n%s:\n" "$@"
	set -ex
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate
	pip install -e .[dev,test]
	@printf "\n[done] project installed in editable mode.\n"

package: venv-ensure stubs ## Build distribution artifacts (wheel and sdist)
	@printf "\n%s:\n" "$@"
	set -ex
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate
	python -m build
	@printf "\n[done] distribution artifacts written to ./dist\n"

setup: venv-ensure build stubs ## Full developer environment setup
	@printf "\n[done] development environment initialized.\n"

# ----------------------------------------------------------
# Type stubs generation
# ----------------------------------------------------------

.PHONY: stubs
TYPINGS_TXT	= .typings.txt
TYPINGS_DIR	= $(CACHE_DIR)/typings
STUBS		= $(if $(wildcard $(TYPINGS_TXT)),$(addsuffix .stub,$(strip $(file <$(TYPINGS_TXT)))),)
stubs:		$(TYPINGS_TXT) $(STUBS) ## Generate type stubs for packages listed in $(TYPINGS_TXT)
	@printf "\n$@:\n"
	@printf "\n[done] type stubs generated in %s\n" "$(TYPINGS_DIR)"
.NOTINTERMEDIATE: $(TYPINGS_DIR)/%/__init__.pyi
%.stub: 	$(TYPINGS_DIR)/%/__init__.pyi ## Generate type stubs for package $*
	@:
$(TYPINGS_DIR)/%/__init__.pyi:
	@printf "\n$@:\n"
	set -x
	mkdir -p "$(dir $@)"
	$(call STUBGEN_RUN,$*,$(TYPINGS_DIR))
	# Append package name to the list for repeatability
	[ -s "$(TYPINGS_TXT)" ] || printf "" >| "$(TYPINGS_TXT)"
	( printf "$*\n"; cat $(TYPINGS_TXT) ) | tr -d '\r' | grep -v '^$$' | sort | uniq >| $(TYPINGS_TXT)

# ----------------------------------------------------------
# Cleanup
# ----------------------------------------------------------

.PHONY: clean
clean:: ## Remove generated stubs and cache directory
	@printf "\n$@:\n"
	set -x
	rm -rf "$(TYPINGS_DIR)"
	rm -rf "$(MYPY_CACHE_DIR)"
	rm -rf "$(CACHE_DIR)"
