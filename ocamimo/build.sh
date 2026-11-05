#!/bin/sh
# build OCamimo, the OCaml interpreter, with the plain compiler (ocamlopt, the standard library and unix; no dune, no packages); output: build/ocamimo
cd "$(dirname "$0")/.." || exit 1
mkdir -p build/oc
./ocamimo/gen_data.sh || exit 1
rm -f build/oc/*
cp ocamimo/src/*.ml build/oc/
cd build/oc || exit 1
ocamlopt -inline 200 -unsafe -o ../ocamimo unix.cmxa bigint.ml base.ml syntax.ml layers.ml core.ml hum.ml types.ml quote.ml data_gen.ml program.ml output.ml main.ml
