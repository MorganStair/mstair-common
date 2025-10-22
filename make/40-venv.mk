# File: make/40-venv.mk

.PHONY : venv
venv : .venv ## Create a virtual environment in .venv
.venv :
	@$(_begin)
	trap "rm -rf .venv" INT TERM ERR
	(	set -x
		python -m venv ".venv"
	)
	if [ "0$(VERBOSE)" -gt 0 ]; then
		(	set -x
			$(VENV_BIN)/python -m ensurepip --upgrade
		)
	else
		(	set -x
			$(VENV_BIN)/python -m ensurepip --upgrade
		) | grep -vE '^(Looking in|Requirement already)' || true
	fi
	(	set -x
		$(VENV_BIN)/python -m pip install -q --upgrade pip setuptools wheel
	)
	@$(_end)

# --------------------------------------------------------------
