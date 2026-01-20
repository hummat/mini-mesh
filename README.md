# mini-mesh

Create detailed, textured 3D meshes of objects like tabletop miniatures from a short smartphone video.

![banner](assets/banner.png)

|                                   |                               |                                       |
|:---------------------------------:|:-----------------------------:|:-------------------------------------:|
| ![mokka](assets/mokka_render.png) | ![dog](assets/dog_render.png) | ![mustard](assets/mustard_render.png) |
| ![mokka](assets/mokka_normal.png) | ![dog](assets/dog_normal.png) | ![mustard](assets/mustard_normal.png) |

## Quick Start

Requires Docker, an NVIDIA GPU with 24GB+ VRAM, and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

```bash
docker/run.sh /path/to/your/video/or/images
```

This downloads the pre-built Docker image and runs the full pipeline. Add `--help` for options.

## Installation

### Docker (recommended)

<details>
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

<details>
<summary><strong>Building custom images</strong></summary>

The pre-built image supports NVIDIA CC 6.1 (GTX 10XX) to 8.9 (RTX 40XX). For other GPUs (e.g. RTX 50XX with CC 12.0):

```bash
docker build -t hummat/mini-mesh -f docker/Dockerfile \
  --build-arg TORCH_CUDA_ARCH_LIST=<YOUR-CC> \
  --build-arg CXXFLAGS="-O3 -DNDEBUG -march=native" .
```

Optional build flags:
- `INSTALL_OPTIONAL_DEPS=OFF` — Disables nerfstudio, rembg, sam2, hloc, vggsfm
- `WITH_GUI=OFF` — Headless COLMAP build (no GUI)

</details>

### Manual Installation

<details>
<summary><strong>Full manual setup</strong></summary>

Requirements: Python 3.11, PyTorch 2.5.1, CUDA 12.4.1, COLMAP, GLOMAP, PoseLib, SDFStudio

1. Install [Python 3.11](https://www.python.org/downloads/release/python-3110)

2. Install [PyTorch 2.5.1](https://pytorch.org/get-started/previous-versions/#v251) with CUDA 12.4:

    ```bash
    pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
    ```

3. Install [CUDA Toolkit 12.4.1](https://developer.nvidia.com/cuda-toolkit)

4. Install [tiny-cuda-nn](https://github.com/NVlabs/tiny-cuda-nn):

   ```bash
   pip install git+https://github.com/NVlabs/tiny-cuda-nn.git@32507f059d7abc8c13f5df81ea9597b70923ee44#subdirectory=bindings/torch
   ```

5. Install [PoseLib](https://github.com/PoseLib/PoseLib) (optional but recommended):

   ```bash
   git clone https://github.com/PoseLib/PoseLib.git && cd PoseLib
   git checkout 7e9f5f53372e43f89655040d4dfc4a00e5ace11c
   # Build per PoseLib README
   ```

6. Install [COLMAP](https://colmap.github.io/install.html) and [GLOMAP](https://github.com/colmap/glomap):
   - COLMAP: `c5f9cefc87e5dd596b638e4cee0ff543c7d14755` (≈ 3.12.6)
   - GLOMAP: `0edb1b8435e0f9a594318908b81a31f078a51bf7` (≈ 1.2.0)

7. Install [SDFStudio](https://github.com/hummat/sdfstudio):

    ```bash
    pip install git+https://github.com/hummat/sdfstudio.git@6289984bd3c3954e5052d02718d142e85e046f11
    ```

</details>

<details>
<summary><strong>Optional dependencies</strong></summary>

```bash
# NeRF/splat models
pip install git+https://github.com/hummat/nerfstudio.git@55a1f83025bb28cbf792760c9b79f9eb22c3a2e4

# Background masking
pip install "rembg[gpu,cli]"
pip install git+https://github.com/hummat/sam2.git@98f488a540f87260b8e51146dc3ab15694dd174c

# Advanced SfM (HLoc)
git clone --recursive https://github.com/cvg/Hierarchical-Localization.git
cd Hierarchical-Localization && git checkout 3bdf494c852f157db57a1cf2039a6c826d52e702
git submodule update --init --recursive && pip install . && cd ..
pip install git+https://github.com/hummat/hloc-cli.git@1b714e1183bbc3cb6f4031ddedcc4bd5190ece29

# Advanced SfM (VGGSfM)
pip install git+https://github.com/hummat/vggsfm.git@d597df629a312a662544006ac3bdbc2782b82834
```

</details>

## Usage

```bash
# Docker
docker/run.sh /path/to/your/video/or/images

# Manual (activate your Python environment first)
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
| `neus` | Baseline NeuS |
| `neus-facto` | NeuS with factorized features (faster, recommended) |
| `neuralangelo` | High-quality with hierarchical hash grids |
| `nerfacto` | General-purpose NeRF (requires nerfstudio) |
| `splatfacto` | 3D Gaussian Splatting (requires nerfstudio) |

**Config suffixes:** `-test` (3K iters), `-min` (7K), `-short` (10-30K), (none) (100K), `-long` (200K+)

**Capacity:** `-small`, (none), `-large` — e.g. `neus-facto-small-short`

<details>
<summary><strong>Export methods</strong></summary>

**SDF models** (automatic): Marching cubes → UV unwrap → texture bake → simplify

**NeRF models** (`export --method <name>`):
- `poisson` — Poisson surface reconstruction (default)
- `tsdf` — TSDF fusion
- `pointcloud` — Export as point cloud
- `gaussian-splat` — For splatfacto

</details>

<details>
<summary><strong>Process options</strong></summary>

- `--mask <method>` — Background masking: `rembg`, `sam2`, `true`, `none`
- `--min-match-ratio <float>` — Minimum acceptable camera pose ratio
- `--crop-factor <top bot left right>` — Crop images before processing

</details>

<details>
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

<details>
<summary><strong>Artist-in-the-loop workflow</strong></summary>

1. Run pipeline up to mesh extraction only:

   ```bash
   scripts/run.sh /path/to/input \
     video --fps 2 sfm --method glomap process --mask rembg \
     train --model neus-facto --config neus-facto \
     export --mesh-only
   ```

2. Edit `train/<name>/<model>/run/mesh.ply` in Blender (don't change global transform)

3. Run texturing only:

   ```bash
   scripts/export.sh /path/to/data/train/<name>/<model>/run --texture-only
   # Or with edited mesh:
   scripts/export.sh /path/to/data/train/<name>/<model>/run \
     --texture-only --input-mesh-filename mesh_edited.ply
   ```

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

- Interactive 3D meshes: *coming soon*
- NeRF/Gaussian splat demos: *coming soon*
- Video overlay examples: *coming soon*

## References

1. [NeuS: Learning Neural Implicit Surfaces by Volume Rendering](https://arxiv.org/abs/2106.10689)
2. [Ref-NeRF: Structured View-Dependent Appearance](https://arxiv.org/abs/2112.03907)
3. [Instant NGP: Multiresolution Hash Encoding](https://arxiv.org/abs/2201.05989)
4. [Neuralangelo: High-Fidelity Neural Surface Reconstruction](https://arxiv.org/abs/2306.03092)
5. [Mip-NeRF 360: Unbounded Anti-Aliased NeRF](https://arxiv.org/abs/2111.12077)

## Credits

Built on [SDFStudio](https://github.com/autonomousvision/sdfstudio), [nerfstudio](https://github.com/nerfstudio-project/nerfstudio), [COLMAP](https://colmap.github.io), [GLOMAP](https://github.com/colmap/glomap), [HLoc](https://github.com/cvg/Hierarchical-Localization), and [VGGSfM](https://vggsfm.github.io).
