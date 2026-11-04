# Writing prelude code for i-1

This is the working guide for adding functions to the standard library (`lib/*.imo`).  Read the README sections 4–10 first for
the language itself; this page is about the practice: the encodings, the idioms, the pitfalls, and how to test.

## 1. The shape of a library file

A library file is **spec notation**, loaded **trusted**: declarations are recorded, bodies are *not* class-checked (they are untyped
lambda terms).  Every symbol is declared before it is defined:

```text
⍝ lib/poly.imo — spec notation — trusted prelude, part 13: polynomials …      (first line: the title used by pymo/mkref.py)
polyadd ∶ 𝔏 ℚ[i] → 𝔏 ℚ[i] → 𝔏 ℚ[i]      ⍝ sum of two polynomials
polyadd ξ η ≔ (…)
```

* `name ∶ class` declares; several declaration lines for one name make an **overload set** (the checker picks by the classes of
  the arguments).  A trailing `⍝ text` on the *first* declaration line of a public symbol is its description in the generated
  reference (`pymo/mkref.py`); write one for every public function.
* `name x y ≔ body` defines (`f x ≔ t` is `f ≔ (x ↦ t)`); definitions are global, may be recursive and mutually recursive, and are
  evaluated by need.
* `⍝` starts a comment to the end of the line.
* Names: any run of characters other than space, `( ) 0 1 . ' "` — so digits 2–9, `_`, `^`, `′`, sub/superscripts are allowed.
  **A name cannot contain 0 or 1** (they are digits of numerals).  Binder names (`ξ η ζ θ ι κ λ μ ν ξ ρ σ τ υ φ χ ψ ω …`) are local.
* Classes used in a declaration must already be declared (files load in the order of `imo.PRELUDE`).
* Facts: `(⊆ A B)` subclass, `(≣ A B)` class equation (A is another name for B), `(↪ f)` f is a canonical coercion (inserted by the
  checker where needed; keep these rare — every coercion is a candidate at every argument position).

## 2. Encodings (everything is a function)

| notion | how to build | how to take apart |
|:--|:--|:--|
| Boolean / digit | `⊤` = λx y. x, `⊥` = λx y. y | `(b then else)` — lazy: only the chosen branch is evaluated |
| pair | `(⊗ a b)` | `(◀ p)`, `(▶ p)`, or `(p (a b ↦ …))` |
| list (Scott) | `(∷ h t)`, empty `⊥` (also written `⊘`) | `(xs (h t ↦ cons-case) nil-case)` |
| ℤ[i] digits `𝔇` | a list of digits, least significant first, `⊥` is 0 | `⊞ᶻ ⊟ᶻ ⊠ᶻ ⊖ᶻ ∅ᶻ ⋚ʳ` … (lib/number.imo, lib/arith.imo) |
| ℚ[i] number | `(⊗ numerator-digits denominator-digits)`; a numeral is read as such a pair | `(◀ x)` numerator digits, `(▶ x)` denominator digits |
| 𝔒 comparison | `⋖ ≖ ⋗` = λx y z. x / y / z | `(o if-less if-same if-greater)` |
| stream `𝔖 α` | an infinite list | as a list |
| let | `((θ ↦ body) value)` — value is computed once (call by need) | |

An `if` on a Boolean whose branches are numbers is simply `((≐ x 0) a b)`.  Short-circuit "and"/"or" are `(∧ a b)`, `(∨ a b)`
(lazy in the second argument).  Bounded quantifiers: `(∀ₗ p xs)`, `(∃ₗ p xs)`.

## 3. Numerals — the most common mistake

In spec (and bin) a bare digit string is **always base i − 1**: `10` is −1 + i, `1100` is 2, `11` is i, `11101` is −1.  Use
`pymo/numeral.py` to write numbers and to read them back:

```text
$ python3 pymo/numeral.py 0 1 2 3 4 5 6 7 8 9 10 -1 -2 i -i 1/2 2+3i 100
$ python3 pymo/numeral.py --read 1100 0.1 1.11
```

| value | numeral | value | numeral | value | numeral |
|--:|:--|--:|:--|--:|:--|
| 0 | `0` | 6 | `111011100` | −1 | `11101` |
| 1 | `1` | 7 | `111011101` | −2 | `11100` |
| 2 | `1100` | 8 | `111000000` | −3 | `10001` |
| 3 | `1101` | 9 | `111000001` | i | `11` |
| 4 | `111010000` | 10 | `111001100` | −i | `111` |
| 5 | `111010001` | 16 | `100000000` | 1/2 | `1.11` or `(÷ 1 1100)` |

