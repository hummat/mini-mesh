#!/usr/bin/env bash
CONFIG=(
  # Variant with reduced hash-grid capacity (faster per-step, lower peak detail).
  # Designed to stack with other configs (neus-grid-dev / neus-grid-preview / neus-grid-min).

  --pipeline.model.sdf-field.num-levels 12
  --pipeline.model.sdf-field.max-res 1024
  --pipeline.model.sdf-field.log2-hashmap-size 18
  --pipeline.model.sdf-field.use-position-encoding False
)

