# File: makefile-rules.mak
#
$(info MAKE=$(MAKE))
$(info CURDIR=$(CURDIR))
$(info MAKEFILE_LIST=$(MAKEFILE_LIST))

.ONESHELL:
SHELL		:= $(abspath C:/Program Files/Git/usr/bin/bash.exe)
.SHELLFLAGS	:= -eu -o pipefail -c

##############################################################
# Project directories and environment
##############################################################

PROJECT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
$(info PROJECT_DIR=$(PROJECT_DIR))
ifndef CACHE_DIR
	CACHE_DIR	:= $(PROJECT_DIR)/.cache
endif
CACHE_DIR		:= $(subst \,/,$(CACHE_DIR))
$(info CACHE_DIR=$(CACHE_DIR))

npm_config_cache	?= $(CACHE_DIR)/.npm-cache
ifndef VIRTUAL_ENV
	VIRTUAL_ENV := $(subst \,/,$(PROJECT_DIR)/.venv)
	$(warning VIRTUAL_ENV not set, assuming '$(VIRTUAL_ENV)')
endif
ACTIVATE	:= $(VIRTUAL_ENV)/Scripts/activate
DEACTIVATE	:= $(VIRTUAL_ENV)/Scripts/deactivate
PYTHONPATH	:= $(PROJECT_DIR)

export

###############################################################
# Other tools and settings
###############################################################

COPY		?= cp -ar
UNZIP		?= 7z.exe x -y -o
ZIP		?= 7z.exe a -tzip -mx5 -mm=Deflate -mcu -r
TR		?= $(shell which tr)
SED		?= $(shell which sed)
GREP		?= $(shell which grep)
SORT		?= $(shell which sort)

define STUBGEN_RUN
	stubgen --package $(1) --output $(2) --quiet 1>/dev/null 2>&1 || ( \
	printf "\n" ; \
	stubgen --package $(1) --output $(2) --no-import --ignore-errors )
endef

empty :=
tab :=	$(empty)

# .DEFAULT_GOAL	:= printenv
# printenv:
# 	@printf "\n$@:\n"
# 	set -x
# 	printenv | sort | grep -oP '^(BASH|PYT|VI|VE|CURDIR|SHELL|PROJ|CACHE).*=.*$$' || true
# 	which tr
