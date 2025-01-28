#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 100001
  --pipeline.model.eval-num-rays-per-chunk 4096
  --pipeline.datamanager.train-num-rays-per-batch 4096
  --pipeline.datamanager.eval-num-rays-per-batch 4096
  --optimizers.fields.optimizer.lr 0.005
  --optimizers.fields.scheduler.max-steps 100000
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.field-background.optimizer.lr 0.005
  --optimizers.field-background.scheduler.max-steps 100000
  --optimizers.field-background.scheduler.warm-up-end 1000
)