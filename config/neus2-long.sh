#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 200001
  --trainer.steps-per-eval-batch 2000
  --trainer.steps-per-eval-image 2000
  --trainer.steps-per-save 10000

  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --pipeline.model.eval-num-rays-per-chunk 8192
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.use-numerical-gradients False

  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 2000
  --optimizers.fields.scheduler.milestones 100000 150000

  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 2000
  --optimizers.field-background.scheduler.milestones 100000 150000
)
