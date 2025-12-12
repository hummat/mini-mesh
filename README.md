# mini-mesh

Create detailed, textured 3D meshes of objects like tabletop miniatures from a short smartphone video

![banner](assets/banner.png)

|                                   |                               |                                       |
|:---------------------------------:|:-----------------------------:|:-------------------------------------:|
| ![mokka](assets/mokka_render.png) | ![dog](assets/dog_render.png) | ![mustard](assets/mustard_render.png) |
| ![mokka](assets/mokka_normal.png) | ![dog](assets/dog_normal.png) | ![mustard](assets/mustard_normal.png) |

## Quick Start

If you already have Docker installed and an NVIDIA GPU with at least 24GB of VRAM you can start immediately by running the following command with default settings:

```bash
docker/run.sh /path/to/your/video/or/images`
```

This will download the pre-built Docker image from Docker Hub and run the `mini-mesh` pipeline on your video or images.
Add `--help` to see all available options. Please consult the [**Usage**](#usage) section for more information.

## Installation

### Option 1: docker (strongly recommended)

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
>
> ```bash
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg TORCH_CUDA_ARCH_LIST=<YOUR-CC> --build-arg CXXFLAGS="-O3 -DNDEBUG -march=native" .
> ```
>
> The Docker image includes optional dependencies (nerfstudio, rembg, sam2, hloc, vggsfm) by default and enables the COLMAP GUI by default (`WITH_GUI=ON`). To build without optional deps or without the GUI:
>
> ```bash
> # Disable optional Python deps
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg INSTALL_OPTIONAL_DEPS=OFF .
>
> # Disable COLMAP GUI (headless build only)
> docker build -t hummat/mini-mesh -f docker/Dockerfile --build-arg WITH_GUI=OFF .
> ```
>
> With `INSTALL_OPTIONAL_DEPS=OFF`, the following features are disabled inside the container:
> - NeRF and Gaussian splatting models (nerfstudio-based training and export).
> - Background masking with `rembg` and `sam2`.
> - Advanced SfM methods `hloc` and `vggsfm`.
> The core COLMAP/GLOMAP + SDF pipeline continues to work without these optional dependencies.

### Option 2: manual

> TL;DR: Install Python 3.11, [PyTorch 2.5.1](https://pytorch.org/get-started/previous-versions/#v251), [CUDA 12.4.1](https://developer.nvidia.com/cuda-toolkit), [`COLMAP`](https://colmap.github.io/install.html), [`GLOMAP`](https://github.com/colmap/glomap?tab=readme-ov-file#getting-started), [`PoseLib`](https://github.com/PoseLib/PoseLib) and [my `SDFStudio` fork](https://github.com/hummat/sdfstudio) with [`tiny-cuda-nn`](https://github.com/NVlabs/tiny-cuda-nn?tab=readme-ov-file#pytorch-extension).

1. Install [Python 3.11](https://www.python.org/downloads/release/python-3110). Bonus points for using [pyenv](https://github.com/pyenv/pyenv), ([micro](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html))[mamba](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html), ([mini](https://docs.conda.io/en/latest/miniconda.html))[conda](https://docs.anaconda.com/anaconda/install/), ...
2. Install [PyTorch 2.5.1](https://pytorch.org/get-started/previous-versions/#v251) with [CUDA 12.4.1](https://developer.nvidia.com/cuda-toolkit) support. For example, using `pip`:

    ```bash
   pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
    ```

3. Install [CUDA Toolkit 12.4.1](https://developer.nvidia.com/cuda-toolkit).
4. Install [`tiny-cuda-nn`](https://github.com/NVlabs/tiny-cuda-nn?tab=readme-ov-file#pytorch-extension) (the commit below corresponds approximately to tiny-cuda-nn 1.7):

   ```bash
   pip install git+https://github.com/NVlabs/tiny-cuda-nn.git@32507f059d7abc8c13f5df81ea9597b70923ee44#subdirectory=bindings/torch
   ```

5. Install [`PoseLib`](https://github.com/PoseLib/PoseLib) (optional but recommended if you build COLMAP/GLOMAP from source; the commit below corresponds approximately to PoseLib 2.0.2):

   ```bash
   git clone https://github.com/PoseLib/PoseLib.git
   cd PoseLib
   git checkout 7e9f5f53372e43f89655040d4dfc4a00e5ace11c
   # Configure & build according to the PoseLib README
   ```

6. Install [`COLMAP`](https://colmap.github.io/install.html) and [`GLOMAP`](https://github.com/colmap/glomap?tab=readme-ov-file#getting-started). Please refer to the respective installation guides. When building from source, you can use the following revisions for reproducibility (corresponding approximately to COLMAP 3.12.6 and GLOMAP 1.2.0):
   - COLMAP: `c5f9cefc87e5dd596b638e4cee0ff543c7d14755` (≈ 3.12.6)
   - GLOMAP: `0edb1b8435e0f9a594318908b81a31f078a51bf7` (≈ 1.2.0)
7. Install [my `SDFStudio` fork](https://github.com/hummat/sdfstudio):

    ```bash
   pip install git+https://github.com/hummat/sdfstudio.git@6289984bd3c3954e5052d02718d142e85e046f11
    ```

8. **(Optional)** Install additional dependencies for advanced features:

   ```bash
   # For NeRF/splat models and ns-export
   pip install git+https://github.com/hummat/nerfstudio.git@55a1f83025bb28cbf792760c9b79f9eb22c3a2e4

    # For background masking with rembg
    pip install "rembg[gpu,cli]"

    # For background masking with SAM2
   pip install git+https://github.com/hummat/sam2.git@98f488a540f87260b8e51146dc3ab15694dd174c

    # For advanced SfM with HLoc
    # Note: Hierarchical-Localization requires local clone with --recursive for submodules
    git clone --recursive https://github.com/cvg/Hierarchical-Localization.git
    cd Hierarchical-Localization
    git checkout 3bdf494c852f157db57a1cf2039a6c826d52e702
    git submodule update --init --recursive
    pip install .
    cd ..
    pip install git+https://github.com/hummat/hloc-cli.git@1b714e1183bbc3cb6f4031ddedcc4bd5190ece29

   # For advanced SfM with VGGSfM
   pip install git+https://github.com/hummat/vggsfm.git@d597df629a312a662544006ac3bdbc2782b82834
    ```

## Usage

Once installed, running the pipeline with default settings only requires a single command:

- **docker:** Run `docker/run.sh /path/to/your/video/or/images`
- **manual:** Activate your Python environment and run `scripts/run.sh /path/to/your/video/or/images`

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

### Logging and Visualization

The training step supports several visualization options to monitor progress:

**Tensorboard (default):**
```bash
docker/run.sh video.mp4 train --vis tensorboard
```
TensorBoard logs are written to the experiment directory alongside your input data. To view them, run from your host machine:
```bash
tensorboard --logdir /path/to/your/data/directory
```
Then open `http://localhost:6006` in your browser.

