#!/usr/bin/env bash
# NeuS2 full config: more similar to neus-grid-fast (hash SDF, larger MLP) but with analytic curvature.
CONFIG=(
  --trainer.max-num-iterations 100001

  # Match neus-grid-fast model shape (2/2 MLP) and hash SDF usage
  --pipeline.model.sdf-field.num-layers 2
  --pipeline.model.sdf-field.num-layers-color 2
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.use-numerical-gradients False  # rely on analytic grads

  # Progressive hash encoding (grid-like capacity, full levels by ~50k)
  --pipeline.model.level-init 4
  --pipeline.model.steps-per-level 1000

  # Ray budgets comparable to neus-grid-fast
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 6144
  --pipeline.datamanager.eval-num-rays-per-batch 4096

  # Loss / optimization closer to neus-grid-fast
  --pipeline.model.rgb-loss-type L1            # match neus-grid-fast
  --pipeline.model.eikonal-loss-mult 0.1       # match SurfaceModel default / neus-grid

  # Optimizers / schedulers (copy from neus-grid-fast)
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.max-steps 100000
  --optimizers.fields.scheduler.warm-up-end 1000

  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.max-steps 100000
  --optimizers.field-background.scheduler.warm-up-end 1000
)
