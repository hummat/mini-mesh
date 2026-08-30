#!/usr/bin/env bash
# Web/blog embed preset: AA-aware splatfacto-mcmc tuned for Spark, Brush, or
# PlayCanvas (with GSplatParams.antiAlias = true). See docs/methods_and_models.md
# section 6 for the rendering-mode trade-off and viewer compatibility matrix.
CONFIG=(
  --max-num-iterations 30001
  --steps-per-save 5000
  --pipeline.model.rasterize-mode antialiased
  # 250k, not the 750k an earlier revision had: the cap doubles as the file-size
  # budget, and the executed blog runs (WEB250k on RMC-C01, 2026-08) validated
  # 250k as the value that keeps .sog output in the 5-20 MB target.
  --pipeline.model.max-gs-num 250000
  --pipeline.model.densify-grad-thresh 0.0008
)
