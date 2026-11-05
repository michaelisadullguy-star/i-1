#!/bin/sh
# build Compimo, the compiler, with plain cargo (no dependencies, no network); output: build/compimo.  It needs a C compiler and the Boehm collector (libgc-dev) at run time.
cd "$(dirname "$0")/.." && mkdir -p build && cargo build --release --offline --manifest-path compimo/Cargo.toml --target-dir build/cs "$@" \
  && cp build/cs/release/compimo build/compimo
