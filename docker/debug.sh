#!/usr/bin/env bash
set -euo pipefail

# Debug helper to reproduce the builder + runtime stages from
# docker/Dockerfile inside an interactive container: builder dependencies,
# PoseLib/COLMAP/GLOMAP, CUDA extension wheels, runtime libraries, wheel
# installs, then Python dependencies.
#
# Usage (inside a container based on pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel
# or a close equivalent):
#   bash docker/debug.sh              # from the repo root if mounted
# or, if the repo is mounted at /app:
#   cd /app && bash docker/debug.sh
#
# You can override these environment variables (must roughly match
# docker/Dockerfile):
#   TORCH_CUDA_ARCH_LIST (default: 75,80,86,89)
#   MAX_JOBS             (default: 8)
#   WORKDIR              (default: current working directory)
#   INSTALL_OPTIONAL_DEPS (default: ON)
#   INSTALL_SYSTEM_DEPS   (default: ON)

TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-75;80;86;89}"
CXXFLAGS="${CXXFLAGS:--O3 -DNDEBUG}"
MAX_JOBS="${MAX_JOBS:-8}"
WORKDIR="${WORKDIR:-$PWD}"
INSTALL_OPTIONAL_DEPS="${INSTALL_OPTIONAL_DEPS:-ON}"
INSTALL_SYSTEM_DEPS="${INSTALL_SYSTEM_DEPS:-ON}"
WITH_GUI="${WITH_GUI:-ON}"
COMPILE_POSELIB="${COMPILE_POSELIB:-ON}"
COMPILE_COLMAP="${COMPILE_COLMAP:-ON}"
COMPILE_GLOMAP="${COMPILE_GLOMAP:-ON}"
COMPILE_TCNN="${COMPILE_TCNN:-ON}"
COMPILE_NVDIFFRAST="${COMPILE_NVDIFFRAST:-ON}"
COMPILE_GSPLAT="${COMPILE_GSPLAT:-ON}"
INSTALL_SDFSTUDIO="${INSTALL_SDFSTUDIO:-ON}"

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
echo "WORKDIR               = ${WORKDIR}"
echo "TORCH_CUDA_ARCH_LIST  = ${TORCH_CUDA_ARCH_LIST}"
echo "CXXFLAGS              = ${CXXFLAGS}"
echo "MAX_JOBS              = ${MAX_JOBS}"
echo "INSTALL_OPTIONAL_DEPS = ${INSTALL_OPTIONAL_DEPS}"
echo "INSTALL_SYSTEM_DEPS   = ${INSTALL_SYSTEM_DEPS}"
echo "COMPILE_POSELIB       = ${COMPILE_POSELIB}"
echo "COMPILE_COLMAP        = ${COMPILE_COLMAP}"
echo "COMPILE_GLOMAP        = ${COMPILE_GLOMAP}"
echo "COMPILE_TCNN          = ${COMPILE_TCNN}"
echo "COMPILE_NVDIFFRAST    = ${COMPILE_NVDIFFRAST}"
echo "COMPILE_GSPLAT        = ${COMPILE_GSPLAT}"
echo "INSTALL_SDFSTUDIO     = ${INSTALL_SDFSTUDIO}"
echo

# Library refs (tags or commits). Can be overridden via env vars.
: "${POSELIB_REF:=7e9f5f53372e43f89655040d4dfc4a00e5ace11c}"  # ~= PoseLib 2.0.2
: "${COLMAP_REF:=c5f9cefc87e5dd596b638e4cee0ff543c7d14755}"   # ~= COLMAP 3.12.6
: "${GLOMAP_REF:=0edb1b8435e0f9a594318908b81a31f078a51bf7}"   # ~= GLOMAP 1.2.0
: "${TCNN_REF:=32507f059d7abc8c13f5df81ea9597b70923ee44}"     # ~= tiny-cuda-nn 1.7
: "${NVDIFFRAST_REF:=253ac4fcea7de5f396371124af597e6cc957bfae}"
: "${GSPLAT_VERSION:=1.4.0}"

