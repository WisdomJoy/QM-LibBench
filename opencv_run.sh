#!/bin/bash
# set -e
echo "=== Starting OpenCV build for RISC-V ==="
cd /opencv
echo "Building OpenCV for RISC-V..."
# 清理旧的 build 目录（避免缓存污染）
echo "Cleaning old build directory..."
rm -rf build
mkdir -p build || { echo "ERROR: Cannot create build directory"; exit 1; }

# 进入 build 目录
cd build || { echo "ERROR: Cannot cd to build"; exit 1; }
echo "Build directory: $(pwd)"

# 确认 toolchain 文件存在
if [ ! -f "/riscv64-toolchain.cmake" ]; then
    echo "ERROR: /riscv64-toolchain.cmake not found!"
    ls -la /
    exit 1
fi
echo "✅ Toolchain file found: /riscv64-toolchain.cmake"
# cmake .. \
#     -DCMAKE_BUILD_TYPE=Release

# cmake --build . -j$(nproc)

cmake     -DCMAKE_TOOLCHAIN_FILE=/riscv64-toolchain.cmake \
     -DCMAKE_INSTALL_PREFIX=../install \
     -DWITH_HAL_RVV=ON \
     -DCPU_BASELINE=DETECT \
     -DCPU_DISPATCH=RVV \
     -DENABLE_RVV=ON \
     -DCPU_RVV_FLAGS_ON="-march=rv64gcv" \
     -DBUILD_ZLIB=ON \
     -DBUILD_JPEG=ON \
     -DBUILD_OPENJPEG=ON \
     -DBUILD_PNG=ON \
     -DWITH_WEBP=ON \
     -DBUILD_WEBP=ON \
     -DBUILD_TIFF=ON \
     -DWITH_LAPACK=OFF \
     -DBUILD_SHARED_LIBS=OFF \
     -DBUILD_opencv_apps=OFF \
     -DBUILD_DOCS=OFF \
     -DBUILD_EXAMPLES=OFF \
     -DBUILD_TESTS=ON \
     -DBUILD_PERF_TESTS=ON \
     -DWITH_GTK=OFF     ..

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

# make -j$(nproc)

# ctest --output-on-failure