# Migration Plan: `video-to-mesh` → `mini-mesh`

This document tracks the migration of features from the internal **`video-to-mesh`** repository into the open‑source **`mini-mesh`** project.

Goal: **Port all user‑facing features** (CLI pipeline, models, configs, SfM modes, masking, export methods, etc.) from `video-to-mesh` to `mini-mesh`, while **excluding internal infra** such as Cissy, Conan, Jenkins, SLURM‑specific behavior, and internal URLs.

---

## 0. Scope & Principles

- [x] Treat `mini-mesh` as the long‑term public home; `video-to-mesh` is the source of additional features.
- [x] Port *features and behavior*, not internal tooling:
  - Do **not** add Cissy, Conan, Jenkins, or DLR‑specific infrastructure.
  - Avoid hard‑coded internal hosts/URLs; keep everything generic.
- [x] Prefer `video-to-mesh` semantics when there is a conflict; backward compatibility with the current `mini-mesh` behavior is **not** required.
- [x] Keep changes coherent and aligned with existing patterns in:
  - `scripts/run.sh`
  - `scripts/train.sh`
  - `config/*.sh`

---

## 1. Core Pipeline Contract (`scripts/run.sh`)

- [x] Review differences between:
  - `mini-mesh/scripts/run.sh`
  - `video-to-mesh/scripts/run.sh`
- [x] Align context model, using `video-to-mesh` as the behavioral reference:
  - [x] Introduce a dedicated `process` context (currently implicit in `mini-mesh`).
  - [x] Ensure context order and semantics: `video → sfm → process → train → export`.
- [x] Harmonize global flags:
  - [x] `--shared` dropped (only useful for internal/HPC shared filesystems).
  - [x] `--mail <addr>` implemented with generic logging (no SLURM dependency).
- [x] Align per‑context `--skip` / `--overwrite` semantics with `video-to-mesh`.
- [x] Ensure directory layout and naming remain consistent:
  - `images/`, `images_orig/`, `sparse/`, `transforms.json`, `train/<exp>/<model>/config.yml`, `mesh.ply`.

---

## 2. Data Processing & Masking (`process` stage)

**Files:** `scripts/run.sh`, new or existing `process` logic.

- [x] Extract current fixed `ns-process-data` call in `mini-mesh/scripts/run.sh` into a proper `process` context.
- [x] Mirror `video-to-mesh` `process` behavior:
  - [x] Use `sdf-process-data images` with:
    - `--data`, `--output_dir`, `--skip-colmap`, `--colmap-model-path`.
  - [x] Support additional CLI args passed via `process` context:
    - [x] `--min-match-ratio`
    - [x] `--crop-factor`
    - [x] Any other sdf-process-data flags (pass-through via process_args)
- [x] Port background masking options from `video-to-mesh`:
  - [x] `--mask rembg|sam2|true|none`:
    - [x] Invoke `rembg` when selected and available in `PATH`.
    - [x] Invoke `sam2` for SAM2 masking if available.
    - [x] Use `masks/` directory when `--mask true`.
  - [x] Integrate masking with directory handling (`masks/`, `images_orig/`).
- [x] Adjust training defaults when masking is enabled:
  - [x] For SDF models, override to `--pipeline.model.background-model none` and adjust mixed precision, matching `video-to-mesh`.
  - [x] For NeRF‑style models, match `video-to-mesh` background behavior (e.g., random background color).

---

## 3. SfM & Deep SfM (`sfm.sh`, `dl_sfm.sh`)

**Files:** `scripts/sfm.sh`, `scripts/dl_sfm.sh`, `scripts/run.sh`.

- [x] Replace or extend `mini-mesh/scripts/sfm.sh` with richer `video-to-mesh` version (minus infra):
  - [x] Add CLI options:
    - `--database_path`
    - `--camera_model`
    - `--matcher`
    - `--extra`
    - `--refine_principal_point`
    - `--convert_txt`
    - `--undistort`
    - `--overwrite`
    - `--num_threads`
    - `--use_glomap`
  - [x] Keep thread selection generic (use `nproc`, avoid SLURM‑only assumptions).
- [x] Replace or extend `mini-mesh/scripts/dl_sfm.sh` with feature‑complete version:
  - [x] Check for commands in PATH instead of auto-installing (hloc, vggsfm-video, vggsfm-image).
  - [x] Port richer CLI from `video-to-mesh`:
    - `--method hloc|vggsfm`
    - `--matcher`
    - `--hloc_feature`
    - `--hloc_matcher`
    - `--hloc_weights`
    - `--hloc_camera`
    - `--vggsfm_max_points`
    - `--vggsfm_max_tri_points`
    - `--overwrite`
  - [x] Ensure behavior on existing sparse/database dirs matches `video-to-mesh` semantics.
