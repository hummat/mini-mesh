#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.field-background.optimizer.lr 0.01
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000
  --pipeline.model.proposal-warmup 200
  --pipeline.model.sdf-field.beta-init 0.1
  # VRAM-friendly defaults for ~12 GB GPUs; higher values are possible on 24 GB+
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 4096
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --optimizers.proposal-networks.scheduler.max-steps 20000
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
