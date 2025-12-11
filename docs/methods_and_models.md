# Methods and Models Overview (mini-mesh / SDFStudio / Nerfstudio)

mini-mesh is a thin wrapper around two method families:

- **SDFStudio** for SDF-based surface reconstruction (`sdf-train …`)
- **Nerfstudio** for NeRF-like and Gaussian-splat-based reconstruction (`ns-train …`)

This document consolidates the most relevant methods from both stacks, so you can pick a model + config without
digging through multiple repos.

The CLI dispatch rules are:

- `scripts/train.sh … --model <NAME> --config <CFG>`  
  → `sdf-train <NAME>` for SDFStudio methods  
  → `ns-train <NAME>` for Nerfstudio methods

Method names below refer directly to those `<NAME>` arguments.

---

## 1. SDFStudio surface methods (`sdf-train`)

These are SDF-based methods from `sdfstudio/configs/method_configs.py`, reachable via `--model <NAME>` when the
selected config is SDF-style.

### 1.1 Baked SDF / Neuralangelo family

| Method          | Code                                     | Paper / project                                                                 |
|-----------------|------------------------------------------|----------------------------------------------------------------------------------|
| `bakedsdf`      | `sdfstudio/models/bakedsdf.py`          | BakedSDF – `https://arxiv.org/abs/2302.14859`                                   |
| `bakedsdf-mlp`  | `sdfstudio/models/bakedsdf.py`          | BakedSDF large-MLP variant (no separate paper)                                   |
| `neuralangelo`  | `sdfstudio/models/neuralangelo.py`      | Neuralangelo – `https://arxiv.org/abs/2306.03092`                                |
| `bakedangelo`   | `sdfstudio/models/bakedangelo.py`       | BakedSDF + Neuralangelo schedules (2302.14859 + 2306.03092)                      |
| `neus2`         | `sdfstudio/models/neus2.py`             | NeuS2-style: NeuS + hash grids + analytic 2nd-order curvature via tcnn double backward |

Notes:

- These are the “big guns” for high-quality, large-scale surface reconstruction from real captures.
- They assume good SfM and benefit from decent coverage and clean masks.

### 1.2 NeuS / VolSDF / UniSurf variants

| Method             | Code                             | Paper / project                                                                 |
|--------------------|----------------------------------|----------------------------------------------------------------------------------|
| `volsdf`           | `sdfstudio/models/volsdf.py`    | VolSDF – `https://arxiv.org/abs/2106.12052`                                      |
| `monosdf`          | `sdfstudio/models/monosdf.py`   | MonoSDF – `https://arxiv.org/abs/2302.12276`                                     |
| `neus`             | `sdfstudio/models/neus.py`      | NeuS – `https://arxiv.org/abs/2106.10689`                                        |
| `mono-neus`        | `sdfstudio/models/neus.py`      | MonoSDF-style monocular cues on NeuS                                             |
| `geo-neus`         | `sdfstudio/models/neus.py`      | Geo-NeuS – `https://arxiv.org/abs/2205.15848`                                    |
| `neus-acc`         | `sdfstudio/models/neus_acc.py`  | NeuS with occupancy-grid acceleration (internal variant)                         |
| `neus-facto`       | `sdfstudio/models/neus_facto.py`| NeuS + Nerfacto / mip-NeRF-style proposal sampling (no dedicated paper)          |
| `neus-facto-bigmlp`| `sdfstudio/models/neus_facto.py`| Large-MLP NeuS-facto variant (no dedicated paper)                                |
| `neus-facto-angelo`| `sdfstudio/models/neus_facto.py`| NeuS-facto with Neuralangelo-style schedules (no dedicated paper)                |
| `unisurf`          | `sdfstudio/models/unisurf.py`   | UniSurf – `https://arxiv.org/abs/2104.00400`                                     |
| `mono-unisurf`     | `sdfstudio/models/unisurf.py`   | MonoSDF-style cues on UniSurf (no separate paper)                                |
| `geo-unisurf`      | `sdfstudio/models/unisurf.py`   | Geo-NeuS-style patch warping on UniSurf (no separate paper)                      |
| `geo-volsdf`       | `sdfstudio/models/volsdf.py`    | VolSDF + Geo-NeuS patch warping (2106.12052 + 2205.15848)                        |
| `dto`              | `sdfstudio/models/dto.py`       | Internal occupancy-field method (“density guided sampling”, no external paper)   |

Notes:

- Use `monosdf` / `mono-*` where you have **monocular priors** (depth/normals) and want better geometry indoors or
  with sparse views.
- Use `geo-*` variants when you have **photometric multi-view consistency** (e.g. DTU) and want patch-warping losses.
- `neus-facto` gives you NeuS with proposal networks, closer in spirit to Nerfstudio’s Nerfacto-style sampling.

### 1.3 Heritage / special-purpose methods

| Method    | Code                                    | Paper / project                               |
|----------|-----------------------------------------|-----------------------------------------------|
| `neusW`  | `sdfstudio/models/neuralreconW.py`      | NeuralRecon-W – `https://arxiv.org/abs/2205.12955` |

Notes:

- Designed for cultural heritage scenes; uses a precomputed occupancy grid from COLMAP points.
- In mini-mesh, it’s mainly relevant if you are explicitly reproducing the SDFStudio heritage experiments.

---

## 2. Shared NeRF-style methods (SDFStudio + Nerfstudio)

The following methods exist in both SDFStudio (`sdf-train`) and Nerfstudio (`ns-train`), with slightly different
defaults but broadly similar behavior.

