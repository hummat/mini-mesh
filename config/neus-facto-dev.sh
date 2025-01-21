#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.field-background.optimizer.lr 0.01
  --pipeline.model.proposal-warmup 200
  --pipeline.model.sdf-field.hash-smoothstep True
  --pipeline.model.eval-num-rays-per-chunk 8192
  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --optimizers.proposal-networks.scheduler.max-steps 20000
)