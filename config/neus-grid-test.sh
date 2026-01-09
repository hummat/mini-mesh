#!/usr/bin/env bash
CONFIG=(
  # Target: ~10–15 minute preview on ~12 GB GPUs

  # Fewer iterations, same per-step ray budget as neus-grid-short (2048)
  --trainer.max-num-iterations 3001
  --trainer.steps-per-eval-batch 2000
  --trainer.steps-per-eval-image 2000
  --trainer.steps-per-save 5000

  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048
  --pipeline.model.sdf-field.use-position-encoding True

  # Cheaper NeuS sampling
  --pipeline.model.num-samples 32
  --pipeline.model.num-samples-importance 32
  --pipeline.model.num-up-sample-steps 2

  # Match schedulers to shorter training
  --optimizers.fields.scheduler.max-steps 3000
  --optimizers.field-background.scheduler.max-steps 3000

  # Camera optimizer: stop a bit earlier on very short runs
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 2000

  # Downscale images for faster preview (can be overridden)
  --downscale-factor 2
)
