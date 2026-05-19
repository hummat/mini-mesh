# Testing Patterns

## Toolchain
- **Runner**: pytest
- **Coverage**: pytest-cov (target: ≥80%)
- **Types**: pyright (must pass, 0 errors)
- **Lint**: ruff
- **Shell**: shellcheck
- **Package manager**: uv
- **All-in-one**: `make check` (runs all checks; CI uses `scripts/lint.sh`)

## Commands
```bash
# Makefile targets (preferred)
make check       # fmt + lint + type + test (all-in-one)
make fmt         # format code (ruff)
make lint        # lint (shellcheck + ruff)
make type        # type check (pyright)
make test        # run tests (pytest)

# Direct uv commands (when you need specific options)
uv run pytest tests/ -v               # verbose output
uv run pytest tests/ -k test_name     # run specific tests
uv run pytest tests/ --cov=webui --cov-report=term-missing
```

## Package Management
```bash
make deps                    # install dev deps (preferred)
uv sync --group dev          # same as above, explicit
uv add <package>             # add dependency
uv run <command>             # run in uv environment
```

## Test Organization
- Tests are in `tests/test_webui.py` (≈100 tests)
- Tests cover command construction/validation for `webui.py`
- `conftest.py` contains shared fixtures
- Core CI installs only the default/dev dependency set. Tests that need optional
  ML packages such as Torch must import them lazily with `pytest.importorskip`
  inside the specific test or fixture, never at module import time.

## What Gets Tested
- `webui.py` command line argument construction
- Validation that `webui.py` arguments align with `scripts/run.sh` contexts/defaults/flags
- NOT the underlying 3D reconstruction pipeline (that's integration territory)

## Integration Validation
To validate the end-to-end pipeline:
1. Run a small example: `scripts/run.sh scene.mp4 video --fps 2 sfm --method glomap process train --model neus-facto --config neus-facto-short export --resolution 512`
2. Verify outputs:
   - `images/`, `sparse/`, `transforms.json`, `train/<exp>/<model>/run/config.yml` created
   - `mesh.ply` and textures written in experiment directory

## When You Touch `webui.py`
- MUST add tests for new functionality in `tests/test_webui.py`
- Run `make check` locally before commit
- Verify arguments still line up with `scripts/run.sh`

## When You Touch Bash/Docker
- Test both `scripts/run.sh` and `docker/run.sh` where relevant
- Run `shellcheck` on modified shell scripts