A numeral with a radix point is a fraction over a power of the base (`1.11` = 1/2).  Inside a definition, write a fraction as
`(÷ a b)`.  In the **human** notation numerals are decimal (`2`, `1/2`, `0.75`).

## 4. Numbers: which operations to use

* **ℚ[i]** (`lib/number.imo`, `lib/arith.imo`): `⊞ ⊟ ⊠ ⊖ ÷ ∗` (conjugate), `≐` (equality), `⩾ ⩽ ≻ ≺ ⋚` (order, on real values),
  `⊜` canonical form z/m, `numer denom`, `ℜ ℑ 𝒩` (re, im, norm), `⌊ ⌈ round div mod abs sgn max min`, `^` (integer powers),
  `gcd lcm quo rem` (ℤ and ℤ[i]), `fact choose isqrt`.  Division is total: `x ÷ 0 = 0`, `x div 0 = 0`, `x mod 0 = x`.
* **Fractions are not reduced** by `⊞ ⊠ ÷`: numerators and denominators grow.  In a loop that iterates arithmetic, apply `⊜` now and
  then (it costs a gcd), or keep integers as integers.  Equality `≐` is cross-multiplication and needs no reduction.
* Integers are ℚ[i] values with denominator 1 *or any other denominator dividing the numerator*; never test integrality by looking at
  the denominator — use `(≐ (denom x) 1)` after `⊜`, or arithmetic.
* **Digit-level ℤ[i]** (`𝔇`): `⊞ᶻ ⊟ᶻ ⊠ᶻ ⊖ᶻ` (add, subtract, multiply, negate), `∅ᶻ` (is zero), `⋚ʳ` (sign of the real part),
  `÷ᶻ` (exact division), `⫽ᶻ` (natural division with remainder), `gcdᶻ`, `𝕓` (·(i−1)), `⌃ ⌄` (head digit, tail).  Use them when you
  work with integers inside an algorithm and want to avoid fraction overhead; `(◀ x)` is the digit string of an integral numeral x
  written with denominator 1, `(↓ᶻ x)` the Gaussian integer of any integral value.
* **Lazy reals ℝ / ℝ[i]** are streams of ℚ[i] approximants (`𝔖 ℚ[i]`).  `⊕ ⊛ ⊖ᴿ ⊟ᴿ ∗ᴿ ÷ᴿ ^ᴿ` are pointwise; `⇡ x` is the constant
  stream; `Σ t₀ ρ` is the exact series with terms t₀, t₀ρ(1), t₀ρ(1)ρ(2), …; `⟐ f x` extends f ∶ ℚ[i] → ℝ[i] to a lazy argument (element
  n of f(xₙ)).  A function returning ℝ[i] should converge, ideally with a stated modulus ("element n is within 2⁻ⁿ").

## 5. Lists and higher-order helpers (lib/logic.imo, lib/list.imo, lib/bounded.imo)

`⫶` map, `⫴` zip-with, `foldr foldl filter take drop nth last reverse concat ⧺ zip replicate iterate tabulate sumof prodof elem
upto sort eqlist`, `ℓ` length, `⍳ n` = 0, 1, …, n − 1, `hd` head, `⌄` tail, `∅` is-empty, `∀ₗ ∃ₗ`.  Matrices are lists of rows
(`lib/linalg.imo`).

## 6. Performance

Pymo costs roughly **10 µs per step on one digit** (Haskimo several times less); a ℚ[i] multiplication of two n-digit numbers is O(n²) digit
steps.  Practical consequences:

* test with small inputs (two- or three-digit numbers, matrices up to 4×4, polynomials up to degree 6, groups up to order ~24);
* avoid exponential algorithms unless the input is tiny, and say so in the description;
* share sub-results with a let `((θ ↦ …) value)` instead of recomputing;
* streams: element n should cost polynomially in n.

## 7. Human names (doc 2)

Every public function gets a human (ASCII) name in `docs/doc2.sbl`, written **between the markers of your module**:

```text
⍝ ==== <poly> polynomials (lib/poly.imo) — lines of this module go between the two markers
polyadd := polyadd ; value
deg := deg ; value
⍝ ==== </poly>
```

`hum := spec1 | spec2 ; value` makes an overload set.  A human name must be a new identifier (`[A-Za-z_][A-Za-z_0-9]*`); check with
`grep -n '^name :=' docs/doc2.sbl`.  Infix operators are `; infixl P` / `infixr P` / `infix P`, prefix `; prefix P`.

