#!/usr/bin/env bash
# NeuS2 dev: short run, hash grid SDF with analytic curvature (tcnn double backward).
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000

  # Keep batches aligned with neus-grid-dev for fair timing
  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048

  # Hash SDF heads (match neuralangelo-dev depth/width)
  --pipeline.model.sdf-field.num-layers 1
  --pipeline.model.sdf-field.num-layers-color 4
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.use-numerical-gradients False  # rely on analytic grads

  # Optimizers / schedulers
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 12000 16000

  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 12000 16000

  # Camera refinement similar to neus-grid-dev
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
