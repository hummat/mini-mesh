#!/usr/bin/env bash
CONFIG=(
  --pipeline.model.steps-per-level 200
  --pipeline.model.curvature-loss-multi 0  # Disable curvature loss
  --pipeline.model.curvature-loss-warmup-steps 200
  --pipeline.model.sdf-field.num-layers 2
  --pipeline.model.sdf-field.num-layers-color 2
  --pipeline.model.sdf-field.log2-hashmap-size 19
  --pipeline.model.sdf-field.hash-features-per-level 2
  --pipeline.model.sdf-field.base-res 16
  --pipeline.model.sdf-field.max-res 2048
  --pipeline.model.sdf-field.use-numerical-gradients False  # Disable numerical gradients
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 6144
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 12000 16000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 200
  --optimizers.field-background.scheduler.milestones 12000 16000
  --trainer.max-num-iterations 200001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000
)