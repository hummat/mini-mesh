# Methods and Models Overview (mini-mesh / SDFStudio / Nerfstudio)

mini-mesh is a thin wrapper around two method families:

- **SDFStudio** for SDF-based surface reconstruction (`sdf-train …`)
- **Nerfstudio** for NeRF-like and Gaussian-splat-based reconstruction (`ns-train …`)

This document assumes you already know **vanilla NeRF** as a continuous radiance field trained with volumetric
rendering. The goal here is to explain how the main methods supported by mini-mesh **layer on top of NeRF**, what
they add, and when you might want each one. Paper links from the original table are kept (and slightly expanded) so
you can dig into the details.

## 0. How mini-mesh maps to SDFStudio and Nerfstudio

- `scripts/train.sh … --model <NAME> --config <CFG>`
  - SDF-style config → `sdf-train <NAME>` (SDFStudio)
  - NS-style config → `ns-train <NAME>` (Nerfstudio)

The `<NAME>` values are exactly the model identifiers referenced below.

---

### Quick model selection (mini-mesh TL;DR)

- If you want a **clean, watertight mesh** from a typical handheld capture:
  Prefer SDFStudio **NeuS-style** models. Start with `--model neus-facto` and a standard config such as
  `neus-facto`. If you can afford more time and VRAM, step up to `neus-facto-angelo` or `neus2` with their
  default or `-short` configs.

- If you care more about **novel-view rendering / videos** than meshes:  
  Use Nerfstudio **Nerfacto-style** models: `--model nerfacto` with `nerfacto-short` for development, or
  `nerfacto-big` / `nerfacto-huge` for higher quality. Avoid classic `vanilla-nerf` unless you’re reproducing
  baselines.

- If you need **real-time-ish inspection** or want to embed splats on the web:
  Use `--model splatfacto-mcmc` with the default 30 000-iteration config (or `splatfacto-short` for development). See
  section 6 for variant deltas, MCMC sizing, and the rendering-mode portability trade-off before exporting.

- If your scene is **large-scale outdoors / architecture** and you want maximum surface detail:
  Try `--model neuralangelo` or `neus-facto-angelo` with their default or `-small` configs. These are slower and
  more finicky, but give best detail when SfM + masks are solid.

- If your views are **sparse or indoor** and you have good depth/normal predictions:  
  Use MonoSDF-style variants: `monosdf`, `mono-neus`, or `mono-unisurf`. They trade assumptions about monocular
  priors for improved geometry under limited coverage.

- If the scene is **dynamic** over time:  
  Only then consider `dnerf`; otherwise avoid it and stay with static-scene models.

The rest of the document explains **how these families build on vanilla NeRF** and why they behave differently.

---

## 1. NeRF and classic NeRF-style baselines

Vanilla NeRF represents a **radiance field** `f(x, d) → (σ, c)` and renders views via volume rendering
[`https://arxiv.org/abs/2003.08934`]. The following methods keep that basic formulation but change how the field is
parameterized or what data it fits.

- `vanilla-nerf` (NeRF, SDFStudio + Nerfstudio)  
  Standard MLP-based NeRF baseline. Good for reproducing classic benchmarks, too slow and brittle for most
  real-capture pipelines.  
  Paper: NeRF – `https://arxiv.org/abs/2003.08934`

- `mipnerf` (Mip-NeRF, SDFStudio + Nerfstudio)  
  Adds **cone tracing and integrated positional encoding** to NeRF to reduce aliasing and handle scale better. Think
  “NeRF, but less aliasy and more robust to resolution changes”.  
  Paper: Mip-NeRF – `https://arxiv.org/abs/2103.13415`

- `dnerf` (D-NeRF, SDFStudio + Nerfstudio)  
  Extends NeRF with a **deformation field over time**, enabling dynamic scenes where geometry changes across frames.  
  Paper: D-NeRF – `https://arxiv.org/abs/2011.13961`

- `tensorf` (TensoRF, SDFStudio + Nerfstudio)  
  Replaces a dense MLP with **factorized 4D tensors**, turning the NeRF volume into a low-rank grid representation.
  This trades memory for much faster rendering and training on static scenes.  
  Paper: TensoRF – `https://arxiv.org/abs/2203.09517`

- `semantic-nerfw` (Semantic-NeRF + NeRF-W, SDFStudio + Nerfstudio)  
  Keeps NeRF-style volume rendering, but adds **per-pixel semantics** plus **NeRF-W-style appearance embeddings** to
  handle in-the-wild images and changing illumination.  
  Papers: Semantic-NeRF / NeRF-W – `https://arxiv.org/abs/2103.15875`, `https://arxiv.org/abs/2008.02268`

- `phototourism` (Nerfacto on PhotoTourism-style data, SDFStudio + Nerfstudio)  
  A config variant that runs Nerfacto (see below) with defaults tuned for sparse internet photos; no dedicated paper.

These baselines are conceptually close to the original NeRF; everything below either **speeds NeRF up**, **adds
stronger priors**, or **switches from volumes to surfaces / Gaussians**.

