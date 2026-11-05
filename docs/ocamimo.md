# OCamimo, the OCaml interpreter of i-1

A fourth interpreter, in OCaml (`ocamimo/`).  Like Pymo, Haskimo and Rustimo it reads the three notations, runs the standard library `lib/*.imo` and prints, for every command of `i1`
(`run`, `check`, `translate`, `eval`, `text`), the same bytes: all the cases of `tests/conformance` conform (`python3 tests/conformance/run.py --impl ocamimo`, 2218 of 2218), and the
suites that go through the command line pass on it (`python3 tests/test_theory.py --core ocamimo`, and `dict lists strings classes`).  No core is the reference: OCamimo is right when
the shared tests pass on it.

```
make ocamimo                                   # or ./ocamimo/build.sh  -> build/ocamimo
./i1 --impl ocamimo run examples/prove.hum.imo # named explicitly: it is not part of auto, both or all
python3 tests/conformance/run.py --impl ocamimo
```

It needs `ocamlopt` (4.14 or newer) and the `unix` library that comes with it; **nothing else**: no opam package, no dune, no Python at run time.  `lib/*.imo`, `docs/doc1.sbl` and
`docs/doc2.sbl` are embedded in the executable (`ocamimo/gen_data.sh` writes them as OCaml quoted strings into `src/data_gen.ml`, which is generated and not kept in git), so
`ocamimo` is one relocatable file of about 3.6 MB.

## How it is made

The modules follow those of Rustimo one for one, in the order in which they are linked:

| file | content |
|:--|:--|
| `src/bigint.ml` | arbitrary-precision integers and rationals (30-bit limbs) for the host side: the digit string ⇄ Gaussian integer isomorphism, decimal numerals, the fractions that `eval` prints |
| `src/base.ml` | errors of the host, UTF-8, the digits of the base i−1, Python's `repr` and `%.12g`, string helpers |
| `src/syntax.ml` | the spec notation: lexer, token trees, statements, classes, the erasure of a definition to a de Bruijn term |
| `src/layers.ml` | doc 1, the bin notation and the translators between the notations |
| `src/core.ml` | the evaluator: terms compiled to code with flat closures, call by need, an explicit stack of continuations (the depth of a computation is limited by memory), decoders |
| `src/hum.ml` | doc 2 and the human notation |
| `src/types.ml` | the class checker (overloads, coercions, subclass facts, unknowns) |
| `src/quote.ml` | statements written as codes for the simplifier |
| `src/program.ml` | loading and checking a program, building the machine (the definitions of the prelude are compiled when first needed) |
| `src/output.ml` | printing values in the three notations; `main` |
| `src/main.ml` | the command line |

Two details that differ from the Rust core: OCaml has no big integers in its standard library, so `bigint.ml` is written here; and the native stack of OCaml is not unlimited, so the
program starts itself once more under `ulimit -s unlimited` (the environment variable `OCAMIMO_STACK` marks the second start).  `serve` (the protocol of `tests/core_serve.py`) is not
implemented.

## Speed

Seconds, 4 cores, the program including its start-up:

| program | Rustimo | OCamimo | Compimo |
|:--|--:|--:|--:|
| `ocamimo check examples/target.hum.imo` (start-up: the prelude is read and its classes recorded) | 0.26 | 0.16 | 0.2 |
| `tests/conformance` (2218 cases, cpu time) | — | 780 | 1192 (compiling each program) |
| the theory suite `tests/test_theory.py` | 126 | 285 | 25 |
| the container suite `tests/test_dict.py` | 5.8 | 8.6 | 11 |
