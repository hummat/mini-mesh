#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 200001
  --pipeline.model.proposal-warmup 2000
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000
  --pipeline.model.sdf-field.hash-smoothstep True
  --pipeline.model.eval-num-rays-per-chunk 8192
  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --optimizers.fields.scheduler.max-steps 200000
  --optimizers.fields.scheduler.warm-up-end 2000
  --optimizers.field-background.scheduler.max-steps 200000
  --optimizers.field-background.scheduler.warm-up-end 2000
  --optimizers.proposal-networks.scheduler.max-steps 200000
)