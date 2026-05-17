.PHONY: help deps build fmt lint type test check clean release

help:
	@echo "Targets:"
	@echo "  deps    Install dev dependencies (uv sync)"
	@echo "  build   Build local pipeline dependencies for webui local mode"
	@echo "  fmt     Format (ruff)"
	@echo "  lint    Lint (shellcheck + ruff)"
	@echo "  type    Type check (pyright)"
	@echo "  test    Tests (pytest)"
	@echo "  check   fmt + lint + type + test"
	@echo "  release Create a GitHub Release via gh (VERSION optional)"

deps:
	@bash scripts/deps.sh

build:
	@if command -v direnv >/dev/null 2>&1 && [ -f .envrc ]; then \
		direnv exec . bash scripts/build.sh; \
	else \
		bash scripts/build.sh; \
	fi

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