In mini-mesh you rarely want these directly, except when:

- you are reproducing paper baselines or debugging NeRF behaviour, or  
- you explicitly need D-NeRF or TensoRF for research reasons.

For day-to-day work on real captures, you will almost always be better served by the models in Sections 2, 3, 4, or 6.

---

## 2. Faster and more practical NeRF variants

The next group keeps NeRF-style volume rendering but makes it practical for real scenes via better encodings,
sampling, and supervision.

- `nerfacto` (Nerfstudio’s default NeRF, SDFStudio + Nerfstudio)  
  Builds on NeRF + mip-NeRF but replaces the MLP with **multi-resolution hash / grid encodings** and **proposal
  networks** (coarse-to-fine sampling). This is the “modern NeRF baseline” used in Nerfstudio.  
  Paper: Nerfstudio – `https://arxiv.org/abs/2302.04264`

- `nerfacto-big`, `nerfacto-huge` (Nerfstudio)  
  Same basic architecture as Nerfacto, but with larger capacity and more aggressive schedules for quality over speed.
  Useful if you want better view synthesis and can afford longer training.

- `depth-nerfacto` (Nerfstudio)  
  Nerfacto with an extra **depth loss** from monocular estimators or depth sensors. This anchors the geometry and
  reduces floaty surfaces in challenging regions.

- `instant-ngp`, `instant-ngp-bounded` (Nerfstudio)  
  Starts from NeRF but uses **hash-grid encodings** and a very small MLP with a fixed coarse occupancy grid; this is
  the classic “few-seconds NeRF” implementation. The bounded variant assumes a tight scene AABB and trades flexibility
  for even more speed.  
  Paper: Instant-NGP – `https://arxiv.org/abs/2201.05989`

- `generfacto` (Nerfstudio)  
  Uses Nerfacto-style fields as the reconstruction backbone inside **text-to-3D / generative pipelines**. No standalone
  method paper; it’s mainly relevant if you integrate generative models into mini-mesh.

In mini-mesh, use these when you want **good NeRF-style view synthesis** and interactive tools rather than pure
surface quality. Roughly:

- default NeRF-ish choice: `nerfacto` / `nerfacto-big` with `nerfacto-short`-like configs;  
- depth sensors / dense depth priors: `depth-nerfacto`;  
- “quick & dirty” previews: `instant-ngp` / `instant-ngp-bounded`;  
- generative text-to-3D: `generfacto`.

---

## 3. From volumetric NeRF to SDF surfaces

Classic NeRF learns densities, so surfaces are only implicit. The following methods start from NeRF’s volume rendering
but replace densities with **signed distance fields (SDFs) or occupancy**, giving explicit surfaces and better
geometry.

### 3.1 Core SDF models: VolSDF, NeuS, UniSurf

- `volsdf` (SDFStudio)  
  Re-interprets NeRF as an SDF `s(x)` with a known mapping from SDF to opacity, and adds **Eikonal regularization** to
  encourage a valid distance field. Compared to NeRF, you get **crisper surfaces** and clean marching-cubes meshes.  
  Paper: VolSDF – `https://arxiv.org/abs/2106.12052`

- `neus` (SDFStudio)  
  Builds on VolSDF but changes the SDF-to-opacity mapping and sampling to avoid bias around the zero level set. In
  practice: **better surface localization** and fewer “thick shells” than VolSDF.  
  Paper: NeuS – `https://arxiv.org/abs/2106.10689`

- `unisurf` (SDFStudio)  
  Similar goal as NeuS (explicit surfaces), but formulates the field as **occupancy instead of SDF** and learns the
  surface via a classification-style loss combined with volume rendering.  
  Paper: UniSurf – `https://arxiv.org/abs/2104.10078`

- `dto` (SDFStudio)  
  An internal **density-guided occupancy** variant; conceptually between NeRF-style densities and UniSurf-style
  occupancy, mainly used as an extra option in SDFStudio (no external paper).

These methods are the conceptual bridge from “NeRF as a volumetric renderer” to “NeRF-like training but with
high-quality surfaces”.

In practice:

- pick **VolSDF / NeuS** when you want a mesh and have decent multi-view coverage;  
- switch to **UniSurf / dto** if you want occupancy-style behaviour or are experimenting with alternatives;  
- for most mini-mesh users, these are useful mainly as building blocks that the later “big” methods refine.

### 3.2 Adding priors and multi-view constraints: MonoSDF and Geo-NeuS families

Starting from VolSDF/NeuS/UniSurf, the next layer adds **extra geometric priors** or **stronger multi-view
photometric constraints**:

- `monosdf` (SDFStudio)  
  Takes VolSDF-style SDFs and adds **monocular depth and normal supervision** from off-the-shelf predictors. This
  stabilizes indoor and sparse-view reconstructions.  
  Paper: MonoSDF – `https://arxiv.org/abs/2206.00665`

- `mono-neus`, `mono-unisurf` (SDFStudio)  
  MonoSDF-style priors applied on top of NeuS / UniSurf respectively. Conceptually: “NeuS/UniSurf + monocular depth +
  normals” (no separate papers).