## 8. Testing

A suite is a plain script `tests/test_<module>.py` using `tests/harness.py`.  Write the test program in the **human** notation (so
doc 2, overload resolution and the class checker are tested too), evaluate it, decode the values, and compare with an independent
Python computation (standard library only: `fractions`, `math`, `cmath`, `itertools`):

```python
from harness import *
rep = Report()
SRC = r'''
a1 in \Q := polyeval([1, 0, 1], i)
'''
def main():
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'poly.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("the test program passes the class checker", not errs, str(errs[:2]))
    if errs: return rep.done()
    P.build(); E = Env(P)
    q = lambda n: E.dq(E.V(P.hum.spec_name(n)))          # a ℚ[i] value -> refmath.Q (exact)
    rep("polyeval: x² + 1 at i is 0", q('a1') == R.Q(0))
    return rep.done()
sys.exit(0 if run_big(main) else 1)
```

Decoders: `E.dq(v)` (ℚ[i] → `R.Q(re, im)` with `Fraction` parts), `E.lst(v, dec)` (list), `E.b(v)` (Boolean), `E.nth(v, n)` (stream
element), `E.ord3(v)` (𝔒 → −1/0/1).  Builders: `E.q(Fraction or R.Q)`, `E.call('symbol', arg, …)`.  Test edge cases (zero, empty
lists, negative numbers, non-real values), not only the happy path.

## 9. Generated files

After changing the prelude:

```text
python3 pymo/mkdoc1.py      # doc 1 (append-only: new symbols get new codes)
python3 pymo/mkbin.py       # lib/prelude.bin.imo and the example .bin.imo / .sbl files
python3 pymo/mkref.py       # docs/reference.generated.md, docs/doc2.generated.md
python3 tests/test_layers.py # doc 1 covers the prelude; spec → bin → spec round trip
```

`pymo/mkprove.py`, `pymo/mkcarry.py`, `pymo/mkdec.py` write generated blocks into `lib/prove.imo`, `lib/number.imo`,
`lib/text.imo`; run them with `--check` if you touched those files.

## 10. Three parallel cores: after you change the library or the language

The language has three parallel cores, interpreters of one specification: Pymo, written in Python (`pymo/`), Haskimo, written in Haskell
(`haskimo/`), and Rustimo, written in Rust (`rustimo/`).  What they share is the language itself: the `.imo` files (`lib/`, `examples/`),
the system documents (`docs/doc1.sbl`, `docs/doc2.sbl`), the `.md` documents and the test suite (`tests/`).  No core is the reference
(README §2.1, §16.5).

* **A change to the library or the documents** needs no change to any core.  The Haskimo and Rustimo executables carry a copy of these
  files made when they are built, so rebuild them (`make`, or `./haskimo/build.sh` and `./rustimo/build.sh`) before you run them.  Then
  add what you wrote to the shared tests: a function with a human name and a signature the generator can write literals for is picked up
  by `python3 pymo/mkconformance.py` (it rewrites `tests/conformance/programs/lib/`; run `python3 pymo/mkconformance.py --cases`
  afterwards for the list of cases), and a program of your own goes into `tests/conformance/programs/misc/` (and `--cases`).  Record the
  expected output with `python3 tests/conformance/run.py --bless --filter <the new cases>`: it runs all the cores and records only what
  they all print.
* **A change to the language itself** (a reader, the checker, the evaluator, the printer) is made in all the cores, in the modules that
  correspond to each other (README §16.5).  Change the cases that should change (`--bless-from pymo`, `--bless-from haskimo` or
  `--bless-from rustimo` records the output of one core while the others have not followed yet), and the other cores are changed until
  `python3 tests/conformance/run.py` passes on all of them.  A case on which the cores disagree is a bug in at least one of them, settled
  by the documents and the tests (with three cores, usually the one that disagrees with the other two).
* The test suites are shared too: `python3 tests/run_suites.py` runs every suite on every core it supports, and a suite that uses only
  `imo.Program`, `Env` and the decoders of `tests/harness.py` runs on Haskimo and Rustimo with `--core haskimo` or `--core rustimo` (README §16.3).  A new library suite
  should be written that way; a suite that needs the Python API of Pymo calls `pymo_only(...)` first.
* `python3 tests/conformance/run.py` runs everything on every core that is built (`--impl pymo,rustimo` picks); `--fast` skips the slow cases; `-v --filter X` shows the differences.
