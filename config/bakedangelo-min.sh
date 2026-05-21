#!/usr/bin/env bash
# Target: ~15 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 10001
  --trainer.steps-per-eval-batch 1000
  --trainer.steps-per-eval-image 1000
  --trainer.steps-per-save 5000
  --pipeline.datamanager.train-num-rays-per-batch 1024
  --pipeline.datamanager.eval-num-rays-per-batch 1024
  --pipeline.model.eval-num-rays-per-chunk 1024
  # BakedAngelo is a large-scene/heritage preset; keep it isolated from the
  # object-centric mini-mesh SDF defaults in config/defaults.sh.
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000.0
  --pipeline.model.background-model grid
  --pipeline.model.sdf-field.bias 1.5
  --pipeline.model.sdf-field.beta-init 0.1
  --pipeline.model.sdf-field.inside-outside True
  --pipeline.model.sdf-field.hash-smoothstep False

  # Optimizers / schedulers
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.max-steps 10000
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.max-steps 10000
)
