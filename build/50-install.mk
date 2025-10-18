# File: build/50-install.mk

STUBS_FILE              = .typings.txt
STUBS                   = $(addsuffix .stub,$(shell cat $(STUBS_FILE) 2>/dev/null || true))

# Generate stubs using stubgen
define _stubgen
        {
                set -x
                stubgen -p "$(1)" -o "$(2)" --include-private -q 2>/dev/null >/dev/null
        }
        if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then
                {
                        set -x
                        stubgen -p "$(1)" -o "$(2)" --include-private -q --no-import --ignore-errors 2>/dev/null >/dev/null
                }
        fi
        if [ ! -s "$(2)/$(1)/__init__.pyi" ]; then
                printf "\n*** stubgen '$(1)' failed ***\n\n" >&2
                exit 1
        fi
endef

# Insert a line into a file if not already present
define _awk_insert_line
        awk -v new_line='$(2)' '
                BEGIN { new_line_seen = 0 }
                {
                        gsub(/\r/, "")
                        if ($$0 ~ /^[[:space:]]*$$/) next
                        if (!seen[$$0]++) print
                        if ($$0 == new_line) new_line_seen = 1
                }
                END { if (!new_line_seen) print new_line; }
        ' '$(1)' 2>/dev/null || true
endef


.PHONY: install-mkinit
install-mkinit: ## Regenerate __init__.py files for package src/mstair/common
        @${_begin}
        ${_activate}
        {
                set -x
                bin/reset_inits.sh src/mstair
                mkinit src/mstair --inplace --noattrs --recursive
                rm -f src/mstair/__init__.py
                ruff format src/mstair
        }
        ${_end}

.PHONY : install-stubs $(STUBS)
install-stubs : $(STUBS) ; @$(_end) ## Generate type stubs for packages listed in STUBS_FILE

.NOTINTERMEDIATE : $(CACHE_DIR)/typings/%/__init__.pyi

$(STUBS) : %.stub : $(CACHE_DIR)/typings/%/__init__.pyi ; @:
.PHONY: %.stub
%.stub: ; @:

$(CACHE_DIR)/typings/%/__init__.pyi:
        @$(_begin)
                pip install -q --upgrade pip setuptools wheel
        }
        $(_end)

.PHONY: install
install: .venv/.install install-mkinit install-stubs; @: ## Install packages into the .venv
.venv/.install: .venv
        $(_begin)
        $(_activate)
        {
                set -x
                pip install -q -e .[dev,test]
                touch $@
        }
        $(_end)


# --------------------------------------------------------------
