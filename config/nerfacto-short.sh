#!/usr/bin/env bash
CONFIG=(
  # VRAM-friendly defaults for ~12 GB GPUs; higher values are possible on 24 GB+
  --pipeline.datamanager.train-num-rays-per-batch 16384
  --pipeline.datamanager.eval-num-rays-per-batch 16384
  --pipeline.model.predict-normals True
  --pipeline.model.use-average-appearance-embedding True
  --use-grad-scaler True
  --steps-per-save 1000
  --max-num-iterations 10001
  --optimizers.fields.scheduler.max-steps 10000
  --optimizers.proposal-networks.scheduler.max-steps 10000
  --optimizers.camera-opt.scheduler.max-steps 1000
  --optimizers.camera-opt.scheduler.lr-final 0.00001
  --optimizers.fields.optimizer.lr 0.05
  --optimizers.camera-opt.optimizer.lr 0.005
  --optimizers.proposal-networks.optimizer.lr 0.05
)
