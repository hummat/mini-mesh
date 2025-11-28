# mini-mesh
Create detailed, textured 3D meshes of objects like tabletop miniatures from a short smartphone video

## Quick Start

If you already have Docker installed and an NVIDIA GPU with at least 24GB of VRAM you can start immediately by running the following command with default settings:

```bash
docker/run.sh /path/to/your/video/or/images`
```

This will download the pre-built Docker image from Docker Hub and run the `mini-mesh` pipeline on your video or images.
Add `--help` to see all available options. Please consult the [**Usage**](#usage) section for more information.

## Installation

### Option 1: docker (recommended)

> TL;DR: Install `docker` and the `nvidia-container-toolkit`, then configure the Docker runtime using `nvidia-ctk` and restart the Docker daemon.

1. Install [Docker](https://docs.docker.com/get-docker)
2. Start and enable the Docker service:
    ```bash
    sudo systemctl start docker
    sudo systemctl enable docker
    ```
3. Install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
4. [Configure](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#configuring-docker) the Docker runtime using `nvidia-container-toolkit` and restart the Docker daemon:
    ```bash
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
    ```
5. Done! :tada:

> Note: The pre-built Docker image comes with support for NVIDIA compute capability (CC) 6.1 (GTX 10XX) to 8.9 (RTX 40XX). If your GPU has a different CC (e.g. 100 for RTX 50XX), you can build the Docker image yourself using:
> ```bash
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg TORCH_CUDA_ARCH_LIST=<YOUR-CC> --build-arg CXXFLAGS="-O3 -DNDEBUG -march=native" .
> ```
>
> The Docker image includes optional dependencies (nerfstudio, rembg, sam2, hloc, vggsfm) by default and enables the COLMAP GUI by default (`WITH_GUI=ON`). To build without optional deps or without the GUI:
> ```bash
> # Disable optional Python deps
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg INSTALL_OPTIONAL_DEPS=OFF .
>
> # Disable COLMAP GUI (headless build only)
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg WITH_GUI=OFF .
> ```

### Option 2: manual

> TL;DR: Install Python 3.10, [PyTorch 2.5.1](https://pytorch.org/get-started/previous-versions/#v251), [CUDA 12.4.1](https://developer.nvidia.com/cuda-toolkit), [`COLMAP`](https://colmap.github.io/install.html), [`GLOMAP`](https://github.com/colmap/glomap?tab=readme-ov-file#getting-started), [`PoseLib`](https://github.com/PoseLib/PoseLib) and [my `SDFStudio` fork](https://github.com/hummat/sdfstudio) with [`tiny-cuda-nn`](https://github.com/NVlabs/tiny-cuda-nn?tab=readme-ov-file#pytorch-extension).

1. Install [Python 3.10](https://www.python.org/downloads/release/python-3100). Bonus points for using [pyenv](https://github.com/pyenv/pyenv), ([micro](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html))[mamba](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html), ([mini](https://docs.conda.io/en/latest/miniconda.html))[conda](https://docs.anaconda.com/anaconda/install/), ...
2. Install [PyTorch 2.5.1](https://pytorch.org/get-started/previous-versions/#v251) with [CUDA 12.4.1](https://developer.nvidia.com/cuda-toolkit) support. For example, using `pip`:
    ```bash
   pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
    ```
3. Install [CUDA Toolkit 12.4.1](https://developer.nvidia.com/cuda-toolkit).
4. Install [`tiny-cuda-nn`](https://github.com/NVlabs/tiny-cuda-nn?tab=readme-ov-file#pytorch-extension) (the commit below corresponds approximately to tiny-cuda-nn 1.7):
   ```bash
   pip install git+https://github.com/NVlabs/tiny-cuda-nn.git@32507f059d7abc8c13f5df81ea9597b70923ee44#subdirectory=bindings/torch
   ```
5. Install [`PoseLib`](https://github.com/PoseLib/PoseLib) (optional but recommended if you build COLMAP/GLOMAP from source; the commit below corresponds approximately to PoseLib 2.0.1):
   ```bash
   git clone https://github.com/PoseLib/PoseLib.git
   cd PoseLib
   git checkout 7e9f5f53372e43f89655040d4dfc4a00e5ace11c
   # Configure & build according to the PoseLib README
   ```
6. Install [`COLMAP`](https://colmap.github.io/install.html) and [`GLOMAP`](https://github.com/colmap/glomap?tab=readme-ov-file#getting-started). Please refer to the respective installation guides. When building from source, you can use the following revisions for reproducibility (corresponding approximately to COLMAP 3.12.6 and GLOMAP 1.2.0):
   - COLMAP: `c5f9cefc87e5dd596b638e4cee0ff543c7d14755` (≈ 3.12.6)
   - GLOMAP: `0edb1b8435e0f9a594318908b81a31f078a51bf7` (≈ 1.2.0)
6. Install [my `SDFStudio` fork](https://github.com/hummat/sdfstudio):
    ```bash
   pip install git+https://github.com/hummat/sdfstudio.git@ba1f247426a283197f724392a3a3b75f4cfa014d
    ```
7. **(Optional)** Install additional dependencies for advanced features:
    ```bash
   # For NeRF/splat models and ns-export
   pip install nerfstudio==1.1.5

    # For background masking with rembg
    pip install "rembg[gpu,cli]"

    # For background masking with SAM2
   pip install git+https://github.com/hummat/sam2.git@98f488a540f87260b8e51146dc3ab15694dd174c

    # For advanced SfM with HLoc
    pip install git+https://github.com/cvg/Hierarchical-Localization.git@abb252080282e31147db6291206ca102c43353f7
    pip install git+https://github.com/hummat/hloc-cli.git@1d8fd95120a339b823e86006fd99cfd03be093e0

   # For advanced SfM with VGGSfM
   pip install git+https://github.com/hummat/vggsfm.git@55b6e4284dc9219f2683849cbc9968349707bff2
    ```

## Usage

Once installed, running the pipeline with default settings only requires a single command:

* **docker:** Run `docker/run.sh /path/to/your/video/or/images`
* **manual:** Activate your Python environment and run `scripts/run.sh /path/to/your/video/or/images`

Add `--help` to see all available options. The pipeline performs the following 5 steps sequentially:
1. **Extract frames (video)** from the input video (if the input is a video)
2. **Estimate camera poses (sfm)** using COLMAP, GLOMAP, HLoc, or VGGSfM
3. **Process the data (process)** to prepare for training (with optional background masking)
4. **Reconstruct the 3D mesh (train)** using a neural surface reconstruction deep learning model
5. **Extract and texture (export)** the mesh

The keywords `video`, `sfm`, `process`, `train` and `export` are sub-commands that can be used to pass arguments to a specific step, e.g.:
```bash
docker/run.sh /path/to/your/video/or/images video --fps 1 sfm --method glomap process --mask rembg train --config neus-facto-fast --vis wandb
```
Steps that have already been completed are skipped by default unless `--overwrite` is specified.
The final mesh can be found next to the input video or images you provided.

### Models and Configurations

The pipeline supports multiple model families:

**SDF Models** (default, best for mesh reconstruction):
- `neus`: Baseline NeuS model
- `neus-facto`: NeuS with factorized features (faster, more memory efficient)
- `neuralangelo`: High-quality reconstruction with hierarchical hash grids

**Available configs** (use with `train --config <name>`):
- `neus-grid-dev`: Fast development config (20k steps)
- `neus-facto-fast`: Fast neus-facto (100k steps)
- `neus-facto-dev`: Development neus-facto (20k steps)

**NeRF Models** (requires nerfstudio, use with `train --model <name>`):
- `nerfacto`: General-purpose NeRF for novel view synthesis
- `splatfacto`: 3D Gaussian Splatting for real-time rendering

**NeRF configs**:
- `nerfacto-dev`: Fast config (10k steps)
- `nerfacto`: Standard config (30k steps)
- `nerfacto-big`: Minimal config with normal prediction
- `nerfacto-huge`: Minimal config with normal prediction

### Export Methods

**For SDF models** (automatic):
- Marching cubes mesh extraction
- UV unwrapping and texture baking
- Mesh simplification

**For NeRF models** (use `export --method <name>`):
- `poisson`: Poisson surface reconstruction (default)
- `tsdf`: TSDF fusion
- `pointcloud`: Export as point cloud
- `gaussian-splat`: Export Gaussian splat (for splatfacto)

### Process Context Options

The `process` context supports:
- `--mask <method>`: Background masking (rembg, sam2, true, none)
- `--min-match-ratio <float>`: Minimum acceptable camera pose ratio
- `--crop-factor <top bot left right>`: Crop images before processing

### Final Touches

For optimal results, you can further improve the final mesh by using a 3D modeling software like Blender. Simply open the
reconstructed `mesh.ply` file and remove any unwanted parts or artifacts. You can also apply smoothing, hole filling, etc.
but don't rotate, translate or scale the mesh as this will break the texture mapping. Save your edits and rerun the
the pipeline which will use the edited mesh as input for the simplification and texturing step.

## Troubleshooting

1. **_CUDA out of memory_:**
   If you have less than 24 GB of VRAM, e.g. 12GB, add the following to the `train` sub-command:
   ```bash
     --pipeline.model.eval-num-rays-per-chunk 2048
     --pipeline.datamanager.train-num-rays-per-batch 2048
     --pipeline.datamanager.eval-num-rays-per-batch 2048
   ```
   Decrease these values appropriately based on your available VRAM. You might also want to decrease the image resolution
   if your images are larger than 1080p. Try adding `--downscale-factor 2` to the `train` sub-command.
2. **Few or no camera poses are estimated during the SfM step:**
   Try adding the following arguments to the `sfm` sub-command in the following order:
   1. `--matcher exhaustive`: Use the exhaustive matcher instead of the default sequential matcher.
   2. `--method glomap`: Use GLOMAP instead of COLMAP.
   3. `--extra`: Sets some extra flags for the SfM step that can help with difficult cases but without GPU support.
   4. `--method hloc`: Use the HLoc toolbox that relies on deep learning features for matching.
   5. `--method vggsfm`: Use VGGSfM for learning-based SfM.
3. **Training does not converge:**
   Try setting the following arguments of the `train` sub-command:
   1. `--pipeline.model.far-plane 0.1` and/or `--pipeline.model.far-plane 10`: Increases reconstruction volume.
   2. `--model neus-facto --config neus-facto-dev`: Use the `neus-facto` instead of the `neus` model.
4. **The final mesh is too small or not detailed enough:**
   Your object of interest should fill a bounding box of +/-1. If your it is very small or you are far away during the 
   image/video capture, you need to adjust `--scale-factor` of the `train` sub-command. The default is 2.5.
5. **Weakly textured, reflective and/or transparent surfaces are not well reconstructed:**
   These are all challenging cases for any reconstruction pipeline. Weakly textured surfaces can lead to inaccurate
   camera poses in the SfM step. You can try to learn improved poses during training using:
   ```bash
      --pipeline.datamanager.camera-optimizer.mode SO3xR3
      # Adjust these values based on your general training config
      --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
      --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
      --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
   ```
   For reflective surfaces you can try enabling the improvements proposed in RefNerf [1]:
   ```bash
      --pipeline.model.sdf-field.use-diffuse-color True
      --pipeline.model.sdf-field.use-specular-tint True
      --pipeline.model.sdf-field.use-reflections True
      --pipeline.model.sdf-field.use-n-dot-v True
   ```
   Transparency is largely out of reach so far. You can try applying a washable paint to the object to make it opaque.

## References

1. [**Ref-NeRF: Structured View-Dependent Appearance for Neural Radiance Fields**](https://arxiv.org/abs/2112.03907)