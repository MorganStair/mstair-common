# File: build/50-install.mk

STUBS_FILE              = .typings.txt
STUBS                   = $(addsuffix .stub,$(shell cat $(STUBS_FILE) 2>/dev/null || true))

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

.PHONY: install-deps
install-deps: ## Install dependencies
	@:
	$(_begin)
	$(_activate)
	(	set -x
		pip install -q -e .[dev,test]
		touch $@
	)
	$(_end)

.PHONY : install-stubs $(STUBS)
install-stubs : $(STUBS) ; @$(_end) ## Generate stubs for listed packages

.NOTINTERMEDIATE : $(CACHE_DIR)/typings/%/__init__.pyi
$(STUBS) : %.stub : $(CACHE_DIR)/typings/%/__init__.pyi # Alias package.stub to package/__init__.pyi
	@$(_end)

.PHONY: %.stub
%.stub: ; @:
$(CACHE_DIR)/typings/%/__init__.pyi: # Generate stub for package %
	@$(_begin)
	$(_activate)
	$(call _stubgen,$*,$(CACHE_DIR)/typings)
	$(_end)

.PHONY: install-mkinit
install-mkinit: ## Regenerate __init__.py files using mkinit
	@$(_begin)
	@$(_activate)
	(	set -x
		bin/reset_inits.sh src/mstair
		mkinit src/mstair --inplace --noattrs --recursive
		rm -f src/mstair/__init__.py
	)
	$(_end)

.PHONY: install-format
install-format: ## Format code using ruff
	@$(_begin)
	@$(_activate)
	(	set -x
		ruff check src/mstair/common --fix
		ruff format src/mstair/common
	)
	@$(_end)

.PHONY: install
install:  install-deps install-mkinit install-stubs install-format ## Install dependencies, generate stubs, and regenerate __init__.py files
	@$(_end)

# --------------------------------------------------------------
