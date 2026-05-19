#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname "$script_dir")"
cd "$repo_root"

: "${MINI_MESH_LOCAL_PREFIX:=$repo_root/.local/mini-mesh}"
: "${MINI_MESH_BUILD_ROOT:=$repo_root/.local/build}"
: "${POSELIB_REF:=7e9f5f53372e43f89655040d4dfc4a00e5ace11c}"
: "${COLMAP_REF:=c5f9cefc87e5dd596b638e4cee0ff543c7d14755}"
: "${GLOMAP_REF:=0edb1b8435e0f9a594318908b81a31f078a51bf7}"
: "${TCNN_REF:=32507f059d7abc8c13f5df81ea9597b70923ee44}"
: "${NVDIFFRAST_REF:=253ac4fcea7de5f396371124af597e6cc957bfae}"
: "${GSPLAT_VERSION:=1.4.0}"
: "${SPLATFACTOW_REF:=119a3bfb3aa03669278e174ff11c4dfdcbcf97d7}"
: "${BUILD_SFM:=ON}"
: "${INSTALL_PYTHON_DEPS:=ON}"
: "${INSTALL_HLOC:=ON}"
: "${WITH_GUI:=ON}"

required_vars=(CUDA_HOME CC CXX CUDAHOSTCXX TORCH_CUDA_ARCH_LIST MAX_JOBS)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "ERROR: $var_name is not set. Load your CUDA build env first." >&2
    echo "       For direnv users: run 'direnv allow' or 'direnv reload'." >&2
    exit 1
  fi
done

required_commands=(git cmake ninja uv "$CC" "$CXX" "$CUDAHOSTCXX" nvcc)
for cmd in "${required_commands[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  fi
done

if [[ ! -f "$CUDA_HOME/include/cuda_runtime.h" ]]; then
  echo "ERROR: CUDA headers not found at $CUDA_HOME/include" >&2
  echo "       Fix your CUDA build environment before running local setup." >&2
  exit 1
fi

if [[ ! -d "$CUDA_HOME/lib64" ]]; then
  echo "ERROR: CUDA libraries not found at $CUDA_HOME/lib64" >&2
  echo "       Fix your CUDA build environment before running local setup." >&2
  exit 1
fi

if [[ "$BUILD_SFM" = ON && -f /usr/lib/libfreeimage.so ]]; then
  freeimage_missing_deps="$(ldd /usr/lib/libfreeimage.so | sed -n '/not found/p')"
  if [[ -n "$freeimage_missing_deps" ]]; then
    echo "ERROR: /usr/lib/libfreeimage.so has missing runtime dependencies:" >&2
    echo "$freeimage_missing_deps" >&2
    echo "       Reinstall or rebuild the host freeimage package before building COLMAP locally." >&2
    exit 1
  fi
fi

