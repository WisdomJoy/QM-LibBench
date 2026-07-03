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

required_compile_sources=()
required_overlay_files=("jsimdcpu.c")

add_required_source() {
    local compile_source="$1"
    shift

    if [[ ! " ${required_compile_sources[*]} " =~ " ${compile_source} " ]]; then
        required_compile_sources+=("${compile_source}")
    fi

    local file
    for file in "$@"; do
        if [[ ! " ${required_overlay_files[*]} " =~ " ${file} " ]]; then
            required_overlay_files+=("${file}")
        fi
    done
}

for target in ${LIBJPEG_TARGETS}; do
    case "${target#test_}" in
        rgb_ycc_convert|rgb_gray_convert|ycc_rgb_convert|h2v1_downsample|h2v2_downsample|fdct_islow|fdct_ifast|quantize|convsamp|idct_islow|idct_ifast|h2v1_upsample|h2v2_upsample|h2v1_fancy_upsample|h2v2_fancy_upsample|h2v1_merged_upsample|h2v2_merged_upsample|huff_encode_one_block|encode_mcu_AC_first_prepare|encode_mcu_AC_refine_prepare|idct_2x2|idct_4x4)
            op="${target#test_}"
            ;;
        *)
            op="${target#perf_}"
            ;;
    esac

    case "${op}" in
        rgb_ycc_convert)
            add_required_source "rvv/jccolor-rvv.c" "jccolor-rvv.c" "jccolext-rvv.c"
            ;;
        rgb_gray_convert)
            add_required_source "rvv/jcgray-rvv.c" "jcgray-rvv.c" "jcgryext-rvv.c"
            ;;
        ycc_rgb_convert)
            add_required_source "rvv/jdcolor-rvv.c" "jdcolor-rvv.c" "jdcolext-rvv.c"
            ;;
        h2v1_downsample|h2v2_downsample)
            add_required_source "rvv/jcsample-rvv.c" "jcsample-rvv.c" "jcsample.h"
            ;;
        fdct_islow)
            add_required_source "rvv/jfdctint-rvv.c" "jfdctint-rvv.c"
            ;;
        fdct_ifast)
            add_required_source "rvv/jfdctfst-rvv.c" "jfdctfst-rvv.c"
            ;;
        quantize|convsamp)
            add_required_source "rvv/jquanti-rvv.c" "jquanti-rvv.c"
            ;;
        idct_islow)
            add_required_source "rvv/jidctint-rvv.c" "jidctint-rvv.c"
            ;;
        idct_ifast)
            add_required_source "rvv/jidctfst-rvv.c" "jidctfst-rvv.c"
            ;;
        h2v1_upsample|h2v2_upsample|h2v1_fancy_upsample|h2v2_fancy_upsample)
            add_required_source "rvv/jdsample-rvv.c" "jdsample-rvv.c"
            ;;
        h2v1_merged_upsample|h2v2_merged_upsample)
            add_required_source "rvv/jdmerge-rvv.c" "jdmerge-rvv.c" "jdmrgext-rvv.c"
            ;;
        huff_encode_one_block)
            add_required_source "rvv/jchuff-rvv.c" "jchuff-rvv.c"
            ;;
        encode_mcu_AC_first_prepare|encode_mcu_AC_refine_prepare)
            add_required_source "rvv/jcphuff-rvv.c" "jcphuff-rvv.c"
            ;;
        idct_2x2|idct_4x4)
            add_required_source "rvv/jidctred-rvv.c" "jidctred-rvv.c"
            ;;
        *)
            echo "ERROR: Unknown libjpeg target: ${target}"
            exit 1
            ;;
    esac
done

for source in "${required_compile_sources[@]}"; do
    if [ ! -f "simd/${source}" ]; then
        echo "ERROR: Required RVV source missing for selected targets: simd/${source}"
        exit 1
    fi
done

echo "Required RVV compile sources: ${required_compile_sources[*]}"

# Keep only files needed by this task so test_adapters does not compile unrelated,
# possibly unimplemented RVV files.
for rvv_file in simd/rvv/*.c; do
    [ -e "${rvv_file}" ] || continue
    basename="$(basename "${rvv_file}")"
    if [[ ! " ${required_overlay_files[*]} " =~ " ${basename} " ]]; then
        rm -f "${rvv_file}"
    fi
done

simd_sources_cmake="${required_compile_sources[*]}"
awk -v replacement="set(SIMD_SOURCES ${simd_sources_cmake})" '
    /^set\(SIMD_SOURCES / {
        print replacement
        skip = 1
        next
    }
    skip && /rvv\/jquanti-rvv\.c\)/ {
        skip = 0
        next
    }
    !skip {
        print
    }
' simd/CMakeLists.txt > simd/CMakeLists.txt.tmp
mv simd/CMakeLists.txt.tmp simd/CMakeLists.txt

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
