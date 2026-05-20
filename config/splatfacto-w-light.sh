#!/usr/bin/env bash
CONFIG=(
  # Mirrors the plugin's Nerfstudio-compatible light preset while making the
  # supported mini-mesh variant explicit. Keep exported PLYs portable by using
  # classic splat rasterization, and use denser splatfacto-big/MCMC-style
  # refinement thresholds instead of W-light's aggressive opacity culling.
  --pipeline.model.use-avg-appearance True
  --pipeline.model.rasterize-mode classic
  --pipeline.model.cull-alpha-thresh 0.005
  --pipeline.model.densify-grad-thresh 0.0005
  --pipeline.model.stop-split-at 25000
  --max-num-iterations 30001
  --steps-per-save 2000
)
