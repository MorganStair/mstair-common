# File: makefile


####################################################################################################
# SECTION: Variable definitions and includes
# Purpose: Bring in reusable rules and determine global paths.
####################################################################################################

include makefile-rules.mak


####################################################################################################
# SECTION: Default target
# Purpose: Print an informational message when no target is provided.
####################################################################################################

.PHONY: default clean
default:
	@printf "\n%s:\n" "$@"
	echo "No targets specified."


####################################################################################################
# SECTION: Package initialization
# Purpose: Auto-generate __init__.py files across src/mstair for clean packaging.
# Depends on: update_package_inits.sh
####################################################################################################

.PHONY: package-inits
package-inits:
	@printf "\n%s:\n" "$@"
	set -x
	update_package_inits.sh


####################################################################################################
# SECTION: Virtual environment management
# Purpose: Recreate local .venv and install dev/test dependencies.
# Outputs: .venv, requirements.txt
####################################################################################################
.PHONY: .venv requirements.txt
.venv:
	@printf "\n%s:\n" "$@"
	set -ex
	rm -rf .venv
	python -m ensurepip --upgrade
	python -m venv .venv
	. .venv/Scripts/activate 2>/dev/null || . .venv/bin/activate
	python -m pip install --upgrade pip setuptools wheel pip-tools
	pip install -e .[dev,test]
	pip install \
		"boto3>=1.35.0" \
		"botocore>=1.35.0" \
		"boto3-stubs[essential,s3,sts]>=1.35.0" \
		"botocore-stubs>=1.35.0" \
		"types-awscrt>=0.21.0" \
		"mypy" "ruff" "pytest"
	[ -f requirements.txt ] || touch requirements.txt
	$(TR) -d '\r' < requirements.txt \
	| $(SED) -E 's/(==[^[:space:]]+)//' \
	| $(SED) -E 's/#.*//' \
	| $(GREP) -v '^[[:space:]]*$$' \
	| $(SORT) -u > requirements.in
	pip-compile --upgrade -o requirements.txt requirements.in
	pip install -r requirements.txt
	@printf "\n[done] virtual environment rebuilt successfully\n"


####################################################################################################
# SECTION: Stub generation
# Purpose: Generate .pyi stubs into .cache/typings using stubgen.
# Input: package names in .typings.txt
# Output: mirrored stub directory under .cache/typings
####################################################################################################

.PHONY: stubs

TYPINGS_TXT	= .typings.txt
TYPINGS_DIR	= $(CACHE_DIR)/typings
STUBS		= $(if $(wildcard $(TYPINGS_TXT)),$(addsuffix .stub,$(strip $(file <$(TYPINGS_TXT)))),)

stubs: $(TYPINGS_TXT) $(STUBS)

.NOTINTERMEDIATE: $(TYPINGS_DIR)/%/__init__.pyi

%.stub: $(TYPINGS_DIR)/%/__init__.pyi
	@:

$(TYPINGS_DIR)/%/__init__.pyi:
	@printf "\n$@:\n"
	set -x
	$(call STUBGEN_RUN,$*,$(TYPINGS_DIR))
	( printf "$*\n"; cat $(TYPINGS_TXT) ) | tr -d '\r' | grep -v '^$$' | sort | uniq >| $(TYPINGS_TXT)

$(TYPINGS_DIR):
	@printf "\n$@:\n"
	set -x
	mkdir -p "$@"

$(TYPINGS_TXT): | $(TYPINGS_DIR)
	@printf "\n$@:\n"
	set -x
	touch "$@"

####################################################################################################
# SECTION: Cleanup
# Purpose: Remove cached artifacts and stub directories.
####################################################################################################

clean::
	@printf "\n$@:\n"
	set -x
	rm -rf "$(TYPINGS_DIR)"
	rm -rf "$(CACHE_DIR)"

####################################################################################################
# Development helper targets
####################################################################################################

# Generate dependency graph for Python modules
.PHONY: pydeps
pydeps:
	@printf "\n$@:\n"
	@echo off; set -x
	pydeps python --show-cycles --only tools --max-bacon=2

# Run linting on all Python code
.PHONY: pylint lint
pylint lint:
	@printf "\n$@:\n"
	pylint python

####################################################################################################
# End of file: makefile
