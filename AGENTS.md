# Repository Guidelines

This file is the single source of truth for agent instructions in this repo.
`CLAUDE.md` is a symlink to this file.

## Conventions

Read relevant `docs/agent/` files before proceeding:
- `workflow.md` — **read before starting any feature** (issues with labels, branching, PRs)
- `code_conventions.md` — **read before writing code** (style, typing, minimal diffs)
- `architecture.md` — read before modifying pipeline or structure
- `testing_patterns.md` — read before writing tests
- `releases.md` — read before releasing (conventional commits, git-cliff)

**REQUIRED: Read `docs/agent/workflow.md` before implementing, updating, fixing, or changing anything.**

---

## Project Overview

- **Type:** Video-to-3D mesh reconstruction pipeline
- **Entry point:** `scripts/run.sh` (single source of truth for pipeline contract)
- **Goal:** Convert videos to textured 3D meshes via SfM → neural reconstruction → export

## Architecture & Key Files

Pipeline orchestrated by Bash scripts (`scripts/`). Configuration in `config/*.sh`.

- `scripts/run.sh` — canonical pipeline entry point
- `config/defaults.sh` — base defaults for all model types
- `webui.py` — Gradio UI wrapping run.sh
- `docker/run.sh` — Docker wrapper for run.sh

Key flows:
- `video` → extract frames (ffmpeg)
- `sfm` → structure from motion (COLMAP/GLOMAP/HLoc/VGGSfM)
- `process` → prepare data for training
- `train` → neural surface reconstruction (sdfstudio)
- `export` → extract and texture mesh

## Commands

```bash
# Install
uv sync --group dev           # via uv (matches CI)
pip install -e ".[dev]"       # editable + dev tools

# Run pipeline
scripts/run.sh /path/to/input [video|sfm|process|train|export ...]
docker/run.sh /path/to/input [same options]

# Dev (use Makefile or directly)
make check                    # fmt + lint + type + test
scripts/lint.sh               # shellcheck + ruff + pyright + pytest

# Tests
uv run pytest tests/ -k foo   # run specific test
```

## Project-Specific Style

- Python >= 3.11; lines ≤ 120 chars (see `[tool.ruff]`)
- Bash: 2-space indent, `set -e`, quote variables
- Keep `scripts/run.sh` as canonical reference; update `webui.py`, `docker/run.sh`, `README.md` when changing flags

## Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`

Examples:
```
feat(export): Add glTF compression option
fix(webui): Handle missing video file gracefully
docs: Update installation instructions
```

See `docs/agent/releases.md` for full details.

## Code Workflow

1. **Before editing**: read files first; understand existing code
2. **After code changes**: `make check` (or `scripts/lint.sh`)
3. **Doc check**: explicitly verify if docs need updating
4. **Pipeline changes**: update `README.md`, `webui.py`, Docker wrappers
