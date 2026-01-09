#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 10001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
  --pipeline.datamanager.train-num-rays-per-batch 4096
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --pipeline.model.eval-num-rays-per-chunk 4096
  # BakedSDF-MLP also runs without a separate background model in upstream configs.
  --pipeline.model.background-model none
  --optimizers.fields.scheduler.max-steps 10000
  --optimizers.field-background.scheduler.max-steps 10000
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
