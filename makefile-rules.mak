# File: makefile-rules.mak

ifdef VERBOSE
$(info CURDIR=$(CURDIR))
$(info MAKE=$(MAKE))
$(info MAKEFILE_LIST=$(MAKEFILE_LIST))
$(info )
endif


export SHELL := C:\Program Files\Git\usr\bin\bash.exe
.SHELLFLAGS	:= -eu -c

asposix = $(subst \,/,$(1))

# ----------------------------------------------------------
# Project directories and environment
# ----------------------------------------------------------

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

# ----------------------------------------------------------
# Other tools and settings
# ----------------------------------------------------------

CAT   ?= /usr/bin/cat
CP    ?= /usr/bin/cp
GREP  ?= /usr/bin/grep
SED   ?= /usr/bin/sed
SORT  ?= /usr/bin/sort
TR    ?= /usr/bin/tr
UNZIP ?= 7z.exe x -y -o
ZIP   ?= 7z.exe a -tzip -mx5 -mm=Deflate -mcu -r

# ----------------------------------------------------------
# Other settings
# ----------------------------------------------------------

define _activate
	{ printf "%ssource %s/activate\n" "$$PS4" "$(VENV_BIN)"; source $(VENV_BIN)/activate; }
endef


define _begin
	@printf '\\n### %s ###\\n' "$@"
endef

define _clear_screen
	@tput clear 2>/dev/null || printf '\033[H\033[2J\033[3J\033[r'; : Clear screen and scrollback, tput fallback-safe
endef

define _end
	@printf "### %s ###\\n" "$@ done"
endef

define _stubgen
	( set -x; stubgen -p "$(1)" -o "$(2)" --include-private -q; ); \
	if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then \
		( set -x; stubgen -p "$(1)" -o "$(2)" --include-private -q --no-import --ignore-errors; ); \
	fi; \
	if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then \
		printf "\n*** stubgen '$(1)' failed ***\n\n" >&2; exit 1; \
	fi
endef
