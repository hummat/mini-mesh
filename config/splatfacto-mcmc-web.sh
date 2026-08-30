#!/usr/bin/env bash
# Web/blog embed preset: AA-aware splatfacto-mcmc tuned for Spark, Brush, or
# PlayCanvas (with GSplatParams.antiAlias = true). See docs/methods_and_models.md
# section 6 for the rendering-mode trade-off and viewer compatibility matrix.
CONFIG=(
  --max-num-iterations 30001
  --steps-per-save 5000
  --pipeline.model.rasterize-mode antialiased
  # The splat cap doubles as the web-delivery file-size budget. 250k keeps SOG
  # output near the 5-20 MB target; override it for denser, larger deliverables.
  --pipeline.model.max-gs-num 250000
  --pipeline.model.densify-grad-thresh 0.0008
)
