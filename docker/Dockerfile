ARG BUILDER_IMAGE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel
ARG RUNTIME_IMAGE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

############################
# Builder stage
############################
FROM ${BUILDER_IMAGE} AS builder

LABEL org.opencontainers.image.title="hummat/colmap-glomap"
LABEL org.opencontainers.image.description="COLMAP, GLOMAP, tiny-cuda-nn base image"
LABEL org.opencontainers.image.source="https://github.com/hummat/mini-mesh"

ARG WORKDIR=/workspace
ARG TORCH_CUDA_ARCH_LIST=61;70;75;80;86;89
ARG MAX_JOBS=8
ARG CXXFLAGS="-O3 -DNDEBUG"
ARG WITH_GUI=ON

ENV QT_XCB_GL_INTEGRATION=xcb_egl
ENV CUDA_HOME=/usr/local/cuda
ENV MAX_JOBS=${MAX_JOBS}
ENV CXXFLAGS="${CXXFLAGS}"
ENV WITH_GUI=${WITH_GUI}

# Avoid conda Boost 1.87, force system Boost 1.74
RUN conda remove -y boost boost-cpp || true
ENV BOOST_ROOT=/usr \
    BOOST_INCLUDEDIR=/usr/include \
    BOOST_LIBRARYDIR=/usr/lib/x86_64-linux-gnu

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    git \
    cmake \
    ninja-build \
    build-essential \
    ccache \
    libboost-program-options-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libsqlite3-dev \
    libglew-dev \
    libcgal-dev \
    libceres-dev \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Qt build deps only if we build the GUI
