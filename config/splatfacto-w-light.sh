#!/usr/bin/env bash
CONFIG=(
  # Mirrors the plugin's Nerfstudio-compatible light preset while making the
  # supported mini-mesh variant explicit.
  --pipeline.model.use-avg-appearance True
  --max-num-iterations 30001
  --steps-per-save 2000
)
