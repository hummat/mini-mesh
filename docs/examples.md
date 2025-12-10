# mini-mesh Examples

Concrete end-to-end commands for common workflows. All examples use `scripts/run.sh` as the single entry point.

Assumptions:

- `INPUT` is a video or image folder.
- You have Docker / local toolchain set up as per `README.md`.
- Methods / configs referenced here exist under `config/*.sh` and in the SDFStudio / Nerfstudio repos.

---

## 1. SDF surface mesh from a video (NeuS-facto)

Static scene, reasonably well-lit, with a handheld video.

```bash
scripts/run.sh /path/to/scene.mp4 \
  video --fps 2 \
  sfm --method glomap \
  process --mask rembg \
  train --model neus-facto --config neus-facto-fast \
  export --resolution 2048
```

Notes:

- Uses SDFStudio `sdf-train neus-facto` with a fast config.
- Outputs mesh + textures under `train/<exp>/neus-facto/`.

---

## 2. High-quality SDF mesh (Neuralangelo-style)

More aggressive, Neuralangelo-influenced reconstruction on a clean, well-covered capture.

```bash
scripts/run.sh /path/to/scene.mp4 \
  video --fps 2 \
  sfm --method glomap \
  process --mask rembg \
  train --model neuralangelo --config neuralangelo-opt \
  export --resolution 4096
```

Notes:

- Hits SDFStudio `sdf-train neuralangelo` with `config/neuralangelo-opt.sh`.
- Use when you care more about quality than speed.

---

## 3. Fast NeRF-style reconstruction (Nerfacto-dev)

For quick NeRF-style view synthesis from an image set (no heavy SDF surface).

```bash
scripts/run.sh /path/to/images \
  sfm --method glomap \
  process --mask none \
  train --model nerfacto --config nerfacto-dev \
  export --method poisson --resolution 1024
```

Notes:

- Routes to `ns-train nerfacto` using `NERF_DEFAULTS` and `config/nerfacto-dev.sh`.
- `export --method poisson` calls `ns-export` to produce a mesh from the NeRF.

---

## 4. Nerfacto-big with multi-GPU training

Same as above but with a larger Nerfacto variant and explicit multi-GPU flags.

```bash
export CUDA_VISIBLE_DEVICES=0,1

scripts/run.sh /path/to/images \
  sfm --method glomap \
  process \
  train --model nerfacto-big --config nerfacto-big \
        --machine.num-devices 2 \
        --pipeline.datamanager.train-num-rays-per-batch 4096 \
  export --method poisson --resolution 2048
```

Notes:

- Uses Nerfstudio’s `nerfacto-big` method, which benefits from more VRAM.
- `--machine.num-devices` and `train-num-rays-per-batch` are passed straight through to `ns-train`.

---

## 5. Gaussian splatting with Splatfacto

Quick reconstruction and rendering using Gaussian splats.

```bash
scripts/run.sh /path/to/scene.mp4 \
  video --fps 2 \
  sfm --method glomap \
  process \
  train --model splatfacto --config splatfacto \
  export --method pointcloud --resolution 1024
```

Notes:

- Calls `ns-train splatfacto` via the Nerfstudio backend.
- `export --method pointcloud` produces a point-like output; for splat exports, use `ns-export gaussian-splat` directly if you need raw `.ply` splats.

---

## 6. Minimal SDF smoke test (Neus-grid-dev)

Very small setup to check the pipeline end-to-end on a tiny example.

```bash
scripts/run.sh /path/to/small_dataset \
  sfm \
  process \
  train --model neus --config neus-grid-dev \
  export --resolution 512
```

Notes:

- Uses `config/neus-grid-dev.sh`, which is tuned for quick tests rather than ultimate quality.
- Good for verifying your environment and SfM/toolchain before running heavier configs.
