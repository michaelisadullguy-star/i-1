#!/bin/sh
# build Cimo, the C interpreter, with the plain C compiler (gcc or cc, and the Boehm collector, libgc-dev); output: build/cimo
cd "$(dirname "$0")/.." || exit 1
mkdir -p build
./cimo/gen_data.sh || exit 1
${CC:-gcc} -O2 -o build/cimo.tmp cimo/src/*.c -lgc -lm && mv build/cimo.tmp build/cimo
