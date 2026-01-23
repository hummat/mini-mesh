# PBR / Inverse Rendering Starter Pack

> **Goal**: Build a correct mental model and implementation path for extracting usable PBR materials (basecolor, roughness, normal, metallic/specular) from a neural surface reconstruction and multi-view imagery.
>
> **Total time**: ~4–5 hours
> **Outcome**: Ready to implement UV-space inverse rendering with a GGX BRDF

**See also**: [`brdf_and_shading_effects.md`](brdf_and_shading_effects.md) — concept cheat sheet with paper citations

---

## Overview

| Section | Topic | Time |
|---------|-------|------|
| 0 | Geometric intuition (optional) | 30–45 min |
| 1 | Target PBR model | 45 min |
| 2 | GGX / Cook–Torrance equations | 60 min |
| 3 | Why neural radiance ≠ PBR | 30 min |
| 4 | Why inverse rendering is hard | 45 min |
| 5 | Differentiable rendering pattern | 30 min |

---

## 0. Prime Geometric Intuition

*Optional but high ROI*

### Freya Holmér — Math for Game Devs

| Resource | Link |
|----------|------|
| **Channel** | https://www.youtube.com/@acegikmo |
| Dot Product video | https://www.youtube.com/watch?v=MOYiVLEnhrw |
| Math for Game Devs [2022] | https://www.youtube.com/watch?v=fjOdtSu4Lm4 |

| Watch | Skip |
|-------|------|
| Dot products | Bézier curves |
| Reflection vectors | Splines |
| Interpolation / remapping (`lerp`, `smoothstep`) | Unrelated geometry |

**Why this matters**:
- `n·l`, `n·v`, reflection direction → core BRDF terms
- Fresnel ramps, roughness remapping → how materials respond to view angle
- Visual intuition prevents PBR from feeling like magic constants

---

## 1. Lock in the Target PBR Model

*Must-watch — defines what "correct" means*

### Brian Karis — Real Shading in Unreal Engine 4

| Resource | Link |
|----------|------|
| **Course page** | https://blog.selfshadow.com/publications/s2013-shading-course/ |
| PDF notes (v2) | https://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf |
| Slides | https://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_slides.pdf |

> **Note**: No official YouTube recording exists for this SIGGRAPH 2013 talk. The PDF notes are the authoritative source.

**This defines**:
- Metal–rough workflow (what glTF and most engines use)
- Why metallic is mostly binary (0 or 1)
- Why roughness dominates appearance
- Why dielectric F₀ ≈ 0.04

> **Litmus test**: If your extracted materials don't behave like this model under relighting, they're wrong.

---

## 2. Learn the Equations You Will Implement

### LearnOpenGL — Physically Based Rendering

| Resource | URL |
|----------|-----|
| **Theory** | https://learnopengl.com/PBR/Theory |
| **Lighting** | https://learnopengl.com/PBR/Lighting |

**Why this is the reference**:
- Cleanest GGX / Cook–Torrance implementation available online
- Matches what engines, glTF, and most papers silently assume
- Your Stage-2 forward renderer should be *structurally identical*

**Focus on these components**:

| Component | What it does |
|-----------|--------------|
| GGX NDF | Microfacet normal distribution |
| Schlick Fresnel | View-angle dependent reflectance |
| Geometry term | Masking–shadowing |
| Metal–rough params | How albedo/F₀ switch between dielectric and metal |

### Fallback Reference (for edge cases)

**Brent Burley — *Physically-Based Shading at Disney* (2012)**

| Resource | Link |
|----------|------|
| **PDF (official)** | https://media.disneyanimation.com/uploads/production/publication_asset/48/asset/s2012_pbs_disney_brdf_notes_v3.pdf |
| PDF (mirror) | https://blog.selfshadow.com/publications/s2012-shading-course/burley/s2012_pbs_disney_brdf_notes_v3.pdf |
| Course page | https://blog.selfshadow.com/publications/s2012-shading-course/ |

Use when:
- Roughness behaves oddly at extremes
- Diffuse looks wrong at grazing angles

Explains the diffuse Fresnel correction that most tutorials skip.

---

## 3. Why Neural Radiance ≠ PBR

*The conceptual bridge between NeRF-style models and material parameters*

### Ref-NeRF — Structured View-Dependent Appearance

| Resource | Link |
|----------|------|
| **Project page** | https://dorverbin.github.io/refnerf/ |
| arXiv | https://arxiv.org/abs/2112.03907 |
| **YouTube (CVPR 2022)** | https://www.youtube.com/watch?v=qrdRH9irAlk |

**Watch for**:
- Diffuse vs specular separation
- Reflection-direction encoding
- `n·v` and Fresnel-like effects

**Key insight**:
- Explains why SDFStudio-style proxy roughness and specular tint *help*
- Also explains why they are *not* a physical BRDF — just better-structured neural radiance

