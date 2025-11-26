ARG IMAGE=nvcr.io/nvidia/pytorch:24.05-py3
ARG DIGEST=d4030fc006cce2e56497fa07d003c5996de0eb7bde3610599fedbe7e7d03adea

FROM ${IMAGE}@sha256:${DIGEST} AS builder
ARG WORKDIR=/workspace
ENV QT_XCB_GL_INTEGRATION=xcb_egl

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    git cmake ninja-build build-essential libboost-program-options-dev libboost-graph-dev \
    libboost-system-dev libboost-filesystem-dev libeigen3-dev libflann-dev libfreeimage-dev libmetis-dev \
    libgoogle-glog-dev libsqlite3-dev libglew-dev qtbase5-dev \
    libqt5opengl5-dev libcgal-dev libceres-dev libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

ARG CUDA_ARCHITECTURES=61;70;75;80;86;89
ARG MARCH_NATIVE=OFF
ARG MAX_JOBS=8
ENV MAX_JOBS=${MAX_JOBS}

WORKDIR ${WORKDIR}

RUN mkdir -p /workspace/git && cd /workspace/git && \
    git clone --recursive https://github.com/vlarsson/PoseLib.git && cd PoseLib && \
    git checkout b3691b791bcedccd5451621b2275a1df0d9dcdeb && \
    cmake . -B build -GNinja \
    -DMARCH_NATIVE=${MARCH_NATIVE} \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/workspace/poselib && \
    ninja -C build install -j ${MAX_JOBS} && \
    cd /workspace/git && rm -rf PoseLib

RUN cd /workspace/git && git clone https://github.com/colmap/colmap.git && cd colmap && \
    git checkout 66fd8e56a0d160d68af2f29e9ac6941d442d2322 && \
    cmake . -B build -GNinja \
    -DCMAKE_PREFIX_PATH=/workspace/poselib \
    -DFETCH_POSELIB=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
    -DCMAKE_INSTALL_PREFIX=/workspace/colmap && \
    ninja -C build install -j ${MAX_JOBS} && \
    cd /workspace/git && rm -rf colmap

RUN cd /workspace/git && git clone https://github.com/colmap/glomap.git && cd glomap && \
    git checkout 26bbd5682c289c7cc36792f6393d311e1354b51a && \
    cmake . -B build -GNinja \
    -DCMAKE_PREFIX_PATH="/workspace/poselib;/workspace/colmap" \
    -DFETCH_POSELIB=OFF \
    -DFETCH_COLMAP=OFF \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
    -DCMAKE_INSTALL_PREFIX=/workspace/glomap && \
    ninja -C build install -j ${MAX_JOBS} && \
    cd /workspace/git && rm -rf glomap

RUN cd /workspace/git && git clone --recursive https://github.com/nvlabs/tiny-cuda-nn.git && cd tiny-cuda-nn && \
    git checkout db4f835b3b44bd451fdae00a74467add3b280cb5 && cd bindings/torch && \
    TCNN_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} MAX_JOBS=${MAX_JOBS} python setup.py bdist_wheel && \
    mv dist/tinycudann*.whl /workspace && cd /workspace && rm -rf git

FROM ${IMAGE}@sha256:${DIGEST} AS runtime
ARG WORKDIR=/workspace
ARG MAX_JOBS=8
ENV MAX_JOBS=${MAX_JOBS}

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    libboost-program-options1.74.0 libboost-filesystem1.74.0 libboost-system1.74.0 \
    libceres2 libfreeimage3 libglew2.2 libgoogle-glog0v5 \
    libqt5core5a libqt5gui5 libqt5widgets5 libcurl4 ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /workspace/colmap /usr/local
COPY --from=builder /workspace/glomap /usr/local

COPY --from=builder /workspace/tinycudann*.whl /tmp/
RUN pip install --no-cache-dir /tmp/tinycudann*.whl && rm /tmp/tinycudann*.whl

RUN pip install --no-cache-dir git+https://github.com/hummat/sdfstudio.git@765488749f5d009ad79886c12f919fa4330ad6e2 opencv-python==4.7.*
