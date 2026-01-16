# Contributing to mini-mesh

Thanks for your interest in contributing! This document covers development setup and guidelines.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [shellcheck](https://www.shellcheck.net/) for shell script linting

### Quick Start

```bash
# Clone the repository
git clone https://github.com/hummat/mini-mesh.git
cd mini-mesh

# Install development dependencies
uv sync --group dev

# Run all checks
scripts/lint.sh
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test
uv run pytest tests/ -k test_name -v

# Run only unit tests
uv run pytest tests/ -m unit
```

## Code Style

### Bash Scripts

- 2-space indentation
- `set -e` at the top of scripts
- `snake_case` for variables and functions
- Quote variables: `"$var"` not `$var`
- Use `[[ ]]` for conditionals

### Python

- 4-space indentation
- Type hints for function signatures
- Follow existing patterns in `webui.py`
- Run `ruff check` and `pyright` before committing

### Configuration Files

- Model configs are Bash arrays in `config/*.sh`
- Follow naming convention: `{model}-{capacity}-{duration}.sh`

## Architecture

Before making changes, read the architecture docs:

- `docs/agent/architecture.md` - Pipeline structure and single source of truth
- `docs/agent/code_conventions.md` - Detailed style guide
- `docs/agent/testing_patterns.md` - Testing approach

### Key Principle: Single Source of Truth

`scripts/run.sh` is the canonical reference for the pipeline. When adding flags:

1. Add to `scripts/run.sh` first
2. Update `webui.py` to expose in the UI
3. Update `docker/run.sh` if needed
4. Update `README.md` documentation

## Pull Request Process

1. **Create an issue first** for non-trivial changes
2. **Fork and branch** from `main`
3. **Make your changes** following the style guide
4. **Run `scripts/lint.sh`** - all checks must pass
5. **Update documentation** if adding/changing features
6. **Submit PR** using the template

### Commit Messages

- Use present tense: "Add feature" not "Added feature"
- Keep the first line under 72 characters
- Reference issues: "Fix crash on export (#42)"

## What to Contribute

### Good First Issues

- Documentation improvements
- Adding test coverage
- Bug fixes with clear reproduction steps

### Feature Ideas

- New model configurations
- Export format options
- UI improvements

### Before Starting Large Features

Please open an issue first to discuss the approach. This helps avoid duplicate work and ensures the feature aligns with project goals.

## Questions?

- Open a [Discussion](https://github.com/hummat/mini-mesh/discussions) for questions
- Check existing [Issues](https://github.com/hummat/mini-mesh/issues) for known problems
