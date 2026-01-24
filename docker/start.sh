#!/usr/bin/env bash
xhost +local:"$(id -un)"
docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
image="${MINI_MESH_IMAGE:-hummat/mini-mesh}"
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
  "$image"
