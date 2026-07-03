set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

# 使用新编译的工具链
set(CMAKE_C_COMPILER /home/weijia/riscv-rvv-linux/bin/riscv64-unknown-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER /home/weijia/riscv-rvv-linux/bin/riscv64-unknown-linux-gnu-g++)

# 确保RVV编译标志正确设置
set(CMAKE_C_FLAGS "-march=rv64gcv -mabi=lp64d -O3")
set(CMAKE_CXX_FLAGS "-march=rv64gcv -mabi=lp64d -O3")

# 设置sysroot路径（如果需要）
# set(CMAKE_SYSROOT /opt/riscv/riscv64-unknown-linux-gnu/sysroot)
# set(CMAKE_FIND_ROOT_PATH /opt/riscv/riscv64-unknown-linux-gnu/sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
