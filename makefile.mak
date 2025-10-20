# File: makefile.mak

include $(wildcard make/*.mk)

.DEFAULT_GOAL           := help

.PHONY : help
help : ## List documented Makefile targets
	@awk -f- $(shell find  ./makefile.mak make -maxdepth 1 -type f -iregex '.*\.ma?k') <<- 'EOFAWK'
	BEGIN {
		RS = "\r?\n"
		FS = "[[:space:]]*:[^#]*##[[:space:]]+"
		printf( "\nMakefile targets:\n\n" )
	}
	{
		if ($$2 ~ /[[:print:]]{3,}/) {
			printf( "  %-20s %s\n", $$1, $$2 )
		}
	}
	END {
		printf( "\n" )
	}
	EOFAWK

# --------------------------------------------------------------
