#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
  cat <<EOF
Usage: docker/build.sh [variant] [options]

Variants:
  full    Multi-GPU support, all optional deps (~11.6GB) [default]
  slim    Multi-GPU support, core only (~9GB)
  local   Single GPU, native CPU optimizations (don't publish)

Options:
  --cuda-arch <CC>   CUDA compute capability for local builds, e.g. 89 or 8.9 (default: auto-detect)
  --max-jobs <N>     Parallel compile jobs (default: 8)
  --no-gui           Build COLMAP without GUI
  --help             Show this help

Environment:
  MINI_MESH_DOCKER_BUILD_NETWORK  Optional docker build network mode, e.g. host

Examples:
  docker/build.sh                    # Build full image
  docker/build.sh slim               # Build slim image
  docker/build.sh local              # Build local with auto-detected GPU
  docker/build.sh local --cuda-arch 89   # Build local for RTX 40xx
EOF
  exit 0
}

# Defaults
VARIANT="full"
CUDA_ARCH=""
MAX_JOBS="8"
WITH_GUI="ON"
CMAKE_CUDA_ARCHES=""
TORCH_CUDA_ARCHES=""

format_cuda_arches() {
  local input="$1"
  local normalized
  local token
  local suffix
  local numeric
  local split_at
  local -a arch_tokens

  normalized="$(printf '%s' "$input" | tr ',' ';' | tr -d '[:space:]')"
  CMAKE_CUDA_ARCHES=""
  TORCH_CUDA_ARCHES=""

  IFS=';' read -r -a arch_tokens <<< "$normalized"
  for token in "${arch_tokens[@]}"; do
    [[ -n "$token" ]] || continue

    suffix=""
    if [[ "$token" == *+PTX ]]; then
      suffix="+PTX"
      token="${token%+PTX}"
    fi

    numeric="${token//./}"
    if [[ ! "$numeric" =~ ^[0-9]+$ || "${#numeric}" -lt 2 ]]; then
      echo "Error: unsupported CUDA arch '$token'. Use values like 89, 8.9, or 75;80;86;89." >&2
      exit 1
    fi

    split_at=$((${#numeric} - 1))
    CMAKE_CUDA_ARCHES+="${CMAKE_CUDA_ARCHES:+;}${numeric}"
    TORCH_CUDA_ARCHES+="${TORCH_CUDA_ARCHES:+;}${numeric:0:split_at}.${numeric:split_at:1}${suffix}"
  done

  if [[ -z "$CMAKE_CUDA_ARCHES" ]]; then
    echo "Error: CUDA arch list is empty." >&2
    exit 1
  fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    full|slim|local)
      VARIANT="$1"
      shift
      ;;
    --cuda-arch)
      CUDA_ARCH="$2"
      shift 2
      ;;
    --max-jobs)
      MAX_JOBS="$2"
      shift 2
      ;;
    --no-gui)
      WITH_GUI="OFF"
      shift
      ;;
    --help|-h)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Auto-detect CUDA arch for local builds
if [[ "$VARIANT" == "local" && -z "$CUDA_ARCH" ]]; then
  # Try env vars first (useful when nvidia-smi unavailable)
  if [[ -n "${TORCH_CUDA_ARCH_LIST:-}" ]]; then
    CUDA_ARCH="$TORCH_CUDA_ARCH_LIST"
    echo "Using TORCH_CUDA_ARCH_LIST from environment: $CUDA_ARCH"
  elif [[ -n "${CUDAARCHS:-}" ]]; then
    CUDA_ARCH="$CUDAARCHS"
    echo "Using CUDAARCHS from environment: $CUDA_ARCH"
  elif [[ -n "${CMAKE_CUDA_ARCHITECTURES:-}" ]]; then
    CUDA_ARCH="$CMAKE_CUDA_ARCHITECTURES"
    echo "Using CMAKE_CUDA_ARCHITECTURES from environment: $CUDA_ARCH"
  elif command -v nvidia-smi &>/dev/null; then
    CUDA_ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d ' \n\r')
    echo "Auto-detected CUDA compute capability: $CUDA_ARCH"
  else
    echo "Error: Cannot detect CUDA arch."
    echo "Set TORCH_CUDA_ARCH_LIST, use --cuda-arch <CC>, or install nvidia-smi"
    exit 1
  fi
fi

if [[ -n "$CUDA_ARCH" ]]; then
  format_cuda_arches "$CUDA_ARCH"
fi

# Build arguments based on variant
case "$VARIANT" in
  full)
    TAG="hummat/mini-mesh:latest"
    BUILD_ARGS=(
      --build-arg "MAX_JOBS=$MAX_JOBS"
      --build-arg "WITH_GUI=$WITH_GUI"
    )
    ;;
  slim)
    TAG="hummat/mini-mesh:slim"
    BUILD_ARGS=(
      --build-arg "MAX_JOBS=$MAX_JOBS"
      --build-arg "WITH_GUI=$WITH_GUI"
      --build-arg "INSTALL_OPTIONAL_DEPS=OFF"
    )
    ;;
  local)
    TAG="hummat/mini-mesh:local"
    BUILD_ARGS=(
      --build-arg "CMAKE_CUDA_ARCHITECTURES=$CMAKE_CUDA_ARCHES"
      --build-arg "TORCH_CUDA_ARCH_LIST=$TORCH_CUDA_ARCHES"
      --build-arg "CXXFLAGS=-O3 -DNDEBUG -march=native"
      --build-arg "MAX_JOBS=$MAX_JOBS"
      --build-arg "WITH_GUI=$WITH_GUI"
    )
    ;;
esac

echo "Building $TAG..."
DOCKER_ARGS=(build -t "$TAG" -f "$SCRIPT_DIR/Dockerfile")
if [[ -n "${MINI_MESH_DOCKER_BUILD_NETWORK:-}" ]]; then
  DOCKER_ARGS+=(--network "$MINI_MESH_DOCKER_BUILD_NETWORK")
fi

DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}" docker "${DOCKER_ARGS[@]}" "${BUILD_ARGS[@]}" "$REPO_ROOT"