- `geo-neus`, `geo-unisurf`, `geo-volsdf` (SDFStudio)  
  Add **Geo-NeuS-style patch warping losses** that explicitly enforce multi-view photometric consistency. These shine
  on calibrated multi-view datasets (e.g. DTU).  
  Paper: Geo-NeuS – `https://arxiv.org/abs/2205.15848`

If you think of NeuS / UniSurf as “NeRF → SDF/occupancy”, these mono/geo variants are **“NeuS/UniSurf + extra
geometry signals”** for harder scenes.

Use these when:

- you have **good monocular depth/normals** (MonoSDF-style) or strong multi-view photometric consistency (Geo-NeuS);  
- base NeuS / VolSDF is too “blobby” or unstable indoors or with sparse views.

Avoid them when:

- your monocular predictions are clearly garbage (strong motion blur, glass, heavy texture-less walls), or  
- your SfM is weak; the extra losses can then hurt more than they help.

### 3.3 Heritage-focused variant

- `neusW` (SDFStudio)  
  NeuS-style SDF model tailored for cultural heritage scenes; it uses a **precomputed occupancy grid from COLMAP
  points** to focus sampling where geometry exists.  
  Paper: NeuralRecon-W – `https://arxiv.org/abs/2205.12955`

You rarely need this outside reproducing SDFStudio’s heritage experiments.

---

## 4. Large-scale and high-quality surfaces: BakedSDF, Neuralangelo, NeuS2

Once you have SDF-based surfaces, the next step is to make them scale to large outdoor scenes and capture difficult
materials (glass, facades, foliage) efficiently.

- `bakedsdf`, `bakedsdf-mlp` (SDFStudio)  
  Start from a NeuS/VolSDF-like SDF but **bake geometry into a multi-resolution grid representation**, separating
  representation from optimization. This enables higher resolution surfaces and faster inference, especially for
  large scenes.  
  Paper: BakedSDF – `https://arxiv.org/abs/2302.14859`

- `neuralangelo` (SDFStudio)  
  Builds on NeuS-style SDF representations but adds **progressive multi-resolution hash-grid encodings and curvature
  regularization schedules**, tuned for outdoor, large-scale, and highly detailed scenes (e.g. buildings, statues).  
  Paper: Neuralangelo – `https://arxiv.org/abs/2306.03092`

- `bakedangelo` (SDFStudio)  
  Combines **BakedSDF’s baked 3D representation** with **Neuralangelo-like training schedules**. Conceptually:
  “Neuralangelo-quality large-scale reconstruction with BakedSDF-style baked grids”.

- `neus2` (SDFStudio)  
  A NeuS-style model that adds **hash-grid encodings and analytic second-order curvature regularization** (via tiny
  CUDA NN double backprop). Compared to NeuS, it sharpens curvature and can better capture fine structures.

These are the “big guns” when you care mostly about **surface quality and detail** and can afford heavier training
and inference.

Concrete guidance:

- start with **`neus2`** if you want a modern NeuS-like SDF with good curvature and hash encodings, without going all
  the way to Neuralangelo;  
- move to **`neuralangelo` / `neus-facto-angelo`** when your scenes are large, outdoor, or highly detailed and you’re
  willing to pay in training time and tuning;  
- consider **`bakedsdf` / `bakedangelo`** when inference speed and baked grid representations matter (e.g. repeated
  rendering or downstream pipelines consuming a baked SDF).

### 4.1 NeuS-family sharpness and bounds (intuitive view)

NeuS-style models (`neus`, `neus-grid`, `neus2`, `neus-facto`, `neuralangelo`, BakedSDF variants) share a few
hyperparameters that control **where the surface lives and how sharp it is**. The exact flag names and recommended
value ranges are listed in the NeuS section of the `README.md`; this subsection is about **what they mean and how
they differ across methods**.

- `bias` (SDF sphere radius at init)  
  With geometric initialization enabled, NeuS-style fields start as a sphere of radius `bias`. Too small → a tiny shell
  deep inside the scene bounds, so gradients are weak and proposal networks rarely see the surface. Too large → the
  initial sphere fills most of the near/far interval, and methods with proposal nets can latch onto **background slabs**
  instead of the object. For object-centric captures after dataparser auto-scaling, you generally want a sphere that
  roughly matches the object scale, not the full camera shell.

- `beta_init` (transition-band thickness)  
  This seeds both the VolSDF Laplace density and the NeuS variance network. Small `beta_init` → a very sharp,
  thin transition band; large `beta_init` → a softer, thicker band. Plain NeuS / `neus-grid` are fairly tolerant:
  a slightly too-soft band will usually shrink as training progresses. Proposal-based models (`neus-facto`,
  BakedSDF/Neuralangelo variants) are more brittle: an extremely sharp initial band can be hard for the proposal nets
  to discover, while an extremely soft one encourages them to spray samples everywhere.

