# File: make/50-install.mk

STUBS_FILE              = .typings.txt

# Concrete pyi files derived from STUBS_FILE lines
STUB_PYIS               = $(addsuffix /__init__.pyi,$(addprefix $(CACHE_DIR)/typings/,$(shell cat $(STUBS_FILE) 2>/dev/null || true)))

# Generate stubs using stubgen
define _stubgen
	(	set -x
		stubgen -p "$(1)" -o "$(2)" --include-private -q 2>/dev/null >/dev/null
	)
	if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then
		(	set -x
			stubgen -p "$(1)" -o "$(2)" --include-private -q --no-import --ignore-errors 2>/dev/null >/dev/null
		)
	fi
	if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then
		printf "\n*** stubgen '$(1)' failed ***\n\n" >&2
		exit 1
	fi
endef

# Insert a line into a file if not already present
define _awk_insert_line
	awk -v new_line='$(2)' '
		BEGIN { new_line_seen = 0; }
		{
			gsub(/\r/, "")
			if ($$0 ~ /^[[:space:]]*$$/) next
			if (!seen[$$0]++) print
			if ($$0 == new_line) new_line_seen = 1
		}
		END { if (!new_line_seen) print new_line; }
	' '$(1)' 2>/dev/null || true
endef

# Phony wrapper builds the dependency stamp
.PHONY : install-deps
install-deps : .venv/.deps ## Install dependencies
	@:

# Dependency installation stamp; rebuild when pyproject changes.
.venv/.deps : .venv pyproject.toml
	@$(_begin)
	if [ "0$(VERBOSE)" -gt 0 ]; then
		(	set -x
			$(VENV_BIN)/python -m pip install -e .[dev,test]
		)
	else
		(	set -x
			$(VENV_BIN)/python -m pip install -q -e .[dev,test]
		)
	fi
	touch "$@"
	$(_end)

# Generate stub for package %
.NOTINTERMEDIATE : $(CACHE_DIR)/typings/%/__init__.pyi
$(CACHE_DIR)/typings/%/__init__.pyi : .venv/.deps
	@$(_begin)
	$(_activate)
	$(call _stubgen,$*,$(CACHE_DIR)/typings)
	$(_end)

# Allow `make pkg.stub` to generate stubs and record the package name
.PHONY : %.stub
%.stub : $(CACHE_DIR)/typings/%/__init__.pyi
	@tmp='$(STUBS_FILE).tmp'; \
		$(call _awk_insert_line,$(STUBS_FILE),$*) > "$$tmp"; \
		mv "$$tmp" '$(STUBS_FILE)' 2>/dev/null || cp "$$tmp" '$(STUBS_FILE)'; \
		printf "Recorded stub entry: %s\n" "$*" 1>&2 || true

# Phony wrapper builds the inits stamp
.PHONY : install-inits
install-inits : .venv/.inits ## Regenerate __init__.py files
	@ :

# __init__ regeneration stamp; depends on version and script
.venv/.inits : .venv/.deps pyproject.toml $(VENV_BIN)/common_reset_inits.py
	@$(_begin)
	$(_activate)
	(	set -x
		python -P -s $(VENV_BIN)/common_reset_inits.py;
	)
	touch "$@"
	$(_end)

# Final install stamp depends on sub-stamps; no phony order-only deps.
#
# NOTE:
#   pip install -e . installs entry points like common_reset_inits.py and
#   common_sitecustomize_setup.py directly into $(VENV_BIN).
#   Do not attempt to relocate or re-generate them; they are managed by pip.
#
.PHONY : install
install : .venv/.install
# Use real deps to decide freshness, and order-only for phony tasks.
# This prevents always rebuilding when .venv/.install is newer than inputs.
.venv/.install : .venv/.deps .venv/.inits .venv/.stubs $(VENV_BIN)/common_sitecustomize_setup.py ## Install dependencies, generate stubs, and regenerate __init__.py files
	@$(_begin)
	$(_activate)
	(	set -x
		$(VENV_BIN)/common_sitecustomize_setup.py
		touch "$@"
	)
	$(_end)

# Stubs wrapper and stamp
.PHONY : install-stubs $(STUBS_PYIS)
install-stubs : .venv/.stubs ## Generate stubs for listed packages
	@$(_end)

.venv/.stubs : .venv $(STUBS_FILE) $(STUB_PYIS)
	@$(_begin)
	touch "$@"
	$(_end)

# --------------------------------------------------------------
