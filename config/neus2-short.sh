#!/usr/bin/env bash
# NeuS2 short: short run corresponding to neus2-fast (hash SDF + analytic curvature).
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000

  # Keep batches aligned with neus-grid-short for fair timing
  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048

  # Match neus2-fast model shape (2/2 MLP) and hash SDF usage
  --pipeline.model.sdf-field.num-layers 2
  --pipeline.model.sdf-field.num-layers-color 2
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.use-numerical-gradients False  # rely on analytic grads

  # Progressive hash encoding (short-scale schedule)
  --pipeline.model.level-init 4
  --pipeline.model.steps-per-level 200

  # Loss / optimization closer to neus-grid-short
  --pipeline.model.rgb-loss-type L1            # match neus-grid
  --pipeline.model.eikonal-loss-mult 0.1       # match SurfaceModel default / neus-grid

  # Optimizers / schedulers (copy from neus-grid-short)
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.warm-up-end 200
  --optimizers.fields.scheduler.milestones 12000 16000

  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.warm-up-end 200
  --optimizers.field-background.scheduler.milestones 12000 16000

  # Camera refinement similar to neus-grid-short
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
