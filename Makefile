# Makefile -- the i-1 language: three interpreters of one specification (Pymo, Python: pymo/;  Haskimo, Haskell: haskimo/;
# Rustimo, Rust: rustimo/).
#
#   make            build Haskimo (build/haskimo) and Rustimo (build/rustimo), the ones whose compiler is found; Pymo needs no build
#   make rustimo    build Rustimo only (cargo);   make haskimo   build Haskimo only (ghc)
#   make install    ./install.sh  (PREFIX=... to choose the place; INSTALL_FLAGS='--pymo-only' etc.)
#   make test       the test suites on every core they support (tests/run_suites.py)
#   make conformance   all the interpreters on the shared cases of tests/conformance (tests/conformance/run.py)
#   make clean
PREFIX ?= $(HOME)/.local
INSTALL_FLAGS ?=
HAVE_GHC := $(shell command -v ghc >/dev/null 2>&1 && echo yes)
HAVE_CARGO := $(shell command -v cargo >/dev/null 2>&1 && echo yes)

.PHONY: all haskimo rustimo install uninstall test conformance clean
all: $(if $(HAVE_GHC),haskimo) $(if $(HAVE_CARGO),rustimo)
	@if [ -z '$(HAVE_GHC)$(HAVE_CARGO)' ]; then echo 'neither ghc nor cargo found: only Pymo can be used'; fi

haskimo: build/haskimo

rustimo: build/rustimo

build/haskimo: $(wildcard haskimo/src/I1/*.hs) haskimo/app/Main.hs $(wildcard lib/*.imo) docs/doc1.sbl docs/doc2.sbl
	./haskimo/build.sh

build/rustimo: $(wildcard rustimo/src/*.rs) rustimo/Cargo.toml $(wildcard lib/*.imo) docs/doc1.sbl docs/doc2.sbl
	./rustimo/build.sh

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