if [ "${INSTALL_SYSTEM_DEPS}" = "ON" ]; then
  echo "=== Step 0: install build dependencies (Dockerfile builder stage) ==="
  if [ "$(id -u)" -ne 0 ]; then
	echo "WARNING: debug.sh is running as non-root (uid $(id -u))."
	echo "         Step 0 (apt-get) will likely fail. For full reproduction,"
	echo "         run this script as root inside the container."
	echo
  fi

  run_step 0 "apt-get build deps (core)" bash -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends --no-install-suggests \
      git cmake ninja-build build-essential ccache \
      libboost-program-options-dev libboost-graph-dev libboost-system-dev \
      libboost-filesystem-dev libeigen3-dev libflann-dev libfreeimage-dev \
      libmetis-dev libgoogle-glog-dev libsqlite3-dev libglew-dev \
      libcgal-dev libceres-dev libcurl4-openssl-dev
  '
  if [ "${WITH_GUI:-ON}" = "ON" ]; then
    run_step 0a "apt-get build deps (qt)" bash -c '
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y --no-install-recommends --no-install-suggests \
        qtbase5-dev libqt5opengl5-dev
    '
  else
    echo "=== Step 0a: SKIPPED Qt build deps (WITH_GUI=${WITH_GUI}) ==="
  fi
else
  echo "=== Step 0: SKIPPED (INSTALL_SYSTEM_DEPS=${INSTALL_SYSTEM_DEPS}) ==="
fi
echo

echo "=== Toolchain versions ==="
python --version || true
cmake --version || true
ninja --version || true
git --version || true
nvidia-smi || true
echo

mkdir -p "${WORKDIR}/git" "${WORKDIR}/wheels"
cd "${WORKDIR}/git"

if [ "${COMPILE_POSELIB}" = "ON" ]; then
  echo "=== Step 1: build and install PoseLib (exact Dockerfile match, approx. PoseLib 2.0.2) ==="
  rm -rf PoseLib
  run_step 1a "clone PoseLib" git clone --recursive https://github.com/PoseLib/PoseLib.git
  cd PoseLib
  run_step 1b "checkout PoseLib ref" git checkout "${POSELIB_REF}"
  git submodule update --init --recursive
  echo "PoseLib HEAD: $(git rev-parse HEAD)" || true
  run_step 1c "cmake PoseLib" cmake . -B build -GNinja \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS}" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="${WORKDIR}/poselib"
  run_step 1d "ninja PoseLib" ninja -C build install -j"${MAX_JOBS}"
  cd "${WORKDIR}/git"
  echo
else
  echo "=== Step 1: SKIPPED (COMPILE_POSELIB=${COMPILE_POSELIB}) ==="
fi

if [ "${COMPILE_COLMAP}" = "ON" ]; then
  echo "=== Step 2: build and install COLMAP (exact Dockerfile match, approx. COLMAP 3.12.6) ==="
  rm -rf colmap
  run_step 2a "clone COLMAP" git clone https://github.com/colmap/colmap.git
  cd colmap
  run_step 2b "checkout COLMAP ref" git checkout "${COLMAP_REF}"
  echo "COLMAP HEAD: $(git rev-parse HEAD)" || true
  run_step 2c "cmake COLMAP" cmake . -B build -GNinja \
    -DCMAKE_PREFIX_PATH="${WORKDIR}/poselib;/usr/local" \
    -DFETCH_POSELIB=OFF \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS}" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_INSTALL_DO_STRIP=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES="${TORCH_CUDA_ARCH_LIST}" \
    -DGUI_ENABLED="${WITH_GUI}" \
    -DCMAKE_INSTALL_PREFIX="${WORKDIR}/colmap"
  run_step 2d "ninja COLMAP" ninja -C build install -j"${MAX_JOBS}"
  echo "COLMAP installed to: ${WORKDIR}/colmap"
  echo "COLMAP config files:"
  find "${WORKDIR}/colmap" -maxdepth 6 -name "colmap-config.cmake" || true
  cd "${WORKDIR}/git"
  echo