**Wandb:**
```bash
# Recommended: set your API key once in your shell
export WANDB_API_KEY=your_api_key  # e.g. in ~/.zshrc or ~/.bashrc

# Then just run the pipeline with wandb visualization
docker/run.sh video.mp4 train --vis wandb

# Or pass it inline for a single run
WANDB_API_KEY=your_api_key docker/run.sh video.mp4 train --vis wandb
```
The Docker wrappers forward `WANDB_API_KEY` (and `WANDB_MODE`, if set) into the
container and set a writable `HOME` so wandb can create its `.netrc` without
permission issues. Uploads metrics to Weights & Biases for cloud-based tracking
and collaboration.

**Web Viewer:**
The viewer is automatically configured with `--viewer.ip-address "0.0.0.0"` and `--viewer.websocket-host "0.0.0.0"` to enable nerfstudio's built-in web viewer. This provides a real-time 3D visualization of training progress that you can access in your browser during training.

### Final Touches

For optimal results, you can further improve the final mesh by using a 3D modeling software like Blender.

**SDF models: artist-in-the-loop workflow**

1. Run the pipeline up to training and SDF mesh extraction only:

   ```bash
   scripts/run.sh /path/to/video_or_images \
     video --fps 2 sfm --method glomap process --mask rembg \
     train --model neus-facto --config neus-facto-fast \
     export --mesh-only
   ```

   This writes the extracted mesh to `train/<name>/<model>/mesh.ply` without running texturing.

