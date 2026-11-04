# The axioms of ℚ[i]: an audit

This document answers the question *"is the axiomatic system on ℚ[i] complete?"* for the prelude of i-1 (`lib/logic.imo`,
`lib/number.imo`, `lib/arith.imo`).  Every law stated here is evaluated **in the language** by `tests/test_axioms.py`; the
proofs are on paper, and §5 says exactly which claims are proved and which are tested.

## 1. Verdict

"Complete" has four reasonable meanings.  For the prelude of i-1 (after the fixes of §3):

| sense | question | answer |
|:--|:--|:--|
| **totality** | does every closed term denote an element? | **yes** — division is total (x ÷ 0 = 0), every operation terminates (§4) |
| **closed decidability** | is every closed atomic sentence `s ≐ t` (ℚ[i]), `s ⩾ t` (ℚ) decided? | **yes** — by evaluation, in time polynomial in the number of digits (Theorem 2) |
| **normal forms** | does every element have exactly one representative? | **yes** — `⊜` gives the canonical form z/m (Theorem 3) |
| **first-order completeness** | is every sentence *with quantifiers* decided? | **no, and no computable axiom system can do it** (§6) |

So the system on ℚ[i] is complete in the strongest sense that is possible for a computable system — every closed equation and
inequation is decided, and every element has a unique normal form — and §6 explains why goal 5 (deciding relations on ℝ[i] by logic: the predicates of `docs/predicates.md`) has to be a
collection of decision procedures for fragments plus a semi-decision procedure, not a single complete algorithm.

Before this audit the answer to the first three questions was **no** (§3).

## 2. The signature

| sort | spec | elements |
|:--|:--|:--|
| digit strings = ℤ[i] | `𝔇` | lists of digits 0/1, least significant first; value Σ dₖ bᵏ, b = i − 1 |
| ℚ[i] | `ℚ[i]` | pairs (p, q) of digit strings, value p/q, **q ≠ 0** |
| Booleans | `𝔹` | `⊤ = λx y. x`, `⊥ = λx y. y` |
| comparisons | `𝔒` | `⋖ ≖ ⋗` (less, equal, greater) = `λx y z. x / y / z` |

| operation | spec | on |
|:--|:--|:--|
| constants | numerals, `11` = i | ℚ[i] |
| field operations | `⊞ ⊟ ⊠ ⊖ ÷` | ℚ[i] (and ℕ ℤ ℚ ℤ[i] by declaration) |
| conjugation | `∗` | ℚ[i] |
| equality | `≐` | ℚ[i] → 𝔹 |
| order | `⋚` (three-way), `⩾ ⩽ ≻ ≺` | ℚ → ℚ → 𝔒 / 𝔹 |
| parts, norm | `ℜ ℑ 𝒩` | ℚ[i] → ℚ |
| canonical form | `⊜`, `numer`, `denom` | ℚ[i] |
| integer structure | `⌊ ⌈ round div mod gcd lcm quo rem ^ fact choose isqrt abs sgn max min` | ℤ, ℤ[i], ℚ |

## 3. Gaps found, and what was changed

| # | gap (before) | consequence | change |
|:--|:--|:--|:--|
| 1 | `÷` by a zero divisor built a pair with denominator 0 | `≐` was **not an equivalence**: 0/0 ≐ 1 and 0/0 ≐ 2, but 1 ≠ 2; every law could fail once such a pair appeared | division is **total**: x ÷ 0 = 0 (the *meadow* convention of Bergstra and Tucker); no reachable pair has denominator 0 |
| 2 | the order searched m = 0, 1, −1, 2, −2, … | time exponential in the number of digits: `4096 ⩾ 0` took 42 s, `⩾` was unusable on stream approximants | **sign automaton**: one pass over the digits (Lemma 4); `4096 ⩾ 0` takes 0.01 s |
| 3 | conjugation was z̄ = d₀ + 110·conj(z′) | quadratic: 11 s for 193 digits, more than a multiplication | z̄ = Re z − i·Im z with Re, Im read off blocks of four digits (Lemma 5): linear, 0.1 s |
| 4 | no exact division, gcd, division with remainder, Re/Im, floor | fractions could not be reduced; no canonical form, so the representation of a value was not unique | `lib/arith.imo`: Hensel division, binary gcd, base-4 long division, Gaussian Euclid, `⊜` |
| 5 | the adder looked its carry up in a 10-entry table by comparing digit lists | correct but slow | the table is compiled into a decision tree on ≤ 4 digits, generated from first principles by `pymo/mkcarry.py` |
| 6 | subtraction = addition of the negation, negation = multiplication by 11101 | 5 additions per subtraction | a serial **subtractor** with its own numeral carry (47 carries), one pass |

