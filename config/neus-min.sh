#!/usr/bin/env bash
# Target: ~15 minute run on ~12 GB GPUs
CONFIG=(
  --trainer.max-num-iterations 10001
  --trainer.steps-per-eval-batch 1000
  --trainer.steps-per-eval-image 1000
  --trainer.steps-per-save 5000

  --pipeline.datamanager.train-num-rays-per-batch 2048
  --pipeline.datamanager.eval-num-rays-per-batch 2048
  --pipeline.model.eval-num-rays-per-chunk 2048

  # Moderately cheaper NeuS sampling
  --pipeline.model.num-samples 48
  --pipeline.model.num-samples-importance 48
  --pipeline.model.num-up-sample-steps 3

  # Optimizers / schedulers
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.fields.scheduler.max-steps 10000
  --optimizers.fields.scheduler.warm-up-end 500
  --optimizers.field-background.optimizer.lr 0.01
  --optimizers.field-background.scheduler.max-steps 10000
  --optimizers.field-background.scheduler.warm-up-end 500
)