| Method          | SDFStudio code                          | Nerfstudio code                           | Paper / project                                               |
|-----------------|-----------------------------------------|-------------------------------------------|----------------------------------------------------------------|
| `nerfacto`      | `sdfstudio/models/nerfacto.py`          | `nerfstudio/models/nerfacto.py`           | Nerfstudio – `https://arxiv.org/abs/2302.04264`                |
| `mipnerf`       | `sdfstudio/models/mipnerf.py`           | `nerfstudio/models/mipnerf.py`            | Mip-NeRF – `https://arxiv.org/abs/2103.13415`                  |
| `semantic-nerfw`| `sdfstudio/models/semantic_nerfw.py`    | `nerfstudio/models/semantic_nerfw.py`     | Semantic-NeRF `+` NeRF-W (2103.15875, 2008.02268)              |
| `vanilla-nerf`  | `sdfstudio/models/vanilla_nerf.py`      | `nerfstudio/models/vanilla_nerf.py`       | NeRF – `https://arxiv.org/abs/2003.08934`                      |
| `tensorf`       | `sdfstudio/models/tensorf.py`           | `nerfstudio/models/tensorf.py`            | TensoRF – `https://arxiv.org/abs/2203.09517`                   |
| `dnerf`         | `sdfstudio/models/dnerf.py`             | `nerfstudio/models/vanilla_nerf.py`       | D-NeRF – `https://arxiv.org/abs/2011.13961`                    |
| `phototourism`  | `sdfstudio/models/nerfacto.py`          | `nerfstudio/models/nerfacto.py`           | Nerfacto on PhotoTourism-style data (no separate method paper) |

Guidance:

- If you want **pure NeRF baselines** in the mini-mesh pipeline, use these names; `scripts/train.sh` will route
  to SDFStudio or Nerfstudio depending on the config.
- For day-to-day use on real captures, `nerfacto` or Nerfstudio’s `instant-ngp` / `splatfacto` tend to be better
  starting points than vanilla NeRF.

---

## 3. Nerfstudio-specific methods (`ns-train`)

These are only exposed via Nerfstudio and **not** duplicated in SDFStudio.

### 3.1 Real-time NeRF-style methods

| Method              | Code                                      | Paper / project                                                     |
|---------------------|-------------------------------------------|----------------------------------------------------------------------|
| `instant-ngp`       | `nerfstudio/models/instant_ngp.py`       | Instant-NGP – `https://arxiv.org/abs/2201.05989`                     |
| `instant-ngp-bounded`| `nerfstudio/models/instant_ngp.py`      | Bounded Instant-NGP variant (same paper as above)                    |
| `depth-nerfacto`    | `nerfstudio/models/depth_nerfacto.py`    | Depth-supervised Nerfacto (Nerfstudio paper)                         |
| `nerfacto-big`      | `nerfstudio/models/nerfacto.py`          | Larger Nerfacto variant (Nerfstudio paper)                           |
| `nerfacto-huge`     | `nerfstudio/models/nerfacto.py`          | Biggest Nerfacto variant (Nerfstudio paper)                          |

Notes:

- Use these when you care about **training speed + interactive viewer** for real scenes.
- mini-mesh will call `ns-train` for these when `--model` is set appropriately in an `NS_DATA_DEFAULTS` config.

### 3.2 Gaussian splatting

| Method           | Code                                   | Paper / project                                                          |
|------------------|----------------------------------------|---------------------------------------------------------------------------|
| `splatfacto`     | `nerfstudio/models/splatfacto.py`      | 3D Gaussian Splatting – `https://arxiv.org/abs/2308.04079`               |
| `splatfacto-big` | `nerfstudio/models/splatfacto.py`      | Higher-quality Splatfacto (same paper)                                   |
| `splatfacto-mcmc`| `nerfstudio/models/splatfacto.py`      | Splatfacto with MCMC densification (same paper)                          |

Notes:

- These are the primary **fast splat** options in the mini-mesh pipeline when you select a splat-style config.

### 3.3 Generative / text-to-3D

| Method        | Code                                   | Paper / project                                  |
|--------------|----------------------------------------|--------------------------------------------------|
| `generfacto` | `nerfstudio/models/generfacto.py`      | Nerfstudio text-to-3D method (no dedicated paper)|

Notes:

- Useful if you ever want to plug generative 3D into the pipeline; not used in the default video→mesh flow.

---

## 4. Practical recommendations for mini-mesh

**If you want the most robust SDF surface reconstruction:**

- Start with `bakedsdf` or `bakedangelo` on clean, well-covered scenes.
- Use `neuralangelo` or `neus-facto-angelo` when you want Neuralangelo-style schedules on SDF data.

**If you want good-quality reconstruction with standard SDFStudio demos:**

- `neus-facto` / `neus-facto-bigmlp` on DTU-style or SDFStudio demo sets.
- `monosdf` / `mono-neus` when you have good monocular priors (depth + normals).

**If you want NeRF-style volume rendering for view synthesis:**

- Use `nerfacto` / `nerfacto-big` (Nerfstudio) as a default.
- Use `instant-ngp` when you want extremely fast training and can tolerate its assumptions.

**If you want fast splat meshes / point-like outputs:**

- Use `splatfacto` (Nerfstudio) + a splat export, then feed that into your downstream mesh/visualization tools.

In all cases, mini-mesh’s `config/*.sh` files already map high-level “configs” (e.g. `neus-facto-fast`,
`nerfacto-dev`, splat configs) onto these method names. This document is primarily a lookup table so you know **what**
you are training when you see `--model <NAME>` in a config.