else
  echo "=== Step 2: SKIPPED (COMPILE_COLMAP=${COMPILE_COLMAP}) ==="
fi

if [ "${COMPILE_GLOMAP}" = "ON" ]; then
  echo "=== Step 3: build and install GLOMAP (exact Dockerfile match, approx. GLOMAP 1.2.0) ==="
  rm -rf glomap
  run_step 3a "clone GLOMAP" git clone https://github.com/colmap/glomap.git
  cd glomap
  run_step 3b "checkout GLOMAP ref" git checkout "${GLOMAP_REF}"
  echo "GLOMAP HEAD: $(git rev-parse HEAD)" || true
  run_step 3c "cmake GLOMAP" cmake . -B build -GNinja \
    -DFETCH_POSELIB=OFF \
    -DFETCH_COLMAP=OFF \
    -DCMAKE_PREFIX_PATH="${WORKDIR}/poselib;${WORKDIR}/colmap;/usr/local" \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS}" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_INSTALL_DO_STRIP=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES="${TORCH_CUDA_ARCH_LIST}" \
    -DCMAKE_INSTALL_PREFIX="${WORKDIR}/glomap"
  echo "GLOMAP CMake configure completed; starting build/install..."
  run_step 3d "ninja GLOMAP" ninja -C build install -j"${MAX_JOBS}"
  cd "${WORKDIR}/git"
  echo
else
  echo "=== Step 3: SKIPPED (COMPILE_GLOMAP=${COMPILE_GLOMAP}) ==="
fi

if [ "${COMPILE_TCNN}" = "ON" ]; then
  echo "=== Step 4: build tiny-cuda-nn wheel (exact Dockerfile match, approx. tiny-cuda-nn 1.7) ==="
  rm -rf tiny-cuda-nn
  run_step 4a "clone tiny-cuda-nn" git clone --recursive https://github.com/nvlabs/tiny-cuda-nn.git
  cd tiny-cuda-nn
  run_step 4b "checkout tiny-cuda-nn SHA" git checkout "${TCNN_REF}"
  git submodule update --init --recursive
  echo "tiny-cuda-nn HEAD: $(git rev-parse HEAD)" || true
  cd bindings/torch
  echo "Running tiny-cuda-nn setup.py with TCNN_CUDA_ARCHITECTURES=${TORCH_CUDA_ARCH_LIST}, MAX_JOBS=${MAX_JOBS}"
  run_step 4c "build tiny-cuda-nn wheel" bash -c 'TCNN_CUDA_ARCHITECTURES="'"${TORCH_CUDA_ARCH_LIST}"'" MAX_JOBS="'"${MAX_JOBS}"'" python setup.py bdist_wheel'
  echo "Built wheel(s):"
  ls dist
  cd "${WORKDIR}/git"
  echo
else
  echo "=== Step 4: SKIPPED (COMPILE_TCNN=${COMPILE_TCNN}) ==="
fi

if [ "${COMPILE_NVDIFFRAST}" = "ON" ]; then
  echo "=== Step 4d: build nvdiffrast wheel (exact Dockerfile ref) ==="
  rm -rf nvdiffrast
  run_step 4d1 "clone nvdiffrast" git clone https://github.com/NVlabs/nvdiffrast.git
  cd nvdiffrast
  run_step 4d2 "checkout nvdiffrast ref" git checkout "${NVDIFFRAST_REF}"
  echo "nvdiffrast HEAD: $(git rev-parse HEAD)" || true
  run_step 4d3 "build nvdiffrast wheel" bash -c 'TORCH_CUDA_ARCH_LIST="'"${TORCH_CUDA_ARCH_LIST}"'" MAX_JOBS="'"${MAX_JOBS}"'" pip wheel . --no-build-isolation --no-deps -w "'"${WORKDIR}/wheels"'"'
  cd "${WORKDIR}/git"
  echo
