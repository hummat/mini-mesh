#!/usr/bin/env bash
set -euo pipefail

mini_mesh_docker_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mini_mesh_repo_root="$(dirname "$mini_mesh_docker_dir")"
mini_mesh_input_path=""
mini_mesh_input_mount=""
mini_mesh_container_input=""
mini_mesh_app_entrypoint=""
mini_mesh_xhost_user=""

mini_mesh_die() {
  echo "ERROR: $*" >&2
  exit 1
}

mini_mesh_shell_join() {
  local quoted_args=()
  local quoted_arg
  local arg
  for arg in "$@"; do
    printf -v quoted_arg "%q" "$arg"
    quoted_args+=("$quoted_arg")
  done
  local IFS=" "
  printf "%s" "${quoted_args[*]}"
}

mini_mesh_cleanup_xhost() {
  if [[ -n "$mini_mesh_xhost_user" ]] && command -v xhost >/dev/null 2>&1; then
    xhost -local:"$mini_mesh_xhost_user" >/dev/null 2>&1 || true
  fi
}

mini_mesh_resolve_input() {
  local input="$1"

  [[ -e "$input" ]] || mini_mesh_die "Input path does not exist: $input"
  mini_mesh_input_path="$(realpath "$input")"
  mini_mesh_input_mount="$(dirname "$mini_mesh_input_path")"
  # shellcheck disable=SC2034  # Used by scripts that source this helper.
  mini_mesh_container_input="/data/$(basename "$mini_mesh_input_path")"
}

mini_mesh_select_image() {
  if [[ -n "${MINI_MESH_IMAGE:-}" ]]; then
    printf '%s\n' "$MINI_MESH_IMAGE"
    return
  fi

  case "${MINI_MESH_USE_LOCAL_IMAGE:-off}" in
    on|true|1)
      if docker image inspect hummat/mini-mesh:local >/dev/null 2>&1; then
        echo "Using local Docker image: hummat/mini-mesh:local" >&2
        printf '%s\n' "hummat/mini-mesh:local"
      else
        mini_mesh_die "MINI_MESH_USE_LOCAL_IMAGE is set, but hummat/mini-mesh:local does not exist"
      fi
      ;;
    off|false|0|"")
      printf '%s\n' "hummat/mini-mesh:latest"
      ;;
    *)
      mini_mesh_die "MINI_MESH_USE_LOCAL_IMAGE must be one of: on, off"
      ;;
  esac
}

mini_mesh_add_tty_args() {
  local default_mode="$1"
  local mode="${MINI_MESH_DOCKER_TTY:-$default_mode}"
  case "$mode" in
    auto)
      if [[ -t 0 && -t 1 ]]; then
        docker_args+=("-it")
      fi
      ;;
    on|true|1)
      docker_args+=("-it")
      ;;
    off|false|0)
      ;;
    *)
      mini_mesh_die "MINI_MESH_DOCKER_TTY must be one of: auto, on, off"
      ;;
  esac
}

mini_mesh_add_x11_args() {
  local mode="${MINI_MESH_DOCKER_X11:-auto}"
  case "$mode" in
    off|false|0|none)
      return
      ;;
    auto|on|true|1)
      ;;
    *)
      mini_mesh_die "MINI_MESH_DOCKER_X11 must be one of: auto, on, off"
      ;;
  esac

  if [[ -z "${DISPLAY:-}" ]] || [[ ! -d /tmp/.X11-unix ]] || ! command -v xhost >/dev/null 2>&1; then
    if [[ "$mode" = on || "$mode" = true || "$mode" = 1 ]]; then
      mini_mesh_die "X11 requested, but DISPLAY, /tmp/.X11-unix, or xhost is unavailable"
    fi
    return
  fi

  mini_mesh_xhost_user="$(id -un)"
  xhost +local:"$mini_mesh_xhost_user" >/dev/null
  trap mini_mesh_cleanup_xhost EXIT

  docker_args+=(
    -e QT_XCB_GL_INTEGRATION=xcb_egl
    -e "DISPLAY=$DISPLAY"
    -e XDG_RUNTIME_DIR=/tmp/runtime
    -v /tmp/.X11-unix:/tmp/.X11-unix
  )
}

mini_mesh_add_port_args() {
  local port="${MINI_MESH_DOCKER_PORT:-7007}"
  case "$port" in
    ""|none|off|0)
      ;;
    *)
      docker_args+=(-p "$port:7007")
      ;;
  esac
}

mini_mesh_set_app_entrypoint() {
  local app_mode="${MINI_MESH_DOCKER_APP:-repo}"
  case "$app_mode" in
    repo)
      docker_args+=(-v "$mini_mesh_repo_root:/app")
      # shellcheck disable=SC2034  # Used by scripts that source this helper.
      mini_mesh_app_entrypoint="/app/scripts/run.sh"
      ;;
    image)
      # shellcheck disable=SC2034  # Used by scripts that source this helper.
      mini_mesh_app_entrypoint="/opt/mini-mesh/scripts/run.sh"
      ;;
    *)
      mini_mesh_die "MINI_MESH_DOCKER_APP must be one of: repo, image"
      ;;
  esac
}

mini_mesh_build_docker_args() {
  local default_tty="$1"
  docker_args=(run --rm)
  mini_mesh_add_tty_args "$default_tty"
  docker_args+=(
    --gpus all
    --ipc=host
    --ulimit memlock=-1
    --ulimit stack=67108864
    -u "$(id -u):$(id -g)"
  )
  mini_mesh_add_port_args
  docker_args+=(
    -e HOME=/tmp
    -e LOGNAME=mini-mesh
    -e MINI_MESH_VENV_BIN=/opt/conda/bin
    -e MINI_MESH_LOCAL_PREFIX=/usr/local
    -e TORCH_HOME=/.cache/torch
    -e TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor
    -e USER=mini-mesh
    -e WANDB_API_KEY
    -e WANDB_MODE
    -e WANDB_PROJECT
  )
  mini_mesh_add_x11_args
  docker_args+=(
    -v "$HOME/.cache:/.cache"
    -v "$HOME/.config:/.config"
    -v "$mini_mesh_input_mount:/data"
  )
}
