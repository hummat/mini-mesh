# Repository Guidelines

## Project Structure & Module Organization
- CLI entrypoints live in `scripts/` (`run.sh`, `ffmpeg.sh`, `sfm.sh`, `dl_sfm.sh`, `train.sh`, `export.sh`) and orchestrate the 5‑step pipeline (video → SfM → process → train → export).
- Training and model hyperparameters are defined as Bash arrays in `config/*.sh` and are sourced by `scripts/train.sh` together with `config/defaults.sh`.
- `config/defaults.sh` defines `DEFAULTS` (SDF models), `NERF_DEFAULTS`, `SPLAT_DEFAULTS`, `DATA_DEFAULTS` (SDF data processing), and `NS_DATA_DEFAULTS` (NeRF data processing).
- Docker assets in `docker/` provide a fully configured runtime (COLMAP, GLOMAP, SDFStudio, Nerfstudio, tiny-cuda-nn, optional: rembg, sam2, hloc, vggsfm); `web.py` exposes the pipeline via a Gradio UI.
- The root contains project docs (`README.md`, `AGENTS.md`); there is currently no `tests/` directory.

## Architecture Overview
- `scripts/run.sh` is the single source of truth for the pipeline contract (contexts, flags, skip/overwrite semantics); `docker/run.sh` and `web.py` are thin wrappers around it.
- `scripts/train.sh` resolves config names to `config/*.sh` and dispatches to `sdf-train` (for SDF models) or `ns-train` (for NeRF/splat models); do not duplicate this logic elsewhere.
- `scripts/export.sh` handles mesh extraction and texturing, dispatching to `sdf-extract-mesh`/`sdf-texture-mesh` (for SDF models) or `ns-export` (for NeRF models).
- Advanced SfM methods (`hloc`, `vggsfm`) are delegated to `scripts/dl_sfm.sh`, which requires the tools to be in PATH.

## Build, Test, and Development Commands
- Manual run (local toolchain): `scripts/run.sh /path/to/video_or_images [global_opts] [video|sfm|process|train|export …]`.
- Docker run (recommended for contributors): `docker/run.sh /path/to/video_or_images [same options]`.
- Web UI: `python web.py` then point a browser to the reported Gradio URL.
- Example with contexts: `scripts/run.sh scene.mp4 video --fps 2 sfm --method glomap process --mask rembg train --model neus-facto --config neus-facto-fast export --resolution 2048`.
- For very fast smoke tests, downscale work: `train --config neus-grid-dev export --resolution 512`.
- NeRF workflow example: `scripts/run.sh scene.mp4 video --fps 1 sfm --method glomap process train --model nerfacto --config nerfacto-dev export --method poisson`.

## Coding Style & Naming Conventions
- Bash: `#!/usr/bin/env bash`, `set -e`, 2‑space indentation, lowercase names with `_`; extend existing case/flag patterns in `scripts/run.sh` rather than inventing new ones.
- Python (`web.py`): 4‑space indentation, type hints where useful, snake_case names; keep side effects in `run()`/`run_workflow()`.
- Add new configs as `CONFIG=(...)` files in `config/`, using Nerfstudio CLI flags consistent with existing ones.

## Testing Guidelines
- No formal unit tests; validate changes by running a small example and checking that:
  - `images/`, `sparse/`, `transforms.json`, and `train/<exp>/<model>/config.yml` are created.
  - `mesh.ply` and textures are written in the experiment directory.
- When changing Docker or CLI behavior, test both `scripts/run.sh` and `docker/run.sh` where relevant.
- If you touch `web.py`, verify that its arguments still line up with `scripts/run.sh` (contexts, defaults, and flags).

## Commit & Pull Request Guidelines
- Follow the existing log style: short, imperative summaries (e.g., `Add CLAUDE.md with project and usage guidelines`).
- PRs should describe what changed, why, and how you validated it (commands + sample input), and call out any new flags, configs, or GPU/VRAM assumptions.
- Include screenshots or meshes for visible quality changes when practical.

## Agent-Specific Instructions
- Prefer minimal, targeted edits over large refactors; do not introduce new heavy dependencies when Bash, Docker, and the SDFStudio CLI are sufficient.
- Mirror existing patterns in `scripts/run.sh`, `scripts/train.sh`, and `config/*.sh`; keep behavior backward compatible unless explicitly requested.
- When adding or changing flags:
  - Update `README.md`, `AGENTS.md`, `web.py`, and any Docker wrapper that surfaces them.
  - Keep old spellings/semantics working where possible; introduce new flags instead of repurposing existing ones.
- Avoid editing `docker/Dockerfile_bak` unless you consciously need the older build path; treat `docker/Dockerfile` as canonical.
- Before large edits, skim this file to align with project expectations and existing workflows.

### Communication Style
- You are a tool, not a buddy. Be direct, blunt, and practical. No sugar-coating.
- Share strong opinions when appropriate. Be concise but clear.
- No conversational fluff or greetings unless the user initiates it.
- Prioritize clarity and usefulness over politeness.
- Ask precise clarifying questions when something is unclear.
- Be concise, humble, direct, practical, exact, precise, thorough, methodical, deliberate, conservative, and skeptical.

### Code Quality Principles
- Strictly adhere to the KISS principle (Keep It Simple, Stupid).
- Follow the Zen of Python for all Python code.
- Use type hints from the `typing` module in Python code.
