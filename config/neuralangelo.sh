#!/usr/bin/env bash
CONFIG=(
  --trainer.max-num-iterations 500001
  --pipeline.model.near-plane 1
  --pipeline.model.far-plane 5
  --pipeline.model.sdf-field.hash-smoothstep True
)