.PHONY: help deps fmt lint type test check clean release

help:
	@echo "Targets:"
	@echo "  deps    Install dev dependencies (uv sync)"
	@echo "  fmt     Format (ruff)"
	@echo "  lint    Lint (shellcheck + ruff)"
	@echo "  type    Type check (pyright)"
	@echo "  test    Tests (pytest)"
	@echo "  check   fmt + lint + type + test"
	@echo "  release Create a GitHub Release via gh (VERSION optional)"

deps:
	@uv sync --group dev

fmt:
	@uv run ruff format .

lint:
	@echo "== shellcheck ==" && shellcheck -x -P SCRIPTDIR -e SC2034 scripts/*.sh docker/*.sh && \
	echo "== ruff ==" && uv run ruff check .

type:
	@uv run pyright

test:
	@uv run pytest

check: fmt lint type test

clean:
	@rm -rf dist/ htmlcov/ .pytest_cache/ .ruff_cache/

release:
	@bash scripts/release.sh "$(VERSION)"
