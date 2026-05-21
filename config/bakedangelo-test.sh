#!/usr/bin/env bash
# Target: ~5-6 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 5001
  --trainer.steps-per-eval-batch 1000
  --trainer.steps-per-eval-image 1000
  --trainer.steps-per-save 5000

  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048
  # BakedAngelo is a large-scene/heritage preset; keep it isolated from the
  # object-centric mini-mesh SDF defaults in config/defaults.sh.
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000.0
  --pipeline.model.overwrite-near-far-plane True
  --pipeline.model.background-model grid
  --pipeline.model.sdf-field.bias 1.5
  --pipeline.model.sdf-field.beta-init 0.1
  --pipeline.model.sdf-field.inside-outside True
  --pipeline.model.sdf-field.hash-smoothstep False

  --pipeline.model.steps-per-level 500
  --pipeline.model.curvature-loss-warmup-steps 500

  # Optimizers / schedulers
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.max-steps 5000
  --optimizers.fields.scheduler.warm-up-end 500
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.max-steps 5000
  --optimizers.field-background.scheduler.warm-up-end 500
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 3000

  # Downscale images for faster preview (routed to dataparser)
  --downscale-factor 2
)
