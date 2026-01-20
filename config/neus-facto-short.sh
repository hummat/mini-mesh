#!/usr/bin/env bash
# Target: ~50–60 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.warm-up-end 500
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.warm-up-end 500
  --pipeline.model.proposal-warmup 200
  # VRAM-friendly defaults for ~12 GB GPUs; higher values are possible on 24 GB+
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 4096
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --optimizers.proposal-networks.scheduler.max-steps 20000
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
