# File: build/30-clean.mk

.PHONY: virgin
virgin: clean ## Remove all generated files and the virtual environment.
	@$(_begin)
	{ set -x; rm -rf .venv; }
	$(_end)

.PHONY: clean
clean: clear ## Remove all generated files, but not the virtual environment.
	@$(_begin)
	{ set -x; rm -rf $(CACHE_DIR) dist uploads *.log *.tmp; }
	find . -name .venv -prune -o -type d -name "*.egg-info" \
		-exec $${SHELL} -x -c 'rm -rf "$@"' _ {} +
	$(_end)

# --------------------------------------------------------------