- `near-plane` / `far-plane` (ray segment where the SDF is expected to live)  
  After SDFStudio’s dataparser rescales poses, it logs an **estimated object scale** and suggested **Near/Far plane**
  in normalized units. Those numbers are your best reference: you want NeuS’s near/far to **tightly bracket the object
  shell** indicated there, with a modest safety margin. Huge intervals (orders of magnitude larger than the reported
  Near/Far) mostly hurt proposal-based methods:

  - for `neus-grid` / plain NeuS, you just waste some samples;  
  - for `neus-facto` and other proposal-net models, the proposal networks spend most of their budget marching through
    empty space and may never focus around the object, which is exactly the “background slab” artefact you see in
    normals.

In practice:

- treat `neus-grid` / `neus2` as **robust baselines**: they work reasonably even with sloppy bounds and slightly off
  sharpness settings;  
- when moving to `neus-facto`, Neuralangelo, or BakedSDF-style models, tighten near/far around the dataparser logs and
  keep `bias` / `beta_init` in sane ranges (see `README.md`) before touching more exotic losses or schedules;
- for full mathematical definitions, metrics such as `s_val`, and detailed schedules, refer to
  `sdfstudio/docs/sdfstudio-methods.md`.

### 4.2 Foreground vs background modelling

SDFStudio surface models always learn a **foreground SDF**; optionally they can also learn a **separate background
radiance field** behind the unit sphere. This is controlled by `--pipeline.model.background-model`:

- `none` – only the SDF field is used; colors and geometry everywhere (foreground + background) must be explained by
  the SDF. With good masks this gives clean object meshes; with cluttered, unmasked scenes it encourages large
  background slabs in the SDF, which show up as colorful normals.
- `mlp` – adds a small NeRF-style MLP background that is rendered behind the SDF foreground. The SDF still defines
  geometry everywhere, but the background MLP can soak up colors in empty space so the SDF is less pressured to fit
  room clutter. This is mini-mesh’s default via `config/defaults.sh` and is generally safest for **unmasked real
  captures**.
- `grid` – uses a hash-grid `nerfacto`-style background field. This is heavier but more expressive and is primarily
  used by large-scale SDFStudio configs (Neuralangelo, BakedSDF).

`scripts/run.sh` wires this up to masking:

- when you run `process --mask rembg|sam2|true … train …`, SDF models are launched with
  `--pipeline.model.background-model none`, because the images have been masked to foreground and a background field
  would only reintroduce background colors;  
- without masking (`--mask none`), SDF models keep the default `background-model mlp` to avoid the SDF having to
  reconstruct every wall and piece of clutter as geometry.

NeRF / splat / ngp models do not use `background-model`; for them only `background-color` matters, which mini-mesh
sets to `random` when masks are present so they do not overfit to a fixed solid background.

### 4.3 Positional encoding vs multi-res hash grids

SDFStudio’s `SDFField` can combine two kinds of spatial encoding for positions `x` before the SDF MLP:

- a **NeRF-style positional encoding (PE)**: sinusoidal features `sin(2^k x), cos(2^k x)` up to
  `position_encoding_max_degree`, controlled by `--pipeline.model.sdf-field.use-position-encoding`;  
- a **multi-resolution hash grid**: learned features from a hash-encoded grid hierarchy, enabled with
  `--pipeline.model.sdf-field.use-grid-feature True`.

Intuitively:

- PE alone (no grid) is the classic **Fourier-feature MLP** setup: cheap, works well for small scenes, but struggles to
  represent very fine detail without very deep/wide networks.
- A hash grid alone (no PE) already acts as a learned positional encoding with many more degrees of freedom, especially
  when progressive hash is used.

How to choose in practice:

- For **MLP-only SDFs** (`use-grid-feature False`): keep positional encoding **enabled**. This is the VolSDF / NeuS
  baseline described in `sdfstudio/docs/sdfstudio-methods.md` and gives the MLP the high-frequency capacity it needs.
- For **hash-grid SDFs**:
  - `neus-grid-*` in mini-mesh run with **PE + hash grid** (`use-position-encoding=True`). This is fine for small
    object-centric scenes and, in practice, avoids some floating-geometry artefacts that appear when you turn PE off
    without using progressive hash.
  - Neuralangelo / NeuS2 / BakedAngelo configs in SDFStudio explicitly set `use_position_encoding=False`, relying on
    the hash grid (plus progressive masks) as the positional encoding. Base `neus-facto` and `bakedsdf` keep PE
    enabled; for those we rely on configs (like `neus-facto-angelo-*`) to decide whether to run “hash only” or
    “hash + PE”. There is no single correct choice; disabling PE mainly trades a bit of expressiveness for simpler,
    often stabler optimization on large scenes.

Interaction with progressive hash:

- When `enable_progressive_hash_encoding=True`, only coarse grid levels are active early in training. If PE is also
  enabled, the network still sees full high-frequency PE features from step 0, which partly defeats the coarse-to-fine
  behavior and makes it easier to overfit noise.
