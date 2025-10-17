#!/usr/bin/env bash
#
# File: bin/reset_inits.sh
#
# Description:
#   Reset all __init__.py files in the given directory (or current directory if not specified)
#
# Usage:
#   bin/reset_inits.sh [directory]
#
# Example:
#   bin/reset_inits.sh src/mstair/common
#
set -euo pipefail
find "${1:-src}" -type f -name '__init__.py' | while read -r f; do
  p="${f#./}"
  cat >"$f" <<EOF
# File: $p

# <AUTOGEN_INIT>
pass
# </AUTOGEN_INIT>

# End of file: $p
EOF
  echo "reset: $p"
done
echo "Reset all __init__.py files"
