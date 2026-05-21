#!/usr/bin/env bash
# Target: ~50–60 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 10001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
  --pipeline.datamanager.train-num-rays-per-batch 4096
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --pipeline.model.eval-num-rays-per-chunk 4096
  # BakedAngelo is a large-scene/heritage preset; keep it isolated from the
  # object-centric mini-mesh SDF defaults in config/defaults.sh.
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000.0
  --pipeline.model.background-model grid
  --pipeline.model.sdf-field.bias 1.5
  --pipeline.model.sdf-field.beta-init 0.1
  --pipeline.model.sdf-field.inside-outside True
  --pipeline.model.sdf-field.hash-smoothstep False
  --optimizers.fields.scheduler.max-steps 10000
  --optimizers.field-background.scheduler.max-steps 10000
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