- With PE disabled, capacity really grows as new hash levels are activated, which is why configs like
  `neuralangelo-small-short` often reach slightly higher `s_val` and finer detail than a comparable `neus-grid-short`
  run, even with similar hash capacity.

Rule of thumb for mini-mesh:

- stick with **`use-position-encoding=True`** for simple MLP/VolSDF-style experiments;  
- for **hash-grid-heavy methods** where configs already disable PE (Neuralangelo / NeuS2, BakedAngelo, `neus-facto-angelo-*`),
  it is usually best to keep it off and rely on the hash grid as the positional encoding unless you have a very
  specific reason to change it.

---

## 5. Hybrid SDF + NeRF-style methods

Some models explicitly mix SDF-style surfaces with Nerfstudio-style proposal sampling and encodings:

- `neus-acc` (SDFStudio)  
  NeuS with an **occupancy grid accelerator** (conceptually similar to Instant-NGP/Nerfacto occupancy grids), mainly
  speeding up ray sampling.

- `neus-facto` (SDFStudio)  
  “NeuS + Nerfacto”: SDF-based surfaces from NeuS, but with **proposal networks and hash/grid encodings** inspired by
  Nerfacto / mip-NeRF. This makes NeuS-style training faster and more robust on real scenes.

- `neus-facto-bigmlp` (SDFStudio)  
  A higher-capacity version of `neus-facto` for harder scenes; no separate paper.

- `neus-facto-angelo` (SDFStudio)  
  `neus-facto` with **Neuralangelo-style schedules**, combining SDF + proposal sampling + large-scale training
  heuristics.

Conceptually, these are **SDF models that borrow the engineering tricks from modern NeRF implementations**.

In mini-mesh this family is often the **safest SDF default**:

- `neus-facto` / `neus-facto-bigmlp` for general-purpose SDF reconstruction on real scenes;  
- `neus-acc` when you care a lot about training speed and have reasonably tight bounds;  
- `neus-facto-angelo` when you want `neus-facto` robustness plus Neuralangelo-style large-scale schedules.

---

## 6. Gaussian splatting in mini-mesh

Gaussian splatting abandons continuous volumetric integration and instead represents the scene as a set of **3D
Gaussians** with features and opacities, splatted directly in screen space.

- `splatfacto`, `splatfacto-big`, `splatfacto-mcmc` (Nerfstudio)  
  Nerfstudio’s implementations of **3D Gaussian Splatting**. They layer Gaussian primitives, camera-space splatting,
  and optional MCMC-based densification for higher quality.  
  Paper: 3D Gaussian Splatting – `https://arxiv.org/abs/2308.04079`

In the mini-mesh pipeline, these are the primary **“fast splat”** options; export paths give you splat-based
representations instead of meshes.

Choose splats when:

- you want **fast, photo-realistic view synthesis and inspection**, or want to **embed splats on the web**, and
- you’re OK either consuming Gaussians directly or running a separate mesh extraction step later.

### 6.1 Splatfacto variants

The three variants differ only in a handful of knobs but produce noticeably different splats:

| Variant | `cull_alpha_thresh` | `densify_grad_thresh` | `stop_split_at` | `strategy` | Typical VRAM |
|---|---|---|---|---|---|
| `splatfacto` | 0.1 | 8e-4 | 15000 | default | ~6 GB |
| `splatfacto-big` | 0.005 | 5e-4 | 15000 | default | ~12 GB |
| `splatfacto-mcmc` | 0.005 | — | 25000 | mcmc | ~12 GB |

All three default to 30 000 iterations and initialise from SfM points. None of them apply Mip-Splatting’s 3D
covariance filter; only the 2D opacity compensation is available, and only when `rasterize_mode=antialiased` (see 6.3).

Rule of thumb:

- `splatfacto`: fast iteration, weaker hardware, small objects.
- `splatfacto-big`: same scenes as base but you have the VRAM and want denser splats.
- `splatfacto-mcmc`: best default for quality. Robust to weak init, and the hard splat-count cap doubles as a
  file-size budget.

### 6.2 MCMC strategy and `max_gs_num`

`splatfacto-mcmc` follows the NeurIPS ’24 *3DGS as MCMC* formulation. Instead of cloning/splitting Gaussians by
heuristic gradient rules, it samples positions via Stochastic Gradient Langevin Dynamics and relocates low-opacity
Gaussians to high-density regions while respecting a hard total cap (`--pipeline.model.max-gs-num`, default
1 000 000). Two L1 penalties run alongside SGLD: `mcmc_opacity_reg` (default 0.01) keeps opacities sparse, and
`mcmc_scale_reg` (default 0.01) keeps scale magnitudes bounded.

Sizing guide for `max-gs-num`:

- 200k–500k: mobile-friendly blog assets, single objects.
- 500k–1M: object/room captures, the safe default.
- 1M–3M: large indoor scenes, outdoor close-range.
- > 3M: only worth it with scene partitioning and LoD viewers; otherwise viewer perf and file size dominate.

For mini-mesh you can pass `--pipeline.model.max-gs-num <N>` on the CLI, or wrap a preset in
`config/splatfacto-mcmc-<size>.sh` if you’re running the same budget repeatedly.

