#!/usr/bin/env bash
# Target: ~5-6 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 5001
  --trainer.steps-per-eval-batch 1000
  --trainer.steps-per-eval-image 1000
  --trainer.steps-per-save 5000

  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048

  # Cheaper NeuS sampling
  --pipeline.model.num-samples 32
  --pipeline.model.num-samples-importance 32
  --pipeline.model.num-up-sample-steps 2

  # Optimizers / schedulers
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.max-steps 5000
  --optimizers.fields.scheduler.warm-up-end 500
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.max-steps 5000
  --optimizers.field-background.scheduler.warm-up-end 500
  --pipeline.datamanager.camera-optimizer.scheduler.max-steps 3000

  # Downscale images for faster preview (routed to dataparser)
  --downscale-factor 2
)