2. Open `mesh.ply` in your DCC (e.g. Blender), remove unwanted parts, fill holes, and smooth as needed.
   Do **not** change the global transform (no scale/rotate/translate), as this breaks the existing camera alignment.

3. Save your edited mesh either in-place (overwrite `mesh.ply`) or as a new file (e.g. `mesh_edited.ply`).

4. Run texturing only:

   ```bash
   # If you overwrote mesh.ply in-place:
   scripts/export.sh /path/to/data/train/<name>/<model> --texture-only

   # If you saved a separate mesh file:
   scripts/export.sh /path/to/data/train/<name>/<model> \
     --texture-only --input-mesh-filename /path/to/data/train/<name>/<model>/mesh_edited.ply
   ```

   You can also drive this via `scripts/run.sh` by repeating the same `--model`/`--name` and passing
   `export --texture-only [--input-mesh-filename ...]`.

For NeRF-based exports (`nerf*`, `splat*`, `ngp*` models), mesh extraction and texturing are handled via `ns-export`
and currently run as a single step.

## Troubleshooting

1. **Results are rubbish!**
   Most likely, your input data is not as good as it could be. Here are some tips to improve it:
   - Make sure you have recorded a 30-120 seconds video or between 50-200 images.
   - Prevent motion blur through fast motion or low light.
   - Try for sufficiently bright, even and diffuse lighting, e.g. outside during a cloudy day.
   - Make sure you cover all details of the object from all sides.
   - Aim for sufficient contrast between the object and the background, i.e. avoid white objects on white backgrounds.
   - Avoid overly cluttered backgrounds.
   - Treat reflective and transparent surfaces if possible (see point 6 below).

   The more of these points you can check off, the higher are the chances of a successful reconstruction.
2. **_CUDA out of memory_:**
   If you have significantly less than 24 GB of VRAM, e.g. 6–8 GB, add the following to the `train` sub-command:

   ```bash
     --pipeline.model.eval-num-rays-per-chunk 1024
     --pipeline.datamanager.train-num-rays-per-batch 1024
     --pipeline.datamanager.eval-num-rays-per-batch 1024
   ```

   Decrease these values appropriately based on your available VRAM. You might also want to decrease the image resolution
   if your images are larger than 1080p. Try adding `--downscale-factor 2` to the `train` sub-command.
3. **Few or no camera poses are estimated during the SfM step:**
   Try adding the following arguments to the `sfm` sub-command in the following order:
   1. `--matcher exhaustive`: Use the exhaustive matcher instead of the default sequential matcher.
   2. `--method glomap`: Use GLOMAP instead of COLMAP.
   3. `--extra`: Sets some extra flags for the SfM step that can help with difficult cases but without GPU support.
   4. `--method hloc`: Use the HLoc toolbox that relies on deep learning features for matching.
   5. `--method vggsfm`: Use VGGSfM for learning-based SfM.
4. **Training does not converge:**
   Try setting the following arguments of the `train` sub-command:
   1. `--pipeline.model.far-plane 0.1` and/or `--pipeline.model.far-plane 10`: Increases reconstruction volume.
   2. `--model neus-facto --config neus-facto-dev`: Use the `neus-facto` instead of the `neus` model.
