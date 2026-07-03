#!/bin/bash
set -e

OPENCV_COMMIT=${OPENCV_COMMIT:-d8bc5b94b851d5b392c61e5b954fba992e18bb73}

if [ ! -d "./repo/opencv" ]; then
    echo "Downloading OpenCV..."

    git clone https://github.com/opencv/opencv.git \
        ./repo/opencv

    cd ./repo/opencv
    git checkout ${OPENCV_COMMIT}
    cd - > /dev/null  # 返回原目录
fi

if [ ! -d "./repo/ncnn" ]; then
    echo "Downloading NCNN..."

    git clone https://github.com/breezejh/ncnn.git \
        ./repo/ncnn

    cd ./repo/ncnn
    git submodule update --init benchmark/googlebenchmark
    cd - > /dev/null  # 返回原目录
fi

if [ ! -d "./repo/libjpeg" ]; then
    echo "Downloading LIBJPEG..."

    git clone https://github.com/WisdomJoy/libjpeg-turbo.git \
        ./repo/libjpeg

    cd ./repo/libjpeg
    cd - > /dev/null  # 返回原目录
fi

exec "$@"