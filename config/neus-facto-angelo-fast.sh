#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 100001
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000
  --pipeline.model.level-init 4
  --pipeline.model.steps-per-level 1000
  --pipeline.model.eikonal-loss-mult 0.1
  --pipeline.model.use-anneal-beta False  # Disable beta annealing
  --pipeline.model.beta-anneal-init 0.1
  --pipeline.model.beta-anneal-max-num-iters 100000
  --pipeline.model.proposal-warmup 1000
  --pipeline.model.curvature-loss-warmup-steps 1000
  --pipeline.model.sdf-field.beta-init 0.1
  --pipeline.model.eval-num-rays-per-chunk 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 60000 80000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 60000 80000
  --optimizers.proposal-networks.scheduler.max-steps 100000
)