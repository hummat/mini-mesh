# Inspired by:
# 1. https://docs.nerf.studio/quickstart/installation.html#using-an-interactive-container
# 2. https://github.com/colmap/colmap/blob/main/docker/run-gui.sh
# 3. NVIDIA
docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run -it --rm --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -u "$(id -u):$(id -g)" \
  -p 7007:7007 \
  -e QT_XCB_GL_INTEGRATION=xcb_egl \
  -e DISPLAY="$DISPLAY" \
  -e XDG_RUNTIME_DIR=/tmp/runtime \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ~/.cache:/.cache \
  -v ~/.config:/.config \
  -v "$(dirname "$1")":/workspace \
  -v "$(dirname "$docker_dir")":/tmp \
  hummat/mini-mesh /tmp/scripts/run.sh /workspace/"$(basename "$1")" "${@:2}"