### 6.3 `rasterize_mode` and viewer compatibility

`--pipeline.model.rasterize-mode` toggles between gsplat’s two rendering modes:

- `classic` (default): screen-space `[0.3, 0.3]` Gaussian blur kernel, no opacity compensation. Matches the original
  3DGS paper; renders correctly in every Gaussian-splat viewer.
- `antialiased`: same dilation plus per-Gaussian opacity scaling by `sqrt(det(Σ_orig) / det(Σ_blurred))`. This is the
  2D side of Mip-Splatting and gives noticeably better quality at non-training resolutions (mobile zoom, distance,
  varying canvas size).

The trade-off is **render-time compatibility**: an antialiased-trained PLY only renders correctly in viewers that
apply the same compensation. The PLY format stores no flag for this; the receiver has to know.

Viewer support for the antialiased compensation (verified 2026-05):

| Viewer | Antialiased support | Notes |
|---|---|---|
| Nerfstudio’s own renderer | yes | renders training-time mode |
| Brush (Arthur Brussee) | yes (opt-in Mip render mode) | `SplatRenderMode::Mip` selects the AA shader variant (`#ifdef MIP_SPLATTING`, `COV_BLUR=0.3`); `Default` is classic |
| Spark (sparkjs.dev) | yes | AA-trained PLY: keep defaults (`blurAmount=0.3` applies the compensation, `preBlurAmount=0.0`). Classic-trained PLY: set `blurAmount=0.0, preBlurAmount=0.3`. |
| PlayCanvas Engine ≥ 2.13 | yes (opt-in) | `GSplatParams.antiAlias = true` |
| SuperSplat editor | partial | inherits from PlayCanvas Engine but does not enable `antiAlias` by default |
| Antimatter15 / Mkkellogg / older WebGL viewers | no | classic only; AA-trained PLY renders too bright on tiny splats |

Recommendation:

- For deliverables shipped as portable PLY to unknown viewers, stay with `classic`.
- When the target viewer is known and verified to support AA compensation (Spark, Brush, PlayCanvas with the flag),
  `antialiased` is the better quality choice.

**Important caveat**: Nerfstudio’s splatfacto only implements Mip-Splatting’s 2D opacity compensation, not the
persistent 3D covariance filter (the per-view sampling-rate computation that gets folded into Gaussian covariances
at training time). To get the full Mip-Splatting effect you need the upstream Mip-Splatting fork or a comparable
custom training pass.

`--pipeline.model.use-bilateral-grid` has the same portability problem and is worse: the grid parameters are never
written to the exported PLY, so the training-time color correction is silently lost on export. Use it only for
renders that stay inside Nerfstudio.

### 6.4 Scale regularization

`--pipeline.model.use-scale-regularization` adds the PhysGaussian anisotropy penalty: every 10 training steps it
pushes Gaussians whose `max_scale / min_scale > max_gauss_ratio` (default 10) back toward isotropy. It suppresses
the needle-like and pancake artifacts that cause spikes and streaks at grazing angles.

It is **off by default** in Nerfstudio for a reason:

- It can soften real thin geometry (wires, leaves, fur, mesh seams, hair).
- With `splatfacto-mcmc` it stacks on top of `mcmc_scale_reg`, which already penalises scale magnitude. The combined
  pressure on anisotropic detail compounds.

Workflow: train once without it, render in your target viewer, and only enable on a re-train if you see specific
needle/spike artifacts — typically around specular highlights, reflections, or sparse-view regions. Enabling
preemptively trades visible quality for an artifact you may not have had.

### 6.5 Splat export path

`scripts/export.sh` writes `splat.ply` for any model whose name contains `splat`, via `ns-export gaussian-splat`. It
does not run TSDF or Poisson auto-meshing for splat models; mesh extraction is a separate step. The exported PLY is
the deliverable, so the portability considerations in 6.3 apply directly.

`splatfacto-w-light` uses `scripts/export_splatfactow.py` for export, which carries the appearance-embedding
handling needed by the in-the-wild variant.

### 6.6 Blog and web embedding recipe

For splats embedded in a webpage where you control the renderer (Spark, Brush, PlayCanvas with `antiAlias=true`),
target the AA-aware path:

```bash
docker/run.sh /path/to/input \
  train --model splatfacto-mcmc --config splatfacto-mcmc-web --name blog-export \
  export
```

`scripts/export.sh` auto-routes splat models through `ns-export gaussian-splat`, so do not pass `--method` — the
flag only accepts `poisson|tsdf|pointcloud` and would fail at the parser.

On the Spark side, keep the defaults (`blurAmount=0.3, preBlurAmount=0.0`); they already apply the opacity
compensation the AA-trained PLY expects. After export, compress `splat.ply` via SuperSplat’s compressed-PLY export
or SOGS/SPZ depending on viewer support; aim for 5–20 MB. Don’t ship uncompressed PLY — even 400k Gaussians is over
100 MB raw.

