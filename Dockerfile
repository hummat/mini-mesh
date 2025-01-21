# This is an Ubuntu 22.04 image that comes with PyTorch 2.4.0, CUDA 12.4.1 and Python 3.10
FROM nvcr.io/nvidia/pytorch:24.05-py3 AS builder

ARG COLMAP_GIT_COMMIT=main
ARG CUDA_ARCHITECTURES=61;70;75;80;86;89
ARG TCNN_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES}
ENV QT_XCB_GL_INTEGRATION=xcb_egl

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    git cmake ninja-build build-essential libboost-program-options-dev libboost-graph-dev \
    libboost-system-dev libeigen3-dev libflann-dev libfreeimage-dev libmetis-dev \
    libgoogle-glog-dev libsqlite3-dev libglew-dev qtbase5-dev \
    libqt5opengl5-dev libcgal-dev libceres-dev libcurl4-openssl-dev

# Build & install COLMAP
RUN git clone https://github.com/colmap/colmap.git && \
    cd colmap && \
    git fetch https://github.com/colmap/colmap.git ${COLMAP_GIT_COMMIT} && \
    git checkout FETCH_HEAD && \
    mkdir build && \
    cd build && \
    cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} -DCMAKE_INSTALL_PREFIX=install && \
    ninja install

# Build tiny-cuda-nn
RUN git clone --recursive https://github.com/nvlabs/tiny-cuda-nn.git && \
    cd tiny-cuda-nn/bindings/torch && \
    python3 setup.py bdist_wheel

FROM nvcr.io/nvidia/pytorch:24.05-py3 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests \
    libboost-program-options1.74.0 libc6 libceres2 libfreeimage3 libgcc-s1 libgl1 libglew2.2 \
    libgoogle-glog0v5 libqt5core5a libqt5gui5 libqt5widgets5 libcurl4 && \
    rm -rf /var/lib/apt/lists/*

# Copy & install tiny-cuda-nn wheel
COPY --from=builder /workspace/tiny-cuda-nn/bindings/torch/dist/tinycudann*.whl /tmp/
RUN pip install --no-cache-dir /tmp/tinycudann*.whl && rm /tmp/tinycudann*.whl

# Copy colmap from builder stage
COPY --from=builder /workspace/colmap/build/install/ /usr/local/
