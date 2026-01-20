#!/usr/bin/env bash
# Neuralangelo dev: same architecture as neuralangelo-fast, but shorter run/schedules.
# Target: ~50–60 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 30001
  --trainer.steps-per-eval-batch 1000
  --trainer.steps-per-eval-image 1000
  --trainer.steps-per-save 5000

  # Keep the same model shape as neuralangelo-fast (inherits from defaults)
  --pipeline.model.steps-per-level 500
  --pipeline.model.curvature-loss-warmup-steps 500

  # Match neuralangelo-fast LRs, but with earlier decay
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 12000 18000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 12000 18000
)
