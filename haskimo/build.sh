#!/bin/sh
# build Haskimo, the Haskell interpreter, with plain ghc (no cabal, no network); output: build/haskimo
# -w: no warnings (GHC 9.8 and later warn about every head and tail; pass -Wall after it to see the others)
cd "$(dirname "$0")/.." && mkdir -p build/hs && ghc -O1 -w -ihaskimo/src -outputdir build/hs -rtsopts "-with-rtsopts=-K2g -A128m" -o build/haskimo haskimo/app/Main.hs "$@"