export PATH="$MINI_MESH_LOCAL_PREFIX/bin${PATH:+:$PATH}"
export LD_LIBRARY_PATH="$MINI_MESH_LOCAL_PREFIX/lib:$MINI_MESH_LOCAL_PREFIX/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CMAKE_PREFIX_PATH="$MINI_MESH_LOCAL_PREFIX${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
export CMAKE_C_COMPILER="$CC"
export CMAKE_CXX_COMPILER="$CXX"
export CMAKE_CUDA_HOST_COMPILER="$CUDAHOSTCXX"
export CMAKE_CUDA_ARCHITECTURES="${TORCH_CUDA_ARCH_LIST//+PTX/}"
export CMAKE_CUDA_ARCHITECTURES="${CMAKE_CUDA_ARCHITECTURES//./}"
export CCACHE_DIR="${CCACHE_DIR:-$repo_root/.local/ccache}"
export CCACHE_TEMPDIR="${CCACHE_TEMPDIR:-$repo_root/.local/ccache-tmp}"

mkdir -p "$MINI_MESH_LOCAL_PREFIX" "$MINI_MESH_BUILD_ROOT" "$CCACHE_DIR" "$CCACHE_TEMPDIR"

run_step() {
  local label="$1"
  shift
  echo "==> $label" >&2
  "$@"
}

configure_and_build() {
  local label="$1"
  shift
  run_step "$label configure" cmake "$@"
  run_step "$label build" ninja -C build install -j "$MAX_JOBS"
}

python_package_matches_source() {
  local dist_name="$1"
  local source_path="$2"

  "$repo_root/.venv/bin/python" -c '
import json
import pathlib
import sys
from importlib.metadata import PackageNotFoundError, distribution

dist_name = sys.argv[1]
source_path = pathlib.Path(sys.argv[2]).resolve()
try:
    dist = distribution(dist_name)
except PackageNotFoundError:
    sys.exit(1)
except Exception as exc:
    print(f"failed to inspect distribution {dist_name}: {exc}", file=sys.stderr)
    sys.exit(2)

direct_url = dist.read_text("direct_url.json")
if direct_url is None:
    sys.exit(1)

try:
    url = json.loads(direct_url).get("url", "")
except json.JSONDecodeError as exc:
    print(f"invalid direct_url.json for {dist_name}: {exc}", file=sys.stderr)
    sys.exit(2)

if not url.startswith("file://"):
    sys.exit(1)

installed_path = pathlib.Path(url.removeprefix("file://")).resolve()
sys.exit(0 if installed_path == source_path else 1)
' "$dist_name" "$source_path"
}

source_checkout_matches() {
  local dir="$1"
  local ref="$2"
  local repo="$MINI_MESH_BUILD_ROOT/$dir"
  local expected_head
  local actual_head

  [[ -d "$repo/.git" ]] || return 1
  expected_head="$(git -C "$repo" rev-parse "$ref^{commit}")" || return 1
  actual_head="$(git -C "$repo" rev-parse HEAD)" || return 1
  [[ "$actual_head" = "$expected_head" ]] || return 1
  git -C "$repo" diff --quiet --ignore-submodules=dirty || return 1
  git -C "$repo" diff --cached --quiet --ignore-submodules=dirty
}

checkout_repo() {
  local url="$1"
  local dir="$2"
  local ref="$3"
  local recursive="${4:-OFF}"

  cd "$MINI_MESH_BUILD_ROOT"
  if [[ ! -d "$dir/.git" ]]; then
    if [[ "$recursive" = ON ]]; then
      run_step "clone $dir" git clone --recursive "$url" "$dir"
    else
      run_step "clone $dir" git clone "$url" "$dir"
    fi
  fi

  cd "$dir"
  run_step "checkout $dir" git fetch --tags --force
  run_step "checkout $dir ref" git checkout "$ref"
  if [[ "$recursive" = ON ]]; then
    run_step "update $dir submodules" git submodule update --init --recursive
  fi
}

build_poselib() {
  local stamp="$MINI_MESH_LOCAL_PREFIX/.stamp-poselib-$POSELIB_REF"
  [[ -f "$stamp" ]] && return

  checkout_repo https://github.com/PoseLib/PoseLib.git PoseLib "$POSELIB_REF" ON
  if grep -q 'Eigen::Vector2d x0;' PoseLib/misc/colmap_models.cc; then
    sed -i '/Eigen::Vector2d x0;/d' PoseLib/misc/colmap_models.cc
  elif git diff --quiet -- PoseLib/misc/colmap_models.cc; then
    echo "ERROR: PoseLib patch site missing: PoseLib/misc/colmap_models.cc" >&2
    exit 1
  fi
  rm -rf build
  configure_and_build "PoseLib" . -B build -GNinja \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS:-}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$MINI_MESH_LOCAL_PREFIX"
  touch "$stamp"
}

build_colmap() {
  local stamp="$MINI_MESH_LOCAL_PREFIX/.stamp-colmap-$COLMAP_REF"
  [[ -f "$stamp" ]] && return

  checkout_repo https://github.com/colmap/colmap.git colmap "$COLMAP_REF"
  if ! grep -q '#include <cassert>' src/colmap/sfm/observation_manager.cc; then
    if ! grep -q '#include "colmap/util/misc.h"' src/colmap/sfm/observation_manager.cc; then
      echo "ERROR: COLMAP patch site missing: src/colmap/sfm/observation_manager.cc" >&2
      exit 1
    fi
    sed -i '/#include "colmap\/util\/misc.h"/a #include <cassert>' src/colmap/sfm/observation_manager.cc
  fi
  rm -rf build
  configure_and_build "COLMAP" . -B build -GNinja \
    -DCMAKE_PREFIX_PATH="$MINI_MESH_LOCAL_PREFIX;/usr/local" \
    -DFETCH_POSELIB=OFF \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_CUDA_HOST_COMPILER="$CUDAHOSTCXX" \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS:-}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES="$CMAKE_CUDA_ARCHITECTURES" \
    -DGUI_ENABLED="$WITH_GUI" \
    -DCMAKE_INSTALL_PREFIX="$MINI_MESH_LOCAL_PREFIX"
  touch "$stamp"
}

