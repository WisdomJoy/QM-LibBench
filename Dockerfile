FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    file \
    cmake \
    ninja-build \
    build-essential \
    python3 \
    git \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    binutils-loongarch64-linux-gnu \
    gcc-14-loongarch64-linux-gnu \
    g++-14-loongarch64-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 下载 riscv64-unknown-linux-gnu 工具链
RUN wget https://github.com/riscv-collab/riscv-gnu-toolchain/releases/download/2026.06.06/riscv64-glibc-ubuntu-24.04-gcc.tar.xz \
    && tar -xJf riscv64-glibc-ubuntu-24.04-gcc.tar.xz -C /opt \
    && rm riscv64-glibc-ubuntu-24.04-gcc.tar.xz

# 将 /opt/riscv/bin 添加到 PATH
ENV PATH="/opt/riscv/bin:${PATH}"

# 验证安装
RUN riscv64-unknown-linux-gnu-gcc --version

COPY opencv_run.sh /opencv_run.sh
RUN chmod +x /opencv_run.sh
COPY ncnn_riscv_run.sh /ncnn_riscv_run.sh
RUN chmod +x /ncnn_riscv_run.sh
COPY ncnn_arm_run.sh /ncnn_arm_run.sh
RUN chmod +x /ncnn_arm_run.sh
COPY ncnn_loongarch_run.sh /ncnn_loongarch_run.sh
RUN chmod +x /ncnn_loongarch_run.sh
COPY libjpeg_run.sh /libjpeg_run.sh
RUN chmod +x /libjpeg_run.sh
COPY riscv64-toolchain.cmake /riscv64-toolchain.cmake
COPY k1.toolchain.cmake /k1.toolchain.cmake
COPY loongarch64-linux-gnu.toolchain.cmake /loongarch64-linux-gnu.toolchain.cmake
ENTRYPOINT ["/opencv_run.sh"]
