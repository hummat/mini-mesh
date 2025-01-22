docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run \
  -u "$(id -u):$(id -g)" -p 7007:7007 -it --rm --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  -v ~/.cache:/.cache \
  -v ~/.config:/.config \
  -v "$(dirname "$1")":/workspace \
  -v "$(dirname "$docker_dir")":/tmp \
  hummat/mini-mesh /tmp/scripts/run.sh /workspace/"$(basename "$1")" "${@:2}"