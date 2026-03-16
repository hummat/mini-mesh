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
                    │  #7  nvdiffrast Docker           P1           │
                    │  #8  gsplat Docker               P1           │
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

### Docker prerequisites

| Issue | Repo | Summary |
|-------|------|---------|
| [#7](https://github.com/hummat/mini-mesh/issues/7) | mini-mesh | Add nvdiffrast to Docker image for GPU-accelerated texturing |
| [#8](https://github.com/hummat/mini-mesh/issues/8) | mini-mesh | Add gsplat to Docker image (build wheel in builder stage) |

Unblocks: GPU texture baking (#11 Stage 3), all Gaussian methods (#13, #14, #15).

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
2. mini-mesh #7 (nvdiffrast) — build change, immediate texture speed benefit
3. mini-mesh #8 (gsplat) — build change, unblocks all Gaussian work
4. mini-mesh #10 (resume) — pipeline logic change

All four tracks are independent and can be parallelized.

## Phase 2: PBR & Gaussian Surface Recon

Requires Phase 1 completion for key dependencies.

### PBR pipeline

| Issue | Repo | Summary | Depends on |
|-------|------|---------|------------|
| [sdfstudio#10](https://github.com/hummat/sdfstudio/issues/10) | sdfstudio | Integrate BRDF/PBR into training pipeline | sdfstudio #11 |
| [#11](https://github.com/hummat/mini-mesh/issues/11) | mini-mesh | PBR texture extraction and BRDF-aware training (Stages 1-2) | sdfstudio #10, #7 |

Multi-stage: verify proxy PBR signals → glTF/GLB export → optional UV-space refinement.

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
| [#11 Stage 2.5/3](https://github.com/hummat/mini-mesh/issues/11) | mini-mesh | Advanced PBR: UV-space inverse rendering, nvdiffrec | #11 Stages 1-2 |

Note: #5 (E2E validation) and #16 (Blender) have no hard dependencies and could be pulled earlier if prioritized.
