#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

status=0

echo "== shellcheck =="
if command -v shellcheck >/dev/null 2>&1; then
  # SC2034 is noisy for intentionally-set but externally-used env vars (e.g. thread hints).
  shellcheck -e SC2034 scripts/*.sh docker/*.sh || status=$?
else
  echo "shellcheck not found; skipping shell lint."
fi

echo
echo "== ruff (Python lint) =="
if command -v ruff >/dev/null 2>&1; then
  ruff check webui.py tests || status=$?
else
  echo "ruff not found; skipping Python lint."
fi

echo
echo "== pyright (type checking) =="
if command -v pyright >/dev/null 2>&1; then
  pyright || status=$?
else
  echo "pyright not found; skipping type checking."
fi

echo
echo "== pytest (unit tests) =="
if command -v pytest >/dev/null 2>&1; then
  pytest || status=$?
else
  echo "pytest not found; skipping tests."
fi

exit "$status"
