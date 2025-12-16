#!/usr/bin/env bash
# NeuS2 reference-ish short: same capacity/loss as neus2-ref but with a short training budget like neus-grid-short.
CONFIG=(
  --trainer.max-num-iterations 20001
  --trainer.steps-per-eval-batch 500
  --trainer.steps-per-eval-image 500
  --trainer.steps-per-save 2000

  # Match neus-grid-short ray budget
  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048

  # Use the same NeuS2-style SDF/encoding as neus2-ref
  --pipeline.model.sdf-field.num-layers 1
  --pipeline.model.sdf-field.num-layers-color 2
  --pipeline.model.sdf-field.use-grid-feature True
  --pipeline.model.sdf-field.use-numerical-gradients False
  --pipeline.model.sdf-field.num-levels 14
  --pipeline.model.sdf-field.log2-hashmap-size 19
  --pipeline.model.sdf-field.hash-features-per-level 2
  --pipeline.model.sdf-field.base-res 16
  --pipeline.model.sdf-field.max-res 2048

  # Progressive hash encoding (quick ramp-up, like neus2-ref)
  --pipeline.model.level-init 3
  --pipeline.model.steps-per-level 200

  # NeuS2-like loss & anneal settings
  --pipeline.model.rgb-loss-type Huber
  --pipeline.model.eikonal-loss-mult 0.01
  --pipeline.model.anneal-end 0

  # Optimizers / schedulers (same as neus2-ref)
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.warm-up-end 1000
  # Scale NeuS2 reference milestones (20k, 30k, 40k over 80k iters)
  # down to a 20k short run ~= 5k, 7.5k, 10k.
  --optimizers.fields.scheduler.milestones 5000 7500 10000

  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.milestones 5000 7500 10000

  # Camera refinement similar to neus-grid-short
  --pipeline.datamanager.camera-optimizer.optimizer.lr 1e-4
  --pipeline.datamanager.camera-optimizer.scheduler.lr-final 1e-5
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 5000
)
