# File: make/30-clean.mk

.PHONY : clean
clean : clear ## Remove generated files.
	@$(_begin)
	( 	set -x
		rm -rf dist
		find \( -regex '.*/(\..*|dist)' \) -prune -o -regex ".*\.egg-info" \
			-printf "+$${PS4}rm -rf %p\n" -exec rm -rf {} +
	)
	$(_end)

.PHONY : virgin
virgin : clean ## Remove generated files and the virtual environment.
	@$(_begin)
	(	set -x
		rm -rf .venv $(CACHE_DIR)
	)
	$(_end)

# 	find src -name "*.egg-info" -printf "$${PS4}rm -rf %p\n" -exec rm -rf {} +
# --------------------------------------------------------------
