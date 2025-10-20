# File: make/80-dist.mk

.PHONY : dist build
dist : build
build : .venv/.test ## Build the source and wheel packages
	$(_begin)
	$(_activate)
	(	set -x
		python -m build .
	)
	$(_end)

# --------------------------------------------------------------
