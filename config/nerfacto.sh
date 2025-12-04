#!/usr/bin/env bash
CONFIG=(
  --pipeline.datamanager.train-num-rays-per-batch 32768
  --pipeline.datamanager.eval-num-rays-per-batch 32768
  --pipeline.model.predict-normals True
  --steps-per-save 2000
  --max-num-iterations 30001
  --optimizers.fields.scheduler.max-steps 30000
  --optimizers.proposal-networks.scheduler.max-steps 30000
  --optimizers.camera-opt.scheduler.max-steps 5000
  --optimizers.camera-opt.scheduler.lr-final 0.00001
  --optimizers.fields.optimizer.lr 0.01
  --optimizers.camera-opt.optimizer.lr 0.001
  --optimizers.proposal-networks.optimizer.lr 0.01
)
