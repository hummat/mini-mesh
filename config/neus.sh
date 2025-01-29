#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 200001
  --optimizers.fields.scheduler.max-steps 200000
  --optimizers.fields.scheduler.warm-up-end 2000
  --optimizers.field-background.scheduler.max-steps 200000
  --optimizers.field-background.scheduler.warm-up-end 2000
)