# Migration Plan: `video-to-mesh` → `mini-mesh`

This document tracks the migration of features from the internal **`video-to-mesh`** repository into the open‑source **`mini-mesh`** project.

Goal: **Port all user‑facing features** (CLI pipeline, models, configs, SfM modes, masking, export methods, etc.) from `video-to-mesh` to `mini-mesh`, while **excluding internal infra** such as Cissy, Conan, Jenkins, SLURM‑specific behavior, and internal URLs.

---

## 0. Scope & Principles

- [ ] Treat `mini-mesh` as the long‑term public home; `video-to-mesh` is the source of additional features.
- [ ] Port *features and behavior*, not internal tooling:
  - Do **not** add Cissy, Conan, Jenkins, or DLR‑specific infrastructure.
  - Avoid hard‑coded internal hosts/URLs; keep everything generic.
- [ ] Prefer `video-to-mesh` semantics when there is a conflict; backward compatibility with the current `mini-mesh` behavior is **not** required.
- [ ] Keep changes coherent and aligned with existing patterns in:
  - `scripts/run.sh`
  - `scripts/train.sh`
  - `config/*.sh`

---

## 1. Core Pipeline Contract (`scripts/run.sh`)

- [ ] Review differences between:
  - `mini-mesh/scripts/run.sh`
  - `video-to-mesh/scripts/run.sh`
- [ ] Align context model, using `video-to-mesh` as the behavioral reference:
  - [ ] Introduce a dedicated `process` context (currently implicit in `mini-mesh`).
  - [ ] Ensure context order and semantics: `video → sfm → process → train → export`.
- [ ] Harmonize global flags:
  - [ ] Port safe, generic flags from `video-to-mesh` (e.g., `--shared`).
  - [ ] Decide whether to support `--mail` (likely omit or keep as stub/no‑op).
- [ ] Align per‑context `--skip` / `--overwrite` semantics with `video-to-mesh`.
- [ ] Ensure directory layout and naming remain consistent:
  - `images/`, `images_orig/`, `sparse/`, `transforms.json`, `train/<exp>/<model>/config.yml`, `mesh.ply`.

---

## 2. Data Processing & Masking (`process` stage)

**Files:** `scripts/run.sh`, new or existing `process` logic.

- [ ] Extract current fixed `ns-process-data` call in `mini-mesh/scripts/run.sh` into a proper `process` context.
- [ ] Mirror `video-to-mesh` `process` behavior:
  - [ ] Use `sdf-process-data images` with:
    - `--data`, `--output_dir`, `--skip-colmap`, `--colmap-model-path`.
  - [ ] Support additional CLI args passed via `process` context:
    - [ ] `--min-match-ratio`
    - [ ] `--crop-factor`
    - [ ] `--downscale-factor`
    - [ ] `--scale-factor`
    - [ ] `--center-method`
    - [ ] `--orientation-method`
    - [ ] `--auto-scale-poses`
    - [ ] `--train-split-fraction`
- [ ] Port background masking options from `video-to-mesh`:
  - [ ] `--mask rembg|sam2|true|none`:
    - [ ] Invoke `rembg` when selected and available in `PATH`.
    - [ ] Invoke `sam2` for SAM2 masking if available.
    - [ ] Use `masks/` directory when `--mask true`.
  - [ ] Integrate masking with directory handling (`masks/`, `images_orig/`).
- [ ] Adjust training defaults when masking is enabled:
  - [ ] For SDF models, override to `--pipeline.model.background-model none` and adjust mixed precision, matching `video-to-mesh`.
  - [ ] For NeRF‑style models, match `video-to-mesh` background behavior (e.g., random background color).

---

## 3. SfM & Deep SfM (`sfm.sh`, `dl_sfm.sh`)

**Files:** `scripts/sfm.sh`, `scripts/dl_sfm.sh`, `scripts/run.sh`.

- [ ] Replace or extend `mini-mesh/scripts/sfm.sh` with richer `video-to-mesh` version (minus infra):
  - [ ] Add CLI options:
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
  - [ ] Keep thread selection generic (use `nproc`, avoid SLURM‑only assumptions).
