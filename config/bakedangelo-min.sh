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
  # BakedAngelo inherits BakedSDF's choice of no background model.
  --pipeline.model.background-model none

  # Optimizers / schedulers
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.max-steps 10000
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.max-steps 10000
)
