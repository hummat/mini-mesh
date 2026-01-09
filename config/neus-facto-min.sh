#!/usr/bin/env bash
CONFIG=(
  # Target: ~25–35 minute run on ~12 GB GPUs

  --trainer.max-num-iterations 7001
  --trainer.steps-per-eval-batch 2000
  --trainer.steps-per-eval-image 2000
  --trainer.steps-per-save 5000

  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048
  --pipeline.model.proposal-warmup 200

  # Match schedulers to shorter training
  --optimizers.fields.scheduler.max-steps 7000
  --optimizers.field-background.scheduler.max-steps 7000
  --optimizers.proposal-networks.scheduler.max-steps 7000
)
