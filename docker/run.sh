#!/usr/bin/env bash
set -euo pipefail

docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=docker/common.sh
source "$docker_dir/common.sh"

usage() {
  cat <<EOF
Usage: docker/run.sh <input_path> [pipeline args...]

Environment:
  MINI_MESH_IMAGE        Docker image to use (default: local image if present, else hummat/mini-mesh:latest)
  MINI_MESH_DOCKER_APP  repo or image (default: repo)
  MINI_MESH_DOCKER_TTY  auto, on, or off (default: auto)
  MINI_MESH_DOCKER_X11  auto, on, or off (default: auto)
  MINI_MESH_DOCKER_PORT Host port for viewer/tensorboard, or none (default: 7007)
EOF
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

mini_mesh_resolve_input "$1"
shift
image="$(mini_mesh_select_image)"
mini_mesh_build_docker_args auto
mini_mesh_set_app_entrypoint

docker "${docker_args[@]}" "$image" "$mini_mesh_app_entrypoint" "$mini_mesh_container_input" "$@"
