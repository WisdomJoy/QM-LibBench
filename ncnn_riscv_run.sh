#!/bin/bash
# set -e
echo "=== Starting ncnn build for RISC-V ==="
cd /ncnn
echo "Building ncnn for RISC-V..."
# 清理旧的 build 目录（避免缓存污染）
echo "Cleaning old build directory..."
rm -rf build
mkdir -p build || { echo "ERROR: Cannot create build directory"; exit 1; }

# 进入 build 目录
cd build || { echo "ERROR: Cannot cd to build"; exit 1; }
echo "Build directory: $(pwd)"

# 确认 toolchain 文件存在
if [ ! -f "/k1.toolchain.cmake" ]; then
    echo "ERROR: /k1.toolchain.cmake not found!"
    ls -la /
    exit 1
fi
echo "✅ Toolchain file found: /k1.toolchain.cmake"
# cmake .. \
#     -DCMAKE_BUILD_TYPE=Release

# cmake --build . -j$(nproc)

cmake -DCMAKE_TOOLCHAIN_FILE=/k1.toolchain.cmake \
    -DCMAKE_BUILD_TYPE=release -DNCNN_BUILD_TESTS=ON -DNCNN_OPENMP=ON \
    -DNCNN_RUNTIME_CPU=OFF -DNCNN_RVV=ON -DNCNN_XTHEADVECTOR=OFF \
    -DNCNN_SIMPLEOCV=ON -DNCNN_BUILD_EXAMPLES=OFF -DNCNN_ZFH=OFF \
    -DNCNN_ZVFH=OFF  -DNCNN_BENCHMARK=ON \
    -DNCNN_BUILD_PERF_BENCHMARK=ON ..


# 检查 CMake 是否成功
if [ $? -ne 0 ]; then
    echo "ERROR: CMake configuration failed!"
    exit 1
fi
echo "✅ CMake configuration successful"

# 开始编译
echo "Starting compilation with $(nproc) cores..."
make -j$(nproc)

# 检查编译是否成功
if [ $? -ne 0 ]; then
    echo "ERROR: Compilation failed!"
    exit 1
fi
echo "✅ Compilation successful"
