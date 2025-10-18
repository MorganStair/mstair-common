# File: makefile.mak

include $(wildcard build/*.mk)

.DEFAULT_GOAL           := help

.PHONY: help
help: ## List documented Makefile targets
	@awk -f- $(shell find . build -maxdepth 1 -name '*.mk') <<- 'EOFAWK'
	BEGIN {
		RS = "\r?\n"
		FS = "[[:space:]]*:[^#]*##[[:space:]]+"
		printf( "\nMakefile targets:\n\n" );
	} {
		if ($$1 ~ /^[[:alnum:]_.-]+$$/ && $$2 ~ /[[:print:]]{3,}/) {
			printf( "  %-20s %s\n", $$1, $$2 );
		}
	}
	END {
		printf( "\n" );
	}
	EOFAWK

.PHONY: cat
cat: ## Concatenate all Makefile parts to stdout
	@printf "\n"
	cat makefile.mak build/*
	printf "\n"

.PHONY: all
all: install stubs mkinit test lint dist ## Run all steps
	@$(_end)

.PHONY: clear
clear:
# Helper to clear the screen
	@$(_clear_screen)

.PHONY: git-crlf
git-crlf:
# Helper to set Git line ending handling
	@set -x
	git config --global core.autocrlf false
	set -x; git config --global core.eol crlf

# End of file: makefile.mak

# --------------------------------------------------------------
