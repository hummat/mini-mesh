#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 200001
  --pipeline.datamanager.train-num-rays-per-batch 8192
  --pipeline.datamanager.eval-num-rays-per-batch 8192
  --pipeline.model.eval-num-rays-per-chunk 8192
  # BakedSDF/BakedAngelo paper/configs use no separate background model; keep that behavior here.
  --pipeline.model.background-model none

  --pipeline.model.steps-per-level 2000
  --pipeline.model.curvature-loss-warmup-steps 2000

  --optimizers.fields.scheduler.max-steps 200000
  --optimizers.fields.scheduler.warm-up-end 2000
  --optimizers.field-background.scheduler.max-steps 200000
  --optimizers.field-background.scheduler.warm-up-end 2000
)