- [x] Integrate advanced SfM options into `mini-mesh/scripts/run.sh`:
  - [x] `sfm` context `--method colmap|glomap|hloc|vggsfm`.
  - [x] Pass through additional CLI args to `sfm.sh` and `dl_sfm.sh` as in `video-to-mesh`.
- [x] Explicitly avoid Cissy‑based SfM calls; rely only on locally installed binaries and the Docker image.

---

## 4. Training Pipeline & Config System (`train.sh`, `config/*.sh`)

**Files:** `scripts/train.sh`, `config/defaults.sh`, additional `config/*.sh`.

- [x] Compare training behavior:
  - `mini-mesh/scripts/train.sh` (currently `sdf-train` only).
  - `video-to-mesh/scripts/train.sh` (SDF vs NeRF branches).
- [x] Data processing flags already handled in `scripts/train.sh`:
  - [x] `--downscale-factor`, `--scale-factor`, `--center-method`, `--orientation-method`, `--auto-scale-poses`, `--train-split-fraction` (lines 62-68).
  - [x] These are train context flags passed to nerfstudio-data parser, not process context.
- [x] Extend `config/defaults.sh`:
  - [x] Port `NERF_DEFAULTS`, `SPLAT_DEFAULTS`, `NS_DATA_DEFAULTS` from `video-to-mesh`.
  - [x] Reconcile camera optimizer defaults:
    - Adopted `video-to-mesh` defaults (lr 1e-5, lr-final 1e-6, max-steps 25000).
- [x] Update `scripts/train.sh` to support multiple model families:
  - [x] For model names containing `nerf`, `splat`, or `ngp`:
    - [x] Call `ns-train` with `NERF_DEFAULTS`/`SPLAT_DEFAULTS` and `NS_DATA_DEFAULTS`.
  - [x] For SDF‑style models (neus, neus-facto, neuralangelo, etc.):
    - [x] Already uses `sdf-train` (updated from `ns-train`).
- [x] Port additional configs from `video-to-mesh/config/`:
  - [x] `nerfacto.sh`
  - [x] `nerfacto-dev.sh`
  - [x] `nerfacto-big.sh`
  - [x] `nerfacto-huge.sh`
- [x] Update or replace existing `mini-mesh` configs (`neus*`, `neus-grid-*`, `neus-facto-*`, `neuralangelo-*`) to match `video-to-mesh` behavior exactly.

---

## 5. Export System (`export.sh` + `run.sh`)

**Files:** `scripts/export.sh` (new in mini-mesh), `scripts/run.sh`.

- [x] Add `scripts/export.sh` to `mini-mesh`, derived from `video-to-mesh/scripts/export.sh`:
  - [x] Implement export for SDF models:
    - `sdf-extract-mesh`
    - `sdf-texture-mesh`
  - [x] Implement export for NeRF/NGP/splat models via `ns-export`:
    - Methods: `poisson`, `tsdf`, `pointcloud`, `gaussian-splat`.
  - [x] Support CLI args:
    - `--resolution`
    - `--bounding-box-min`, `--bounding-box-max`
    - `--marching-cube-threshold`
    - `--px-per-uv-triangle`
    - `--num-pixels-per-side`
    - `--target-num-faces`
    - `--method`
    - `--obb-center`, `--obb-scale`
    - `--downscale-factor`
    - `--overwrite`
- [x] Simplify `mini-mesh/scripts/run.sh` export logic:
  - [x] Replace inline `ns-extract-mesh`/`ns-texture-mesh` calls with:
    - `"$script_dir"/export.sh "$exp_path" "${export_args[@]}"`
  - [x] Adopt sensible defaults based on `video-to-mesh` and document them.

---

## 6. Docker Image Integration (`docker/`)

**Files:** `docker/Dockerfile`, `docker/run.sh`.

- [x] Ensure Docker image includes all runtime tools needed by ported features:
  - [x] `sdfstudio` fork (already present; consider pinning a commit/tag instead of tracking `main`).
  - [x] `nerfstudio` (for NeRF/nerfacto training and `ns-export` modes).
  - [x] `hloc` / `hloc-cli` (for HLoc SfM).
  - [x] `vggsfm` (for VGGSfM SfM).
  - [x] `rembg` (for background masking).
  - [x] `sam2` (for Segment Anything v2 masking).
  - [x] Any additional CLI tools introduced by `video-to-mesh` feature ports.