For “download and view in any viewer” deliverables, train with `--pipeline.model.rasterize-mode classic` (override
`splatfacto-mcmc-web` on the CLI, or use a separate config) and accept slightly softer rendering at non-training
resolutions. In Spark, classic-trained PLY needs `blurAmount=0.0, preBlurAmount=0.3`.

---

## 7. Practical mini-mesh guidance

- For **default "good mesh" from a real capture (static object / room)**:
  Use `--model neus-facto` with `neus-facto` (or `neus-facto-short` for quicker iterations). If you need more detail
  and can spend more time, move to `neus2` with its default config or `neus-facto-bigmlp`.

- For **large outdoor scenes / facades / cultural heritage**:
  Use `neuralangelo` or `neus-facto-angelo` with the corresponding default or `-small` configs, and make sure your SfM,
  masks, and exposure are clean. If you have heritage-style COLMAP point clouds and occupancy masks, `neusW` is the
  most faithful replication of the NeuralRecon-W setting.

- For **challenging indoor / sparse-view scenes with priors**:  
  Use `monosdf`, `mono-neus`, or `mono-unisurf` when you have strong monocular depth + normals; add `geo-*` variants
  when you also have good multi-view coverage and want sharper, more consistent textures.

- For **NeRF-style view synthesis or turning videos into flythroughs**:  
  Use `nerfacto` with `nerfacto-short` as your main workhorse. Scale up to `nerfacto-big` / `nerfacto-huge` when GPU
  memory allows. Fall back to `instant-ngp` if you mainly care about fast previews.

- For **fast experimentation / smoke tests**:  
  Downscale data and use lighter configs such as `neus-grid-short` / `neus2-short` for SDF or `nerfacto-short` for NeRF. Aim
  for a few thousand iterations to check masks, SfM, and basic scene framing before committing to long runs.

  - For **splat-based outputs, real-time-ish inspection, or web embedding**:
    Use `splatfacto-mcmc` as the default; drop to `splatfacto` for faster iteration on weak hardware, and
    `splatfacto-big` if you have ~12 GB VRAM and want denser splats. See section 6.3 before picking `rasterize-mode`
    when the splats are going to a specific web viewer. The export path writes `splat.ply` only; mesh extraction is
    a separate step.

  As always, mini-mesh's `config/*.sh` files map friendly config names (e.g. `neus-facto`, `neus2`,
  `neuralangelo`, `nerfacto-short`, `splatfacto`) onto these model identifiers. This document is meant as a
  **conceptual and practical map** so you can quickly decide **which model to run and why** given your data and goals.

### 7.1 SDF tuning workflow (object-centric scenes)

This is a concrete “what to try first” workflow for SDF models, assuming a typical tabletop / room capture with
reasonable SfM and no ground-truth masks.

1. **Baseline run with `neus-grid-short`**

   - Start with a robust, proposal-free NeuS baseline:

     ```bash
     scripts/run.sh your_scene.mp4 \
       video --fps 1 \
       sfm --method glomap \
       process \
       train --model neus --config neus-grid-short \
       export --resolution 1024
     ```

   - Let it run for at least ~5–10k steps and inspect:
     - dataparser logs (`Estimated object scale`, `Near plane`, `Far plane`);
     - normals / depth in the viewer or quick exports.
   - If geometry is already decent here, *do not* jump to Neuralangelo/neus-facto yet; first tighten global NeuS
     hyperparameters.

2. **Tune global NeuS sharpness and bounds**

   Tweak only these first (see `README.md` for suggested ranges):

   - `--pipeline.model.near-plane`, `--pipeline.model.far-plane`  
     - Base them on dataparser logs: set near slightly below the reported Near and far slightly above the reported Far
       (e.g. `Near*0.8`, `Far*1.2`), not `[0.01, 1000]`.  
     - If you see background slabs in normals, shrink `far-plane` before touching anything else.
   - `--pipeline.model.sdf-field.bias`  
     - Start around `0.3–0.5` for object-centric scenes.  
     - If training stalls with almost no geometry, increase `bias` a bit; if everything collapses to a large shell that
       clearly includes the background, consider reducing `bias` or tightening `far-plane`.
   - `--pipeline.model.sdf-field.beta-init`  
     - Keep it in `0.1–0.3`. Smaller makes surfaces razor-thin and brittle; larger makes them mushy.  
     - For plain `neus` / `neus-grid` you very rarely need to leave this range.

   Once `neus-grid-short` looks good under these knobs, you have a solid reference: method switches should *improve* on it,
   not rescue bad data.

3. **Add regularizers and BRDF flags**

   Still on `neus-grid-short`, add light regularization if needed:

   - Orientation loss: `--pipeline.model.orientation-loss-mult 1e-4` for wobbly or flipped normals.  
   - Distortion loss: `--pipeline.model.distortion-loss-mult 0.001–0.003` if you see double walls / smeared depth.  
   - Ref-NeRF flags (`use-diffuse-color`, `use-n-dot-v`, `use-reflections`, `use-specular-tint`) only after geometry is
     mostly correct; they mainly help appearance and can hide geometric issues if used too early.

