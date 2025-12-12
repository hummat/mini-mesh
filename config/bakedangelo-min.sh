#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 7001
  --trainer.steps-per-eval-batch 2000
  --trainer.steps-per-eval-image 2000
  --trainer.steps-per-save 7001
  --pipeline.datamanager.train-num-rays-per-batch 1024
  --pipeline.datamanager.eval-num-rays-per-batch 1024
  --pipeline.model.eval-num-rays-per-chunk 1024
  # BakedAngelo inherits BakedSDF's choice of no background model.
  --pipeline.model.background-model none
)
