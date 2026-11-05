# Cimo, the C interpreter of i-1

A sixth interpreter, in C (`cimo/`).  Like the others it reads the three notations, runs the standard library `lib/*.imo` and prints, for every command of `i1` (`run`, `check`,
`translate`, `eval`, `text`), the same bytes: all the cases of `tests/conformance` conform (`python3 tests/conformance/run.py --impl cimo`), and so do the suites that go through the
command line (`python3 tests/test_theory.py --core cimo`, and `dict lists strings classes`).  It is *not* the compiler: Cimo interprets (the compiler of i-1 to C is Compimo,
[`docs/compimo.md`](compimo.md)); Cimo is a program in C that reads, checks and evaluates i-1 programs each time it runs.

```
make cimo                                     # or ./cimo/build.sh  -> build/cimo
./i1 --impl cimo run examples/prove.hum.imo   # named explicitly: it is not part of auto, both or all
python3 tests/conformance/run.py --impl cimo
```

It needs a C compiler (`gcc`, or `$CC`) and the Boehm collector (`libgc-dev`) to be built, and nothing at run time but the collector's shared library.  `lib/*.imo`, `docs/doc1.sbl` and
`docs/doc2.sbl` are embedded in the executable (`cimo/gen_data.sh` writes them as byte arrays into `src/data_gen.c`, which is generated and not kept in git).

## How it is made

The modules follow those of OCamimo and Rustimo one for one.  C has neither lists nor exceptions nor big numbers, so `util.c` supplies them: immutable singly linked lists, buffers,
string and UTF-8 helpers, hash tables, big integers and rationals (32-bit limbs), and **errors as `setjmp`/`longjmp`** (`TRY(h) … ENDTRY(h)`, `raise_err`: the same four kinds of error of
the host and the class errors, which the checker raises and the loader collects).  All memory is allocated with the Boehm collector and never freed by hand.

| file | content |
|:--|:--|
| `src/cimo.h` | every type and prototype |
| `src/util.c` | lists, strings, UTF-8, hash tables, errors, big integers, the digits of the base i−1, Python's `repr` and `%.12g` |
| `src/syntax.c` | the spec notation: lexer, token trees, statements, classes, the erasure of a definition to a de Bruijn term |
| `src/layers.c` | doc 1, the bin notation and the translators between the notations |
| `src/core.c` | the evaluator: terms compiled to code with flat closures, call by need, an explicit stack of continuations (the depth of a computation is limited by memory), decoders |
| `src/hum.c` | doc 2 and the human notation |
| `src/types.c` | the class checker (overloads, coercions, subclass facts, unknowns) |
| `src/quote.c` | statements written as codes for the simplifier |
| `src/program.c` | loading and checking a program, building the machine (the definitions of the prelude are compiled when first needed) |
| `src/output.c` | printing values in the three notations; `main` |
| `src/main.c` | the command line |

The host recursion (reading and printing deeply nested terms) can be deep, so the program starts itself again under `ulimit -s unlimited` (the environment variable `CIMO_STACK` marks the
second start).  `serve` (the protocol of `tests/core_serve.py`) is not implemented.

## Speed

Seconds, 4 cores, the program including its start-up.  Cimo is a plain translation, with the Boehm collector allocating every thunk and frame; it has not been tuned.

| program | Rustimo | OCamimo | Cimo | Schimo | Compimo |
|:--|--:|--:|--:|--:|--:|
| `check examples/target.hum.imo` (the prelude is read and its classes recorded) | 0.26 | 0.16 | 0.23 | 0.56 | 0.2 |
| `tests/conformance` (2218 cases, cpu time) | — | 780 | 1064 | 2307 | 1192 |
| the theory suite `tests/test_theory.py` | 126 | 285 | 491 | 667 | 25 |
| the container suite `tests/test_dict.py` | 5.8 | 8.6 | 10.3 | 21.6 | 11 |