5. **The final mesh is incomplete or too small/not detailed enough:**
   Your object of interest (OOI) should fill a bounding box of +/-1. If it your were too close during capture (the OOI isn't fully visible in each frame), is very small or you are far away during the image/video capture, you need to adjust `--scale-factor` of the `train` sub-command. The default is 2.5.
6. **Weakly textured, reflective and/or transparent surfaces are not well reconstructed:**
   These are all challenging cases for any reconstruction pipeline.

   **Weakly textured surfaces (pose / alignment issues):**  
   Weak texture often means poor feature matches and therefore noisy SfM poses. You can try to learn improved poses
   during training using:

   ```bash
      --pipeline.datamanager.camera-optimizer.mode SO3xR3
      # Adjust these values based on your general training config
      --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
      --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
      --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
   ```

   **Reflective / glossy surfaces (view-dependent appearance issues):**  
   Here the main problem is not just pose, but that specular highlights move with the camera and can “confuse”
   geometry learning. You can bias SDFStudio’s BRDF head to handle this better by enabling the Ref-NeRF–style flags:

   ```bash
      --pipeline.model.sdf-field.use-diffuse-color True
      --pipeline.model.sdf-field.use-specular-tint True
      --pipeline.model.sdf-field.use-reflections True
      --pipeline.model.sdf-field.use-n-dot-v True
   ```

   Recommended usage:

   - Mostly diffuse / matte scenes, but with some view dependence:  
     Enable at least:

     ```bash
     --pipeline.model.sdf-field.use-diffuse-color True
     --pipeline.model.sdf-field.use-n-dot-v True
     ```

     `use-diffuse-color` splits view-independent “albedo” from view-dependent effects, which helps keep geometry
     honest. `use-n-dot-v` provides the angle of incidence (cosine term) so the network can easily learn
     foreshortening / limb-darkening and Fresnel-like ramps.

   - Strong specular highlights / moderately reflective materials (glossy plastics, varnished wood, ceramics):  
     Use the full Ref-NeRF bundle:

     ```bash
     --pipeline.model.sdf-field.use-diffuse-color True
     --pipeline.model.sdf-field.use-specular-tint True
     --pipeline.model.sdf-field.use-reflections True
     --pipeline.model.sdf-field.use-n-dot-v True
     ```

     `use-reflections` feeds reflection directions into the color MLP, making specular highlight *position* much more
     sensitive to geometry and normals. `use-specular-tint` lets specular become colored (metals / coated surfaces)
     instead of always white.

   - Very shiny / metallic objects (strong mirror-like reflections):  
     In addition to the above, you can enable roughness prediction and the mixed view/reflection encoding:

     ```bash
     --pipeline.model.sdf-field.enable-pred-roughness True
     ```

     With `use-reflections=True`, this predicts a roughness in `[0, 1]` and uses it to mix view-direction features
     (rough, diffuse-like) and reflection-direction features (smooth, specular-like). This tends to give cleaner
     specular geometry and a more interpretable roughness map. It adds a bit of capacity and complexity, so only use
     it when you actually have strong specular behavior.

   Notes:

   - All of these flags affect only the *appearance* model; geometry is still learned from color via the SDF and its
     regularizers. They mainly change how strongly color residuals push on normals and surface shape, which can help
     or hurt geometry depending on the scene.
   - With `use-diffuse-color=True`, the color MLP no longer sees raw points/normals directly; that’s good for
     separating albedo from specular, but it also makes it easier for the BRDF heads (`use-specular-tint`,
     `use-reflections`, `enable-pred-roughness`) to “explain away” view-dependent artifacts instead of fixing the SDF.
     On some scenes this can manifest as slightly wavier surfaces than a simpler setup.
   - `use-reflections` and especially `enable-pred-roughness` noticeably increase appearance capacity. They are most
     useful on clearly glossy / metallic objects; for mostly diffuse scenes, they may add complexity without clear
     gains and can slow down or destabilize geometry a bit.
   - `use-appearance-embedding` (when enabled in the underlying SDFStudio config) adds a small per-image latent code
     to the color network. For the typical mini-mesh use case (short, shaky smartphone videos with imperfect lighting),
     this usually helps, because it lets the model soak up per-frame exposure / white-balance / noise differences
     without twisting geometry. For very clean, studio-lit photo sets, advanced users may prefer to disable it to push
     more supervision into geometry instead of appearance.
   - Foreground vs background modelling:
     - For **SDF models** (`neus*`, `neuralangelo*`, `bakedsdf*`), `--pipeline.model.background-model` controls whether a
       separate NeRF-style background field is trained in addition to the foreground SDF:
       - `mlp` (mini-mesh default via `config/defaults.sh`) learns a simple MLP background behind the SDF foreground.
         This is robust for unmasked, cluttered captures but will happily reconstruct walls and room clutter as real
         geometry.
       - `grid` uses a hash-grid `nerfacto`-style background (heavier but more expressive), used by some SDFStudio
         large-scale configs (e.g. Neuralangelo/BakedSDF).
       - `none` disables the background field; the SDF must then explain all pixels. This is ideal when you have good
         foreground masks (as in `scripts/run.sh process --mask …`), but on unmasked data it will cause the SDF to
         reconstruct background slabs as geometry.
     - For **NeRF / splat / ngp models**, there is no SDF/background split; instead, mini-mesh toggles
       `--pipeline.model.background-color random` when masks are used so they do not overfit to a fixed solid
       background.
   - The NeuS sharpness parameters interact with scene scale:
     - ``bias`` (in the SDF field config) sets the radius of the initial geometric SDF sphere. For small tabletop
       objects, values around ``0.3–0.5`` generally give a more stable start than an extremely tight sphere; if you
       make it too small, the initial surface can be so tiny that gradients are weak.
     - ``beta-init`` seeds both the VolSDF Laplace density scale and the NeuS variance network. Typical values are
       ``0.1–0.3``; smaller makes the initial band sharper, larger makes it softer.
     - ``s_val`` (logged as a metric) is the learned NeuS sharpness scalar; it roughly controls how thin the transition
       band around the surface is (thickness ≈ ``1 / s_val`` in SDF units). You should see it rise from its initial
       value and then plateau. Treat it as a diagnostic (is training doing something?) rather than a target — higher is
       only better if the rendered images and meshes also improve.
     - ``near-plane`` / ``far-plane`` (in the surface model config) define the ray segment where NeuS samples and where
       the SDF field is expected to live after the dataparser’s auto-scaling. For typical object-centric captures, you
       want this interval to tightly bracket the object shell reported by the dataparser logs (``Estimated object
       scale``, ``Near plane``, ``Far plane``), with a modest safety margin—not orders of magnitude larger. Extremely
       wide bounds (e.g. ``0.01–1000`` in normalized units) make proposal-based methods like ``neus-facto`` much more
       brittle, because their proposal networks waste most samples in empty space before ever seeing the surface.
     - For a more detailed discussion of these parameters, their metrics (e.g. ``s_val``), and schedules in upstream
       SDFStudio, see `sdfstudio/docs/sdfstudio-methods.md`. This README is meant as a practical tuning cheat sheet; the
       `docs/methods_and_models.md` file explains how the different NeuS-style methods build on each other conceptually.
   - `use-n-dot-v` is cheap and generally safe to keep **on** whenever you care about good geometry.
   - Do **not** treat the full Ref-NeRF bundle as an “always on” preset. A practical ablation order is:
     1) turn on `use-n-dot-v`, 2) add `use-reflections` for glossy scenes, 3) add `use-diffuse-color` if you care
     about albedo/specular separation, and 4) only then add `use-specular-tint`/`enable-pred-roughness` for very
     shiny/metallic objects, checking that geometry does not regress at each step.

   You can further regularize geometry with:

   - **Orientation loss (Ref-NeRF-style)** – encourages visible normals to face the camera:

     ```bash
      --pipeline.model.orientation-loss-mult 1e-4
     ```

     Works for SDF-based models (`neus`, `neus-facto`, `neuralangelo` variants) and is most useful when normals are
     noisy or flipped in low-texture regions.

   - **Distortion loss (Mip-NeRF 360-style)** – discourages stretched or double-peaked depth distributions:

     ```bash
     # neus (single-level)
     --pipeline.model.distortion-loss-mult 0.002

     # neus-facto / bakedsdf / bakedangelo (proposal-based)
     --pipeline.model.distortion-loss-mult 0.002
     ```

     Start with small values; this is a soft regularizer to tighten geometry, not a replacement for good data.

   - **Interlevel loss (Mip-NeRF 360-style, proposal-based)** – encourages consistency between proposal-network
     samples and the final NeuS / VolSDF samples along each ray:

     ```bash
     # neus-facto / bakedsdf / bakedangelo (proposal-based)
     --pipeline.model.interlevel-loss-mult 1.0
     ```

     This loss only does something for methods that use proposal networks (e.g. ``neus-facto*``, ``bakedsdf*``,
     ``bakedangelo*``). It helps keep coarse proposal distributions aligned with the final SDF-induced density, which
     in turn stabilizes proposal sampling. If you see very noisy depth distributions or proposal samples that never
     focus near the surface, increasing this multiplier slightly is often more robust than trying to fix geometry by
     further shrinking ``beta-init`` or widening near/far.

   In practice, apply changes roughly in this order:

   1. Fix SfM and poses (stronger `sfm` settings, then camera-optimizer in `train`).
   2. Enable robust BRDF flags (`use-diffuse-color`, `use-n-dot-v`, plus `use-reflections`/`use-specular-tint` for glossy scenes).
   3. If needed, turn up existing geometry priors (patch warping, mono priors, sparse SfM point losses) via the SDFStudio config.
   4. Only after that, consider heavier capture changes (matte spray, textured backgrounds, polarization) or research-level models with explicit lighting/BRDF.

   Transparency is largely out of reach so far. You can try applying a washable paint to the object to make it opaque.