## 4. Statements and proofs

Throughout, b = i − 1, N(z) = z z̄ = |z|², and digit strings are least significant digit first.

**Lemma 1 (expansions; Penney 1965, Knuth TAOCP vol. 2 §4.1).**  Every Gaussian integer z has exactly one expansion
z = Σₖ dₖ bᵏ with dₖ ∈ {0, 1} and finitely many dₖ = 1.
*Proof.*  ℤ[i]/(b) has two elements (N(b) = 2), and z ≡ x + y (mod b) for z = x + yi, so d₀ ≡ x + y (mod 2) is forced, and
z′ = (z − d₀)/b is a Gaussian integer with N(z′) = N(z − d₀)/2 ≤ (√N(z) + 1)²/2, which is < N(z) as soon as N(z) ≥ 6.  So the
digit sequence is unique, and the recursion reaches the finite set {N(z) ≤ 5}, all of whose 21 elements terminate (checked).
`⊡` removes trailing zeros, so `⊡` of any digit string of z *is* this expansion.  ∎

**Lemma 2 (the adder and the subtractor).**  For digit strings x, y and a carry numeral c = d + b·t,
with o = x₀ ⊕ y₀ ⊕ d:

* adder: x₀ + y₀ + d = o + 2m with m the majority; since 2 = b² + b³,
  val x + val y + val c = o + b·(val x′ + val y′ + t + m·(b + b²)), and b + b² = 110 = −1 − i;
* subtractor: x₀ − y₀ + d = o + 2s with s ∈ {−1, 0, 1}, so
  val x − val y + val c = o + b·(val x′ − val y′ + t + s·110).

So the value is invariant, the output digit is right, and the next carry is t + {0, ±110}.  The carries reachable from 0 form a
finite set — 15 numerals for the adder, 47 for the subtractor — computed by `pymo/mkcarry.py` as the closure of
c ↦ tail(c) + {0, ±110}; the decision trees in `lib/number.imo` are generated from exactly these transitions (the test-suite checks
that they are up to date).  Once both inputs are exhausted, m = s = 0 and the carry is shifted out digit by digit, so the
transducers stop.  Hence `⊞ᶻ` and `⊟ᶻ` are correct and terminate in O(length) steps.  ∎

**Lemma 3 (multiplication).**  `⊠ᶻ x (d : y′) = d·x + b·(x ⊠ᶻ y′)` is the identity x·(d + b y′) = d x + b (x y′); by induction on
the length of the second argument, `⊠ᶻ` is correct and terminates.  ∎

**Lemma 4 (the sign of Re z in one pass).**  Split the digits into blocks of four, cⱼ = d₄ⱼ + d₄ⱼ₊₁ b + d₄ⱼ₊₂ b² + d₄ⱼ₊₃ b³.
Because b⁴ = −4, z = Σ cⱼ (−4)ʲ and Re z = Σ rⱼ (−4)ʲ with rⱼ = Re cⱼ = d₄ⱼ − d₄ⱼ₊₁ + 2d₄ⱼ₊₃ ∈ {−1, …, 3}.
Let J be the largest index with r_J ≠ 0.  Then |Σ_{j<J} rⱼ(−4)ʲ| ≤ Σ_{j<J} 3·4ʲ = 4ᴶ − 1 < 4ᴶ ≤ |r_J (−4)ᴶ|, so
**sign Re z = sign(r_J)·(−1)ᴶ**.  The automaton `⋚ʳ′` reads the blocks least significant first and keeps the sign given by the
last non-zero block; `⋚ⁱ′` does the same with Im cⱼ = d₄ⱼ₊₁ − 2d₄ⱼ₊₂ + 2d₄ⱼ₊₃ ∈ {−2, …, 3} (again |·| ≤ 3).  ∎

