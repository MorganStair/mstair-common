# File: make/00-globals.mk

ifdef VERBOSE
$(info CURDIR=$(CURDIR))
$(info MAKE=$(MAKE))
$(info MAKEFILE_LIST=$(MAKEFILE_LIST))
$(info )
endif

export SHELL    := bash
.SHELLFLAGS     := -e -u -c
.ONESHELL :

asposix = $(subst \,/,$(1))

ifndef PROJECT_DIR
export PROJECT_DIR := .
$(warning PROJECT_DIR not set, assuming '$(PROJECT_DIR)')
endif
PROJECT_DIR := $(call asposix,$(PROJECT_DIR))

ifndef CACHE_DIR
export CACHE_DIR := $(PROJECT_DIR).cache
$(warning CACHE_DIR not set, assuming '$(CACHE_DIR)')
endif
CACHE_DIR := $(call asposix,$(CACHE_DIR))

ifndef MYPY_CACHE_DIR
export MYPY_CACHE_DIR := $(CACHE_DIR)/.mypy_cache
$(warning MYPY_CACHE_DIR not set, assuming '$(MYPY_CACHE_DIR)')
endif
MYPY_CACHE_DIR := $(call asposix,$(MYPY_CACHE_DIR))

ifndef MYPYPATH
export MYPYPATH := $(PROJECT_DIR)/.cache/typings:$(PROJECT_DIR)/src
$(warning MYPYPATH not set, assuming '$(MYPYPATH)')
endif

ifndef npm_config_cache
export npm_config_cache := $(CACHE_DIR)/.npm-cache
endif
export npm_config_cache := $(call asposix,$(npm_config_cache))

ifdef VERBOSE
export PIP_VERBOSE = $(VERBOSE)
endif

ifneq (,$(findstring Windows_NT,$(OS)))
export VENV_BIN := .venv/Scripts
else
export VENV_BIN := .venv/bin
endif

UNZIP ?= 7z.exe x -y -o
ZIP   ?= 7z.exe a -tzip -mx5 -mm=Deflate -mcu -r

define _activate
	printf "%ssource %s/activate\n" "$$PS4" "$(VENV_BIN)"
	source $(VENV_BIN)/activate
	PS4="+$${PS4}"
endef

define _begin
	@printf '\\n### BEGIN %s: %s ###\\n' "$@" "$*"
endef

define _clear_screen
	@tput clear 2>/dev/null || printf '\033[H\033[2J\033[3J\033[r'
endef

define _end
	@printf "### END %s: %s ###\\n" "$@" "$*"
endef

# --------------------------------------------------------------
