# File: build/40-venv.mk

.PHONY: venv
venv: .venv ## Create a virtual environment in .venv
.venv:
	@$(_begin)
	@trap "rm -rf .venv" INT TERM ERR; \
	set -x;
	python -m venv ".venv";
	mv -n $(VENV_BIN)/activate $(VENV_BIN)/activate-original
	mv -n $(VENV_BIN)/Activate.ps1 $(VENV_BIN)/ActivateOriginal.ps1
	mv -n $(VENV_BIN)/activate.bat $(VENV_BIN)/activate-original.bat
	mv -n $(VENV_BIN)/activate.fish $(VENV_BIN)/activate-original.fish
	cp -n scripts/venv-shims/* $(VENV_BIN)/
	cp -n scripts/sitecustomize.py .venv/Lib/site-packages/
	@trap "rm -rf .venv" INT TERM ERR; \
	$(_activate); \
	set -x; \
	python -m ensurepip --upgrade | /usr/bin/grep -vE '^(Looking in|Requirement already)' || true; \
	pip install -q --upgrade pip setuptools wheel
	@$(_end)

# --------------------------------------------------------------
