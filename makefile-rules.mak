# File: makefile-rules.mak
#
$(info CURDIR=$(CURDIR))
$(info MAKE=$(MAKE))
$(info MAKEFILE_LIST=$(MAKEFILE_LIST))

.ONESHELL:
SHELL		:= $(abspath C:/Program Files/Git/usr/bin/bash.exe)
.SHELLFLAGS	:= -eu -o pipefail -c
export PATH	:= /c/Program\ Files/Git/cmd:$(PATH)


# ----------------------------------------------------------
# Project directories and environment
# ----------------------------------------------------------

ifndef PROJECT_DIR
export PROJECT_DIR := $(abspath $(dir $(firstword $(MAKEFILE_LIST))))
$(warning PROJECT_DIR not set, assuming '$(PROJECT_DIR)')
endif

ifndef CACHE_DIR
export CACHE_DIR := $(PROJECT_DIR)/.cache
$(warning CACHE_DIR not set, assuming '$(CACHE_DIR)')
endif

ifndef MYPY_CACHE_DIR
export MYPY_CACHE_DIR := $(CACHE_DIR)/.mypy-cache
$(warning MYPY_CACHE_DIR not set, assuming '$(MYPY_CACHE_DIR)')
endif

ifndef npm_config_cache
export npm_config_cache := $(CACHE_DIR)/.npm-cache
endif

ifndef VIRTUAL_ENV
export VIRTUAL_ENV := $(subst \,/,$(PROJECT_DIR)/.venv)
$(warning VIRTUAL_ENV not set, assuming '$(VIRTUAL_ENV)')
endif

ifndef PYTHONPATH
export PYTHONPATH := $(PROJECT_DIR)
$(warning PYTHONPATH not set, assuming '$(PYTHONPATH)')
endif

# ----------------------------------------------------------
# Other tools and settings
# ----------------------------------------------------------

CAT 		?= /usr/bin/cat
CP			?= /usr/bin/cp
GREP		?= /usr/bin/grep
SED			?= /usr/bin/sed
SORT		?= /usr/bin/sort
TR			?= /usr/bin/tr
UNZIP		?= 7z.exe x -y -o
ZIP			?= 7z.exe a -tzip -mx5 -mm=Deflate -mcu -r

define STUBGEN_RUN
	stubgen --package $(1) --output "$(2)" --quiet 1>/dev/null 2>&1 || ( \
	printf "\n" ; \
	stubgen --package $(1) --output "$(2)" --no-import --ignore-errors )
endef

# ----------------------------------------------------------
# Other settings
# ----------------------------------------------------------

empty :=
tab :=	$(empty)
