#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
  --pipeline.model.sdf-field.num-layers 2
  --pipeline.model.sdf-field.num-layers-color 2
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.hash-smoothstep True
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 6144
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.max-steps 20000
  --optimizers.fields.scheduler.warm-up-end 200
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.max-steps 20000
  --optimizers.field-background.scheduler.warm-up-end 200
)