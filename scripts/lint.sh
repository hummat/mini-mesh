#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

status=0

echo "== shellcheck =="
# SC2034: noisy for intentionally-set but externally-used env vars
# SC1091: can't follow sourced files (expected, not an error)
# Note: shellcheck is not a Python package and must be system-installed
if ! command -v shellcheck >/dev/null 2>&1; then
  echo "WARNING: shellcheck not found, skipping shell linting"
else
  shellcheck -e SC2034 -e SC1091 scripts/*.sh docker/*.sh || status=$?
fi

echo
echo "== ruff (Python lint) =="
uv run ruff check webui.py tests || status=$?

echo
echo "== pyright (type checking) =="
uv run pyright || status=$?

echo
echo "== pytest (unit tests) =="
uv run pytest || status=$?

exit "$status"
