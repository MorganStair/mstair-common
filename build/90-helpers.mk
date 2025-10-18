# File: build/90-helpers.mk

.PHONY: cat
cat: ## Concatenate all Makefile parts to stdout
	@printf "\n"
	cat makefile.mak build/*
	printf "\n"

.PHONY: clear
clear: # Helper to clear the screen
	@$(_clear_screen)

.PHONY: git-crlf
git-crlf: # Helper to set Git line ending handling
	@set -x
	git config --global core.autocrlf false
	set -x; git config --global core.eol crlf

.PHONY: all
all: venv install test dist ## Alias for "make venv install test dist"
	@$(_end)

# --------------------------------------------------------------
