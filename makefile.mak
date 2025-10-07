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

# Variable definitions and includes
include makefile-rules.mak

############################################################
# "default" target prints an informational message
############################################################
.PHONY: default
default:
	@printf "\n%s:\n" "$@"
	echo "No targets specified. Try 'make .venv' or 'make stubs'."

############################################################
# ".venv" cleans up everything and recreates the development environment
############################################################
.PHONY: .venv
.venv:	clean
	@printf "\n%s:\n" "$@"
	set -x
	rm -rf .venv
	python -m ensurepip --upgrade
	python -m venv .venv
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate
	python -m pip install --upgrade pip setuptools wheel pip-tools
	pip install -e .[dev,test]
	pip install "mypy" "ruff" "pytest"
	@printf "\n[done] virtual environment rebuilt successfully\n"

############################################################
# "stubs" target generates type stubs for listed packages in .typings.txt.
############################################################
.PHONY: stubs
TYPINGS_TXT	= .typings.txt
TYPINGS_DIR	= $(CACHE_DIR)/typings
STUBS		= $(if $(wildcard $(TYPINGS_TXT)),$(addsuffix .stub,$(strip $(file <$(TYPINGS_TXT)))),)
stubs:		$(TYPINGS_TXT) $(STUBS)

############################################################
# "%.stub" target generates a stub for a single package and appends it to .typings.txt.
# Uses .NOTINTERMEDIATE to avoid deletion of generated stubs during cleanup.
############################################################
.NOTINTERMEDIATE: $(TYPINGS_DIR)/%/__init__.pyi
%.stub: 	$(TYPINGS_DIR)/%/__init__.pyi
	@:
$(TYPINGS_DIR)/%/__init__.pyi:
	@printf "\n$@:\n"
	set -x
	mkdir -p "$(dir $@)"
	$(call STUBGEN_RUN,$*,$(TYPINGS_DIR))
	# Append package name to the list for repeatability
	[ -s "$(TYPINGS_TXT)" ] || printf "" >| "$(TYPINGS_TXT)"
	( printf "$*\n"; cat $(TYPINGS_TXT) ) | tr -d '\r' | grep -v '^$$' | sort | uniq >| $(TYPINGS_TXT)

############################################################
# "clean" target removes generated stubs and cache directory.
############################################################
.PHONY: clean
clean::
	@printf "\n$@:\n"
	set -x
	rm -rf "$(TYPINGS_DIR)"
	rm -rf "$(CACHE_DIR)"
