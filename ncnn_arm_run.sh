#!/bin/bash
# set -e
echo "=== Starting ncnn build for ARM ==="
cd /ncnn
echo "Building ncnn for ARM..."
# 清理旧的 build 目录（避免缓存污染）
echo "Cleaning old build directory..."
rm -rf build
mkdir -p build || { echo "ERROR: Cannot create build directory"; exit 1; }

# 进入 build 目录
cd build || { echo "ERROR: Cannot cd to build"; exit 1; }
echo "Build directory: $(pwd)"

# 确认 toolchain 文件存在
TOOLCHAIN_FILE="/ncnn/toolchains/aarch64-linux-gnu.toolchain.cmake"
if [ ! -f "${TOOLCHAIN_FILE}" ]; then
    echo "ERROR: ${TOOLCHAIN_FILE} not found!"
    ls -la /ncnn/toolchains
    exit 1
fi
echo "✅ Toolchain file found: ${TOOLCHAIN_FILE}"
# cmake .. \
#     -DCMAKE_BUILD_TYPE=Release

# cmake --build . -j$(nproc)

cmake   -DCMAKE_TOOLCHAIN_FILE="${TOOLCHAIN_FILE}" \
  -DCMAKE_BUILD_TYPE=Release   -DNCNN_ARM82=ON   -DNCNN_ARM82DOT=ON \
    -DNCNN_ARM82FP16FML=OFF   -DNCNN_ARM84BF16=OFF   -DNCNN_ARM84I8MM=OFF \
      -DNCNN_ARM86SVE=OFF   -DNCNN_ARM86SVE2=OFF   -DNCNN_ARM86SVEBF16=OFF \
        -DNCNN_ARM86SVEI8MM=OFF   -DNCNN_ARM86SVEF32MM=OFF \
        -DCMAKE_BUILD_TYPE=release -DNCNN_BUILD_TESTS=ON \
        -DNCNN_OPENMP=ON -DNCNN_RUNTIME_CPU=OFF \
        -DNCNN_XTHEADVECTOR=OFF -DNCNN_SIMPLEOCV=ON -DNCNN_BUILD_EXAMPLES=OFF \
        -DNCNN_ZFH=OFF -DNCNN_ZVFH=OFF  -DNCNN_BENCHMARK=ON  \
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
