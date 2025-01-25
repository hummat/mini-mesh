#!/usr/bin/env bash
CONFIG=(
  --pipeline.model.steps-per-level 1000
  --pipeline.model.near-plane 1
  --pipeline.model.far-plane 5
  --pipeline.model.curvature-loss-warmup-steps 1000
  --pipeline.model.sdf-field.hash-smoothstep True
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 60000 80000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 60000 80000
  --trainer.max-num-iterations 100001
)