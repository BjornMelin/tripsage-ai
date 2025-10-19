#!/usr/bin/env bash
set -euo pipefail

# Remove ignored directories from git tracking without deleting working files.
# Usage: scripts/maintenance/untrack_ignored.sh

echo "Untracking ignored paths (docs/archive) without deleting files..."

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a git repository" >&2
  exit 1
fi

# Ensure .gitignore contains docs/archive/
if ! grep -qE '^docs/archive/?$' .gitignore 2>/dev/null; then
  echo "Warning: docs/archive/ is not in .gitignore; adding it now" >&2
  echo "docs/archive/" >> .gitignore
fi

# Untrack any already-tracked files under docs/archive and CLAUDE.md
git ls-files -z docs/archive | xargs -0 -r git rm -r --cached --ignore-unmatch
git ls-files -z CLAUDE.md | xargs -0 -r git rm --cached --ignore-unmatch

echo "Done. Commit the changes:"
echo "  git commit -m 'chore: untrack docs/archive per .gitignore'"
echo "  git push"
