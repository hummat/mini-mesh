#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 100001
  --pipeline.model.near-plane 1
  --pipeline.model.far-plane 3
  --pipeline.model.sdf-field.num-layers 2
  --pipeline.model.sdf-field.num-layers-color 2
  # --pipeline.model.sdf-field.hidden-dim 512
  # --pipeline.model.sdf-field.hidden-dim-color 512
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.hash-smoothstep True
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 6144
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.max-steps 100000
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.max-steps 100000
  --optimizers.field-background.scheduler.warm-up-end 1000
)