# File: makefile

include makefile-rules.mak

.PHONY: default clean
default:
	@printf "\n%s:\n" "$@"
	echo "No targets specified."

####################################################################################################
# Sanity checks
####################################################################################################
.PHONY: sanity

sanity:
	@printf "\n%s:\n" "$@"
	set -e
	which python > /dev/null
	which pip > /dev/null
	which node > /dev/null
	which npm > /dev/null
	which npx > /dev/null
	which aws > /dev/null
	which cdk > /dev/null
	which git > /dev/null
	which make > /dev/null
	if [ ! -f .env ]; then ( \
		printf "# .env\n"; \
		printf "# LOG_LEVEL=\"debug, *.xlogging.*=warning, tools.lib.click*=warning\"\n" \
		) > .env; \
	fi
	echo "Sanity checks passed."

####################################################################################################
# package __init__.py files
####################################################################################################

.PHONY: package-inits

package-inits:
	@printf "\n%s:\n" "$@"
	set -x
	update_package_inits.sh

####################################################################################################
# Virtual Environment Creation
####################################################################################################

.PHONY: .venv requirements.txt

# Recreate and upgrade all packages in the virtual environment
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
# Stub Generation
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

clean::
	@printf "\n$@:\n"
	set -x
	rm -rf "$(TYPINGS_DIR)"

####################################################################################################
# Build and deployment targets
####################################################################################################

clean::
	@printf "\n$@:\n"
	set -x
	rm -rf $(CACHE_DIR)

####################################################################################################
# Development tools
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
