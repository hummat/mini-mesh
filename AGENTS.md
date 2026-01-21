# Repository Guidelines

**GitHub**: `hummat/mini-mesh`

Read relevant `docs/agent/` files before proceeding:

- `workflow.md` — **read before starting any feature** (issues, branching, PRs)
- `architecture.md` — **read before modifying pipeline or structure**
- `code_conventions.md` — **read before writing code**
- `testing_patterns.md` — **read before writing tests**
- `releases.md` — **read before releasing** (conventional commits, git-cliff)

**REQUIRED: Read `docs/agent/workflow.md` before implementing, updating, fixing, or changing anything.**

---

## Quick Reference

```bash
# Run pipeline
scripts/run.sh /path/to/input [video|sfm|process|train|export ...]
docker/run.sh /path/to/input [same options]

# Dev
scripts/lint.sh              # shellcheck + ruff + pyright + pytest
uv run pytest tests/ -k foo  # run specific test
```

## Key Files

- `scripts/run.sh` — single source of truth for pipeline contract
- `config/defaults.sh` — base defaults for all model types
- `webui.py` — Gradio UI wrapping run.sh

## Workflow

1. Read files before editing
2. Run `scripts/lint.sh` after changes
3. Update `README.md`, `webui.py`, Docker wrappers when changing flags
4. Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `refactor:`
