# mini-mesh
Create detailed, textured 3D meshes of objects like tabletop miniatures from a short smartphone video

## Quick Start

If you already have Docker installed and an NVIDIA GPU with at least 24GB of VRAM you can start immediately by running the following command with default settings:

```bash
./docker/run.sh /path/to/your/video/or/images`
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
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg CUDA_ARCHITECTURES=<YOUR-CC> --build-arg MARCH_NATIVE=ON .
> ```

### Option 2: manual

> TL;DR: Install Python 3.10, [PyTorch 2.4.0](https://pytorch.org/get-started/previous-versions/#v240), [CUDA 12.4.1](https://developer.nvidia.com/cuda-toolkit), [`COLMAP`](https://colmap.github.io/install.html), [`GLOMAP`](https://github.com/colmap/glomap?tab=readme-ov-file#getting-started) and [my `SDFStudio` fork](https://github.com/hummat/sdfstudio) with [`tiny-cuda-nn`](https://github.com/NVlabs/tiny-cuda-nn?tab=readme-ov-file#pytorch-extension).

1. Install [Python 3.10](https://www.python.org/downloads/release/python-3100). Bonus points for using [pyenv](https://github.com/pyenv/pyenv), ([micro](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html))[mamba](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html), ([mini](https://docs.conda.io/en/latest/miniconda.html))[conda](https://docs.anaconda.com/anaconda/install/), ...
2. Install [PyTorch 2.4.0](https://pytorch.org/get-started/previous-versions/#v240) with [CUDA 12.4.1](https://developer.nvidia.com/cuda-toolkit) support. For example, using `pip`:
    ```bash
    pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu124
    ```
3. Install [CUDA Toolkit 12.4.1](https://developer.nvidia.com/cuda-toolkit).
4. Install [`tiny-cuda-nn`](https://github.com/NVlabs/tiny-cuda-nn?tab=readme-ov-file#pytorch-extension):
    ```bash
    pip install git+https://github.com/NVlabs/tiny-cuda-nn/#subdirectory=bindings/torch
    ```
5. Install [`COLMAP`](https://colmap.github.io/install.html) and [`GLOMAP`](https://github.com/colmap/glomap?tab=readme-ov-file#getting-started). Please refer to the respective installation guides.
6. Install [my `SDFStudio` fork](https://github.com/hummat/sdfstudio):
    ```bash
    pip install git+https://github.com/hummat/sdfstudio
    ```

## Usage

Once installed, running the pipeline with default settings only requires a single command:

* **docker:** Run `./docker/run.sh /path/to/your/video/or/images`
* **manual:** Activate your Python environment and run `./scripts.run.sh /path/to/your/video/or/images`

Add `--help` to see all available options. The pipeline performs the following 5 steps sequentially:
1. **Extract frames (video)** from the input video (if the input is a video)
2. **Estimate camera poses (sfm)** using COLMAP or GLOMAP
3. **Process the data** to prepare for the training
4. **Reconstruct the 3D mesh (train)** using a neural surface reconstruction deep learning model.
5. **Extract and texture (export)** the mesh.
6. 
The keywords `video`, `sfm`, `train` and `export` are sub-commands that can be used to pass arguments to a specific step, e.g.:
```bash
./docker/run.sh /path/to/your/video/or/images video --fps 1 sfm --use_glomap train --config neus-facto-fast --vis wandb
```
Steps that have already been completed are skipped by default unless `--overwrite` is specified.
The final mesh can be found next to the input video or images you provided.

If you have less VRAM, e.g. 12GB, add the following to the `train` sub-command:
```bash
  --pipeline.model.eval-num-rays-per-chunk 2048
  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
```