**See also**: [`brdf_and_shading_effects.md` §4–5](brdf_and_shading_effects.md#4-nerf--sdf-specific-modeling-topics) for SDFStudio flag mapping.

---

## 4. Why Inverse Rendering is Hard

*Justifies your multi-view UV-space approach*

### TU Wien Rendering Course — Károly Zsolnai-Fehér

| Resource | Link |
|----------|------|
| **Course page** | https://users.cg.tuwien.ac.at/zsolnai/gfx/rendering-course/ |
| **YouTube Playlist** | https://www.youtube.com/playlist?list=PLujxSBD-JXgnGmsn7gEyN28P1DnRZG7qi |
| Lecture #1 (Introduction) | https://www.youtube.com/watch?v=pjc1QAI6zS0 |

**Watch** (most relevant for inverse rendering):
- Light transport basics (early lectures)
- Monte Carlo methods / importance sampling (#24, #31)
- The rendering equation concepts

> **Note**: This course focuses on *forward* rendering (ray tracing, global illumination). Inverse rendering concepts are covered implicitly via light transport theory. For explicit inverse rendering content, see Section 5.

**Why this matters**:

| Problem | Solution |
|---------|----------|
| Lighting + material is underdetermined | Multi-view observations |
| Single-image decomposition is ill-posed | Known geometry from neural recon |
| Optimization can collapse | Priors (TV, diffusion SVBRDF models) |

This underpins your UV-space multi-view optimization stage.

---

## 5. Renderer Inside an Optimizer

*The pattern you will implement*

### Wenzel Jakob et al. — Physics-Based Differentiable Rendering

| Resource | Link |
|----------|------|
| **Course page (SIGGRAPH 2020)** | https://courses.shuangz.com/pbdr-course-sg20/ |
| **YouTube (SIGGRAPH course)** | https://www.youtube.com/watch?v=Atofdz4ZmEg |
| YouTube (Jakob talk) | https://www.youtube.com/watch?v=ldvUuGZxSx0 |
| CVPR 2021 tutorial | https://www.youtube.com/watch?v=Tou8or1ed6E |

> **Correction**: The comprehensive course is from SIGGRAPH **2020**, not 2019. Authors: Shuang Zhao, Wenzel Jakob, Tzu-Mao Li.

**The core loop**:
```
parameters → renderer → predicted image → loss → gradients → update
```

**Why this matters**:
- Exactly the structure of your GGX + lighting fitting loop
- Geometry is frozen; you optimize material params + lighting
- Gradients flow through the render equation

You don't need Mitsuba implementation details — just the optimization mindset.

---

## Optional: Sanity-Checking Outputs

### Marmoset Toolbag — PBR Workflow Videos

**Use for**:
- Sanity-check roughness maps (do they look plausible?)
- Learn what real-world PBR textures look like
- Validate that your exports render correctly in standard tools

**Not for**: Algorithm design

---

## Minimal Viewing Order

If you want the **fastest path** (~3 hours):

| Order | Resource | Format |
|-------|----------|--------|
| 1 | Brian Karis — Real Shading in Unreal Engine 4 | PDF |
| 2 | LearnOpenGL — PBR Theory + Lighting | Web |
| 3 | Ref-NeRF (CVPR 2022) | [YouTube](https://www.youtube.com/watch?v=qrdRH9irAlk) |
| 4 | TU Wien — Light transport basics | [Playlist](https://www.youtube.com/playlist?list=PLujxSBD-JXgnGmsn7gEyN28P1DnRZG7qi) |
| 5 | Differentiable Rendering (SIGGRAPH 2020) | [YouTube](https://www.youtube.com/watch?v=Atofdz4ZmEg) |

After this sequence, you are ready to implement.

---

## Reality Check

> There is **no single canonical video** that explains:
>
> *neural surface reconstruction → proxy PBR → UV-space GGX inverse rendering → diffusion priors*
>
> That gap is real. The resources above cover the pieces; your implementation plan is the glue.

---

## Quick Reference: Minimal PBR Material

For completeness, here's what you're trying to extract:

| Map | Encoding | Notes |
|-----|----------|-------|
| Basecolor / Albedo | sRGB | Diffuse reflectance (dielectric) or specular color (metal) |
| Normal | Linear, tangent-space | Usually OpenGL convention (+Y up) |
| Roughness | Linear | Controls microfacet distribution width |
| Metallic | Linear | Usually 0 everywhere (dielectric); 1 for metals |
| F₀ (specular) | Constant | 0.04 for dielectrics; derived from basecolor for metals |

**Energy conservation + microfacet BRDF (GGX) + proper lighting = physically plausible result.**

---

## Related Documentation

- [`brdf_and_shading_effects.md`](brdf_and_shading_effects.md) — BRDF concepts cheat sheet with paper citations
- [`missing_brdf_papers_analysis.md`](missing_brdf_papers_analysis.md) — additional inverse rendering papers (TensoIR, NeILF, PBR-NeRF, etc.)