- [ ] Replace or extend `mini-mesh/scripts/dl_sfm.sh` with feature‑complete version:
  - [ ] Preserve ability to bootstrap HLoc/VGGSfM into a writable `$GIT_ROOT` (from current `mini-mesh`).
  - [ ] Port richer CLI from `video-to-mesh`:
    - `--method hloc|vggsfm`
    - `--matcher`
    - `--hloc_feature`
    - `--hloc_matcher`
    - `--hloc_weights`
    - `--hloc_camera`
    - `--vggsfm_max_points`
    - `--vggsfm_max_tri_points`
    - `--overwrite`
  - [ ] Ensure behavior on existing sparse/database dirs matches `video-to-mesh` semantics.
- [ ] Integrate advanced SfM options into `mini-mesh/scripts/run.sh`:
  - [ ] `sfm` context `--method colmap|glomap|hloc|vggsfm`.
  - [ ] Pass through additional CLI args to `sfm.sh` and `dl_sfm.sh` as in `video-to-mesh`.
- [ ] Explicitly avoid Cissy‑based SfM calls; rely only on locally installed binaries and the Docker image.

---

## 4. Training Pipeline & Config System (`train.sh`, `config/*.sh`)

**Files:** `scripts/train.sh`, `config/defaults.sh`, additional `config/*.sh`.

- [ ] Compare training behavior:
  - `mini-mesh/scripts/train.sh` (currently `ns-train` only).
  - `video-to-mesh/scripts/train.sh` (SDF vs NeRF branches).
- [ ] Extend `config/defaults.sh`:
  - [ ] Port `NERF_DEFAULTS`, `SPLAT_DEFAULTS`, `NS_DATA_DEFAULTS` from `video-to-mesh`.
  - [ ] Reconcile camera optimizer defaults:
    - Decide whether to keep `mini-mesh`’s more aggressive settings or adopt `video-to-mesh` defaults.
- [ ] Update `scripts/train.sh` to support multiple model families:
  - [ ] For model names containing `nerf`, `splat`, or `ngp`:
    - [ ] Call `ns-train` with `NERF_DEFAULTS`/`SPLAT_DEFAULTS` and `NS_DATA_DEFAULTS`.
  - [ ] For SDF‑style models (neus, neus-facto, neuralangelo, etc.):
    - [ ] Use `sdf-train` (or stay with `ns-train` if that’s a deliberate choice), but mirror `video-to-mesh` behavior.
- [ ] Port additional configs from `video-to-mesh/config/`:
  - [ ] `nerfacto.sh`
  - [ ] `nerfacto-dev.sh`
  - [ ] `nerfacto-big.sh`
  - [ ] `nerfacto-huge.sh`
- [ ] Update or replace existing `mini-mesh` configs (`neus*`, `neus-grid-*`, `neus-facto-*`, `neuralangelo-*`) where needed to match `video-to-mesh` behavior.

---

## 5. Export System (`export.sh` + `run.sh`)

**Files:** `scripts/export.sh` (new in mini-mesh), `scripts/run.sh`.

- [ ] Add `scripts/export.sh` to `mini-mesh`, derived from `video-to-mesh/scripts/export.sh`:
  - [ ] Implement export for SDF models:
    - `sdf-extract-mesh`
    - `sdf-texture-mesh`
  - [ ] Implement export for NeRF/NGP/splat models via `ns-export`:
    - Methods: `poisson`, `tsdf`, `pointcloud`, `gaussian-splat`.
  - [ ] Support CLI args:
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
- [ ] Simplify `mini-mesh/scripts/run.sh` export logic:
  - [ ] Replace inline `ns-extract-mesh`/`ns-texture-mesh` calls with:
    - `"$script_dir"/export.sh "$exp_path" "${export_args[@]}"`
  - [ ] Adopt sensible defaults based on `video-to-mesh` and document them.

---

## 6. Docker Image Integration (`docker/`)

**Files:** `docker/Dockerfile`, `docker/run.sh`.

