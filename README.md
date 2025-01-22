# mini-mesh
Create detailed, textured 3D meshes of objects like tabletop miniatures from a short smartphone video

## Installation

### Option 1: Docker (recommended)

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

> Note: The pre-built Docker image comes with NVIDIA compute capabilities 6.1 (Pascal) to 8.9 (Ampere). If your GPU has a different compute capability, you can build the Docker image yourself using:
> ```bash
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg CUDA_ARCHITECTURES=native --build-arg MARCH_NATIVE=ON .
> ```

### Option 2: Manual

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