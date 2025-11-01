#!/usr/bin/env bash
set -euo pipefail

# Scrub Supabase project identifiers from full git history using git-filter-repo.
#
# WARNING: This rewrites history. Only run on disposable branches or
#           coordinate with your team before force-pushing.
#
# Requirements:
#   - git
#   - git-filter-repo (https://github.com/newren/git-filter-repo)
#
# Usage:
#   ./scripts/security/supabase_history_scrub.sh
#   # then force-push the rewritten branch after validation

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

if ! command -v git >/dev/null; then
  echo "git is required" >&2; exit 1
fi

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo is required (pipx install git-filter-repo or see project README)" >&2
  exit 2
fi

# Create a safety tag and a working branch
SAFE_TAG="pre-supabase-scrub-$(date +%Y%m%d_%H%M%S)"
git tag "$SAFE_TAG"
git checkout -b chore/history-scrub-supabase

REPLACE_FILE="scripts/security/git-filter-replace.txt"
if [ ! -f "$REPLACE_FILE" ]; then
  echo "Missing $REPLACE_FILE" >&2; exit 3
fi

git-filter-repo \
  --quiet \
  --replace-text "$REPLACE_FILE" \
  --force

echo "History rewritten. Verify with: git log -p -n 5 and ripgrep for sensitive tokens."
echo "When satisfied, force-push: git push -u origin chore/history-scrub-supabase --force-with-lease"