RUN if [ "$WITH_GUI" = "ON" ]; then \
    apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    qtbase5-dev \
    libqt5opengl5-dev \
    && rm -rf /var/lib/apt/lists/* ; \
    fi

RUN mkdir -p /workspace/git

# TODO: Also compile Ceres from source with CUDA support?

# PoseLib 2.0.2
RUN cd /workspace/git && git clone --recursive https://github.com/PoseLib/PoseLib.git PoseLib && cd PoseLib && \
    git checkout 7e9f5f53372e43f89655040d4dfc4a00e5ace11c && \
    git submodule update --init --recursive && \
    cmake . -B build -GNinja \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS}" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/workspace/poselib && \
    ninja -C build install -j ${MAX_JOBS} && \
    cd /workspace/git && rm -rf PoseLib

# COLMAP 3.12.6 (but actually 3.13.0.dev0?)
RUN cd /workspace/git && git clone https://github.com/colmap/colmap.git && cd colmap && \
    git checkout c5f9cefc87e5dd596b638e4cee0ff543c7d14755 && \
    cmake . -B build -GNinja \
    -DCMAKE_PREFIX_PATH="/workspace/poselib;/usr/local" \
    -DFETCH_POSELIB=OFF \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS}" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_INSTALL_DO_STRIP=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=${TORCH_CUDA_ARCH_LIST} \
    -DGUI_ENABLED=${WITH_GUI} \
    -DCMAKE_INSTALL_PREFIX=/workspace/colmap && \
    ninja -C build install -j ${MAX_JOBS} && \
    cd /workspace/git && rm -rf colmap

# GLOMAP 1.2.0
RUN cd /workspace/git && git clone https://github.com/colmap/glomap.git && cd glomap && \
    git checkout 0edb1b8435e0f9a594318908b81a31f078a51bf7 && \
    cmake . -B build -GNinja \
    -DFETCH_POSELIB=OFF \
    -DFETCH_COLMAP=OFF \
    -DCMAKE_PREFIX_PATH="/workspace/poselib;/workspace/colmap;/usr/local" \
    -DCMAKE_CXX_FLAGS="${CXXFLAGS}" \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_INSTALL_DO_STRIP=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=${TORCH_CUDA_ARCH_LIST} \
    -DCMAKE_INSTALL_PREFIX=/workspace/glomap && \
    ninja -C build install -j ${MAX_JOBS} && \
    cd /workspace/git && rm -rf glomap

# tiny-cuda-nn wheel (for torch, approx. tiny-cuda-nn 1.7)
RUN cd /workspace/git && git clone --recursive https://github.com/nvlabs/tiny-cuda-nn.git && cd tiny-cuda-nn && \
    git checkout 32507f059d7abc8c13f5df81ea9597b70923ee44 && \
    git submodule update --init --recursive && \
    cd bindings/torch && \
    TCNN_CUDA_ARCHITECTURES=${TORCH_CUDA_ARCH_LIST} MAX_JOBS=${MAX_JOBS} python setup.py bdist_wheel && \
    mv dist/tinycudann*.whl /workspace && cd /workspace && rm -rf git


############################
# Runtime stage
############################
FROM ${RUNTIME_IMAGE} AS runtime

LABEL org.opencontainers.image.title="hummat/mini-mesh"
LABEL org.opencontainers.image.description="Mini-mesh runtime with COLMAP, GLOMAP, tiny-cuda-nn and SDF/NeRF deps"
LABEL org.opencontainers.image.source="https://github.com/hummat/mini-mesh"

ARG WORKDIR=/workspace
ARG MAX_JOBS=8
ARG WITH_GUI=ON
ARG INSTALL_OPTIONAL_DEPS=ON

ENV MAX_JOBS=${MAX_JOBS}
ENV WITH_GUI=${WITH_GUI}

# Make PyTorch's vendored CUDA runtime visible to non-Python binaries (COLMAP, etc.)
ENV LD_LIBRARY_PATH=/opt/conda/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH

WORKDIR ${WORKDIR}

# Core COLMAP/GLOMAP runtime deps (headless)
RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    git \
    libboost-program-options1.74.0 \
    libboost-filesystem1.74.0 \
    libboost-system1.74.0 \
    libceres2 \
    libfreeimage3 \
    libglew2.2 \
    libgoogle-glog0v5 \
    libcurl4 \
    ffmpeg \
    libopengl0 \
    libsqlite3-0 \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# GUI runtime deps only if WITH_GUI=ON
RUN if [ "$WITH_GUI" = "ON" ]; then \
    apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    libqt5core5a \
    libqt5gui5 \
    libqt5widgets5 \
    libqt5opengl5 \
    && rm -rf /var/lib/apt/lists/* ; \
    fi

COPY --from=builder /workspace/colmap /usr/local
COPY --from=builder /workspace/glomap /usr/local

COPY --from=builder /workspace/tinycudann*.whl /tmp/
RUN pip install --no-cache-dir /tmp/tinycudann*.whl && rm /tmp/tinycudann*.whl

# Pin only the core PyTorch-related packages (from base image)
RUN pip list --format=json | python -c 'import sys, json; \
    keys = {"torch", "torchvision", "torch-tensorrt", "numpy"}; \
    print("\n".join(["{}=={}".format(p["name"], p["version"]) for p in json.load(sys.stdin) if p["name"] in keys]))' \
    > /tmp/constraints.txt

# Core Python deps that must not disturb the torch stack
RUN pip install --no-cache-dir -c /tmp/constraints.txt \
    scikit-build-core>=0.11 \
    pybind11>=2.6 \
    git+https://github.com/hummat/sdfstudio.git@ba1f247426a283197f724392a3a3b75f4cfa014d

RUN if [ "$INSTALL_OPTIONAL_DEPS" = "ON" ]; then \
    pip install --no-cache-dir --no-build-isolation -c /tmp/constraints.txt \
    "rembg[gpu,cli]" \
    nerfstudio==1.1.5 \
    git+https://github.com/hummat/sam2.git@98f488a540f87260b8e51146dc3ab15694dd174c \
    git+https://github.com/cvg/Hierarchical-Localization.git@abb252080282e31147db6291206ca102c43353f7 \
    git+https://github.com/hummat/hloc-cli.git@1d8fd95120a339b823e86006fd99cfd03be093e0 \
    git+https://github.com/hummat/vggsfm.git@55b6e4284dc9219f2683849cbc9968349707bff2; \
    fi

CMD ["bash"]