# Makefile -- the i-1 language: three interpreters of one specification (Pymo, Python: pymo/;  Haskimo, Haskell: haskimo/;
# Rustimo, Rust: rustimo/).
#
#   make            build Haskimo (build/haskimo) and Rustimo (build/rustimo), the ones whose compiler is found; Pymo needs no build
#   make rustimo    build Rustimo only (cargo);   make haskimo   build Haskimo only (ghc)
#   make ocamimo    build OCamimo, the OCaml interpreter (ocamlopt, standard library only); it is not part of `make`
#   make cimo       build Cimo, the C interpreter (gcc and libgc-dev); it is not part of `make`
#   make schimo     build Schimo, the Racket (Scheme) interpreter (raco make); it is not part of `make`
#   make rimo       set up Rimo, the R interpreter (R and the package gmp; nothing is compiled); it is not part of `make`
#   make compimo    build Compimo, the compiler (cargo; at run time it needs gcc and libgc-dev); it is not part of `make`; then  build/compimo prelude  compiles the prelude once
#   make install    ./install.sh  (PREFIX=... to choose the place; INSTALL_FLAGS='--pymo-only' etc.)
#   make test       the test suites on every core they support (tests/run_suites.py)
#   make conformance   all the interpreters on the shared cases of tests/conformance (tests/conformance/run.py)
#   make clean
PREFIX ?= $(HOME)/.local
INSTALL_FLAGS ?=
HAVE_GHC := $(shell command -v ghc >/dev/null 2>&1 && echo yes)
HAVE_CARGO := $(shell command -v cargo >/dev/null 2>&1 && echo yes)

.PHONY: all haskimo rustimo compimo ocamimo schimo cimo rimo install uninstall test conformance clean
all: $(if $(HAVE_GHC),haskimo) $(if $(HAVE_CARGO),rustimo)
	@if [ -z '$(HAVE_GHC)$(HAVE_CARGO)' ]; then echo 'neither ghc nor cargo found: only Pymo can be used'; fi

haskimo: build/haskimo

rustimo: build/rustimo

compimo: build/compimo

ocamimo: build/ocamimo

schimo: build/schimo

rimo: build/rimo

cimo: build/cimo

build/haskimo: $(wildcard haskimo/src/I1/*.hs) haskimo/app/Main.hs $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./haskimo/build.sh

build/rustimo: $(wildcard rustimo/src/*.rs) rustimo/Cargo.toml $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./rustimo/build.sh

build/compimo: $(wildcard compimo/src/*.rs) $(wildcard compimo/rt/*) compimo/Cargo.toml $(wildcard rustimo/src/*.rs) $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./compimo/build.sh

build/ocamimo: $(wildcard ocamimo/src/[a-z]*.ml) ocamimo/gen_data.sh $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./ocamimo/build.sh

build/schimo: $(wildcard schimo/src/[a-z]*.rkt) schimo/gen_data.sh $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./schimo/build.sh

build/rimo: $(wildcard rimo/R/*.R) rimo/build.sh $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./rimo/build.sh

build/cimo: $(wildcard cimo/src/[a-z]*.c) cimo/src/cimo.h cimo/gen_data.sh $(wildcard lib/*.imo) lib/MANIFEST docs/doc1.sbl docs/doc2.sbl
	./cimo/build.sh

install:
	./install.sh --prefix '$(PREFIX)' $(INSTALL_FLAGS)

uninstall:
	./install.sh --prefix '$(PREFIX)' --uninstall

test:
	@$(MAKE) --no-print-directory all
	python3 tests/run_suites.py

conformance:
	@$(MAKE) --no-print-directory all
	python3 tests/conformance/run.py

clean:
	rm -rf build dist-newstyle rustimo/target
