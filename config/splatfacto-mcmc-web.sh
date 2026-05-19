#!/usr/bin/env bash
# Web/blog embed preset: AA-aware splatfacto-mcmc tuned for Spark, Brush, or
# PlayCanvas (with GSplatParams.antiAlias = true). See docs/methods_and_models.md
# section 6 for the rendering-mode trade-off and viewer compatibility matrix.
CONFIG=(
  --max-num-iterations 30001
  --steps-per-save 5000
  --pipeline.model.rasterize-mode antialiased
  --pipeline.model.max-gs-num 750000
)
