#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 100001
  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --pipeline.model.eval-num-rays-per-chunk 8192
  # BakedSDF paper/configs use no separate background model; keep that behavior here.
  --pipeline.model.background-model none
  --optimizers.fields.scheduler.max-steps 100000
  --optimizers.fields.scheduler.warm-up-end 1000
  --optimizers.field-background.scheduler.max-steps 100000
  --optimizers.field-background.scheduler.warm-up-end 1000
)