**Lemma 5 (Re z, Im z, z̄ in linear time).**  Re z = Σ rⱼ b⁴ʲ where each rⱼ has a numeral of at most five digits.  The even blocks
(j = 0, 2, 4, …) can therefore be written side by side, eight digits per block, without any addition; so can the odd blocks; one
addition joins the two.  The same holds for Im z, and z̄ = Re z + (−i)·Im z with −i = 111.  ∎

**Lemma 6 (exact division, Hensel).**  If q is odd (q₀ = 1) then q ≡ 1 (mod b), so the quotient w/q (when it exists) has last digit
w₀, and w/q = w₀ + b·((w − w₀ q)/b)/q.  `÷ᴴ` follows this recursion; it stops when w = 0, which happens after as many steps as the
quotient has digits.  A general divisor is first made odd by removing common factors b (`÷ᶻ`).  ∎

**Lemma 7 (gcd and division with remainder).**  For a *real* integer n, b | n ⇔ 2 | n (N(b) = 2 divides N(n) = n² iff n is even),
so "even" is "last digit 0", and n/2 = (n/b²)·(−i).  With this, Stein's binary gcd (`gcdᶻ`) is the usual algorithm.  `⫽ᶻ` is long
division in base 4 = −b⁴: the multiples d·4ᵏ are visited from the largest down and each quotient digit (0…3) costs two
subtractions and two sign tests (Lemma 4).  `quoᶻ` rounds both coordinates of a·b̄/N(b), so N(a − q b) ≤ N(b)/2, and Euclid's
algorithm (`ggcdᶻ`) stops after O(log N(b)) steps; the result is normalised to Re > 0, Im ≥ 0.  ∎

**Theorem 1 (ℚ[i] is a field with total division).**  Let P be the set of pairs (p, q) of digit strings with q ≠ 0.  P is closed
under `⊞ ⊟ ⊠ ⊖ ∗ ÷` (products of non-zero Gaussian integers are non-zero; `÷` returns 0 for a zero divisor), `≐` (p s = r q) is an
equivalence relation on P and a congruence for all these operations, and (p, q) ↦ p/q is an isomorphism P/≐ → ℚ(i) carrying
`÷` to the zero-totalised division of ℚ(i).  Consequently every law of fields, of involutive meadows
((x⁻¹)⁻¹ = x, x·(x·x⁻¹) = x, 0⁻¹ = 0) and of conjugation holds modulo `≐`.
*Proof.*  ℤ[i] is an integral domain, so this is the field of fractions; the only point to check is q ≠ 0, which holds for every
numeral (q = bᵏ) and is preserved by every operation.  ∎

**Theorem 2 (closed sentences are decided).**  Let s, t be closed terms built from numerals and the operations of §2.  Evaluation of
`(≐ s t)` terminates and gives ⊤ iff s and t denote the same element of ℚ(i); for terms of class ℚ, `(⋚ s t)` gives the order.
Hence every closed atomic sentence — and every Boolean combination of them — is decided, in time polynomial in the number of
digits of the operands.
*Proof.*  Lemmas 2–7 and Theorem 1.  ∎

