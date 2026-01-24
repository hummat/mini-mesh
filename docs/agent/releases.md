# Releases

## Prerequisites

```bash
# Check if git-cliff is installed
git-cliff --version || cargo install git-cliff  # or: brew install git-cliff
```

## Creating a Release

```bash
# 1. Bump version in pyproject.toml
# 2. Generate changelog
git cliff -o CHANGELOG.md

# 3. Commit version bump and changelog
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): prepare v0.X.Y"

# 4. Create and push tag
git tag v0.X.Y
git push origin main --tags

# 5. Create GitHub release with generated notes
git cliff --latest --strip header | gh release create v0.X.Y --notes-file -
```

## Changelog Generation

```bash
# Generate full changelog
git cliff -o CHANGELOG.md

# Preview unreleased changes
git cliff --unreleased

# Generate notes for specific release
git cliff --latest --strip header
```

## Version Bumping

Manual bump in `pyproject.toml`:

- Pre-1.0: minor = breaking, patch = non-breaking
- Post-1.0: semver (major.minor.patch)

## Conventional Commits

**Required format:** `type(scope): description`

| Type | Purpose | Version Impact |
|------|---------|----------------|
| `feat:` | New feature | Minor bump |
| `fix:` | Bug fix | Patch bump |
| `docs:` | Documentation only | Patch bump |
| `refactor:` | Code restructure, no behavior change | Patch bump |
| `perf:` | Performance improvement | Patch bump |
| `test:` | Adding/updating tests | Patch bump |
| `chore:` | Build, CI, tooling | Patch bump |
| `ci:` | CI configuration | Patch bump |
| `revert:` | Revert previous commit | Depends |

**Scope** (optional): Component affected, e.g., `fix(export):`, `feat(webui):`

**Breaking changes:** Add `!` after type or include `BREAKING CHANGE:` in body:
```
feat!: Remove deprecated config option
feat(export)!: Change default resolution
```

## Examples

```
feat: Add new texturing options to export script
fix(export): Handle missing argument values gracefully
docs: Update installation instructions
chore: Bump sdfstudio to v0.8.0
refactor(webui): Simplify config loading
ci: Fix shellcheck to follow sourced files
```

## Key Files

- `cliff.toml` — git-cliff changelog config
- `pyproject.toml` — version source of truth

## Docker Image Publishing

Docker images are built locally (due to long CUDA compile times) and distributed via CI.

### Build Variants

Use `docker/build.sh` for all builds:

```bash
docker/build.sh full    # Multi-GPU, all deps (~11.6GB)
docker/build.sh slim    # Multi-GPU, core only (~9GB)
docker/build.sh local   # Single GPU, native optimizations (auto-detects GPU)
```

| Variant | Tag | Size | GPU Support | Optional Deps |
|---------|-----|------|-------------|---------------|
| `full` | `hummat/mini-mesh:latest` | ~11.6GB | GTX 16xx / RTX 20xx – RTX 40xx | Yes |
| `slim` | `hummat/mini-mesh:slim` | ~9GB | GTX 16xx / RTX 20xx – RTX 40xx | No |
| `local` | `hummat/mini-mesh:local` | ~8GB | Your GPU only | Yes |

**Options:**
```bash
docker/build.sh local --cuda-arch 89   # Explicit compute capability
docker/build.sh full --max-jobs 4      # Limit parallel jobs
docker/build.sh slim --no-gui          # Headless COLMAP
```

> **Note:** `local` uses `-march=native` for CPU-specific optimizations — don't publish these images!

### Publish Workflow

```bash
# 1. Build full and slim images (see above)

# 2. Test images
docker run --rm hummat/mini-mesh:latest --help
docker run --rm hummat/mini-mesh:slim --help

# 3. Push to Docker Hub (manual)
docker login
docker push hummat/mini-mesh:latest
docker push hummat/mini-mesh:slim

# 4. Trigger CI to mirror and tag
#    Actions → "Publish Docker image" → Run workflow → enter version (e.g., 0.3.0)
```

CI workflow (`.github/workflows/docker-publish.yml`):
- Pulls `hummat/mini-mesh:latest` from Docker Hub
- Tags with version on Docker Hub
- Mirrors to GHCR with `latest` and version tags

### Registries

| Registry | URL |
|----------|-----|
| Docker Hub | `hummat/mini-mesh` (default in README) |
| GHCR | `ghcr.io/hummat/mini-mesh` |

### Required Secrets

- `DOCKERHUB_USERNAME` — Docker Hub username
- `DOCKERHUB_TOKEN` — Docker Hub access token (hub.docker.com → Account Settings → Security)

### When to Publish

Publish Docker images when:
- Dockerfile changes
- Base dependencies change (COLMAP, GLOMAP, sdfstudio versions)
- Major releases that users should pull fresh

Not every code release needs a new image — the image provides the environment, `scripts/run.sh` is mounted at runtime.

## Troubleshooting

- "Working tree is dirty" → commit or stash first
- "Tag exists" → `git tag -d vX.Y.Z` then `git push --delete origin vX.Y.Z`
- Docker push fails → check `DOCKERHUB_TOKEN` secret is set and not expired
