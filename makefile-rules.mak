# File: makefile-rules.mak
#
ifdef VERBOSE
$(info CURDIR=$(CURDIR))
$(info MAKE=$(MAKE))
$(info MAKEFILE_LIST=$(MAKEFILE_LIST))
$(info )
endif

# ----------------------------------------------------------
# Helper macros and functions
# ----------------------------------------------------------

define STUBGEN_RUN
	args=(-p "$(1)" -o "$(2)" --include-private -q); \
	stubgen "$${args[@]}" || \
	stubgen "$${args[@]}" --no-import --ignore-errors
endef

asposix = $(subst \,/,$(abspath $(1)))

define _begin
	@printf '\n### %s ###\n' "$@"
endef
define _end
	@printf "### %s ###\n" "$@ done"
endef


SHELL		:= $(call asposix,C:/Program Files/Git/usr/bin/bash.exe)
.SHELLFLAGS	:= -eu -o pipefail -c
export MSYS2_PATH_TYPE := inherit
export PATH	:= $(call asposix,C:/Program Files/Git/cmd):$(PATH)
export PATH	:= $(call asposix,C:/Program Files/Git/usr/bin):$(PATH)

# ----------------------------------------------------------
# Project directories and environment
# ----------------------------------------------------------

ifndef PROJECT_DIR
export PROJECT_DIR := $(dir $(firstword $(MAKEFILE_LIST)))
$(warning PROJECT_DIR not set, assuming '$(PROJECT_DIR)')
endif
PROJECT_DIR := $(call asposix,$(PROJECT_DIR))

ifndef CACHE_DIR
export CACHE_DIR := $(PROJECT_DIR)/.cache
$(warning CACHE_DIR not set, assuming '$(CACHE_DIR)')
endif
CACHE_DIR := $(call asposix,$(CACHE_DIR))

ifndef MYPY_CACHE_DIR
export MYPY_CACHE_DIR := $(CACHE_DIR)/.mypy-cache
$(warning MYPY_CACHE_DIR not set, assuming '$(MYPY_CACHE_DIR)')
endif
MYPY_CACHE_DIR := $(call asposix,$(MYPY_CACHE_DIR))

ifndef npm_config_cache
export npm_config_cache := $(CACHE_DIR)/.npm-cache
endif
npm_config_cache := $(call asposix,$(npm_config_cache))

ifndef VIRTUAL_ENV
export VIRTUAL_ENV := $(PROJECT_DIR)/.venv)
$(warning VIRTUAL_ENV not set, assuming '$(VIRTUAL_ENV)')
endif
VIRTUAL_ENV := $(call asposix,$(VIRTUAL_ENV))

ifndef PYTHONPATH
export PYTHONPATH := $(PROJECT_DIR)
$(warning PYTHONPATH not set, assuming '$(PYTHONPATH)')
endif
PYTHONPATH := $(call asposix,$(PYTHONPATH))

# ----------------------------------------------------------
# Other tools and settings
# ----------------------------------------------------------

CAT 		?= /usr/bin/cat
CP		?= /usr/bin/cp
GREP		?= /usr/bin/grep
SED		?= /usr/bin/sed
SORT		?= /usr/bin/sort
TR		?= /usr/bin/tr
UNZIP		?= 7z.exe x -y -o
ZIP		?= 7z.exe a -tzip -mx5 -mm=Deflate -mcu -r

# ----------------------------------------------------------
# Other settings
# ----------------------------------------------------------

empty :=
tab :=	$(empty)
