# Rustimo, the Rust interpreter of i-1

One of the three parallel cores of the language, next to Pymo, the Python one in `pymo/`, and Haskimo, the Haskell one in `haskimo/`.  It
reads the same three notations, runs the same standard library (`lib/*.imo`) and prints the same bytes for every command of
`pymo/i1.py` (`run`, `check`, `translate`, `eval`, `text`).  No core is the reference: the language is what the shared files say (the
`.imo` files, the `.md` documents, the test suite), and a core is right when the shared tests pass on it.  i-1 is interpreted — Rustimo
is a compiled Rust program that reads, checks and evaluates i-1 programs each time it runs, and compiles none of them.  See README.md §2.1
(how to install and choose) and §16.5 (how the three cores are kept identical).

## Build

Needs `cargo` and `rustc` (1.70 or newer).  **No crates**: `Cargo.toml` has no dependencies, so nothing is downloaded and the build works
offline.

```sh
./rustimo/build.sh                 # from the repository root                     -> build/rustimo
make rustimo                       # the same, with dependency tracking
./install.sh --rustimo-only [--prefix DIR]    # build and install as DIR/bin/rustimo (+ the dispatcher i1)
```

`rustimo` is one self-contained executable of about 2 MB: `lib/*.imo`, `docs/doc1.sbl` and `docs/doc2.sbl` are embedded at compile
time (`src/data.rs`, `include_str!`), so it needs no data directory and no Python.  After editing a file of `lib/` or `docs/` rebuild it
(`make` notices).  Programs and their `.sbl` tables are read from disk, as in the other cores.

```sh
build/rustimo run examples/main.hum.imo
build/rustimo eval examples/target.hum.imo z 14
build/rustimo translate examples/target.hum.imo --to bin
```

## Modules (`src/`), each the counterpart of one module of Haskimo and of Pymo

| Rustimo | Haskimo | Pymo | role |
|:--|:--|:--|:--|
| `base.rs`, `bigint.rs` | `Base.hs` | `pymo/base_b.py` | digit arithmetic of base i − 1; Python-compatible `repr` and `%g` (messages and `eval` print them); a small big-integer and rational type, because the standard library has none |
| `syntax.rs` | `Syntax.hs` | `pymo/syntax.py` | spec lexer and parser, class terms, pretty-printers, erasure to de Bruijn terms, numeral expansion |
| `layers.rs` | `Layers.hs` | `pymo/layers.py` | binary lexer, doc 1, spec ↔ bin, `@bin` `@spec` `@hum` sections |
| `hum.rs` | `Hum.hs` | `pymo/hum.py` | doc 2, the human lexer and Pratt parser |
| `types.rs` | `Types.hs` | `pymo/imotypes.py` | the class checker (a class error is a `Result::Err(String)`; an exception of the host is a `R<..>`) |
| `quote.rs` | `Quote.hs` | `pymo/quote.py` | statements as codes, the table of definitions (the doc 1 table is updated in the order of first use) |
| `core.rs` | `Core.hs` | `pymo/imo_core.py` | the evaluator, below; the decoders |
| `program.rs` | `Program.hs` | `pymo/imo.py` | loader: notations → statements → checker → evaluator |
| `output.rs` | `Output.hs` | `pymo/output.py` | the printer, the Speller, `main`, the output notations |
| `serve.rs` | `Serve.hs` | — | `rustimo serve`: a loaded program as a service for the shared test suite |
| `main.rs` | `app/Main.hs` | `pymo/i1.py` | the command line |
| `data.rs`, `alloc.rs` | `EmbedTH.hs`, `Data.hs` | — | the embedded system files; a small-block allocator for the evaluator |

## The evaluator (`src/core.rs`)

* **Code.**  A definition is an untyped lambda term in de Bruijn form.  It is compiled once to a tree of `Code` with **flat closures**: a
  lambda captures exactly the variables it uses, a delayed argument (a thunk) too, and a frame is the captured values followed by the
  arguments of the call.  A chain `λx.λy.…` is one lambda of arity n, a chain `((f a) b) c` one call (eval/apply: fewer arguments make a
  partial application, more apply the result to the rest).
