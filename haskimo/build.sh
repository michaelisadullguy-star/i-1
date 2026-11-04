#!/bin/sh
# build Haskimo, the Haskell interpreter, with plain ghc (no cabal, no network); output: build/haskimo
cd "$(dirname "$0")/.." && mkdir -p build/hs && ghc -O1 -ihaskimo/src -outputdir build/hs -rtsopts "-with-rtsopts=-K2g -A128m" -o build/haskimo haskimo/app/Main.hs "$@"
