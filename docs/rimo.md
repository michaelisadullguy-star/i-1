# Rimo, the R interpreter of i-1

A seventh interpreter, in R (4.x), in `rimo/`.  Like the others it reads the three notations, runs the standard library `lib/*.imo` and prints, for every command of `i1` (`run`, `check`, `translate`, `eval`,
`text`), the same bytes.  It is the slowest of the cores: R is an interpreted language with a slow function call, so the evaluator below is two to three orders of magnitude slower than Rustimo (see *Speed*).
It is there to show that the specification can be implemented in a language that is not made for it, and it passes what it can be given the time to pass (see *What was run*).

```
make rimo                                      # or ./rimo/build.sh  -> build/rimo (a launcher); nothing is compiled
./i1 --impl rimo run examples/hello.hum.imo    # named explicitly: it is not part of auto, both or all
tests/conformance/run.sh --impl rimo --fast --sample-lib 12      # the conformance cases, one of twelve of the library sweep (the shell runner needs no Python)
tests/run_imo.sh --impl rimo --set small                          # the self-checking .imo tests
```

It needs `Rscript` (R ≥ 4.0: `apt-get install r-base-core`) and the CRAN package **gmp** (`apt-get install r-cran-gmp`) for the exact integers and rationals (R has none).  No other package and no Python at run time.
`lib/*.imo`, `docs/doc1.sbl` and `docs/doc2.sbl` are read from the repository; the parsed and checked prelude (about 8000 statements, 4 s to make) is kept in `~/.cache/rimo/prelude-<hash>.rds`
(`$RIMO_CACHE`), the hash covering the library files, the documents and the front-end sources, so a changed library is read again by itself.  The launcher `build/rimo` sets `LC_ALL=C.UTF-8`, an unlimited
stack and a large protection stack for R.

## How it is made

The modules follow those of Schimo (and so of OCamimo and Rustimo) one for one.  R has no structures, so a term is a list whose first element is a tag; a mutable cell (a thunk) is an environment; text is handled as
vectors of code points (`utf8ToInt`) wherever a loop walks over it.

| file | content |
|:--|:--|
| `R/base.R` | errors of the host (R conditions), the digits of the base i−1 (gmp), Python's `repr` and `%.12g` (computed from the exact value of the double), string helpers |
| `R/syntax.R` | the spec notation: lexer, token trees, statements, classes, the erasure of a definition to a de Bruijn term |
| `R/layers.R` | doc 1, the bin notation and the translators between the notations |
| `R/core.R` | the evaluator: terms compiled to code with flat closures, call by need, an **explicit stack** of continuations in one loop (R's own recursion stops at some thousands of calls, so the depth of a computation is limited by memory), decoders |
| `R/hum.R` | doc 2 and the human notation |
| `R/types.R` | the class checker (overloads, coercions, subclass facts, unknowns) |
| `R/quote.R` | statements written as codes for the simplifier |
| `R/program.R` | loading and checking a program, the cache of the prelude, building the machine (the definitions of the prelude are compiled when first needed) |
| `R/output.R` | printing values in the three notations; `main` |
| `R/main.R` | the command line |

`serve` (the protocol of `tests/core_serve.py`) is not implemented.

Three things of R that the port had to work around: `x[-integer(0)]` is empty, not `x`; `gmp::as.bigz("025")` reads octal, so decimal numerals are parsed by `bz_dec`; and a function that recurses a few thousand
times dies with "evaluation nested too deeply" or "node stack overflow", so nothing in the evaluator recurses with the depth of the program.

## Speed

Seconds, the program including its start-up (R needs 0.2 s, the cached prelude 0.2 s, checking the program and building the machine another 0.5 s):

| program | Rustimo | Schimo | Rimo |
|:--|--:|--:|--:|
| `main in \NN := 1 + 1` | 0.25 | 0.6 | 1.6 |
| `acos(1/2 + 3/4*i)` to 12 digits (`tests/conformance/programs/lib/acos.1.hum.imo`) | 0.46 | — | 72 |
| a file of `tests/imo/small` with 150 checks | 0.3 to 5 | 2 to 30 | 27 to 340 (one of 62 hash and random-number checks: 1076) |

The evaluator does about 100 000 steps per second (Rustimo: 10 to 30 million).  Half of the time is the interpretation of the loop, a fifth the allocation of thunks.

## What was run

* the conformance cases of `tests/conformance` that are not marked slow, all of them except the library sweep (`lib.*`, 1625 cases, three notations of 540 programs, many of them real-number functions that take
  minutes), of which one in twelve was run (`tests/conformance/run.sh --impl rimo --fast --sample-lib 12`): **726 of 726 conform**, byte for byte, standard output and exit status;
* the self-checking `.imo` files of `tests/imo/small` (`tests/run_imo.sh --impl rimo --set small -j 4`): **33 of 33 files pass, 4057 checks**, in 6790 s on four processes (the slowest file, the 62 theory checks of `theory-01`, takes 82 minutes alone; `prng-01` 18).