**Theorem 3 (canonical forms).**  For x ∈ ℚ(i), `⊜ x` = (z, m) where m is the least natural number with m·x ∈ ℤ[i], z = m·x, and
both are written as in Lemma 1.  So x ≐ y ⇔ `⊜ x` and `⊜ y` are the same pair of digit strings.
*Proof.*  For x = p/q, w = p q̄ and n = N(q) give x = w/n.  With g = gcd(Re w, Im w, n), `⊜` returns z = w/g, m = n/g.  If k·x ∈ ℤ[i]
then n | k·Re w and n | k·Im w, so (n/g) | k·(gcd(Re w, Im w)/g); the two factors are coprime, so m = n/g divides k.  ∎

## 5. What is proved and what is tested

| claim | status |
|:--|:--|
| Lemmas 1–7, Theorems 1–3 | proved above (on paper) |
| the decision trees are the transitions of Lemma 2 | generated by `pymo/mkcarry.py`; `--check` is run by the test-suite |
| the prelude's definitions are the algorithms of the lemmas | **tested**, not proved: exhaustive on short inputs (adder: all 961 pairs ≤ 4 digits; subtractor: all 3969 pairs ≤ 5; sign, Re, Im, z̄: all strings ≤ 11 / ≤ 8 digits; sign rule: all 524 287 strings ≤ 18 digits in its python twin) and random on long ones |
| the field, meadow, conjugation and order laws | **tested** in the language over a sample with several representations per value (all 512 triples for associativity and distributivity) |
| the class signatures of the prelude | trusted declarations (as before) |

## 6. What no axiom system can do, and what this means for predicates

* **First-order sentences.**  The full first-order theory of ℚ (Julia Robinson, 1949) and of every number field, ℚ(i) included
  (J. Robinson, 1959), is undecidable: ℤ is definable in them, so Gödel's incompleteness theorem applies.  No computable set of axioms
  decides every sentence with quantifiers over ℚ[i].
* **Existential sentences** (Hilbert's tenth problem).  Over the ring ℤ[i] it is undecidable (Denef, 1975, for the rings of integers of
  quadratic fields); over the *field* ℚ(i), as over ℚ, it is open.  Since ∀x̄. f(x̄) ≠ 0 is the negation of ∃x̄. f(x̄) = 0, the
  same holds for universal sentences that have hypotheses or inequations.
* **What is decidable** and is therefore a target for the prover of `lib/prove.imo`:
  * closed sentences (Theorem 2);
  * polynomial identities ∀x̄. s(x̄) = t(x̄) without hypotheses: ℚ(i) is infinite, so they hold iff s − t has the zero polynomial as its
    normal form;
  * linear systems over ℚ(i) (Gaussian elimination) and linear inequalities over ℚ (Fourier–Motzkin);
  * one polynomial equation in one variable: its roots in ℚ(i) are among finitely many candidates (rational root theorem in ℤ[i]),
    and degree ≤ 2 has a closed form with an exact square root test;
  * bounded quantifiers over finite lists (already in the prelude).
* **ℝ[i].**  Equality of two computable reals is undecidable (it would decide the halting problem: the stream "0 until the machine
  stops, then 2⁻ⁿ" is 0 iff the machine never stops).  For ℝ[i] relations a predicate can only (a) treat transcendental constants as
  symbols and prove identities that hold for *all* their values, or (b) prove inequalities from certified approximations.

## References

* W. Penney, *A "binary" system for complex numbers*, J. ACM 12 (1965) 247–248.
* D. E. Knuth, *The Art of Computer Programming*, vol. 2, §4.1 (positional number systems, base i − 1).
* J. A. Bergstra, J. V. Tucker, *The rational numbers as an abstract data type*, J. ACM 54 (2007) — meadows, 0⁻¹ = 0.
* J. Robinson, *Definability and decision problems in arithmetic*, J. Symbolic Logic 14 (1949) 98–114.
* J. Robinson, *The undecidability of algebraic rings and fields*, Proc. AMS 10 (1959) 950–957.
* J. Denef, *Hilbert's tenth problem for quadratic rings*, Proc. AMS 48 (1975) 214–220.
