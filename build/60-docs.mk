# File: build/60-docs.mk

.PHONY: docs
docs: # Generate documentation in docs/
        @: No documentation to generate yet

.PHONY: docs-serve
docs-serve: docs # Helper to generate and serve documentation locally
        @set -x
        python -m http.server 8000 --directory docs/

# --------------------------------------------------------------
