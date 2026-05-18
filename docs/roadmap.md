# Roadmap

Implementation roadmap for mini-mesh and its upstream forks.
Tracked on the [project board](https://github.com/users/hummat/projects/4).

## Dependency Graph

```
                    ┌──────────────────────────────────────────────┐
                    │              sdfstudio fork                   │
                    │  #11 anneal-beta ──┐                         │
                    │  #12 focus center ─┤── quality fixes (Ph.1)  │
                    │  #13 bakedsdf priors┘                        │
                    │  #14 audit branches ──── low-effort (Ph.1)   │
                    │  #10 BRDF/PBR ────────── needs #11 (Ph.2)    │
                    └────────────┬─────────────────────────────────┘
                                 │ enables
                    ┌────────────▼─────────────────────────────────┐
                    │               mini-mesh                       │
                    │                                               │
                    │  Phase 1 ─────────────────────────────────── │
                    │  #10 resume training             P1           │
                    │                                               │
                    │  Phase 2 ─────────────────────────────────── │
                    │  #11 PBR textures    ← sdfstudio #10   P2    │
                    │  #13 Gaussian surface recon ← #8       P2    │
                    │  #6  retopology                        P2    │
                    │                                               │
                    │  Phase 3 ─────────────────────────────────── │
                    │  #14 hybrid SDF→GS   ← #13, blocked   P3    │
                    │  #15 GS densification                  P3    │
                    │  #16 Blender integration                P3    │
                    │  #5  E2E validation                    P3    │
                    └───────────────────────────────────────────────┘
```

## Phase 1: Foundation & Unblocking

Independent work streams that unblock everything downstream.

### Completed in v0.4.0

| Issue | Repo | Summary |
|-------|------|---------|
| [#7](https://github.com/hummat/mini-mesh/issues/7) | mini-mesh | Added nvdiffrast to Docker image for GPU-accelerated texturing |
| [#8](https://github.com/hummat/mini-mesh/issues/8) | mini-mesh | Added gsplat to Docker image (built as a wheel in the builder stage) |

### Pipeline UX

| Issue | Repo | Summary |
|-------|------|---------|
| [#10](https://github.com/hummat/mini-mesh/issues/10) | mini-mesh | Support resuming interrupted training runs (`--resume` flag) |

Biggest user-facing improvement. Long training runs (hours) currently lose all progress on interruption.

### SDFStudio quality fixes

| Issue | Repo | Summary |
|-------|------|---------|
| [sdfstudio#11](https://github.com/hummat/sdfstudio/issues/11) | sdfstudio | Add anneal-beta option to base surface model |
| [sdfstudio#12](https://github.com/hummat/sdfstudio/issues/12) | sdfstudio | Add focus centering method to dataparser |
| [sdfstudio#13](https://github.com/hummat/sdfstudio/issues/13) | sdfstudio | Add depth/normal prior support to BakedSDF |
| [sdfstudio#14](https://github.com/hummat/sdfstudio/issues/14) | sdfstudio | Audit upstream branches for unmerged features |

Three upstream PR ports (#11-#13) that improve SDF reconstruction quality. #14 is a low-effort audit that may surface free features.

### Suggested order (if sequential)

1. sdfstudio #11, #12, #13 — small, well-scoped upstream ports
2. mini-mesh #10 (resume) — pipeline logic change

The remaining tracks are independent and can be parallelized.

## Phase 2: PBR & Gaussian Surface Recon

Requires Phase 1 completion for key dependencies.

### PBR pipeline

| Issue | Repo | Summary | Depends on |
|-------|------|---------|------------|
| [sdfstudio#10](https://github.com/hummat/sdfstudio/issues/10) | sdfstudio | Integrate BRDF/PBR into training pipeline | sdfstudio #11 |
| [#11](https://github.com/hummat/mini-mesh/issues/11) | mini-mesh | **Tracking issue** — PBR texture extraction and BRDF-aware training | sdfstudio #10, #7 |
| [#19](https://github.com/hummat/mini-mesh/issues/19) | mini-mesh | glTF/GLB exporter with PBR channels (basecolor / ORM / normal) | — |
| [#20](https://github.com/hummat/mini-mesh/issues/20) | mini-mesh | UV-space multi-view texel observation builder | — |
| [#23](https://github.com/hummat/mini-mesh/issues/23) | mini-mesh | Differentiable GGX dielectric BRDF + UV-space optimizer | #20 |
| [#24](https://github.com/hummat/mini-mesh/issues/24) | mini-mesh | Per-view environment lighting estimator (SH + Spherical Gaussians) | #20 |
| [#21](https://github.com/hummat/mini-mesh/issues/21) | mini-mesh | PBR-NeRF energy conservation + NDF-weighted specular loss | sdfstudio#10, #5 |
| [#22](https://github.com/hummat/mini-mesh/issues/22) | mini-mesh | Evaluate TensoIR / NeILF++ as inverse-rendering backends | #5 |

Stage decomposition: #19 (export container) ← #23 + #24 ← #20 (observations).
Training-time regularizers: #21 (PBR-NeRF losses) on top of sdfstudio#10.
Alternative path: #22 (TensoIR/NeILF++) as research investigation.

### Gaussian surface reconstruction

| Issue | Repo | Summary | Depends on |
|-------|------|---------|------------|
| [#13](https://github.com/hummat/mini-mesh/issues/13) | mini-mesh | Support Gaussian-based surface recon (2DGS, SuGaR, DN-Splatter) | #8 |

Extends the pipeline to extract meshes from Gaussian methods, not just SDF. Requires updating `train.sh` routing and `export.sh`.

### Mesh quality

| Issue | Repo | Summary | Depends on |
|-------|------|---------|------------|
| [#6](https://github.com/hummat/mini-mesh/issues/6) | mini-mesh | Optional mesh retopology step (quad-dominant remeshing) | — |

Independent, but more valuable after PBR export exists (clean topology improves texturing).

## Phase 3: Research & Integration

Forward-looking features, some research-grade. Less deterministic timelines.

| Issue | Repo | Summary | Depends on |
|-------|------|---------|------------|
| [#14](https://github.com/hummat/mini-mesh/issues/14) | mini-mesh | Hybrid SDF→Gaussian pipeline | #13 |
| [#15](https://github.com/hummat/mini-mesh/issues/15) | mini-mesh | Surface-aware Gaussian densification strategies | #13 |
| [#16](https://github.com/hummat/mini-mesh/issues/16) | mini-mesh | Blender integration for viewing/artistic workflows | — |
| [#5](https://github.com/hummat/mini-mesh/issues/5) | mini-mesh | End-to-end validation with ground truth meshes | — |

Note: #5 (E2E validation) and #16 (Blender) have no hard dependencies and could be pulled earlier if prioritized.