else
  echo "=== Step 4d: SKIPPED (COMPILE_NVDIFFRAST=${COMPILE_NVDIFFRAST}) ==="
fi

if [ "${COMPILE_GSPLAT}" = "ON" ]; then
  echo "=== Step 4e: build gsplat wheel (exact Dockerfile version) ==="
  rm -rf gsplat
  run_step 4e1 "clone gsplat" git clone https://github.com/nerfstudio-project/gsplat.git
  cd gsplat
  run_step 4e2 "checkout gsplat tag" git checkout "v${GSPLAT_VERSION}"
  echo "gsplat HEAD: $(git rev-parse HEAD)" || true
  run_step 4e3 "build gsplat wheel" bash -c 'TORCH_CUDA_ARCH_LIST="'"${TORCH_CUDA_ARCH_LIST}"'" MAX_JOBS="'"${MAX_JOBS}"'" pip wheel . --no-build-isolation --no-deps -w "'"${WORKDIR}/wheels"'"'
  cd "${WORKDIR}/git"
  echo
else
  echo "=== Step 4e: SKIPPED (COMPILE_GSPLAT=${COMPILE_GSPLAT}) ==="
fi

if [ "${INSTALL_SYSTEM_DEPS}" = "ON" ]; then
  echo "=== Step 5: install runtime libraries (Dockerfile runtime stage) ==="
  run_step 5 "apt-get runtime libs (core)" bash -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends --no-install-suggests \
      git libboost-program-options1.74.0 \
      libboost-filesystem1.74.0 libboost-system1.74.0 \
      libceres2 libfreeimage3 libglew2.2 libgoogle-glog0v5 \
      libcurl4 ffmpeg libopengl0 build-essential cmake
  '
  if [ "${WITH_GUI:-ON}" = "ON" ]; then
    run_step 5a "apt-get runtime libs (qt)" bash -c '
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y --no-install-recommends --no-install-suggests \
        libqt5core5a libqt5gui5 libqt5widgets5 libqt5opengl5
    '
  else
    echo "=== Step 5a: SKIPPED Qt runtime libs (WITH_GUI=${WITH_GUI}) ==="
  fi
else
  echo "=== Step 5: SKIPPED (INSTALL_SYSTEM_DEPS=${INSTALL_SYSTEM_DEPS}) ==="
fi

echo
if [ "${COMPILE_TCNN}" = "ON" ]; then
  echo "=== Step 6: install tiny-cuda-nn wheel into Python env ==="
  cd "${WORKDIR}/tiny-cuda-nn/bindings/torch"
  TCNN_WHL="$(find dist -maxdepth 1 -type f -name 'tinycudann*.whl' | head -n 1 || true)"
  if [ -z "${TCNN_WHL}" ]; then
    echo "ERROR: tiny-cuda-nn wheel not found under dist/" >&2
    exit 1
  fi
  echo "Installing wheel: ${TCNN_WHL}"
  run_step 6 "pip install tiny-cuda-nn wheel" pip install --no-cache-dir "${TCNN_WHL}"
else
  echo "=== Step 6: SKIPPED (COMPILE_TCNN=${COMPILE_TCNN}) ==="
fi

if [ "${COMPILE_NVDIFFRAST}" = "ON" ]; then
  echo "=== Step 6a: install nvdiffrast wheel into Python env ==="
  NVDIFFRAST_WHL="$(find "${WORKDIR}/wheels" -maxdepth 1 -type f -name 'nvdiffrast*.whl' | head -n 1 || true)"
  if [ -z "${NVDIFFRAST_WHL}" ]; then
    echo "ERROR: nvdiffrast wheel not found under ${WORKDIR}/wheels" >&2
    exit 1
  fi
  echo "Installing wheel: ${NVDIFFRAST_WHL}"
  run_step 6a "pip install nvdiffrast wheel" pip install --no-cache-dir "${NVDIFFRAST_WHL}"