4. **When to switch methods**

   - If `neus-grid-short` converges but you need **more detail / smoother curvature** at similar scene scale:  
     move to `neus2` with `neus2-short` / `neus2`, keeping the same near/far/bias/beta-init as your working NeuS
     setup.
   - If the scene is **large-scale / outdoor / architectural** and NeuS2 still leaves facades noisy:
     switch to `neuralangelo` or `neus-facto-angelo` (default configs), but only after you trust your bounds and
     masks—these models are less forgiving.
   - If you want **faster convergence / better use of samples** on real scenes and are willing to tune more:
     try `neus-facto` (`neus-facto-short` / `neus-facto`) once a plain NeuS config works.

5. **Method-specific tweaks (proposal-based models)**

   For `neus-facto`, BakedSDF, and Neuralangelo-style configs:

   - Keep `near-plane` / `far-plane` **tight**. Proposal nets hate huge empty intervals; background slabs almost always
     mean bounds are too wide rather than that `beta-init` is “wrong”.  
   - Start with the same `bias` and `beta-init` that worked for `neus-grid-short`. Only then:
     - Adjust `beta-init` modestly (e.g. `0.1 → 0.2–0.3`) if surfaces remain overly thick or noisy even with good
       bounds.
     - Increase `--pipeline.model.interlevel-loss-mult` (e.g. `1.0 → 1.5–2.0`) if proposal depth maps never focus on
       the object or keep wandering.
     - Enable / tune `--pipeline.model.distortion-loss-mult` for unbounded scenes with streaky geometry.
   - For heavy schedules (Neuralangelo / BakedSDF), prefer staying close to the upstream defaults in
     `sdfstudio/configs/method_configs.py` and only change one thing at a time (bounds → bias/beta → losses).

   Method-specific knobs that are sometimes worth touching, but **only after** the above:

   - **`neus-facto` / `neus-facto-angelo`**
     - `--pipeline.model.interlevel-loss-mult` – already mentioned above; this is the main stabilizer for proposal
       networks. Increase slightly if proposals never concentrate near the object; decrease if they are stable but
       you see over-regularization.
     - `--pipeline.model.distortion-loss-mult` – off by default for base `neus-facto`. Values around `0.001–0.003`
       help suppress double walls in cluttered / unbounded scenes but add some compute.
     - `--pipeline.model.enable_progressive_hash_encoding` / `steps-per-level` – in `neus-facto-angelo` you can delay
       higher hash levels by increasing `steps-per-level` if you see early overfitting on noise; disabling progressive
       hash entirely is usually a last resort for debugging, not a default.
     - `--pipeline.model.use-anneal-beta` / `beta-anneal-*` – by default only `neus-facto-angelo` uses a beta schedule.
       Enabling it on base `neus-facto` can make training more forgiving on long runs, but it also hides whether bad
       geometry comes from beta vs bounds. Treat this as an advanced tweak.

   - **`neus2`**
     - Inherits the Neuralangelo schedules but has no curvature loss by default (`curvature-loss-multi=0`). If you see
       very wavy surfaces that plain NeuS does not have, you can turn on a small curvature penalty, e.g.

       ```bash
       --pipeline.model.curvature-loss-multi 1e-4
       ```

       This uses analytic (double-backward) curvature; keep the value small to avoid over-smoothing.

   - **`neuralangelo`**
     - `--pipeline.model.curvature-loss-multi` – default `≈5e-4` with a warmup/schedule. Reduce to `1e-4` or even
       disable (`0.0`) if small objects get over-smoothed; increase slightly on huge outdoor scenes with very wiggly
       facades.
     - `--pipeline.model.enable_progressive_hash_encoding` / `steps-per-level` – progressive hash is usually helpful.
       If you hit memory or see early aliasing, slowing down progression (larger `steps-per-level`) can help; turning
       it off usually costs detail.
     - `--pipeline.model.enable_numerical_gradients_schedule` – controls the finite-difference step for curvature and
       some diagnostics. Leave it on unless you are explicitly benchmarking analytic vs numerical gradients.

   - **`bakedsdf` / `bakedsdf-mlp` / `bakedangelo`**
     - `--pipeline.model.use-anneal-beta` / `beta-anneal-*` – the beta schedule is core to BakedSDF; only tweak it if
       you know you want a different sharpness schedule (e.g. shorter runs with a faster decay).
     - `--pipeline.model.use_spatial_varying_eikonal_loss` – lets far-away regions carry stronger eikonal weight.
       Helpful when large scenes are noisy far from the cameras; unnecessary for small object-centric captures.

6. **Background handling**

   - For **unmasked captures** (what this workflow assumes), keep `background-model mlp` (mini-mesh default). Turning it
     off forces the SDF to model every wall as geometry.  
   - If you generate masks via `process --mask rembg|sam2`, let `scripts/run.sh` switch SDF models to
     `background-model none` for you; in that regime, focus on `bias`/`beta-init`/bounds again rather than trying to
     micro-tune the background.
