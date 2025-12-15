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
  --pipeline.model.near-plane 1
  --pipeline.model.far-plane 5
  --pipeline.model.overwrite-near-far-plane True
  --pipeline.model.background-model mlp
  --pipeline.model.eval-num-rays-per-chunk 1024
  --pipeline.model.sdf-field.inside-outside False
  --pipeline.model.sdf-field.hash-smoothstep True
  --pipeline.model.sdf-field.bias 0.1
  --pipeline.model.sdf-field.beta-init 0.2
  --pipeline.model.sdf-field.use-appearance-embedding True
  --pipeline.model.sdf-field.appearance-embedding-dim 16
  # --pipeline.model.sdf-field.use-diffuse-color True
  # --pipeline.model.sdf-field.use-specular-tint True
  # --pipeline.model.sdf-field.use-reflections True
  # --pipeline.model.sdf-field.use-n-dot-v True
  # --pipeline.model.sdf-field.off-axis True
  --pipeline.datamanager.camera-optimizer.optimizer.weight-decay 0
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-6
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 25000
  --vis tensorboard
  --viewer.ip-address "0.0.0.0"
)

NERF_DEFAULTS=(
  --vis tensorboard
  --viewer.websocket-host "0.0.0.0"
)

SPLAT_DEFAULTS=(
  --vis tensorboard
  --viewer.websocket-host "0.0.0.0"
)

DATA_DEFAULTS=(
  --downscale-factor 1
  --scale-factor 2.5
  --center-method focus
  --orientation-method vertical
  --auto-scale-poses median
  --train-split-fraction 0.95
  # --use-all-train-images True
)

NS_DATA_DEFAULTS=(
  --downscale-factor 1
  --scale-factor 1
  --center-method focus
  --orientation-method vertical
  --auto-scale-poses True
  --train-split-fraction 0.95
  # --use-all-train-images True
)
