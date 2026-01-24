# mini-mesh

Create detailed, textured 3D meshes of anything from a short smartphone video.

![banner](assets/banner.png)

|                                   |                               |                                       |
|:---------------------------------:|:-----------------------------:|:-------------------------------------:|
| ![mokka](assets/mokka_render.png) | ![dog](assets/dog_render.png) | ![mustard](assets/mustard_render.png) |
| ![mokka](assets/mokka_normal.png) | ![dog](assets/dog_normal.png) | ![mustard](assets/mustard_normal.png) |

_Head over to the repository's [**GitHub** Pages site](https://hummat.github.io/mini-mesh) for a prettier and more
interactive version of this README!_

## Quick Start

Requires [Docker](https://docs.docker.com/get-docker), an NVIDIA GPU with 12GB+ VRAM (6GB minimum), and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

```bash
docker/run.sh /path/to/your/video/or/images
```

This downloads the pre-built Docker image and runs the full pipeline. Add `--help` for options.

## Installation

### Docker (recommended)

<details markdown="1">
<summary><strong>Setup instructions</strong></summary>

1. Install [Docker](https://docs.docker.com/get-docker)
2. Start and enable the Docker service:

    ```bash
    sudo systemctl start docker
    sudo systemctl enable docker
    ```

3. Install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
4. Configure the Docker runtime and restart:

    ```bash
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
    ```

</details>

<details markdown="1">
<summary><strong>Image variants</strong></summary>

| Image | Size | Use when |
|-------|------|----------|
| `hummat/mini-mesh:latest` | ~11.6GB | Default — includes all features |
| `hummat/mini-mesh:slim` | ~9GB | Limited VRAM or disk space (no rembg, nerfstudio, sam2, hloc, vggsfm) |

Also available on GitHub Container Registry: `ghcr.io/hummat/mini-mesh`

To use slim:
```bash
docker pull hummat/mini-mesh:slim
MINI_MESH_IMAGE=hummat/mini-mesh:slim docker/run.sh /path/to/input
```

</details>

<details markdown="1">
<summary><strong>Building custom images</strong></summary>

The pre-built image supports GPUs from GTX 16XX/RTX 20XX to RTX 40XX (compute capabilities 7.5–8.9).

```bash
docker/build.sh local  # Build optimized for your GPU
```

See [CONTRIBUTING.md](/.github/CONTRIBUTING.md#docker) for build variants and options.

**RTX 50XX (Blackwell) not yet supported** — requires CUDA 12.8+ and PyTorch with sm_120 support. Track [PyTorch#159207](https://github.com/pytorch/pytorch/issues/159207) for updates.

</details>

### Manual Installation

<details markdown="1">
<summary><strong>Full manual setup</strong></summary>

Requirements: Python 3.11, CUDA 12.4.1, COLMAP, GLOMAP, uv

1. Install [Python 3.11](https://www.python.org/downloads/release/python-3110)

2. Install [CUDA Toolkit 12.4.1](https://developer.nvidia.com/cuda-toolkit)

3. Install [PoseLib](https://github.com/PoseLib/PoseLib) (optional but recommended):

   ```bash
   git clone https://github.com/PoseLib/PoseLib.git && cd PoseLib
   git checkout 7e9f5f53372e43f89655040d4dfc4a00e5ace11c
   # Build per PoseLib README
   ```

4. Install [COLMAP](https://colmap.github.io/install.html) and [GLOMAP](https://github.com/colmap/glomap):
   - COLMAP: `c5f9cefc87e5dd596b638e4cee0ff543c7d14755` (≈ 3.12.6)
   - GLOMAP: `0edb1b8435e0f9a594318908b81a31f078a51bf7` (≈ 1.2.0)

5. Install Python dependencies:

   ```bash
   uv sync --extra local
   ```

6. Activate the virtual environment:

   ```bash
   source .venv/bin/activate
   ```

</details>

<details markdown="1">
<summary><strong>Optional dependencies</strong></summary>

If you used `uv sync --extra local`, these are already installed (except HLoc).

```bash
# NeRF/splat models
uv pip install git+https://github.com/hummat/nerfstudio.git@55a1f83025bb28cbf792760c9b79f9eb22c3a2e4

# Background masking
uv pip install "rembg[gpu,cli]"
uv pip install git+https://github.com/hummat/sam2.git@98f488a540f87260b8e51146dc3ab15694dd174c

# Advanced SfM (HLoc) - requires manual clone
git clone --recursive https://github.com/cvg/Hierarchical-Localization.git
cd Hierarchical-Localization && git checkout 3bdf494c852f157db57a1cf2039a6c826d52e702
git submodule update --init --recursive && uv pip install -e . && cd ..
uv pip install git+https://github.com/hummat/hloc-cli.git@1b714e1183bbc3cb6f4031ddedcc4bd5190ece29

# Advanced SfM (VGGSfM)
uv pip install git+https://github.com/hummat/vggsfm.git@d597df629a312a662544006ac3bdbc2782b82834

# GPU texture baking (nvdiffrast) - requires CUDA toolkit
uv pip install --no-build-isolation git+https://github.com/NVlabs/nvdiffrast.git
```

</details>

## Usage

```bash
# Docker
docker/run.sh /path/to/your/video/or/images

# Manual
source .venv/bin/activate  # if using uv
scripts/run.sh /path/to/your/video/or/images
```

The pipeline runs 5 steps: **video** → **sfm** → **process** → **train** → **export**

Pass arguments to specific steps using sub-commands:

```bash
docker/run.sh /path/to/input video --fps 1 sfm --method glomap process --mask rembg train --model neus-facto
```

The final mesh appears next to your input. Steps already completed are skipped (use `--overwrite` to re-run).

### Models

| Model | Description |
|-------|-------------|
| `neus` | Baseline surface reconstruction |
| `neus-facto` | Faster surface reconstruction (recommended) |
| `neuralangelo` | Higher quality via multi-resolution features, slower |
| `nerfacto` | View synthesis, not watertight meshes (requires nerfstudio) |
| `splatfacto` | Fast view synthesis via point clouds (requires nerfstudio) |

**Config suffixes:** `-test` (3K iters), `-min` (7K), `-short` (10-30K), (none) (100K), `-long` (200K+)

**Capacity:** `-small`, (none), `-large` — e.g. `neus-facto-small-short`

<details markdown="1">
<summary><strong>Export methods</strong></summary>

**SDF models** (automatic): Extracts mesh → creates texture coordinates → bakes colors onto texture → simplifies geometry

**NeRF models** (`export --method <name>`):
- `poisson` — Reconstructs smooth surface from rendered point cloud (default)
- `tsdf` — Fuses depth maps into a volume, then extracts mesh
- `pointcloud` — Export as point cloud (no mesh)
- `gaussian-splat` — For splatfacto

</details>

<details markdown="1">
<summary><strong>Process options</strong></summary>

- `--mask <method>` — Background masking: `rembg`, `sam2`, `true`, `none`
- `--min-match-ratio <float>` — Fail if fewer than this fraction of images get poses (default: 0.5)
- `--crop-factor <top bot left right>` — Crop images before processing

</details>

<details markdown="1">
<summary><strong>Visualization</strong></summary>

**TensorBoard (default):**
```bash
docker/run.sh video.mp4 train --vis tensorboard
tensorboard --logdir /path/to/your/data  # on host
```

**Weights & Biases:**
```bash
export WANDB_API_KEY=your_api_key  # add to ~/.bashrc
docker/run.sh video.mp4 train --vis wandb
```

**Web Viewer:** Automatically configured for nerfstudio's real-time 3D viewer.

</details>

<details markdown="1">
<summary><strong>Artist-in-the-loop workflow</strong></summary>

1. Run pipeline up to mesh extraction only:

   ```bash
   docker/run.sh /path/to/input video --fps 2 sfm --method glomap process --mask rembg train --model neus-facto --config neus-facto export --mesh-only
   ```

2. Edit `train/<name>/<model>/run/mesh.ply` in Blender (don't change global transform)

3. Run texturing only:

   ```bash
   docker/run.sh /path/to/input export --texture-only
   # Or with edited mesh:
   docker/run.sh /path/to/input export --texture-only --input-mesh-filename mesh_edited.ply
   ```

4. **(Optional) Optimize for web delivery:**

   The exported GLB files are ~10MB due to uncompressed geometry and PNG textures. For web use (e.g., `<model-viewer>`), compress with [gltf-transform](https://gltf-transform.dev/):

   ```bash
   npx @gltf-transform/cli optimize mesh.glb mesh_web.glb --compress draco --texture-compress webp
   ```

   This typically achieves **90-95% size reduction** (10MB → 500KB-1MB) by:
   - **Welding vertices**: Blender's GLB export duplicates vertices at UV seams; `optimize` merges them back
   - **Draco compression**: Quantizes geometry to 14-bit precision + entropy coding
   - **WebP textures**: Lossy compression, visually identical to PNG at ~10% the size

   The mesh quality is preserved—the bloat comes from export artifacts, not your edits.

<details markdown="1">
<summary>Without Docker</summary>

```bash
# Step 1: Extract mesh only
scripts/run.sh /path/to/input \
  video --fps 2 sfm --method glomap process --mask rembg train --model neus-facto --config neus-facto export --mesh-only

# Step 3: Texture only (after editing mesh)
scripts/export.sh /path/to/data/train/<name>/<model>/run --texture-only
# Or with edited mesh:
scripts/export.sh /path/to/data/train/<name>/<model>/run --texture-only --input-mesh-filename mesh_edited.ply
```

</details>

</details>

## Troubleshooting

Common issues and solutions:

| Problem | Quick fix |
|---------|-----------|
| Bad results | Improve input: 30-120s video, good lighting, cover all angles |
| CUDA OOM | Reduce ray batch sizes, add `--downscale-factor 2` |
| Few SfM poses | Try `--matcher exhaustive`, `--method glomap`, or `--method hloc` |
| Training diverges | Adjust `near-plane`/`far-plane`, try `neus-facto` |
| Wrong mesh scale | Adjust `--scale-factor` (default 2.5) |

For advanced tuning (BRDF flags, regularizers, NeuS parameters), see **[docs/troubleshooting.md](docs/troubleshooting.md)**.

## Documentation

- **[Troubleshooting](docs/troubleshooting.md)** — Common issues and advanced tuning
- **[Methods & Models](docs/methods_and_models.md)** — How NeuS, NeRF, and other methods work
- **[BRDF & Shading](docs/brdf_and_shading_effects.md)** — Handling reflective and glossy surfaces
- **[Examples](docs/examples.md)** — Additional usage examples

## Demos

Visit the [GitHub Pages site](https://hummat.github.io/mini-mesh) for:

- **Interactive 3D meshes** — rotate, zoom, and inspect reconstructed models in your browser
- **2D/3D gallery toggle** — compare rendered colors with normal maps
- **Video overlay** — see the input capture process

## References

1. [NeuS: Learning Neural Implicit Surfaces by Volume Rendering](https://arxiv.org/abs/2106.10689)
2. [Ref-NeRF: Structured View-Dependent Appearance](https://arxiv.org/abs/2112.03907)
3. [Instant NGP: Multiresolution Hash Encoding](https://arxiv.org/abs/2201.05989)
4. [Neuralangelo: High-Fidelity Neural Surface Reconstruction](https://arxiv.org/abs/2306.03092)
5. [Mip-NeRF 360: Unbounded Anti-Aliased NeRF](https://arxiv.org/abs/2111.12077)

## Credits

Built on [SDFStudio](https://github.com/autonomousvision/sdfstudio), [nerfstudio](https://github.com/nerfstudio-project/nerfstudio), [COLMAP](https://colmap.github.io), [GLOMAP](https://github.com/colmap/glomap), [HLoc](https://github.com/cvg/Hierarchical-Localization), and [VGGSfM](https://vggsfm.github.io).
