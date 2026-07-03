#!/bin/bash
# set -e
echo "=== Starting Libjpeg build for RISC-V ==="
cd /libjpeg
echo "Building Libjpeg for RISC-V..."

# 确认 toolchain 文件存在
if [ ! -f "/riscv64-toolchain.cmake" ]; then
    echo "ERROR: /riscv64-toolchain.cmake not found!"
    ls -la /
    exit 1
fi
echo "✅ Toolchain file found: /riscv64-toolchain.cmake"

if [ -z "${LIBJPEG_TARGETS}" ]; then
    echo "ERROR: LIBJPEG_TARGETS is empty. Pass the test/perf targets to build."
    exit 1
fi
echo "Targets: ${LIBJPEG_TARGETS}"

echo "Cleaning old build directory..."
rm -rf build
mkdir -p build || { echo "ERROR: Cannot create build directory"; exit 1; }

cd build || { echo "ERROR: Cannot cd to build"; exit 1; }
echo "Build directory: $(pwd)"

cmake -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE=/riscv64-toolchain.cmake \
    -DENABLE_SHARED=FALSE \
    -DREQUIRE_SIMD=TRUE \
    -DWITH_GTEST_PERF=ON \
    -DBUILD_VERSION=native \
    -DTARGET_ARCH=riscv \
    ..

# 检查 CMake 是否成功
if [ $? -ne 0 ]; then
    echo "ERROR: CMake configuration failed!"
    exit 1
fi
echo "✅ CMake configuration successful"

# 开始编译指定目标，避免未实现算子导致全量构建失败
echo "Starting compilation for targets: ${LIBJPEG_TARGETS}"
ninja ${LIBJPEG_TARGETS}

# 检查编译是否成功
if [ $? -ne 0 ]; then
    echo "ERROR: Compilation failed!"
    exit 1
fi
echo "✅ Compilation successful"