else
  echo "=== Step 6a: SKIPPED (COMPILE_NVDIFFRAST=${COMPILE_NVDIFFRAST}) ==="
fi

echo
if [ "${INSTALL_SDFSTUDIO}" = "ON" ]; then
  echo "=== Step 7: install sdfstudio (Dockerfile match, constraints approximated) ==="
  run_step 7 "pip install sdfstudio" pip install --no-cache-dir \
    git+https://github.com/hummat/sdfstudio.git@v0.8.0
else
  echo "=== Step 7: SKIPPED (INSTALL_SDFSTUDIO=${INSTALL_SDFSTUDIO}) ==="
fi

if [ "$INSTALL_OPTIONAL_DEPS" = "ON" ]; then
  echo
  echo "=== Step 8: install optional dependencies (nerfstudio, masking, advanced SfM) ==="

  echo "=== Step 8a: rembg ==="
  run_step 8a "pip install rembg" pip install --no-cache-dir --no-build-isolation \
    "rembg[gpu,cli]"

  if [ "${COMPILE_GSPLAT}" = "ON" ]; then
    echo "=== Step 8b0: gsplat ==="
    GSPLAT_WHL="$(find "${WORKDIR}/wheels" -maxdepth 1 -type f -name 'gsplat*.whl' | head -n 1 || true)"
    if [ -z "${GSPLAT_WHL}" ]; then
      echo "ERROR: gsplat wheel not found under ${WORKDIR}/wheels" >&2
      exit 1
    fi
    run_step 8b0 "pip install gsplat wheel" pip install --no-cache-dir "${GSPLAT_WHL}"
  fi

  echo "=== Step 8b: nerfstudio ==="
  run_step 8b "pip install nerfstudio" pip install --no-cache-dir --no-build-isolation \
    git+https://github.com/hummat/nerfstudio.git@55a1f83025bb28cbf792760c9b79f9eb22c3a2e4

  echo "=== Step 8c: sam2 ==="
  run_step 8c "pip install sam2" pip install --no-cache-dir --no-build-isolation \
    git+https://github.com/hummat/sam2.git@98f488a540f87260b8e51146dc3ab15694dd174c

  echo "=== Step 8d: hloc (requires local clone with --recursive for submodules) ==="
  rm -rf Hierarchical-Localization
  run_step 8d1 "clone hloc" git clone --recursive https://github.com/cvg/Hierarchical-Localization.git
  cd Hierarchical-Localization
  run_step 8d2 "checkout hloc ref" git checkout 3bdf494c852f157db57a1cf2039a6c826d52e702
  git submodule update --init --recursive
  echo "HLoc HEAD: $(git rev-parse HEAD)" || true
  run_step 8d3 "pip install hloc" pip install --no-cache-dir --no-build-isolation -e .
  run_step 8d4 "pip install hloc-cli" pip install --no-cache-dir --no-build-isolation \
    git+https://github.com/hummat/hloc-cli.git@1b714e1183bbc3cb6f4031ddedcc4bd5190ece29
  cd "${WORKDIR}/git"

  echo "=== Step 8e: vggsfm ==="
  run_step 8e "pip install vggsfm" pip install --no-cache-dir --no-build-isolation \
    git+https://github.com/hummat/vggsfm.git@d597df629a312a662544006ac3bdbc2782b82834
else
  echo
  echo "=== Step 8: SKIPPED (INSTALL_OPTIONAL_DEPS=${INSTALL_OPTIONAL_DEPS}) ==="
fi

echo
echo "=== debug.sh completed successfully ==="
echo "Artifacts:"
echo "  PoseLib  : ${WORKDIR}/poselib"
echo "  COLMAP   : ${WORKDIR}/colmap"
echo "  GLOMAP   : ${WORKDIR}/glomap"
echo "  tcnn whl : ${WORKDIR}/tiny-cuda-nn/bindings/torch/dist"
echo "  wheels   : ${WORKDIR}/wheels"
