#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

status=0

echo "== shellcheck =="
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/*.sh docker/*.sh || status=$?
else
  echo "shellcheck not found; skipping shell lint."
fi

echo
echo "== ruff (Python format + lint) =="
if command -v ruff >/dev/null 2>&1; then
  ruff format web.py || status=$?
  ruff check web.py || status=$?
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

exit "$status"
