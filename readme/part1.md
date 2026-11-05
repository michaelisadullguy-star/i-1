# i-1  (`.imo`)

**A small, lazy, class-checked mathematical language whose foundation is the Gaussian integers ℤ[i], written in base i − 1.  The Gaussian rationals ℚ[i] and the real numbers are constructed from them.**

```
π + e·i   is defined, exactly and in three lines, as

    pi in \RR := sum(2, k in \QQ |-> k / (2 * k + 1))
    e  in \RR := sum(1, k in \QQ |-> 1 / k)
    z  in \R  := pi + e * i
```

*i-1* (file extension `.imo`) is a language for writing mathematics down so that it can be **run**: every number is an exact element of ℚ[i], real and complex numbers are lazy streams of such elements, higher-dimensional algebras are built with the Cayley–Dickson construction (and are never collapsed back down), and function spaces of any dimension — including infinite — are ordinary values.  The language has **three interchangeable notations** (binary, specific/unicode and human), connected by two system documents.  A program has an entry point, `main`, and prints its result in any of the three notations; a statement that contains a predicate — a relation between real or complex numbers, which no evaluation can decide, or a relation about an *unknown* — is **simplified by logic, from the definitions**, to its simplest form: `true`, `false`, or its solution set; and the library covers complex analysis, linear algebra, number theory, polynomials, groups, rings, fields and Galois theory, all computed in the language.

```
4 * atan(1) == pi                        true      (the same series, written twice)
exp(i/2) == cos(1/2) + i * sin(1/2)      true      (Euler's formula, proved, not computed)
pi lt 22/7                               true      (certified error bounds)
```

