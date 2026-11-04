# Haskimo, the Haskell interpreter of i-1

One of the three parallel cores of the language, next to Pymo, the Python one in `pymo/`, and Rustimo, the Rust one in `rustimo/`.  It reads the same three notations, runs the same
standard library (`lib/*.imo`) and prints the same bytes for every command of `pymo/i1.py` (`run`, `check`, `translate`, `eval`,
`text`).  Neither core is the reference: the language is what the shared files say (the `.imo` files, the `.md` documents, the test
suite), and a core is right when the shared tests pass on it.  i-1 is interpreted — Haskimo is a compiled Haskell program that reads,
checks and evaluates i-1 programs each time it runs, and compiles none of them.  See README.md §2.1 (how to install and choose) and
§16.5 (how the three cores are kept identical).

## Build

Needs GHC 9.x and its boot libraries only (`base`, `containers`, `mtl`, `template-haskell`, `directory`).  Nothing from Hackage.

```sh
./haskimo/build.sh                 # plain ghc, from the repository root          -> build/haskimo
make                       # the same, with dependency tracking
cabal build exe:haskimo    # the same, with cabal                         (cabal install exe:haskimo installs it)
./install.sh --haskimo-only [--prefix DIR]    # build and install as DIR/bin/haskimo (+ the dispatcher i1)
```

`haskimo` is one self-contained executable: `lib/*.imo`, `docs/doc1.sbl` and `docs/doc2.sbl` are embedded at compile time
(`src/I1/EmbedTH.hs`, Template Haskell), so it needs no data directory and no Python.  After editing a file of `lib/` or `docs/`
rebuild it (`make` notices).  Programs and their `.sbl` tables are read from disk, as in Pymo.

```sh
build/haskimo run examples/main.hum.imo
build/haskimo eval examples/target.hum.imo z 14
build/haskimo +RTS -s -RTS run examples/hello.hum.imo      # run-time statistics (the stack limit is -K2g, the allocation area -A128m)
```

## Modules (`src/I1/`), each the counterpart of one module of Pymo

| Haskimo | Pymo | role |
|:--|:--|:--|
| `Base.hs` | `pymo/base_b.py` | digit arithmetic of base i − 1; Python-compatible `repr` and `%g` (messages and `eval` print them) |
| `Syntax.hs` | `pymo/syntax.py` | spec lexer and parser, class terms, pretty-printers, erasure to de Bruijn terms, numeral expansion |
| `Layers.hs` | `pymo/layers.py` | binary lexer, doc 1, spec ↔ bin, `@bin` `@spec` `@hum` sections |
| `Hum.hs` | `pymo/hum.py` | doc 2, the human lexer and Pratt parser |
| `Types.hs` | `pymo/imotypes.py` | the class checker (pure, in `Either String`; the Python `ImoTypeError` is a `Left`) |
| `Quote.hs` | `pymo/quote.py` | statements as codes, the table of definitions (a `State` over doc 1: codes are given in order of first use) |
| `Core.hs` | `pymo/imo_core.py` | the evaluator: closures; call-by-need is Haskell's own laziness; closed sub-terms are floated out; the decoders |
| `Program.hs` | `pymo/imo.py` | loader: notations → statements → checker → evaluator |
| `Output.hs` | `pymo/output.py` | the printer, the Speller, `main`, the output notations |
| `../app/Main.hs` | `pymo/i1.py` | the command line |
| `EmbedTH.hs`, `Data.hs` | — | the embedded system files |

## Differences from Pymo

* **Errors in the host.**  An error of the language (a class error, an unknown whose value is needed, a value that cannot be printed)
  is reported exactly as in Pymo.  A malformed source file raises a parse error in all of them, with status 1, but the texts of the host's own
  exceptions differ (a Python traceback, a Haskimo `haskimo: ...` line).  The conformance suite contains no such case.
* **Speed and memory.**  Several times faster than Pymo (README §16.5 has the table); the allocation area is large (`-A128m`), so even
  a small program shows about 150 MB of memory in use.
* **The Python API** (`imo.load`, `Machine.val`, ...) used by `tests/test_*.py` exists in Python only.

## Test

The test suite is shared by the three cores; nothing in it is specific to Haskimo.

```sh
python3 tests/conformance/run.py --impl haskimo      # the shared command-line cases, against the bytes on which all the cores agree
python3 tests/conformance/run.py                     # every core that is built
python3 tests/conformance/run.py --impl haskimo -v --filter prove
python3 tests/test_poly.py --core haskimo            # a library suite on Haskimo (fourteen of the eighteen suites can)
python3 tests/run_suites.py --core haskimo           # all of them
```

`haskimo serve FILE...` is what lets the library suites, which were written against the Python API of Pymo, run on Haskimo: it loads the
program and answers one request per line on standard input (take the value of a symbol, apply it, decode a digit string, a truth value, a
list cell, a pair), keeping the values inside the process and naming them by handles.  The protocol is described at the top of
`src/I1/Serve.hs`; the client is `tests/core_serve.py` (which also serves Rustimo, whose `rustimo serve` speaks the same protocol).  Every decision about a value is made by Haskimo's evaluator.
