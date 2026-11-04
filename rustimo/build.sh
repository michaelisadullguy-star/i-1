#!/bin/sh
# build Rustimo, the Rust interpreter, with plain cargo (no dependencies, no network); output: build/rustimo
cd "$(dirname "$0")/.." && mkdir -p build && cargo build --release --offline --manifest-path rustimo/Cargo.toml --target-dir build/rs "$@" \
  && cp build/rs/release/rustimo build/rustimo
