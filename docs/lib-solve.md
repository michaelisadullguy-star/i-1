# The simplifier (`lib/solve.imo`)

`simplify′ ε φ` takes the code φ of a statement and the table ε of definitions and returns the code of the **simplest form** of the
statement: `true` if it holds for every value of its unknowns, `false` if it holds for none, otherwise the simplest equivalent statement.
The contract, the unknowns, the class `Prop` and the printing rules are in [`docs/predicates.md`](predicates.md); this page is about the
engine itself.  It is written in spec notation and runs in the language, on base-(i − 1) numerals: a truth value is the digit 1 or 0, a
polynomial is a list of numbers, every decision (a sign, a divisibility, which interval contains a root) is a digit selecting a branch.
Helper names end in `_sv`.  It builds on `lib/poly.imo` (factorisation over ℚ, Sturm sequences, root isolation, exact signs) and on the
older exact prover of `lib/prove.imo` for closed relations.

## Stages

1. **Expansion.**  A symbol that is defined and mentions an unknown is replaced by its definition (bounded fuel), λ-applications are
   β-reduced, `prop` / `decide` are transparent.
2. **Terms to polynomials.**  A term of ℚ[i] arithmetic (`+ − · ÷ ^ conj re im √`) becomes a multivariate polynomial: a list of terms
   `(c, e)` in graded-lexicographic order, `c ≠ 0` canonical, `e` the exponent vector; equal polynomials are equal lists.  A division by
   an unknown, a non-integer power, an unknown inside a function that is not polynomial (`exp(x)`) makes the term *not polynomial*; the
   atom is then kept as it is and the relation stays in the answer.
3. **Formulas.**  A formula is a constant, an atom `p rel 0`, or `and` / `or`; `not` is pushed onto the relations, `implies` / `iff`
   expanded.  Atoms with no unknown are decided by the closed prover (`fo` of `lib/prove.imo`).
4. **One real unknown (ℝ, ℚ, ℤ, ℕ).**  Every atom is a polynomial in the variable.  It is **factored over ℚ** (`polyfactor`: square-free
   decomposition, factorisation modulo primes, Hensel lifting, recombination), the real roots of all the factors are **isolated together**
   by Sturm sequences, and the **exact sign of every factor** is found at every root (a root of another factor: `signat`, an exact test
   through gcd and bisection) and on every interval between them (to the right of its own simple root: the sign of the derivative there;
   left of all roots: (−1)^degree).  The formula is evaluated on each of these *cells*; adjacent cells with the same value are merged, and
   the cells are written as points and intervals with exact endpoints (`u + v*sqrt(d)` for a quadratic factor, `root(p, k)` otherwise).
   Over ℚ an irrational root is not a point of the domain: the intervals on its two sides are joined when the statement holds on both.
   Over ℤ and ℕ the real solution is turned into integer intervals by floor and ceiling (`refine` of `lib/poly.imo` to the width needed).
5. **One complex unknown (ℂ, ℚ(i), ℤ[i]).**  Only (in)equalities make sense.  The roots of the atoms are grouped into *blocks*: monic
   polynomials that are linear (a Gaussian rational root), quadratic without Gaussian root, or of higher degree (kept symbolic).  An atom
   is true on all roots of a block or on none (the block divides the polynomial), so the formula is evaluated once per block and once for
   a generic point; over ℚ(i) and ℤ[i] only the Gaussian rational roots count.
6. **Several unknowns.**  Each atom is first rewritten: an equality with complex coefficients over real unknowns splits into its real and
   imaginary parts; a complex unknown under `conj`, `re` or `im` is split into two real unknowns; a **sum of even powers** (all
   non-constant monomials of even degree in every unknown, coefficients of one sign) is bounded by its constant term, which decides it
   (`x² + y² + 1 > 0` is `true`, `x² + y² == 0` is `x == 0 and y == 0`).  Then the conjuncts that are **affine equations** are solved by
   Gauss–Jordan elimination (the pivot unknowns are substituted into the other conjuncts, which may become affine in turn) and the
   conjuncts that are left about one unknown are solved by stage 4 or 5.  What remains is printed as relations `P rel c`, with P primitive,
   leading coefficient positive, the constant on the right.
7. **Output.**  A code built from `⊤ ⊥ ∧ ∨ ¬`, the relations, and terms (see `docs/predicates.md` §5); the printer of `pymo/output.py` spells it.

Everything the engine decides is decided exactly: no step approximates a number.

## Limits

* Relations that are not polynomial in the unknown stay (`exp(x) == 1`, `sin(x) lt x`); so do systems of non-linear polynomial relations in
  several unknowns (the Gröbner machinery of `lib/ring.imo` is a library, not yet part of the simplifier).
* Non-real roots of an irreducible factor of degree ≥ 3 are not written out: the equation `p(x) == 0` stays.
* Cost: a statement with one unknown and polynomials of degree ≤ 6 takes a fraction of a second to a few seconds (factorisation and
  isolation dominate); the example program of the README (nine statements) prints in about four seconds.

## Tests

`tests/test_solve.py` (12 checks): hand-checked answers for every domain and every solver (including the four examples of the
specification: `x^2 > 7 and x^3 < 27` is `x < −√7 or √7 < x < 3`, `z·conj(z) + 1 == 0` is `false`, `x^2 + 1 == 0` over ℝ is `false`,
`y^2 + 1 == 0` over ℂ is `y == −i or y == i`), the several-unknown rewrites, and a **randomized check against exact arithmetic**:
random polynomial statements (degree ≤ 4, one real unknown, `and` / `or`) are simplified, and the answer and the original statement are
evaluated with exact rational arithmetic (roots to 40 digits) at 281 sample points each.  `tests/test_predicates.py` (55 checks) tests the
compiler side: unknowns, `Prop`, quotation, coercions, the printer in hum, spec and bin.
