#!/usr/bin/env bash
DEFAULTS=(
  --trainer.mixed-precision True
  --trainer.steps-per-eval-batch 5000
  --trainer.steps-per-eval-image 5000
  --trainer.steps-per-save 20000
  --optimizers.fields.optimizer.lr 0.001
  --optimizers.fields.optimizer.weight-decay 0.01
  --optimizers.field-background.optimizer.lr 0.001
  --optimizers.field-background.optimizer.weight-decay 0.01
  --pipeline.model.near-plane 0.01
  --pipeline.model.far-plane 1000
  --pipeline.model.overwrite-near-far-plane True
  --pipeline.model.background-model mlp
  --pipeline.model.eval-num-rays-per-chunk 1024
  --pipeline.model.sdf-field.inside-outside False
  --pipeline.model.sdf-field.bias 0.1
  --pipeline.model.sdf-field.beta-init 0.1
  --pipeline.model.sdf-field.use-appearance-embedding True
  --pipeline.model.sdf-field.appearance-embedding-dim 16
  # --pipeline.model.sdf-field.use-diffuse-color True
  # --pipeline.model.sdf-field.use-specular-tint True
  # --pipeline.model.sdf-field.use-reflections True
  # --pipeline.model.sdf-field.use-n-dot-v True
  # --pipeline.model.sdf-field.off-axis True
  --vis wandb
)

DATA_DEFAULTS=(
  --downscale-factor 1
  --scale-factor 2
  --center-method focus
  --orientation-method vertical
  --train-split-fraction 0.95
  # --use-all-train-images True
)