#!/usr/bin/env bash
# Inspired by:
# 1. https://docs.nerf.studio/quickstart/installation.html#using-an-interactive-container
# 2. https://github.com/colmap/colmap/blob/main/docker/run-gui.sh
# 3. NVIDIA
xhost +local:"$(id -un)"
docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run -it --rm --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -u "$(id -u):$(id -g)" \
  -p 7007:7007 \
  -e QT_XCB_GL_INTEGRATION=xcb_egl \
  -e HOME=/tmp \
  -e TORCH_HOME=/.cache/torch \
  -e WANDB_API_KEY \
  -e WANDB_MODE \
  -e WANDB_PROJECT \
  -e DISPLAY="$DISPLAY" \
  -e XDG_RUNTIME_DIR=/tmp/runtime \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ~/.cache:/.cache \
  -v ~/.config:/.config \
  -v "$(dirname "$1")":/data \
  -v "$(dirname "$docker_dir")":/app \
  hummat/mini-mesh /app/scripts/run.sh /data/"$(basename "$1")" "${@:2}"
