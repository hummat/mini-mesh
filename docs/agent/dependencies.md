# Dependencies

mini-mesh orchestrates several external projects. Most are maintained as
independent forks because upstream is stale or changes are needed faster than
upstream can absorb.

## Dependency Map

```
mini-mesh (scripts/*.sh, webui.py)
├── hummat/sdfstudio ........... neural surface reconstruction (sdf-train, sdf-extract-mesh, sdf-texture-mesh)
│   └── tiny-cuda-nn .......... multi-resolution hash encoding (built from source)
├── hummat/nerfstudio .......... NeRF/splat methods (ns-train, ns-export)
│   └── gsplat ................. CUDA Gaussian splatting kernels (built locally/Docker wheel)
├── COLMAP ..................... classical SfM (feature extraction, matching, mapping)
├── GLOMAP ..................... global SfM mapper (alternative to COLMAP's incremental mapper)
├── PoseLib .................... C++ pose estimation library (used by COLMAP/GLOMAP)
├── hummat/hloc-cli ............ CLI for HLoc deep-learning SfM
│   └── cvg/Hierarchical-Localization  (requires manual recursive clone)
├── hummat/vggsfm .............. visual-geometry-grounded SfM
├── hummat/sam2 ................ interactive segmentation for background masking
├── rembg ...................... automatic background removal
├── nvdiffrast ................. NVIDIA differentiable rasterizer (GPU texture baking)
└── ffmpeg ..................... video frame extraction
```

## Forked Repositories

### hummat/sdfstudio

