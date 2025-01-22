ARG IMAGE=nvcr.io/nvidia/pytorch:24.05-py3
ARG DIGEST=d4030fc006cce2e56497fa07d003c5996de0eb7bde3610599fedbe7e7d03adea

FROM ${IMAGE}@sha256:${DIGEST} AS builder
ARG WORKDIR=/workspace
ENV QT_XCB_GL_INTEGRATION=xcb_egl

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    git cmake ninja-build build-essential libboost-program-options-dev libboost-graph-dev \
    libboost-system-dev libeigen3-dev libflann-dev libfreeimage-dev libmetis-dev \
    libgoogle-glog-dev libsqlite3-dev libglew-dev qtbase5-dev \
    libqt5opengl5-dev libcgal-dev libceres-dev libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

ARG POSELIB_VERSION=56d158f
ARG COLMAP_VERSION=cf8f116
ARG GLOMAP_VERSION=18a70ee
ARG TCNN_VERSION=1e38444
ARG CUDA_ARCHITECTURES=61;70;75;80;86;89
ARG MARCH_NATIVE=OFF

RUN git clone --no-checkout --depth 1 https://github.com/vlarsson/PoseLib.git && \
    cd PoseLib && git checkout ${POSELIB_VERSION} && git submodule update --init --recursive && \
    cmake . -B build -GNinja \
    -DMARCH_NATIVE=${MARCH_NATIVE} \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/workspace/poselib-install && \
    ninja -C build install -j $(nproc) && \
    cd /workspace && rm -rf PoseLib

RUN git clone --no-checkout --depth 1 https://github.com/colmap/colmap.git && \
    cd colmap && git checkout ${COLMAP_VERSION} && \
    cmake . -B build -GNinja \
    -DCMAKE_PREFIX_PATH=/workspace/poselib-install \
    -DFETCH_POSELIB=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
    -DCMAKE_INSTALL_PREFIX=/workspace/colmap-install && \
    ninja -C build install -j $(nproc) && \
    cd /workspace && rm -rf colmap

RUN git clone --no-checkout --depth 1 https://github.com/colmap/glomap.git && \
    cd glomap && git checkout ${GLOMAP_VERSION} && \
    cmake . -B build -GNinja \
    -DCMAKE_PREFIX_PATH="/workspace/poselib-install;/workspace/colmap-install" \
    -DFETCH_POSELIB=OFF \
    -DFETCH_COLMAP=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
    -DCMAKE_INSTALL_PREFIX=/workspace/glomap-install && \
    ninja -C build install -j $(nproc) && \
    cd /workspace && rm -rf glomap

RUN git clone --no-checkout --depth 1 https://github.com/nvlabs/tiny-cuda-nn.git && \
    cd tiny-cuda-nn && git checkout ${TCNN_VERSION} && git submodule update --init --recursive && cd bindings/torch && \
    TCNN_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} MAX_JOBS=$(nproc) python setup.py bdist_wheel && \
    mv dist/tinycudann*.whl /workspace && cd /workspace && rm -rf tiny-cuda-nn

FROM ${IMAGE}@sha256:${DIGEST} AS runtime
ARG WORKDIR=/workspace

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    libboost-program-options1.74.0 libceres2 libfreeimage3 libglew2.2 libgoogle-glog0v5 \
    libqt5core5a libqt5gui5 libqt5widgets5 libcurl4 ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /workspace/colmap-install /usr/local
COPY --from=builder /workspace/glomap-install /usr/local

COPY --from=builder /workspace/tinycudann*.whl /tmp/
RUN pip install --no-cache-dir /tmp/tinycudann*.whl && rm /tmp/tinycudann*.whl

RUN pip install --no-cache-dir git+https://github.com/hummat/sdfstudio.git opencv-python==4.7.*