build_glomap() {
  local stamp="$MINI_MESH_LOCAL_PREFIX/.stamp-glomap-$GLOMAP_REF"
  [[ -f "$stamp" ]] && return

  checkout_repo https://github.com/colmap/glomap.git glomap "$GLOMAP_REF"
  if grep -q 'find_package(Eigen3 3\.4 REQUIRED)' cmake/FindDependencies.cmake; then
    sed -i 's/find_package(Eigen3 3\.4 REQUIRED)/find_package(Eigen3 REQUIRED)/' cmake/FindDependencies.cmake
  elif ! grep -q 'find_package(Eigen3 REQUIRED)' cmake/FindDependencies.cmake; then
    echo "ERROR: GLOMAP patch site missing: cmake/FindDependencies.cmake" >&2
    exit 1
  fi
  rm -rf build
  configure_and_build "GLOMAP" . -B build -GNinja \
    -DFETCH_POSELIB=OFF \
    -DFETCH_COLMAP=OFF \
    -DCMAKE_PREFIX_PATH="$MINI_MESH_LOCAL_PREFIX;/usr/local" \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_CXX_COMPILER="$CXX" \
    -DCMAKE_CUDA_HOST_COMPILER="$CUDAHOSTCXX" \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS:-}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES="$CMAKE_CUDA_ARCHITECTURES" \
    -DCMAKE_INSTALL_PREFIX="$MINI_MESH_LOCAL_PREFIX"
  touch "$stamp"
}

install_cuda_package() {
  local name="$1"
  local dist_name="$2"
  local url="$3"
  local dir="$4"
  local ref="$5"
  local subdir="${6:-.}"
  local stamp="$MINI_MESH_LOCAL_PREFIX/.stamp-python-$name-$ref"
  local source_path="$MINI_MESH_BUILD_ROOT/$dir/$subdir"
  local package_status=0

  if [[ -f "$stamp" ]] && source_checkout_matches "$dir" "$ref"; then
    python_package_matches_source "$dist_name" "$source_path" || package_status=$?
    if [[ "$package_status" -eq 0 ]]; then
      return
    fi
    if [[ "$package_status" -gt 1 ]]; then
      echo "ERROR: failed to inspect installed $dist_name; refusing to reinstall blindly." >&2
      exit "$package_status"
    fi
  fi

  checkout_repo "$url" "$dir" "$ref" ON
  cd "$source_path"
  run_step "install $name" uv pip install --reinstall --no-build-isolation --no-deps .
  touch "$stamp"
}

install_python_deps() {
  # uv sync can restore the locked LightGlue package; install HLoc afterwards
  # so its recursive submodule copy wins for local hloc runs.
  run_step "sync Python local extras" uv sync --extra local --frozen --inexact

  install_cuda_package tiny-cuda-nn tinycudann \
    https://github.com/nvlabs/tiny-cuda-nn.git \
    tiny-cuda-nn \
    "$TCNN_REF" \
    bindings/torch
  install_cuda_package nvdiffrast nvdiffrast \
    https://github.com/NVlabs/nvdiffrast.git \
    nvdiffrast \
    "$NVDIFFRAST_REF" \
    .
  install_cuda_package gsplat gsplat \
    https://github.com/nerfstudio-project/gsplat.git \
    gsplat \
    "v$GSPLAT_VERSION" \
    .

  uv pip install --no-build-isolation --no-deps \
    "sdfstudio[cuda,export] @ git+https://github.com/hummat/sdfstudio.git@v0.8.0" \
    "nerfstudio @ git+https://github.com/hummat/nerfstudio.git@55a1f83025bb28cbf792760c9b79f9eb22c3a2e4" \
    "splatfacto-w @ git+https://github.com/KevinXu02/splatfacto-w.git@$SPLATFACTOW_REF"
}

install_hloc() {
  local hloc_ref="3bdf494c852f157db57a1cf2039a6c826d52e702"
  local hloc_cli_ref="1b714e1183bbc3cb6f4031ddedcc4bd5190ece29"

  checkout_repo https://github.com/cvg/Hierarchical-Localization.git Hierarchical-Localization "$hloc_ref" ON
  run_step "install Hierarchical-Localization" uv pip install --no-build-isolation -e "$MINI_MESH_BUILD_ROOT/Hierarchical-Localization"
  run_step "install hloc-cli" uv pip install --no-build-isolation --no-deps \
    "git+https://github.com/hummat/hloc-cli.git@$hloc_cli_ref"
}

if [[ "$BUILD_SFM" = ON ]]; then
  build_poselib
  build_colmap
  build_glomap
fi

if [[ "$INSTALL_PYTHON_DEPS" = ON ]]; then
  install_python_deps
fi

if [[ "$INSTALL_HLOC" = ON ]]; then
  install_hloc
fi

echo "Local mini-mesh dependencies installed." >&2
echo "Prefix: $MINI_MESH_LOCAL_PREFIX" >&2
echo "Run: direnv reload" >&2
