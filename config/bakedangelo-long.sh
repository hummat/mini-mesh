#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 200001
  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --pipeline.model.eval-num-rays-per-chunk 8192
  # BakedAngelo is a large-scene/heritage preset; keep it isolated from the
  # object-centric mini-mesh SDF defaults in config/defaults.sh.
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000.0
  --pipeline.model.background-model grid
  --pipeline.model.sdf-field.bias 1.5
  --pipeline.model.sdf-field.beta-init 0.1
  --pipeline.model.sdf-field.inside-outside True
  --pipeline.model.sdf-field.hash-smoothstep False

  --pipeline.model.steps-per-level 2000
  --pipeline.model.curvature-loss-warmup-steps 2000

  --optimizers.fields.scheduler.max-steps 200000
  --optimizers.fields.scheduler.warm-up-end 2000
  --optimizers.field-background.scheduler.max-steps 200000
  --optimizers.field-background.scheduler.warm-up-end 2000
)
