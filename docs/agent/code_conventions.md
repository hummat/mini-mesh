# Code Conventions

## Bash (scripts/)
- Shebang: `#!/usr/bin/env bash`
- Always include `set -e`
- Indentation: 2 spaces
- Naming: lowercase with underscores (`video_input_dir`, `run_sfm_step`)
- Extend existing case/flag patterns in `scripts/run.sh`; don't invent new ones
- Source configs with `source config/<name>.sh`

## Python (webui.py, tests/)
- Indentation: 4 spaces
- Type hints from `typing` module where useful
- Snake_case names
- Keep side effects in `run()`/`run_workflow()`
- Follow Zen of Python

## Configuration (config/*.sh)
- Format: `CONFIG=(--flag1 value1 --flag2 value2 ...)`
- Use Nerfstudio CLI flags consistent with existing configs
- Add new configs as separate files in `config/`

## Python Config (pyproject.toml)
- Build backend: hatchling
- Dev deps in `[dependency-groups]` for uv sync
- Tool config: pytest, coverage, ruff, pyright

## Making Changes
- Minimal diffs; don't reformat unrelated code
- Match existing patterns in the file you're editing
- For multi-file edits: label filenames clearly, keep changes localized
- When adding/modifying flags: update `README.md`, `AGENTS.md`, `web.py`, and Docker wrappers
- Keep old spellings/semantics working; add new flags instead of repurposing

## Principles
- KISS principle: simplest solution that works
- No new heavy dependencies when Bash/Docker/SDFStudio CLI are sufficient
- Backward compatible unless explicitly requested
- Treat `docker/Dockerfile` as canonical; avoid `Dockerfile_bak`
