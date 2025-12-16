#!/usr/bin/env bash
# NeuS2 reference-ish config: NeuS2-style hash grid + MLP sizes and loss/schedules, longer training budget.
CONFIG=(
  # Use a longer training budget than neus-grid-short, closer to NeuS2's per-scene training
  --trainer.max-num-iterations 80001
  --trainer.steps-per-eval-batch 2000
  --trainer.steps-per-eval-image 2000
  --trainer.steps-per-save 10000

  # Slightly larger per-step ray budget (like neuralangelo-opt-short)
  --pipeline.datamanager.train-num-rays-per-batch 6144
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --pipeline.model.eval-num-rays-per-chunk 4096

  # NeuS2-style hash SDF: 1 hidden layer for SDF, 2 for color
  --pipeline.model.sdf-field.num-layers 1
  --pipeline.model.sdf-field.num-layers-color 2
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.use-numerical-gradients False  # rely on analytic grads
  --pipeline.model.sdf-field.num-levels 14
  --pipeline.model.sdf-field.log2-hashmap-size 19
  --pipeline.model.sdf-field.hash-features-per-level 2
  --pipeline.model.sdf-field.base-res 16
  --pipeline.model.sdf-field.max-res 2048

  # Progressive hash encoding (approximate NeuS2-style quick ramp-up)
  --pipeline.model.level-init 3
  --pipeline.model.steps-per-level 200

  # Loss weights closer to NeuS2 hyperparams
  --pipeline.model.rgb-loss-type Huber          # NeuS2 uses Huber loss
  --pipeline.model.eikonal-loss-mult 0.01        # ek_loss_weight ~ 0.01
  --pipeline.model.anneal-end 0                  # disable cos-anneal (NeuS2-style)

  # Optimizers / schedulers (approximate NeuS2 ExponentialDecay)
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.fields.scheduler.milestones 20000 30000 40000

  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 20000 30000 40000

  # Camera refinement similar to other short configs
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