* **Call-by-need on an explicit stack.**  The machine keeps its continuation (update frames and pending arguments) in a vector on the
  heap, not on the stack of the host, so the depth of a computation is limited by memory only.  A thunk is updated with its value when it
  is evaluated; a thunk that is entered again while it is being evaluated is a loop (`<<loop>>`), one that failed fails again with the
  same error.
* **What is done at once, what is delayed.**  A variable and a global are passed as the pointer that is already there, a lambda is built,
  a function of known arity applied to too few arguments is built as a partial application, every other argument becomes a thunk.  A
  call of a global of known arity enters it directly, a call of a variable that holds an evaluated closure of the right arity too.
* **Floating out.**  Every closed application is evaluated at most once for the whole run (it becomes a shared thunk), as in the other
  cores.
* **Lazy compilation.**  The library is a few thousand definitions and a program uses a few hundred, so a library definition is erased
  and compiled when it is first needed.  This and the lack of a runtime are why `rustimo run examples/hello.hum.imo` takes 40 ms.
* **Memory.**  Values are reference counted (`Rc`); dropping a long list or a deep chain of thunks is iterative, so it cannot overflow the
  stack.  Blocks of up to 256 bytes come from per-thread free lists (`alloc.rs`).  Peak memory is a fraction of Haskimo's (a
  generational copying collector with a large allocation area).
* **The decoders** (`to_bool`, `to_list`, `to_pair`, `to_ord`, `stream_nth`, `cell_or_nil`, and the Speller's `nodeOf`) apply a language
  value to builders of the host — the markers ⊤ and ⊥, the list and pair builders, the five constructors of a code — and read what
  comes back, exactly as Haskimo's `Core.hs` does.  Nothing is decided by the host.

## Differences from the other cores

* **Errors in the host.**  An error of the language (a class error, an unknown whose value is needed, a value that cannot be printed)
  is reported exactly as in Pymo and Haskimo.  A malformed source file raises a parse error in all of them, with status 1, but the texts
  of the host's own exceptions differ (a Python traceback, a `haskimo: ...` line, a `rustimo: ...` line).  The conformance suite
  contains no such case.
* **Speed and memory.**  About as fast as Haskimo on evaluation-heavy programs, several times faster than Pymo; it starts in a few
  milliseconds (Haskimo needs 0.2 s to set up) and needs about a tenth of Haskimo's memory.  README §16.5 has the table.
* **Laziness of the host.**  Rustimo's loader and checker are eager, Haskimo's are lazy (as Haskell is): the order in which two host errors in one program are noticed can differ.  No shipped case depends on it.
* **The Python API** (`imo.load`, `Machine.val`, ...) used by four of the eighteen suites exists in Python only.

## Test

The test suite is shared by the three cores; nothing in it is specific to Rustimo.

```sh
python3 tests/conformance/run.py --impl rustimo      # the shared command-line cases, against the bytes on which all the cores agree
python3 tests/conformance/run.py                     # every core that is built
python3 tests/conformance/run.py --impl rustimo -v --filter prove
python3 tests/test_poly.py --core rustimo            # a library suite on Rustimo (fourteen of the eighteen suites can)
python3 tests/run_suites.py --core rustimo           # all of them
cd rustimo && cargo test --release                   # the unit tests of the arithmetic (big integers, base i − 1, Python-compatible %g)
```

`rustimo serve FILE...` is what lets the library suites, which were written against the Python API of Pymo, run on Rustimo: it loads the
program and answers one request per line on standard input (take the value of a symbol, apply it, decode a digit string, a truth value, a
list cell, a pair), keeping the values inside the process and naming them by handles.  The protocol is described at the top of
`src/serve.rs`; the client is `tests/core_serve.py`, shared with Haskimo.  Every decision about a value is made by Rustimo's evaluator.
