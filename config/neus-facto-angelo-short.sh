#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000

  --pipeline.datamanager.train-num-rays-per-batch 4096
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.model.proposal-warmup 200

  --pipeline.model.steps-per-level 1000
  --pipeline.model.curvature-loss-warmup-steps 1000

  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 12000 18000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 12000 18000
  --optimizers.proposal-networks.scheduler.max-steps 20000

  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
