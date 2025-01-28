#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 100001
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000
  --pipeline.model.proposal-warmup 1000
  --pipeline.model.sdf-field.hash-smoothstep True
  --pipeline.model.eval-num-rays-per-chunk 8192
  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.max-steps 100000
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.max-steps 100000
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.proposal-networks.scheduler.max-steps 100000
)