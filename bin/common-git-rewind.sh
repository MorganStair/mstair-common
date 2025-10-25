#!/usr/bin/env bash
# File: common-git-rewind.sh
#
# Show a file at a given date (default: yesterday)

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path-to-file> [date]"
    exit 1
fi

file="$1"
date_str="${2:-yesterday}"

commit=$(git rev-list -1 --before="$date_str" HEAD -- "$file")

if [ -z "$commit" ]; then
    echo "No commit found before '$date_str' for $file"
    exit 2
fi

git show "${commit}:${file}"
