# Troubleshooting

This guide covers common issues and advanced tuning for mini-mesh.

## Common Issues

### 1. Results are rubbish

Most likely, your input data is not as good as it could be. Tips to improve:

- Record a 30-120 second video or capture 50-200 images
- Prevent motion blur (avoid fast motion or low light)
- Use bright, even, diffuse lighting (e.g. outside on a cloudy day)
- Cover all details of the object from all sides
- Ensure sufficient contrast between object and background
- Avoid overly cluttered backgrounds
- Treat reflective and transparent surfaces if possible (see [section 6](#6-reflective-glossy-and-transparent-surfaces))

### 2. CUDA out of memory

If you have less than 12 GB of VRAM (target) or are running on the 6 GB minimum, add the following to the `train` sub-command:

```bash
--pipeline.model.eval-num-rays-per-chunk 1024
--pipeline.datamanager.train-num-rays-per-batch 1024
--pipeline.datamanager.eval-num-rays-per-batch 1024
```

Decrease these values based on your available VRAM. For 4K input images,
mini-mesh automatically trains with `--downscale-factor 2` unless a config or
CLI argument already sets `--downscale-factor`. For full-image methods, this
downscale flag matters more than ray batch size.

### 3. Few or no camera poses estimated during SfM

Try these arguments to the `sfm` sub-command (in order):

1. `--matcher exhaustive` — Use exhaustive matcher instead of sequential
2. `--method glomap` — Use GLOMAP instead of COLMAP
3. `--extra` — Extra flags for difficult cases (no GPU support)
4. `--method hloc` — HLoc toolbox with deep learning features
5. `--method vggsfm` — VGGSfM for learning-based SfM

### 4. Training does not converge

Try these `train` sub-command arguments:

1. `--pipeline.model.near-plane 0.1` and/or `--pipeline.model.far-plane 10` — Adjust reconstruction volume
2. `--model neus-facto --config neus-facto-short` — Use neus-facto instead of neus

mini-mesh sets PyTorch float32 matmul precision to `high` by default. On Ampere
and newer NVIDIA GPUs this enables TF32 matmul, which is usually faster but not
bit-identical to strict FP32. For comparison runs, set
`MINI_MESH_FLOAT32_MATMUL_PRECISION=highest`; to leave PyTorch's default alone,
set `MINI_MESH_FLOAT32_MATMUL_PRECISION=default`.

### 5. Mesh is incomplete or wrong scale

Your object of interest should fill a bounding box of ±1. If you were too close during capture, the object is very small, or you were far away, adjust `--scale-factor` (default: 2.5) in the `train` sub-command.

### 6. Reflective, glossy, and transparent surfaces

These are challenging cases for any reconstruction pipeline.

#### Weakly textured surfaces (pose/alignment issues)

Weak texture often means poor feature matches and noisy SfM poses. **Camera optimization is most beneficial when:**

1. **Learning-based SfM** (VGGSfM) — poses are often noisier than classical methods
2. **GLOMAP** — global optimization can sometimes produce locally suboptimal poses
3. **Sequential COLMAP matcher** — fewer matches than exhaustive can lead to drift

For classical exhaustive COLMAP, camera optimization is usually unnecessary and may even destabilize training—**provided SfM successfully registered most images** (see `--min-match-ratio`). If many images failed to get poses, the surviving poses may still benefit from refinement.

```bash
--pipeline.datamanager.camera-optimizer.mode SO3xR3  # refine both rotation and position
--pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
--pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
--pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
```

<details>
<summary>What does <code>SO3xR3</code> mean?</summary>

`SO3xR3` means the optimizer refines both camera rotation (SO3 = 3D rotations) and translation (R3 = 3D position). Alternative modes: `off` (no refinement), `SO3` (rotation only).

</details>

#### Reflective/glossy surfaces (view-dependent appearance)

Specular highlights move with the camera and can confuse geometry learning. Enable Ref-NeRF-style BRDF flags based on material type.

**When using BRDF/PBR flags**, the color MLP must learn more complex view-dependent effects. Recommended adjustments:

- **Larger color MLP** — increase from default 2 to 4 layers:
  ```bash
  --pipeline.model.sdf-field.num-layers-color 4
  ```
- **Longer training** — BRDF decomposition takes more iterations to converge; consider a `-long` config or 1.5–2× iterations

**Recommended usage by material type:**

<details>
<summary><strong>Mostly diffuse/matte scenes with some view dependence</strong></summary>

```bash
--pipeline.model.sdf-field.use-diffuse-color True
--pipeline.model.sdf-field.use-n-dot-v True
```

`use-diffuse-color` splits view-independent albedo from view-dependent effects. `use-n-dot-v` provides angle of incidence for Fresnel-like ramps.

</details>

<details>
<summary><strong>Glossy plastics (lego, toys, ceramics)</strong></summary>

Dielectric materials have **white/neutral specular** highlights. Do NOT use `use-specular-tint` (that's for metals).

```bash
--pipeline.model.sdf-field.use-diffuse-color True
--pipeline.model.sdf-field.use-reflections True
--pipeline.model.sdf-field.use-n-dot-v True
--pipeline.model.sdf-field.enable-pred-roughness True
--pipeline.model.sdf-field.specular-exclude-geo-features True
--pipeline.model.sdf-field.use-roughness-gated-specular True
```

- `use-reflections` feeds reflection directions into the color MLP for sharper highlights
- `enable-pred-roughness` predicts roughness in [0, 1] for gloss variation
- `specular-exclude-geo-features` forces spatial color into diffuse only (recommended for uniform plastic)
- `use-roughness-gated-specular` gates specular by (1 - roughness) so rough areas have no specular

Optional enhancements:
```bash
--pipeline.model.sdf-field.use-fresnel-term True        # Schlick Fresnel for edge brightening
--pipeline.model.sdf-field.use-roughness-in-color-mlp True  # Feed roughness to color MLP
```

</details>

<details>
<summary><strong>Metals and colored specular (brass, gold, coated surfaces)</strong></summary>

Metals have **colored specular** that matches or tints the base color. Enable `use-specular-tint`:

```bash
--pipeline.model.sdf-field.use-diffuse-color True
--pipeline.model.sdf-field.use-specular-tint True
--pipeline.model.sdf-field.use-reflections True
--pipeline.model.sdf-field.use-n-dot-v True
--pipeline.model.sdf-field.enable-pred-roughness True
```

`use-specular-tint` learns an RGB tint for the specular component.

</details>

<details>
<summary><strong>Very shiny/mirror-like objects</strong></summary>

In addition to the above, consider:

```bash
--pipeline.model.sdf-field.learned-specular-scale True  # Per-point specular intensity
--pipeline.model.sdf-field.roughness-blend-space direction  # Alternative mixing mode
```

- `learned-specular-scale` replaces the fixed 0.5 specular multiplier with a learned per-point value
- `roughness-blend-space direction` blends raw directions before encoding (vs default "encoding" which blends after)

</details>

#### Available BRDF flags reference

| Flag | Purpose | Requires |
|------|---------|----------|
| `use-diffuse-color` | Diffuse/specular split | — |
| `use-reflections` | Reflection-direction encoding | — |
| `use-n-dot-v` | Angle of incidence input | — |
| `use-fresnel-term` | Schlick Fresnel scalar input | — |
| `use-specular-tint` | Colored specular (metals only) | — |
| `enable-pred-roughness` | Predict roughness [0,1] | `use-reflections` |
| `use-roughness-in-color-mlp` | Feed roughness to color MLP | `enable-pred-roughness` |
| `specular-exclude-geo-features` | Purely view-dependent specular | `use-diffuse-color` |
| `use-roughness-gated-specular` | Gate specular by (1-roughness) | `enable-pred-roughness` + `use-diffuse-color` |
| `learned-specular-scale` | Per-point specular intensity | `use-diffuse-color` |
| `roughness-blend-space` | "encoding" (default) or "direction" | `enable-pred-roughness` + `use-reflections` |

#### Practical ablation order

1. Start with `use-diffuse-color` + `use-n-dot-v` (minimal view dependence)
2. Add `use-reflections` for glossy scenes
3. Add `enable-pred-roughness` for roughness variation
4. For plastic: add `specular-exclude-geo-features` + `use-roughness-gated-specular`
5. For metals: add `use-specular-tint` instead
6. Optional: `use-fresnel-term`, `learned-specular-scale`

Check that geometry does not regress at each step.

#### Transparency

Largely out of reach. Consider applying washable paint to make the object opaque.

For more details on BRDF and shading effects, see [brdf_and_shading_effects.md](brdf_and_shading_effects.md).

### 7. Wandb authentication prompts in Docker

Set your API key as an environment variable:

```bash
# One-time setup (add to ~/.zshrc or ~/.bashrc)
export WANDB_API_KEY=your_api_key

# Docker wrappers automatically forward this
docker/run.sh your_video.mp4 train --vis wandb
```

Get your key from https://wandb.ai/authorize.

---

## Advanced Tuning

This section covers parameters for users comfortable with neural rendering internals. If you're new to this, start with the Common Issues section above—these settings rarely need adjustment.

### Geometry regularizers

These losses encourage cleaner geometry by penalizing physically implausible solutions.

<details>
<summary><strong>Orientation loss (Ref-NeRF-style)</strong></summary>

Encourages visible normals to face the camera:

```bash
--pipeline.model.orientation-loss-mult 1e-4
```

Works for SDF-based models (`neus`, `neus-facto`, `neuralangelo`). Most useful when normals are noisy or flipped in low-texture regions.

</details>

<details>
<summary><strong>Distortion loss (Mip-NeRF 360-style)</strong></summary>

Encourages the model to concentrate density at a single surface rather than spreading it across multiple depths (which causes floaters and fog):

```bash
# neus (single-level)
--pipeline.model.distortion-loss-mult 0.002

# neus-facto / bakedsdf / bakedangelo (proposal-based)
--pipeline.model.distortion-loss-mult 0.002
```

Start with small values; this is a soft regularizer, not a replacement for good data.

</details>

<details>
<summary><strong>Interlevel loss (Mip-NeRF 360-style, proposal-based)</strong></summary>

For faster models like `neus-facto`, a lightweight "proposal network" first guesses where surfaces are, then the main network refines those regions. This loss ensures the two networks agree:

```bash
# neus-facto / bakedsdf / bakedangelo
--pipeline.model.interlevel-loss-mult 1.0
```

Only for `-facto` style methods. Helps when depth estimates are noisy.

</details>

### NeuS sharpness parameters

These control how "sharp" the surface boundary is during training. They interact with scene scale:

| Parameter | Description | Typical values |
|-----------|-------------|----------------|
| `bias` | Initial sphere size the model starts from | 0.3–0.5 |
| `beta-init` | Initial surface "fuzziness" (lower = sharper start) | 0.1–0.3 |
| `s_val` | Learned sharpness (diagnostic—watch it rise then plateau) | — |
| `near-plane`/`far-plane` | How close/far the model looks for surfaces | Tightly bracket your object |

For `-facto` methods, extremely wide near/far bounds make training unstable.

### Foreground vs background modeling

**SDF models** (`neus*`, `neuralangelo*`, `bakedsdf*`):

| `--pipeline.model.background-model` | Description |
|-------------------------------------|-------------|
| `mlp` (default) | Simple MLP background. Robust for unmasked captures but reconstructs room clutter. |
| `grid` | Hash-grid nerfacto-style background (heavier, more expressive) |
| `none` | No background field. Ideal with good masks; without masks, SDF reconstructs background as geometry. |

`bakedangelo*` configs are the exception: they keep `background-model grid` and wide upstream-style scene bounds as
large-scene/heritage presets.

**NeRF/splat/ngp models**: No SDF/background split. With masks, mini-mesh uses `--pipeline.model.background-color random`.

### Appearance embedding

`use-appearance-embedding` lets each image have its own color/brightness adjustment. For smartphone videos where lighting or white balance varies frame-to-frame, this prevents the model from baking those variations into the geometry. For controlled studio lighting, you can disable it.

For supported NeuS/SDF and Nerfacto-style configs, mini-mesh also enables the mean appearance embedding by default
for inference/export. That is usually a better neutral choice than training image 0, whose embedding may just encode
the first frame's exposure or white balance. `splatfacto-w-light` follows the same policy with its own
`use-avg-appearance` flag and bakes the mean appearance into exported standard SH splats unless you pass
`export --appearance-mode index --appearance-idx <N>`. Its mini-mesh preset also uses classic rasterization plus denser
splatfacto-style culling/splitting thresholds so exported PLYs behave more like regular splatfacto outputs in common
viewers. Regular `splatfacto`, `splatfacto-mcmc`, and `instant-ngp` do not have this appearance switch.

### Practical tuning order

1. Fix SfM and poses (stronger `sfm` settings, then camera-optimizer in `train`)
2. Enable robust BRDF flags (`use-diffuse-color`, `use-n-dot-v`, plus `use-reflections`/`use-specular-tint` for glossy)
3. Turn up geometry priors (patch warping, mono priors, sparse SfM point losses) via SDFStudio config
4. Only then consider capture changes (matte spray, textured backgrounds, polarization) or research-level models

For detailed method explanations, see [methods_and_models.md](methods_and_models.md).
