#!/usr/bin/env bash
set -euo pipefail

# Debug helper to reproduce the builder stage from docker/Dockerfile
# (PoseLib -> COLMAP -> GLOMAP -> tiny-cuda-nn) inside an interactive
# container.
#
# Usage (inside a container based on nvcr.io/nvidia/pytorch:24.05-py3):
#   bash docker/debug.sh              # from the repo root if mounted
# or, if the repo is mounted at /tmp:
#   cd /tmp && bash docker/debug.sh
#
# You can override these environment variables (must match docker/Dockerfile):
#   CUDA_ARCHITECTURES  (default: 61;70;75;80;86;89)
#   MARCH_NATIVE        (default: OFF)
#   MAX_JOBS            (default: 8)
#   WORKDIR             (default: /workspace)

CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES:-61;70;75;80;86;89}"
MARCH_NATIVE="${MARCH_NATIVE:-OFF}"
MAX_JOBS="${MAX_JOBS:-8}"
WORKDIR="${WORKDIR:-/workspace}"

run_step() {
  local step_id="$1"; shift
  local label="$1"; shift
  echo "[step ${step_id}] BEGIN: ${label}" >&2
  if "$@"; then
    echo "[step ${step_id}] OK: ${label}" >&2
  else
    local code=$?
    echo "[step ${step_id}] FAILED (${code}): ${label}" >&2
    return "${code}"
  fi
}

echo "=== debug.sh: settings ==="
echo "WORKDIR            = ${WORKDIR}"
echo "CUDA_ARCHITECTURES = ${CUDA_ARCHITECTURES}"
echo "MARCH_NATIVE       = ${MARCH_NATIVE}"
echo "MAX_JOBS           = ${MAX_JOBS}"
echo

if [ "$(id -u)" -ne 0 ]; then
  echo "WARNING: debug.sh is running as non-root (uid $(id -u))."
  echo "         Step 0 (apt-get) will likely fail. For full reproduction,"
  echo "         run this script as root inside the container."
  echo
fi

echo "=== Step 0: install build dependencies (Dockerfile builder stage) ==="
run_step 0 "apt-get build deps" bash -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends --no-install-suggests \
    git cmake ninja-build build-essential \
    libboost-program-options-dev libboost-graph-dev libboost-system-dev \
    libeigen3-dev libflann-dev libfreeimage-dev libmetis-dev \
    libgoogle-glog-dev libsqlite3-dev libglew-dev qtbase5-dev \
    libqt5opengl5-dev libcgal-dev libceres-dev libcurl4-openssl-dev
'
echo

echo "=== Toolchain versions ==="
python --version || true
cmake --version || true
ninja --version || true
git --version || true
nvidia-smi || true
echo

mkdir -p "${WORKDIR}/git"
cd "${WORKDIR}/git"

echo "=== Step 1: build and install PoseLib (exact Dockerfile match) ==="
rm -rf PoseLib
run_step 1a "clone PoseLib" git clone --recursive https://github.com/vlarsson/PoseLib.git
cd PoseLib
run_step 1b "checkout PoseLib SHA" git checkout b3691b791bcedccd5451621b2275a1df0d9dcdeb
echo "PoseLib HEAD: $(git rev-parse HEAD)" || true
run_step 1c "cmake PoseLib" cmake . -B build -GNinja \
  -DMARCH_NATIVE="${MARCH_NATIVE}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${WORKDIR}/poselib"
run_step 1d "ninja PoseLib" ninja -C build install -j"${MAX_JOBS}"
cd "${WORKDIR}/git"
echo

echo "=== Step 2: build and install COLMAP (exact Dockerfile match) ==="
rm -rf colmap
run_step 2a "clone COLMAP" git clone https://github.com/colmap/colmap.git
cd colmap
run_step 2b "checkout COLMAP SHA" git checkout 66fd8e56a0d160d68af2f29e9ac6941d442d2322
echo "COLMAP HEAD: $(git rev-parse HEAD)" || true
run_step 2c "cmake COLMAP" cmake . -B build -GNinja \
  -DCMAKE_PREFIX_PATH="${WORKDIR}/poselib" \
  -DFETCH_POSELIB=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
  -DCMAKE_INSTALL_PREFIX="${WORKDIR}/colmap"
run_step 2d "ninja COLMAP" ninja -C build install -j"${MAX_JOBS}"
echo "COLMAP installed to: ${WORKDIR}/colmap"
echo "COLMAP config files:"
find "${WORKDIR}/colmap" -maxdepth 6 -name "colmap-config.cmake" || true
cd "${WORKDIR}/git"
echo

echo "=== Step 3: build and install GLOMAP (exact Dockerfile match) ==="
rm -rf glomap
run_step 3a "clone GLOMAP" git clone https://github.com/colmap/glomap.git
cd glomap
run_step 3b "checkout GLOMAP SHA" git checkout 26bbd5682c289c7cc36792f6393d311e1354b51a
echo "GLOMAP HEAD: $(git rev-parse HEAD)" || true
run_step 3c "cmake GLOMAP" cmake . -B build -GNinja \
  -DCMAKE_PREFIX_PATH="${WORKDIR}/poselib;${WORKDIR}/colmap" \
  -DFETCH_POSELIB=OFF \
  -DFETCH_COLMAP=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
  -DCMAKE_INSTALL_PREFIX="${WORKDIR}/glomap"
echo "GLOMAP CMake configure completed; starting build/install..."
run_step 3d "ninja GLOMAP" ninja -C build install -j"${MAX_JOBS}"
cd "${WORKDIR}/git"
echo

echo "=== Step 4: build tiny-cuda-nn wheel (exact Dockerfile match) ==="
rm -rf tiny-cuda-nn
run_step 4a "clone tiny-cuda-nn" git clone --recursive https://github.com/nvlabs/tiny-cuda-nn.git
cd tiny-cuda-nn
run_step 4b "checkout tiny-cuda-nn SHA" git checkout db4f835b3b44bd451fdae00a74467add3b280cb5
echo "tiny-cuda-nn HEAD: $(git rev-parse HEAD)" || true
cd bindings/torch
echo "Running tiny-cuda-nn setup.py with TCNN_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES}, MAX_JOBS=${MAX_JOBS}"
run_step 4c "build tiny-cuda-nn wheel" bash -c 'TCNN_CUDA_ARCHITECTURES="'"${CUDA_ARCHITECTURES}"'" MAX_JOBS="'"${MAX_JOBS}"'" python setup.py bdist_wheel'
echo "Built wheel(s):"
ls dist

echo
echo "=== debug.sh completed successfully ==="
echo "Artifacts:"
echo "  PoseLib  : ${WORKDIR}/poselib"
echo "  COLMAP   : ${WORKDIR}/colmap"
echo "  GLOMAP   : ${WORKDIR}/glomap"
echo "  tcnn whl : ${WORKDIR}/tiny-cuda-nn/bindings/torch/dist"