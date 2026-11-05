# Schimo, the Scheme (Racket) interpreter of i-1

A fifth interpreter, in Racket (a Scheme: `#lang racket/base`, the compiler of Racket CS is Chez Scheme), in `schimo/`.  Like the others it reads the three notations, runs the standard
library `lib/*.imo` and prints, for every command of `i1` (`run`, `check`, `translate`, `eval`, `text`), the same bytes: all the cases of `tests/conformance` conform
(`python3 tests/conformance/run.py --impl schimo`), and so do the suites that go through the command line (`python3 tests/test_theory.py --core schimo`, and `dict lists strings classes`).

```
make schimo                                    # or ./schimo/build.sh  -> build/schimo (a launcher); the compiled modules are kept in schimo/src/compiled
./i1 --impl schimo run examples/prove.hum.imo  # named explicitly: it is not part of auto, both or all
python3 tests/conformance/run.py --impl schimo
```

It needs `racket` (8.x; the package of the same name on Debian and Ubuntu) and nothing else: no package of the Racket catalogue, no Python at run time.  `lib/*.imo`, `docs/doc1.sbl` and
`docs/doc2.sbl` are embedded in the program (`schimo/gen_data.sh` writes them as here strings into `src/data-gen.rkt`, which is generated and not kept in git).

## How it is made

The modules follow those of OCamimo and Rustimo one for one; Racket has exact integers and rationals, so there is no module for big numbers.

| file | content |
|:--|:--|
| `src/base.rkt` | errors of the host, the digits of the base i−1 (exact integers), Python's `repr` and `%.12g` (computed from the exact value of the float), string helpers |
| `src/syntax.rkt` | the spec notation: lexer, token trees, statements, classes (structs), the erasure of a definition to a de Bruijn term |
| `src/layers.rkt` | doc 1, the bin notation and the translators between the notations |
| `src/core.rkt` | the evaluator: terms compiled to code with flat closures, call by need, an explicit stack of continuations (the depth of a computation is limited by memory, not by Racket's), decoders |
| `src/hum.rkt` | doc 2 and the human notation |
| `src/types.rkt` | the class checker (overloads, coercions, subclass facts, unknowns) |
| `src/quote.rkt` | statements written as codes for the simplifier |
| `src/program.rkt` | loading and checking a program, building the machine (the definitions of the prelude are compiled when first needed) |
| `src/output.rkt` | printing values in the three notations; `main` |
| `src/main.rkt` | the command line |

`serve` (the protocol of `tests/core_serve.py`) is not implemented.

## Speed

Seconds, 4 cores, the program including its start-up (Racket itself needs about 0.3 s to start):

| program | Rustimo | OCamimo | Schimo | Compimo |
|:--|--:|--:|--:|--:|
| `check examples/target.hum.imo` (the prelude is read and its classes recorded) | 0.26 | 0.16 | 0.56 | 0.2 |
| `tests/conformance` (2218 cases, cpu time) | — | 780 | 2307 | 1192 |
| the theory suite `tests/test_theory.py` | 126 | 285 | 667 | 25 |
| the container suite `tests/test_dict.py` | 5.8 | 8.6 | 21.6 | 11 |
