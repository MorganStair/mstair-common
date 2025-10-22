# File: make/80-dist.mk

.PHONY : dist build
dist : build
build : .venv/.test ## Build the source and wheel packages
	$(_begin)
	if [ ! -f "MANIFEST.in" ]; then
		exit 0
	fi
	$(_activate)
	if [ "0$(VERBOSE)" -gt 0 ] ; then
		(	set -x
			python -m build -v .
		)
	else
		(	set -x; python -m build . 2>/dev/null; ) | grep -vE '^[A-Za-z]\w+ing |^\* |^  - '
	fi
	$(_end)

# --------------------------------------------------------------