7. **Wandb authentication prompts in Docker:**
   To avoid entering your wandb API key every time when using `--vis wandb`, set it as an environment variable:

   ```bash
   # One-time setup in your shell (recommended)
   export WANDB_API_KEY=your_api_key  # e.g. in ~/.zshrc or ~/.bashrc

   # Docker wrappers automatically forward this into the container
   docker/run.sh your_video.mp4 train --vis wandb
   ```

   Get your key from https://wandb.ai/authorize.

## References

1. [**NeuS: Learning Neural Implicit Surfaces by Volume Rendering for Multi-view Reconstruction**](https://arxiv.org/abs/2106.10689)
2. [**Ref-NeRF: Structured View-Dependent Appearance for Neural Radiance Fields**](https://arxiv.org/abs/2112.03907)
3. [**Instant Neural Graphics Primitives with a Multiresolution Hash Encoding**](https://arxiv.org/abs/2201.05989)
4. [**Neuralangelo: High-Fidelity Neural Surface Reconstruction**](https://arxiv.org/abs/2306.03092)
5. [**Mip-NeRF: A Multiscale Representation for Anti-Aliasing Neural Radiance Fields**](https://arxiv.org/abs/2103.13415)
6. [**Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields**](https://arxiv.org/abs/2111.12077)
7. [**NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis**](https://arxiv.org/abs/2003.08934)

## Credits

This project is based on the following awesome projects:

1. [**SDFStudio**](https://github.com/autonomousvision/sdfstudio)
2. [**nerfstudio**](https://github.com/nerfstudio-project/nerfstudio)
3. [**COLMAP**](https://colmap.github.io)
4. [**GLOMAP**](https://github.com/colmap/glomap)
5. [**HLoc**](https://github.com/cvg/Hierarchical-Localization)
6. [**VGGSfM**](https://vggsfm.github.io)