- [x] Keep image size reasonable; consider:
  - [x] Optional installation with INSTALL_OPTIONAL_DEPS build arg for heavy packages (nerfstudio, rembg, sam2, hloc, vggsfm).
  - [x] Clear documentation in `README.md` about which features are supported by the default image vs. require a custom build.
- [x] Confirm `docker/run.sh` remains a thin wrapper around `scripts/run.sh`:
  - [x] Test that all contexts and key new flags are usable through Docker.
  - [x] Host mounts and environment variables verified:
    - [x] `HOME=/tmp` inside container, `~/.cache` / `~/.config` mounted.
    - [x] X11/Qt environment (`DISPLAY`, `QT_XCB_GL_INTEGRATION`, `/tmp/.X11-unix`) works for COLMAP GUI.

---

## 7. Web UI Integration (`webui.py`)

**Files:** `webui.py`.

- [x] Extend UI to match the enriched pipeline contract:
  - [x] Add controls for `process` context:
    - `--min-match-ratio`, `--crop-factor`, `--mask`.
  - [x] Expose advanced SfM options:
    - `sfm` method (colmap/glomap/hloc/vggsfm).
    - Basic HLoc/VGGSfM settings remain CLI‑only for now.
  - [x] Extend training controls:
    - Include NeRF/nerfacto/splat models in the model dropdown.
    - Optional config selection for nerfacto variants.
    - Expose data processing flags under the train context (consistent with `scripts/train.sh`): `--downscale-factor`, `--scale-factor`, `--center-method`, `--orientation-method`, `--auto-scale-poses`, `--train-split-fraction`.
  - [x] Extend export controls:
    - `--method`, resolution, texture resolution, pixels-per-UV-triangle, target faces.
    - Basic OBB center/scale controls for NeRF exports.
- [x] Ensure `run_pipeline` builds CLI invocations consistent with updated `scripts/run.sh`.

---

## 8. Documentation & Examples (`README.md`, `AGENTS.md`)

**Files:** `README.md`, `AGENTS.md`.

- [x] Update `README.md`:
  - [x] Document the new `process` stage and its flags.
  - [x] Document advanced SfM modes and when to use them.
  - [x] Document masking options and VRAM/quality trade‑offs.
  - [x] Introduce NeRF/nerfacto/splat models and export methods.
  - [x] Provide concise "recipe" examples for common workflows.
  - [x] Port visual assets and references from `video-to-mesh`:
    - [x] Copy `assets/` images (banner, example renders, normal maps).
    - [x] Add banner and example table to README.
    - [x] Expand References section with additional papers (NeuS, Instant NGP, Neuralangelo, Mip-NeRF, etc.).
    - [x] Add Credits section acknowledging foundational projects.
    - [x] Add "Results are rubbish!" troubleshooting section with recording tips.
- [x] Update `AGENTS.md`:
  - [x] Reflect the richer CLI contract and configuration system for code assistants.
  - [x] Clearly state that `AGENTS.md` is the canonical agent guidance file (with `CLAUDE.md` as a symlink for compatibility, if present).
- [ ] Create GitHub Pages branch with interactive content:
  - [ ] Port video overlay from `video-to-mesh/README.md`.
  - [ ] Add example 3D meshes for interactive viewing.
  - [ ] Add NeRF/Gaussian splat demos if applicable.
  - [x] Placeholder links added to README Demos section (update when Pages ready).

---

## 9. De‑internalization & Cleanup

- [x] Scan new code for internal infra references:
  - [x] Verified no references to:
    - Cissy (`cissy run ...`).
    - Conan commands.
    - Jenkins or internal CI URLs.
    - DLR‑specific domains (e.g. `rmc-github.robotic.dlr.de`).
- [x] All added files retain MIT license compatibility and generic wording.

---

## 10. Validation & Release

**Status: Pending GPU access**

- [ ] Create a small validation checklist:
  - [ ] SDF pipeline (neus-grid-short) end‑to‑end via Docker.
  - [ ] NeRF pipeline (nerfacto-short) with `poisson` export.
  - [ ] Masked run using `--mask rembg` or `sam2`.
  - [ ] Advanced SfM run (`--method hloc` or `vggsfm`).
- [ ] Run those scenarios locally and document:
  - Inputs, commands, output locations, rough runtimes, VRAM usage.
- [ ] Tag a `mini-mesh` release once the migration is stable (e.g. `v1.0.0`) and note:
  - [ ] "Feature parity with `video-to-mesh` (minus internal infra)" in release notes.
