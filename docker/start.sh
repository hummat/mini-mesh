#!/usr/bin/env bash
set -euo pipefail

docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=docker/common.sh
source "$docker_dir/common.sh"

usage() {
  cat <<EOF
Usage: docker/start.sh <input_or_data_path> [command...]

Starts a mini-mesh container with the same mounts and GPU settings as docker/run.sh.
If command is omitted, starts an interactive shell.
EOF
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

mini_mesh_resolve_input "$1"
shift
image="$(mini_mesh_select_image)"

if [[ $# -eq 0 ]]; then
  mini_mesh_build_docker_args on
  command_args=(bash)
else
  mini_mesh_build_docker_args auto
  command_args=("$@")
fi

if [[ "${MINI_MESH_DOCKER_APP:-repo}" = repo ]]; then
  docker_args+=(-v "$mini_mesh_repo_root:/app")
elif [[ "${MINI_MESH_DOCKER_APP:-repo}" != image ]]; then
  mini_mesh_die "MINI_MESH_DOCKER_APP must be one of: repo, image"
fi

docker "${docker_args[@]}" "$image" "${command_args[@]}"
