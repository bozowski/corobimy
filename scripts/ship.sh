#!/usr/bin/env bash
# Usage: ./scripts/ship.sh [branch-name]
# Creates a branch, pushes it, and opens a PR against main.
# If branch-name is omitted, one is generated from the latest commit message.

set -euo pipefail

MAIN="main"

# Determine branch name
if [[ $# -ge 1 ]]; then
  BRANCH="$1"
else
  # Slugify the last commit subject: lowercase, spaces→hyphens, strip non-alphanum/hyphen
  SLUG=$(git log -1 --pretty=%s | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 ]//g' | tr ' ' '-' | sed 's/-\+/-/g' | cut -c1-50)
  BRANCH="${SLUG}-$(date +%s)"
fi

# Refuse to run on main itself
CURRENT=$(git branch --show-current)
if [[ "$CURRENT" == "$MAIN" ]]; then
  git checkout -b "$BRANCH"
else
  BRANCH="$CURRENT"
fi

echo "Branch: $BRANCH"

git push -u origin "$BRANCH"

gh pr create \
  --base "$MAIN" \
  --head "$BRANCH" \
  --fill

echo ""
echo "PR opened. Waiting for CI to pass, then merge with:"
echo "  gh pr merge $BRANCH --squash --delete-branch"