> **License.**  Free for non-commercial use under the [i-1 License](LICENSE) (attribution required, strong copyleft); commercial use needs a paid license from the author, with the attribution duty waived and the copyleft kept ([§22](#22-license), [`COMMERCIAL.md`](COMMERCIAL.md)).

> **Status.**  i-1 is defined by what its three interpreters share — the `.imo` files, the `.md` documents and the test suite — and has three parallel interpreters, the cores: **Pymo**, written in Python, **Haskimo**, written in Haskell, and **Rustimo**, written in Rust.  None is the reference ([§2.1](#21-three-interpreters-pymo-haskimo-and-rustimo)).  Everything marked ✅ in [§17 Status](#17-status-limits-and-roadmap) is implemented and covered by the test-suite; everything else is explicitly listed there as a limitation or as roadmap.  Nothing in this README describes behaviour that is not either tested or labelled.

---

## Contents

1. [At a glance](#1-at-a-glance)
2. [Quick start](#2-quick-start)
3. [Design principles](#3-design-principles)
4. [The three notation systems](#4-the-three-notation-systems)
5. [The system documents (doc 1 and doc 2)](#5-the-system-documents-doc-1-and-doc-2)
6. [Numbers: base i-1, the Gaussian integers, and the Gaussian rationals built from them](#6-numbers-base-i-1-the-gaussian-integers-and-the-gaussian-rationals-built-from-them)
7. [Classes: every symbol is declared first](#7-classes-every-symbol-is-declared-first)
8. [Characters and strings](#8-characters-and-strings)
9. [Evaluation model](#9-evaluation-model)
10. [Lazy complex numbers, series, the Cayley–Dickson tower, function spaces](#10-lazy-complex-numbers-series-the-cayleydickson-tower-function-spaces)
11. [The axioms of ℚ[i]: complete in every sense a computable system can be](#11-the-axioms-of-qi-complete-in-every-sense-a-computable-system-can-be)
12. [Programs: `main` and the output notations](#12-programs-main-and-the-output-notations)
13. [Predicates: relations simplified to their simplest form](#13-predicates-relations-simplified-to-their-simplest-form)
14. [Standard library reference](#14-standard-library-reference)
15. [Worked examples](#15-worked-examples)
16. [Implementation and tests](#16-implementation-and-tests)
17. [Status, limits and roadmap](#17-status-limits-and-roadmap)
18. [Extending the language](#18-extending-the-language)
19. [FAQ](#19-faq) · [Glossary](#20-glossary) · [Repository layout](#21-repository-layout) · [License](#22-license)

---

## 1. At a glance

| Property | What it means in i-1 |
|:--|:--|
| **Foundation** | **ℤ[i], the Gaussian integers**, as binary strings: the digits of a Gaussian integer in base i − 1.  A Gaussian rational ℚ[i] is a pair (numerator, denominator) of Gaussian integers (a numeral such as `1100` is the Gaussian integer 2, held as a rational with denominator 1), a real or complex number is a stream of such rationals.  An ordered pair of integers is a Gaussian integer, **a + b·i := (a, b)**. |
| **Types are decoding keys** | A type tells how to read a binary string and never changes the string: `110101` is 1 − 6i in ℤ[i], the pair (1, −6) in ℤ², the fraction −1/6; a pair of strings, `("Hello, world!", "Welcome to i - 1!")`, is one binary string read as `String²` ([§6.6](#66-types-are-decoding-keys)). |
| **Number system** | Base **i − 1**, digits `0` and `1`.  Every Gaussian integer has a unique finite expansion, so ℤ[i] needs no sign and no separate real/imaginary parts.  `11` is *i*, `1100` is 2, `11101` is −1. |
| **ℝ[i] is lazy** | A real or complex number is an infinite stream of ℚ[i] elements (its approximants).  Nothing is computed until an element is demanded. |
| **Dimension only goes up** | Cayley–Dickson trees: complex numbers → quaternions → octonions → sedenions → … of unbounded depth.  Lower-depth values are lifted by *a ↦ (a, 0)*; no operation ever trims a tree, so a zero of depth 3 stays a zero of depth 3. |
| **Infinite dimensions** | `𝔉 A` is the algebra of all functions ℚ[i] → A, with pointwise operations; inner products are streams of partial sums. |
| **Classes first** | Every value, variant and function must be declared with its class (domain → codomain) before it is defined.  Classes form a lattice (ℕ ⊆ ℤ ⊆ ℚ ⊆ ℚ[i] …) with a few explicit widening coercions. |
| **Everything from ℚ[i]** | Booleans are digits, `Char` is a natural number (a code point), `String` is a list of `Char`, lists and pairs are lambda terms over numerals. |
| **Three notations** | **bin** (only `1 0 . space ( ) newline`), **spec** (unicode glyphs), **hum** (ASCII / TeX-like).  Two system documents map between them: *doc 1* `[spec sbl] := [bin sbl]`, *doc 2* `[hum sbl] := [spec sbl] or [bin sbl]`. |
| **Evaluation** | Lazy (call-by-need).  Infinite streams and function spaces are ordinary values. |
| **ℚ[i] is complete** | Division is total (x ÷ 0 = 0), every closed equation and inequation is decided, every element has one canonical form `⊜` — the axioms are audited in [§11](#11-the-axioms-of-qi-complete-in-every-sense-a-computable-system-can-be) and `docs/axioms.md`. |
| **Programs** | `main` is the entry point: `i1.py run x.hum.imo` (or just `i1.py x.hum.imo`).  A `String` main is its own output; any other value is printed as a normal-form term in bin, spec or hum — by default in the notation `main` is written in. |
| **Predicates** | A statement with a predicate is simplified when it is evaluated: `true` if it holds for every value of its unknowns, `false` if for none, otherwise its simplest equivalent form (`x^2 + 1 == 0` over ℂ is `x == -i or x == i`, over ℝ it is `false`).  Closed relations on ℝ[i] are decided from the definitions (expansion, ring normal forms, isomorphism of series, certified bounds) — true, false, or *undetermined*, never a guess. |
| **Mathematical library** | More than 400 named functions in the language itself: complex functions (Γ, ζ, erf, Bessel J and I, elliptic integrals, all inverse trigonometric and hyperbolic functions with cmath's branch cuts …), linear algebra, number theory, polynomials over ℚ and GF(p), groups, rings and Gröbner bases, finite and number fields, Galois groups of low-degree polynomials ([§14](#14-standard-library-reference)). |
| **One system** | ⊤/⊥ are the digits 1/0: a truth value is a number (`1 + true` is 2), and `+`, `or`, `max`, `union` are one family of operations. |

### The target, π + e·i, in all three notations

The three programs below are the *same program*: the human text is compiled to the spec text by the class checker (overloads are resolved by class), and the spec text is re-spelled into the binary text by doc 1.  All three are loaded by the test-suite and produce identical streams.

**human** — `examples/target.hum.imo`

```text
{{FILE:examples/target.hum.imo}}```

**spec** — `examples/target.spec.imo`  (class declaration first, then the definition)

```text
{{FILE:examples/target.spec.imo}}```

**bin** — `examples/target.bin.imo`  (the whole file uses only `1 0 . space ( )` and newline; `.B.` is a symbol, `.` = `↦`, `..` = `≔`, `...` = `∶`, a bare bit string is a ℚ[i] numeral)

```text
{{FILE:examples/target.bin.imo}}```

The binary program refers to the prelude (the standard library), which itself ships in all-binary form as `lib/prelude.bin.imo` (**{{PRELUDE_BIN_CHARS}} characters**).  The symbol table for the three program-local names is `examples/target.sbl`.

---

## 2. Quick start

The commands below run Pymo, the Python core, which needs Python 3.11 or newer (the test-suites pass on 3.11 and 3.13, the example commands also ran on 3.12; older versions are untested) and nothing else: there is nothing to install, it uses only the standard library.  Haskimo, the Haskell core, needs GHC instead and no Python at all, and takes the same commands ([§2.1](#21-three-interpreters-pymo-haskimo-and-rustimo)).

```bash
# run a program: evaluate its main and print it
python3 pymo/i1.py examples/main.hum.imo
python3 pymo/i1.py examples/prove.hum.imo                  # relations on ℝ[i], decided by logic
python3 pymo/i1.py examples/predicates.hum.imo              # statements with unknowns, simplified to their simplest form
python3 pymo/i1.py examples/decode.hum.imo                  # one binary string, several decoding keys (about 40 s)
python3 pymo/i1.py run examples/main.hum.imo --out spec     # the output notation: bin | spec | hum

# check a program: load the prelude + your file, run the class checker
python3 pymo/i1.py check     examples/target.hum.imo

# evaluate one symbol: stream element 14 of  z = π + e·i
python3 pymo/i1.py eval      examples/target.hum.imo z 14
#   element 14 of the stream:  457311809536/145568097675 + 47395032961/17435658240 i   (≈ 3.14156615934 + 2.71828182846 i)

# re-spell a program in another notation
python3 pymo/i1.py translate examples/target.hum.imo --to spec
python3 pymo/i1.py translate examples/target.hum.imo --to bin

# run the test-suites (each prints PASS/FAIL lines; together a few minutes).  Nineteen of them also run on Haskimo and Rustimo: add  --core haskimo  or  --core rustimo
# (all of them on every core they support:  python3 tests/run_suites.py)
python3 tests/test_layers.py       # notations, docs, class checker, Char/String, order, quantifiers, analysis
python3 tests/test_algebra.py      # ℤ[i], ℚ[i], Cayley–Dickson tower, lazy ℝ[i], function spaces
python3 tests/test_axioms.py       # the axiom audit of ℚ[i]: field, meadow, order, conjugation, canonical forms
python3 tests/test_classes.py      # the class system: lattice, overload sets, human operators (all three cores agree)
python3 tests/test_lists.py        # lists: folds, scans, sorting, searching, combinatorics (against Python)
python3 tests/test_strings.py      # characters and strings: case, splitting, bases, Roman numerals, edit distance
python3 tests/test_dict.py         # dictionaries, sets, multisets, heaps, queues (tries over the digits)
python3 tests/test_theory.py       # theories: packages of axioms, and the decision of statements (true / false / undetermined)
python3 tests/test_library.py      # the library: arithmetic, lists, analysis, linear algebra, sets (from the human notation)
python3 tests/test_output.py       # main, the three output notations, round trips
python3 tests/test_prove.py       # predicates: relations on ℝ[i] decided by logic
python3 tests/test_predicates.py   # statements: unknowns, the class Prop, the printer in three notations
python3 tests/test_solve.py        # the simplifier: simplest forms for every domain, against exact arithmetic
python3 tests/test_poly.py         # polynomials: gcd, resultants, Sturm, real roots, factorisation over ℚ
python3 tests/test_numtheory.py    # number theory: primes, factoring, congruences, arithmetic functions, partitions
python3 tests/test_group.py        # permutations, finite groups, subgroups, actions, Burnside
python3 tests/test_linalg.py       # exact linear algebra over ℚ[i]
python3 tests/test_complex.py      # functions of a complex variable (about 25 minutes; --first: 40 seconds)
python3 tests/test_ring.py         # Z/n, ideals, quotient rings, multivariate polynomials, Gröbner bases
python3 tests/test_field.py        # GF(p), GF(p^n), number fields, algebraic numbers
python3 tests/test_galois.py       # Galois groups of low-degree polynomials, cyclotomy, Frobenius
python3 tests/test_codec.py        # types as decoding keys: 110101 as 1 - 6i, (1, -6), -1/6; pairs of strings
python3 tests/test_readme.py       # the hand-written numbers and messages of this README
```

`eval` (an inspection command of the interpreters) prints a value according to its **declared class**: a ℚ[i] value as an exact fraction, a stream element (`N` defaults to 10), a Cayley–Dickson tree as `⟨a, b⟩`, a `String` as text, a `Bool` as `true` / `false`.

Files choose their notation by extension — `x.hum.imo` human, `x.bin.imo` binary, `x.imo` / `x.spec.imo` spec — or by `@hum`, `@spec`, `@bin` section headers inside one file (see [§4.5](#45-files-extensions-and-mixing-notations)).

### 2.1 Three interpreters: Pymo, Haskimo and Rustimo

i-1 has three **interpreters**: a program is read, class-checked and evaluated every time it runs ([§9](#9-evaluation-model) says what the evaluator does inside); a fourth program, **Compimo** ([§2.2](#22-compimo-the-compiler)), translates a program to C and compiles it.  The language is defined by what the repository **shares**: the `.imo` files (the standard library `lib/`, the examples, and the two system documents `docs/doc1.sbl` and `docs/doc2.sbl`), the `.md` files (this README and `docs/`) and the test suite (`tests/`).  Everything else is one of three **parallel cores**, three interpreters of that one specification, which read the same files and print the same bytes.  They are peers: none is the reference, and a core is right when the shared test suite passes on it.

```text
lib/  examples/  docs/*.sbl               the language: the .imo files and the system documents                          shared
README.md  readme/  docs/*.md             the documentation                                                              shared
tests/                                    the test suite (tests/conformance and 19 of the 23 suites run on all cores)    shared
pymo/                                     Pymo, the Python core, with the scripts that write the generated files         parallel
haskimo/                                  Haskimo, the Haskell core                                                      parallel
rustimo/                                  Rustimo, the Rust core                                                         parallel
i1  install.sh  Makefile  haskimo.cabal   choose, install and build any of the cores
```

| | **Pymo** | **Haskimo** | **Rustimo** |
|:--|:--|:--|:--|
| written in | Python | Haskell | Rust |
| source | `pymo/` | `haskimo/`, package `haskimo.cabal` | `rustimo/`, package `rustimo/Cargo.toml` |
| needs | Python 3.11+, standard library only | GHC 9.x and its boot libraries only (`base`, `containers`, `mtl`, `template-haskell`, `directory`); nothing from Hackage | `cargo` and `rustc` 1.70+; no crates at all (the standard library only) |
| program | `python3 pymo/i1.py` (installed as `pymo`) | `haskimo`: one self-contained executable — the standard library is compiled into it, so it runs from any directory and needs no Python | `rustimo`: one self-contained executable of about 2 MB, the standard library compiled into it, no Python and no runtime |
| evaluator | lambda terms compiled to Python | closures built with Haskell's own laziness (a generational garbage collector) | flat closures on an explicit stack with update frames (reference counting); depth of recursion limited by memory only |
| commands | `run` `check` `translate` `eval` `text` | the same commands, options and output | the same commands, options and output |

Install any of them or all, then choose one per command:

```bash
./install.sh                           # every interpreter whose compiler is found (python3, ghc, cargo), into ~/.local
./install.sh --prefix /usr/local       # elsewhere (PREFIX/bin/{i1,pymo,haskimo,rustimo}, PREFIX/share/i1/)
./install.sh --pymo-only               # or --haskimo-only, or --rustimo-only
./install.sh --default haskimo         # what `i1` uses when you do not say: pymo | haskimo | rustimo | auto (auto = rustimo, else haskimo, else pymo)
./install.sh --uninstall

i1 run examples/main.hum.imo                   # the default interpreter
i1 --impl pymo    run examples/main.hum.imo    # Pymo     (also  I1_IMPL=pymo i1 run …     or   pymo run …)
i1 --impl haskimo run examples/main.hum.imo    # Haskimo  (also  I1_IMPL=haskimo i1 run …  or   haskimo run …)
i1 --impl rustimo run examples/main.hum.imo    # Rustimo  (also  I1_IMPL=rustimo i1 run …  or   rustimo run …)
i1 --impl all     run examples/main.hum.imo    # all of them at the same time: the output is printed once if they agree; if not, exit status 3 and a diff
```

`py`, `hs` and `rs` are accepted for `pymo`, `haskimo` and `rustimo` (`--impl rs`, `--default py`).  From a checkout, without installing: `make` builds `build/haskimo` and `build/rustimo` (`make rustimo`, or `./rustimo/build.sh`, for the Rust one alone), and `./i1 --impl rustimo run examples/main.hum.imo` works in place.  `cabal install exe:haskimo` installs Haskimo alone.  `i1` takes the commands and options of `pymo/i1.py` unchanged.  How the three interpreters are kept identical — one interpreter-neutral test that all of them must pass, `tests/conformance/run.py` — is described in [§16.5](#165-the-three-cores-and-the-shared-test-suite).


### 2.2 Compimo, the compiler

**Compimo** is the compiled version of i-1 (`compimo/`, Rust and C, no Python; [`docs/compimo.md`](docs/compimo.md)).  It uses the front end of Rustimo (readers, class checker, printer), translates the
program to C, compiles it together with the prelude (compiled once and cached) and a small run-time system, and runs it; it prints the same bytes as the interpreters (all the cases of
`tests/conformance`).  Its speed comes from three things: constructors and pattern matches become data objects and switches, small functions are inlined, and the arithmetic on digit strings —
almost all that i-1 does — is done on arrays of digits by native versions that return *the same lists* as the definitions (`compimo selftest` checks it on random strings).

```bash
make compimo                       # needs cargo, a C compiler and libgc-dev; build/compimo
build/compimo prelude              # once: compile the prelude (about 3 minutes)
build/compimo run examples/prove.hum.imo
i1 --impl compimo run examples/prove.hum.imo       # it is chosen by name only (not part of auto, both or all)
```

---

## 3. Design principles

1. **One foundation, everything else defined.**  The Gaussian integers ℤ[i] (binary strings in base i − 1) are the only native domain.  ℚ[i] (pairs of Gaussian integers), ℝ[i] (streams of them), ℕ, ℤ, ℚ, ℝ, `Char`, `String`, lists, pairs, algebras and function spaces are *classes over* ℤ[i], not additional primitives; a class is a decoding key for a binary string ([§6.6](#66-types-are-decoding-keys)).
2. **Base i − 1.**  Writing numbers in base i − 1 makes the Gaussian integers a free monoid on two digits.  Addition needs a carry that is itself a numeral ([§6.3](#63-addition-with-a-numeral-as-carry)); multiplication by the base is *prepending the digit 0*.
3. **Laziness instead of limits; logic instead of evaluation.**  A real number is the stream of its approximants, computed on demand.  A relation between reals — or about an unknown — is never decided by evaluating streams: it is simplified by logic, from the definitions ([§13](#13-predicates-relations-simplified-to-their-simplest-form)), and when no rule decides it the answer is *undetermined*.
4. **Dimension is monotone.**  The Cayley–Dickson construction only adds dimensions.  The only conversion between depths is the inclusion *a ↦ (a, 0)*.
5. **Declare first, then define.**  A symbol without a class declaration cannot be defined or used.  Classes are written as terms in the language itself, and the same line may be repeated to give a symbol several classes (an *overload set*).
6. **Three notations, one meaning.**  Notation is a *spelling layer*.  Doc 1 and doc 2 are plain data files; translators between notations are mechanical and are tested for exact round trips.
7. **Keep the systems apart.**  Mixing notations in one section of code does not break anything — the reader supports `@bin` / `@spec` / `@hum` section headers — but it is **strongly discouraged**: keep one notation per file and let the translators produce the others.
8. **Honest scope.**  The prelude's class signatures are *trusted declarations* (they are tested, not proved).  User programs are fully checked against them.  Limits are listed in [§17](#17-status-limits-and-roadmap), not hidden.
9. **Purity at level i − 1.**  Everything is a function and every computation goes through the base-(i−1) digits: arithmetic, gcd, decimal text, the canonical forms printed as output, and the proofs of the predicates all run *in the language* — the all-binary programs give the same answers.  The host only reads digits back (the isomorphism digit string ↔ Gaussian integer) and spells them.
10. **One system.**  The digits are the truth values, so a relation's answer is a number, and the joins of the different structures — `+` on truth values, `or`, `max`, `union` — are one operation in different places ([§13.5](#135-one-system)).

### 2.3 More interpreters: OCamimo, Schimo, Cimo and Rimo

**OCamimo** (`ocamimo/`, OCaml, standard library only; [`docs/ocamimo.md`](docs/ocamimo.md)) is a fourth interpreter, a peer of Pymo, Haskimo and Rustimo: it reads the same files and prints the same
bytes for every command (`python3 tests/conformance/run.py --impl ocamimo`: all the cases conform).  Build it with `make ocamimo` and choose it by name, `./i1 --impl ocamimo run program.hum.imo`; it is not part of `auto`, `both` or `all`.

**Schimo** (`schimo/`, Racket, a Scheme; [`docs/schimo.md`](docs/schimo.md)) is a fifth one: `make schimo`, `./i1 --impl schimo run program.hum.imo`, and all the cases conform too.

**Cimo** (`cimo/`, C with the Boehm collector; [`docs/cimo.md`](docs/cimo.md)) is a sixth one: `make cimo`, `./i1 --impl cimo run program.hum.imo`, and all the cases conform too.  (It interprets; the compiler of i-1 to C is Compimo, §2.2.)

**Rimo** (`rimo/`, R with the package gmp; [`docs/rimo.md`](docs/rimo.md)) is a seventh one: `make rimo`, `./i1 --impl rimo run program.hum.imo`.  It is two to three orders of magnitude slower than Rustimo (R is not made for this), so it
was run on the conformance cases that are not slow, with one in twelve of the library sweep (726 cases, all conform), and on the self-checking `.imo` tests of `tests/imo/small` (33 files, 4057 checks, all pass; [`docs/rimo.md`](docs/rimo.md) says what was run and how long it takes).