- [ ] Ensure Docker image includes all runtime tools needed by ported features:
  - [ ] `sdfstudio` fork (already present; consider pinning a commit/tag instead of tracking `main`).
  - [ ] `nerfstudio` (for NeRF/nerfacto training and `ns-export` modes).
  - [ ] `hloc` / `hloc-cli` (for HLoc SfM).
  - [ ] `vggsfm` (for VGGSfM SfM).
  - [ ] `rembg` (for background masking).
  - [ ] `sam2` (for Segment Anything v2 masking).
  - [ ] Any additional CLI tools introduced by `video-to-mesh` feature ports.
- [ ] Keep image size reasonable; consider:
  - [ ] Optional installation or build-time flags for heavy packages (e.g., advanced SfM and masking).
  - [ ] Clear documentation in `README.md` about which features are supported by the default image vs. require a custom build.
- [ ] Confirm `docker/run.sh` remains a thin wrapper around `scripts/run.sh`:
  - [ ] Test that all contexts and key new flags are usable through Docker.
  - [ ] Revisit host mounts and environment variables once masking and deep SfM are ported:
    - [ ] Decide whether to standardize `HOME` inside the container (e.g., `/root`) and mount host `~/.cache` / `~/.config` there.
    - [ ] Verify that X11/Qt environment (`DISPLAY`, `QT_XCB_GL_INTEGRATION`, `/tmp/.X11-unix`) still works for COLMAP GUI.

---

## 7. Web UI Integration (`web.py`)

**Files:** `web.py`.

- [ ] Extend UI to match the enriched pipeline contract:
  - [ ] Add controls for `process` context:
    - `--min-match-ratio`, `--crop-factor`, `--mask`, `--downscale-factor`, `--scale-factor`, `--center-method`, `--orientation-method`, `--auto-scale-poses`.
  - [ ] Expose advanced SfM options:
    - `sfm` method (colmap/glomap/hloc/vggsfm).
    - Basic HLoc/VGGSfM settings if desired (or keep them CLI‑only for now).
  - [ ] Extend training controls:
    - Include NeRF/nerfacto/splat models in the model dropdown.
    - Optional config selection for nerfacto variants.
  - [ ] Extend export controls:
    - `--method`, resolution, bbox, OBB center/scale, texture resolution, target faces.
- [ ] Ensure `run_workflow` builds CLI invocations consistent with updated `scripts/run.sh`.

---

## 8. Documentation & Examples (`README.md`, `AGENTS.md`)

**Files:** `README.md`, `AGENTS.md`.

- [ ] Update `README.md`:
  - [ ] Document the new `process` stage and its flags.
  - [ ] Document advanced SfM modes and when to use them.
  - [ ] Document masking options and VRAM/quality trade‑offs.
  - [ ] Introduce NeRF/nerfacto/splat models and export methods.
  - [ ] Provide concise “recipe” examples for common workflows.
- [ ] Update `AGENTS.md`:
  - [ ] Reflect the richer CLI contract and configuration system for code assistants.
  - [ ] Clearly state that `AGENTS.md` is the canonical agent guidance file (with `CLAUDE.md` as a symlink for compatibility, if present).

---

## 9. De‑internalization & Cleanup

- [ ] Scan new code for internal infra references:
  - [ ] Remove or avoid:
    - Cissy (`cissy run ...`).
    - Conan commands.
    - Jenkins or internal CI URLs.
    - DLR‑specific domains (e.g. `rmc-github.robotic.dlr.de`).
- [ ] Ensure all added files retain MIT license compatibility and generic wording.

---

## 10. Validation & Release

- [ ] Create a small validation checklist:
  - [ ] SDF pipeline (neus-grid-dev) end‑to‑end via Docker.
  - [ ] NeRF pipeline (nerfacto-dev) with `poisson` export.
  - [ ] Masked run using `--mask rembg` or `sam2`.
  - [ ] Advanced SfM run (`--method hloc` or `vggsfm`).
- [ ] Run those scenarios locally and document:
  - Inputs, commands, output locations, rough runtimes, VRAM usage.
- [ ] Tag a `mini-mesh` release once the migration is stable (e.g. `v1.0.0`) and note:
  - [ ] “Feature parity with `video-to-mesh` (minus internal infra)” in release notes.
