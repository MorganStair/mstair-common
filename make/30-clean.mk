# File: make/30-clean.mk

.PHONY : virgin
virgin : clean ## Remove all generated files and the virtual environment.
	@$(_begin)
	(	set -x
		rm -rf .venv
	)
	$(_end)

.PHONY : clean
clean : clear ## Remove all generated files, but not the virtual environment.
	@$(_begin)
	( 	set -x
		rm -rf $(CACHE_DIR) dist uploads
		find \( -regex '.*/\..*' \) -prune -o -regex ".*\.egg-info" \
			-printf "+$${PS4}rm -rf %p\n" -exec rm -rf {} +
	)
	$(_end)

# 	find src -name "*.egg-info" -printf "$${PS4}rm -rf %p\n" -exec rm -rf {} +
# --------------------------------------------------------------
