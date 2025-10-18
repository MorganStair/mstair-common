# File: build/80-dist.mk

dist: .venv/.install ## Build the source and wheel packages
	$(_begin)
	$(_activate)
	{
		set -x
		python -m build -C--quiet .
	}
	$(_end)

# --------------------------------------------------------------
