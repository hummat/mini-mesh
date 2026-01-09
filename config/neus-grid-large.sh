#!/usr/bin/env bash
CONFIG=(
  # Variant with increased hash-grid capacity (higher peak detail).
  # Designed to stack with other configs (neus-grid / neus-grid-short / neus-grid-min).

  --pipeline.model.sdf-field.num-levels 16
  --pipeline.model.sdf-field.max-res 4096
  --pipeline.model.sdf-field.log2-hashmap-size 21
  --pipeline.model.sdf-field.use-position-encoding True
)