| | |
|---|---|
| **Upstream** | [autonomousvision/sdfstudio](https://github.com/autonomousvision/sdfstudio) (last commit 2023, effectively abandoned) |
| **Fork** | [hummat/sdfstudio](https://github.com/hummat/sdfstudio) `@v0.8.0` |
| **Role** | NeuS/VolSDF/BakedSDF surface reconstruction, mesh extraction, texture baking |
| **Divergence** | ~40 commits, 320 files changed |

Key fork changes:
- Modernized PyTorch (GradScaler, autocast imports for current PyTorch)
- RTX 40XX support via configurable CUDA arch lists
- Expects local/Docker builds to prebuild tiny-cuda-nn and nvdiffrast before install
- Portable config paths and `--data` override for cross-environment usage
- PBR/GLB export fixes (dielectric defaults, metallic channel)
- CPU/CUDA variant selection via pip extras
- CI, docs, and release infrastructure

### hummat/nerfstudio

| | |
|---|---|
| **Upstream** | [nerfstudio-project/nerfstudio](https://github.com/nerfstudio-project/nerfstudio) |
| **Fork** | [hummat/nerfstudio](https://github.com/hummat/nerfstudio) `@55a1f83` |
| **Role** | NeRF (nerfacto) and Gaussian splatting (splatfacto) training + export |
| **Divergence** | 6 commits, 14 files changed |

Key fork changes:
- Fixed deprecated PyTorch imports (GradScaler, amp decorators)
- Added method documentation
- Minor exporter fixes

### hummat/sam2

| | |
|---|---|
| **Upstream** | [facebookresearch/sam2](https://github.com/facebookresearch/sam2) |
| **Fork** | [hummat/sam2](https://github.com/hummat/sam2) `@98f488a` |
| **Role** | Interactive segmentation for background masking (`--mask sam2`) |
| **Divergence** | 19 commits, 10 files changed |

Key fork changes:
- **Added full CLI** (`sam2/cli.py`, ~614 lines) — upstream has no CLI
- Supports multiple points, bounding boxes, and interactive mask prediction
- Relaxed torch/torchvision version constraints

### hummat/vggsfm

| | |
|---|---|
| **Upstream** | [facebookresearch/vggsfm](https://github.com/facebookresearch/vggsfm) |
| **Fork** | [hummat/vggsfm](https://github.com/hummat/vggsfm) `@d597df6` |
| **Role** | Deep learning SfM alternative (`--method vggsfm`) |
| **Divergence** | 20 commits, 15 files changed |

Key fork changes:
- Reorganized configs into package (pip-installable)
- Fixed Hydra config paths for package-relative resolution
- Configurable `max_points_num` and `max_tri_points_num`
- Fixed autocast for CUDA compatibility
- Added missing dependencies (scipy, LightGlue)

### hummat/hloc-cli (original)

| | |
|---|---|
| **Upstream** | — (original project, not a fork) |
| **Repo** | [hummat/hloc-cli](https://github.com/hummat/hloc-cli) `@1b714e1` |
| **Role** | CLI wrapper for HLoc deep-learning SfM (`--method hloc`) |
| **Depends on** | [cvg/Hierarchical-Localization](https://github.com/cvg/Hierarchical-Localization) `@3bdf494` (requires manual recursive clone) |

Provides an `hloc` CLI command for running SuperGlue/SuperPoint-based feature
extraction and matching through a COLMAP-like SfM pipeline.

## C/C++ Dependencies (built from source)

These are compiled in the Docker builder stage and copied to the runtime image.
For Web UI `local` mode, `scripts/build.sh` builds the same pinned refs into
`.local/mini-mesh` and the repo `.venv`.
Docker release builds target CUDA architectures `75;80;86;89` for CMake
projects and `7.5;8.0;8.6;8.9+PTX` for PyTorch extension wheels. This gives
native cubins through Ada/RTX 40xx and a PTX JIT fallback for newer GPUs.

| Dependency | Pinned commit | Version | Purpose |
|---|---|---|---|
| [COLMAP](https://github.com/colmap/colmap) | `c5f9cefc` | ~3.12.6 | Feature extraction, matching, incremental mapping |
| [GLOMAP](https://github.com/colmap/glomap) | `0edb1b84` | ~1.2.0 | Global SfM mapper (faster, more robust than COLMAP mapper) |
| [PoseLib](https://github.com/PoseLib/PoseLib) | `7e9f5f53` | 2.0.2 | Minimal pose solvers (used by COLMAP/GLOMAP) |
| [tiny-cuda-nn](https://github.com/NVlabs/tiny-cuda-nn) | `32507f0` | ~1.7 | Multi-resolution hash encoding (used by sdfstudio) |
| [nvdiffrast](https://github.com/NVlabs/nvdiffrast) | `253ac4f` | — | GPU-accelerated rasterization for texture baking |
| [gsplat](https://github.com/nerfstudio-project/gsplat) | `v1.4.0` | 1.4.0 | CUDA Gaussian splatting kernels (used by nerfstudio) |

## Stale Branches

### `neus2-integration` (abandoned, Dec 2025)

Single commit (`c6fc7c2`, 2025-12-10) adding NeuS2 as an external tool. Not
merged, not actively pursued. Preserved on remote for reference.

- Adds `config/neus2.sh`, two Python format converters
  (`convert_colmap_to_ngp.py`, `convert_studio_to_ngp.py`)
- Modifies `scripts/train.sh` and `scripts/export.sh` with NeuS2 dispatch
- Treats NeuS2 as an external binary (`NEUS2_ROOT` env var), not an sdfstudio
  model
- Includes Dockerfile additions, tests, and webui changes
- 688 lines across 9 files

If reviving NeuS2 support, this branch is the starting point — but it would
need rebasing onto current `main` and re-evaluation of the integration approach.

## Version Pins

All Python fork dependencies are pinned to specific commits in `pyproject.toml`.
C/C++ and CUDA extension dependencies are pinned in `docker/Dockerfile` and
`scripts/build.sh`.

When updating a pin, check:
1. The fork's commit history for breaking changes
2. `docker/Dockerfile` build commands
3. `scripts/build.sh` local build refs
4. `README.md` manual install instructions
5. `pyproject.toml` optional dependency URLs

## Docker Wrapper Contract

`docker/run.sh` and `docker/start.sh` are the public Docker entry points. By
default they mount the current checkout at `/app` and run the host checkout's
scripts, matching the README workflow where users clone the repository first.

The runtime image also contains a baked copy of `scripts/` and `config/` under
`/opt/mini-mesh`. Set `MINI_MESH_DOCKER_APP=image` to test those baked scripts
without mounting the checkout. Keep this path working when changing Docker
runtime dependencies or wrapper behavior.
