# Polynomials in one indeterminate (`lib/poly.imo`)

Univariate polynomials over the Gaussian rationals ℚ[i] — the foundation the predicate simplifier, linear algebra, rings, fields and
Galois theory build on.  Every algorithm below is written in spec notation in `lib/poly.imo` and runs **in the language**, on base-(i − 1)
digit strings; the Python host only parses, checks classes and spells digits.

## Representation

A polynomial is the list of its coefficients, **lowest degree first**: 3 + 2x² is `[3, 0, 2]`.  The class is

```text
ℚ[i][x] ∶ 𝒦      (≣ ℚ[i][x] (𝔏 ℚ[i]))          doc 2:  Poly := ℚ[i][x] ; class
```

so a `Poly` *is* a `List(\Q)`; lists and polynomials convert freely, and every function also accepts `List(\ZZ)`, `List(\QQ)`,
`List(\Z)` (overloads keep the class of the input where the operation preserves it, e.g. `polymul` of two `List(\ZZ)` is a `List(\ZZ)`).

**Canonical form**: every coefficient in the canonical form `⊜` (z/m with m a positive natural and gcd(Re z, Im z, m) = 1) and no
trailing zero coefficient; the zero polynomial is the empty list `[]`.  Every public function accepts non-canonical input (trailing zeros,
unreduced fractions) and returns canonical output.

Internally the real-coefficient algorithms (gcd, Sturm sequences, pseudo-remainders, Zassenhaus) run **fraction-free** on lists of
ℤ[i] digit strings; rational arithmetic is used only where the field is needed (complex gcd, division with remainder, interpolation).

Every decision is taken in the language, on digits: the truth values are the digits 1 (⊤) and 0 (⊥) — `polyeq` and `isirreducible`
return them, zero tests are "every digit is 0" (`∅ᶻ`), signs are read from the base-(i − 1) digits (`⋚ʳ`), divisibility is a remainder
digit string being empty — and the case distinctions of every algorithm (which half of an interval holds the root, whether a candidate
divides, whether a degree survives the sieve) are these digits selecting a branch.  No other representation of truth is used.

Human names equal spec names, except `disc` (spec `discriminant`, because the spec name `disc` belongs to `lib/prove.imo`).

## Functions

Classes are written in human notation; `P` stands for `Poly` (= `List(\Q)`), `Q` for the real-rational list `List(\QQ)`.

### Construction, access, ring operations

| name | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `poly(p)` | `P -> P` (also on `List(\ZZ)`, `List(\QQ)`, `List(\Z)`) | the canonical form | `⊜` on every coefficient (cheap path for a real denominator), trailing zeros removed |
| `deg(p)` | `P -> \ZZ` | the degree; `deg([]) = -1` | |
| `lc(p)` | `P -> \Q` (and `\ZZ`, `\QQ`, `\Z`) | the leading coefficient; 0 for the zero polynomial | |
| `coeff(p, k)` | `P -> \NN -> \Q` | the coefficient of xᵏ (0 beyond the degree) | |
| `polyx` | `List(\ZZ)` | the polynomial x = `[0, 1]` | |
| `monomial(c, n)` | `\Q -> \NN -> P` | c·xⁿ (`[]` for c = 0) | |
| `polyadd(p, q)`, `polysub(p, q)`, `polyneg(p)` | `P -> P -> P`, `P -> P` | sum, difference, negation | coefficientwise, one reduction per coefficient |
| `polyscale(c, p)` | `\Q -> P -> P` | c·p | |
| `polymul(p, q)` | `P -> P -> P` | product | schoolbook, unreduced inner sums, one `⊜` per coefficient |
| `polypow(p, n)` | `P -> \NN -> P` | pⁿ (p⁰ = 1) | squaring on the digits of n |
| `polydivmod(p, q)` | `P -> P -> Pair(P, P)` | (quotient, remainder), deg r < deg q; `polydivmod(p, 0) = (0, p)` | long division with 1/lc(q) |
| `polyquo(p, q)`, `polyrem(p, q)` | `P -> P -> P` | the two parts of `polydivmod` | |
| `polypowmod(p, n, m)` | `P -> \NN -> P -> P` | pⁿ mod m (m = 0: pⁿ) | squaring, reduced at every step |
| `polyeq(p, q)` | `P -> P -> Bool` | equality as values (trailing zeros and unreduced coefficients do not matter) | |

### Evaluation, composition, calculus

| name | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `polyeval(p, z)` | `P -> \Q -> \Q` (also `\NN`, `\ZZ`, `\QQ`, `\Z`) | p(z) | Horner, one reduction at the end |
| `polyevalmany(p, zs)` | `P -> List(\Q) -> List(\Q)` | the values p(z) for every z of the list | Horner at every point |
| `polyevalR(p, x)` | `P -> \R -> \R` (and `Q -> \RR -> \RR`) | p(x) for a lazy x | pointwise: element n is p(xₙ); it converges to p(x) since \|p(xₙ) − p(x)\| ≤ L·\|xₙ − x\| (L a Lipschitz constant of p near x) |
| `polycompose(p, q)` | `P -> P -> P` | p(q(x)) | Horner in polynomials |
| `polyshift(p, a)` | `P -> \Q -> P` | p(x + a) | composition with x + a |
| `polyderiv(p)` | `P -> P` | p′ | |
| `polyinteg(p)` | `P -> P` | the antiderivative with constant term 0 | |
| `polyconj(p)` | `P -> P` | the polynomial with conjugated coefficients | |

### Divisibility

| name | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `polymonic(p)` | `P -> P` | the monic multiple (0 stays 0) | |
| `polygcd(p, q)` | `P -> P -> P` | the monic gcd; `gcd(0, 0) = 0` | real p, q: fraction-free primitive remainder sequence on digit strings; otherwise Euclid over ℚ(i) with monic remainders |
| `polyegcd(p, q)` | `P -> P -> Pair(P, Pair(P, P))` | (g, (s, t)) with s·p + t·q = g = gcd(p, q) | extended Euclid, every remainder made monic together with its cofactors; (0, (0, 0)) for p = q = 0 |
| `polylcm(p, q)` | `P -> P -> P` | the monic lcm (0 if either is 0) | p·q / gcd |
| `polycontent(p)` | `Q -> \QQ` | the content c > 0 with p = ±c·polyprimitive(p); 0 for the zero polynomial | gcd of the numerators / lcm of the denominators |
| `polyprimitive(p)` | `Q -> List(\ZZ)` | the primitive part: coprime integer coefficients, positive leading coefficient | |
| `sqfree(p)` | `P -> P` | the square-free part p / gcd(p, p′), monic (0 stays 0) | |
| `sqfreefactor(p)` | `P -> List(Pair(P, \NN))` | Yun's square-free factorisation: (fₖ, k) with every fₖ monic, square-free, pairwise coprime, non-constant, and p = lc(p)·Π fₖᵏ; `[]` for a constant | Yun's algorithm |
| `resultant(p, q)` | `P -> P -> \Q` | Res(p, q); 0 if either is 0; 1 for two non-zero constants; bᵐ for a constant b | Euclid: Res(A, B) = (−1)^(mn)·lc(B)^(m − deg R)·Res(B, R) |
| `disc(p)` | `P -> \Q` | the discriminant (−1)^(n(n−1)/2)·Res(p, p′)/lc(p) (b² − 4ac for a quadratic); 1 in degree 1, 0 for a constant | |

### Real roots (real-rational coefficients)

The predicate simplifier relies on these; they are exact, and fast for degree ≤ 6 with small coefficients.

| name | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `sturm(p)` | `Q -> List(List(\ZZ))` | the Sturm sequence p, p′, −rem(p, p′), …, every element scaled by a **positive** factor to a primitive integer polynomial (sign variations unchanged); `[]` for p = 0 | fraction-free pseudo-remainders |
| `nrealroots(p)` | `Q -> \NN` | the number of distinct real roots; 0 for p = 0 | V(−∞) − V(+∞) |
| `countroots(p, a, b)` | `Q -> \QQ -> \QQ -> \NN` | the number of distinct real roots in the half-open (a, b]; 0 if a ≥ b or p = 0 | Sturm sequence divided by gcd(p, p′) (valid at roots too) |
| `isolate(p)` | `Q -> List(Pair(\QQ, \QQ))` | sorted, pairwise disjoint intervals: (a, b) with a < b means exactly one distinct root in (a, b) and p(b) ≠ 0; (r, r) is a rational root r met at a bisection point | bisection of (−M, M], M the power of two above Cauchy's bound, Sturm counts; both endpoints kept over one denominator, reduced only on return |
| `refine(p, a, b, n)` | `Q -> \QQ -> \QQ -> \NN -> Pair(\QQ, \QQ)` | the interval (a, b] isolating one root, bisected to width ≤ 2⁻ⁿ (a root hit exactly gives (r, r)); returned unchanged when (a, b] does not contain exactly one distinct root | sign of the square-free part |
| `signat(q, p, a, b)` | `Q -> Q -> \QQ -> \QQ -> \ZZ` | the sign −1/0/1 of q at the unique root of p in (a, b] (a = b stands for the rational root a, as `isolate` returns it); 0 if (a, b] does not isolate one root, if p(a) ≠ 0 for a = b, or if q = 0 | exact: q(root) = 0 iff g = gcd(sqfree p, q) has a root in (a, b] (Sturm count of g); otherwise bisection until q has no root in [a, b] |
| `root(p, k)` | `Q -> \NN -> \RR` | the k-th distinct real root in increasing order (k ≥ 1) as a lazy real, **element n within 2⁻ⁿ**; the constant 0 when there is no k-th root | isolation, then bisection; a rational root is exact. Accepts a plain list of numbers: `root([-2, 0, 0, 1], 1)` = ∛2 |
| `realroots(p)` | `Q -> List(\RR)` | all distinct real roots as lazy reals, increasing (element n within 2⁻ⁿ) | |

### Roots in ℚ(i), complex roots, factorisation

| name | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `ratroots(p)` | `P -> List(\Q)` | the distinct roots of p that lie in ℚ(i), sorted by (Re, Im); `[]` for p = 0 | exact. **Real coefficients**: the rational roots from the Sturm isolation — every rational root r of the square-free primitive f satisfies aₙ·r ∈ ℤ, so its interval is refined to width ≤ 1/(2\|aₙ\|) and the single candidate ⌊\|aₙ\|·b⌋/\|aₙ\| is tested exactly; after dividing them out, the non-real roots z ∈ ℚ(i) of the remaining h come in pairs z, z̄ whose primitive integer quadratic factor kx² + lx + m = k(x − z)(x − z̄) (k, m > 0) is positive on ℝ: a Kronecker search with the nodes ∞, 0, 1 — k \| lc h, m \| h(0), k + l + m \| h(1) over the positive divisors — keeps a candidate when k − l + m divides h(−1), gcd(k, l, m) = 1, 4km − l² = s² is a non-zero square, and h((−l + s·i)/(2k)) = 0 exactly. **Non-real coefficients**: the rational root theorem in the factorial ring ℤ[i] — with P = L·p (L the lcm of the denominators, coefficients in ℤ[i]) a root w/v in lowest terms has w \| P(0) and v \| lc P (after removing the factor x^k, which contributes the root 0); the candidates ε·u/v run over one Gaussian divisor u, v per associate class (found from the divisors d of the norm as x + yi with x² + y² = d) and the four units ε, pruned by the root bound N(w) ≤ C²·N(v) and by the divisibilities v − w \| P(1), v + w \| P(−1), and are tested exactly. Cost grows with the number of divisors of the values (fine for small coefficients; the divisors are found by trial division) |
| `croots(p)` | `P -> List(\R)` | all complex roots **with multiplicity**, as lazy complex numbers | numerical: Weierstrass (Durand–Kerner) iteration on each monic square-free factor from Yun's decomposition (so multiple roots are simple there), in fixed point base i − 1 with F = 2n + 24 digits for element n; iterates until every correction has \|W\| ≤ 2⁻ⁿ⁻³/d (by Gerschgorin's theorem for the Weierstrass matrix the root is then within about (d − 1)\|W\| < 2⁻ⁿ), at most 48 iterations per element, each element starting from the previous one. Degree-1 factors are exact. Convergence of Durand–Kerner from the starting points (0.4 + 0.9i)ᵏ is observed for all practical inputs but not proved in general; when the iteration limit is reached the element is the last iterate |
| `polyfactor(p)` | `Q -> Pair(\QQ, List(Pair(List(\ZZ), \NN)))` | the complete factorisation over ℚ: (c, [(f, k)]) with p = c·Π fᵏ, every f irreducible over ℚ, primitive, with positive leading coefficient, pairwise distinct; (p, []) for a constant | Yun's square-free decomposition; for each square-free part: rational roots (as above), then **Zassenhaus**: distinct-degree factorisation modulo the first three good odd primes p (p ∤ lc, square-free mod p); a **degree sieve** keeps only the degrees that are subset sums of the modular factor degrees for every prime (only 0 and n left: irreducible, nothing is lifted); otherwise, for the prime with the fewest modular factors, Cantor–Zassenhaus equal-degree splitting (deterministic enumeration of splitting polynomials, which always succeeds), quadratic Hensel lifting to M = p^(2^j) > 2B with the Mignotte-type bound B = 2ⁿ·Σ\|hᵢ\|, recombination of the subsets of lifted factors whose degree passes the sieve, smallest first, with exact trial division. All modular arithmetic runs on digit strings with lazy reduction. Exact for every input; the recombination is exponential in the number of modular factors (fine for degree ≤ 8–10; x⁴ + 1-like polynomials that split into many factors mod every prime are the worst case) |
| `isirreducible(p)` | `Q -> Bool` | irreducible over ℚ: degree ≥ 1 and no proper factorisation (constants are not irreducible) | `polyfactor` |

### Interpolation, special polynomials, text

| name | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `interpolate(xs, ys)` | `List(\Q) -> List(\Q) -> P` | the polynomial of degree < n through the n points (xⱼ, yⱼ); a repeated node is ignored (its first value counts); `[]` for no points | Newton's divided differences |
| `polyfromroots(rs)` | `List(\Q) -> P` | Π (x − r) (1 for the empty list) | |
| `cyclotomic(n)` | `\NN -> List(\ZZ)` | the cyclotomic polynomial Φₙ (cyclotomic(0) = 1) | Φ₁ = x − 1, Φₘₚ(x) = Φₘ(xᵖ)/Φₘ(x) over the distinct primes p of n, then Φₙ(x) = Φ_rad(n)(x^(n/rad n)) |
| `chebyshevT(n)`, `chebyshevU(n)` | `\NN -> List(\ZZ)` | Chebyshev polynomials of the first and second kind | Tₙ₊₁ = 2x·Tₙ − Tₙ₋₁ (T₁ = x), the same with U₁ = 2x |
| `legendreP(n)` | `\NN -> List(\QQ)` | Legendre Pₙ | (n + 1)Pₙ₊₁ = (2n + 1)x·Pₙ − n·Pₙ₋₁ |
| `hermiteH(n)` | `\NN -> List(\ZZ)` | (physicists') Hermite Hₙ | Hₙ₊₁ = 2x·Hₙ − 2n·Hₙ₋₁ |
| `laguerreL(n)` | `\NN -> List(\QQ)` | Laguerre Lₙ | (n + 1)Lₙ₊₁ = (2n + 1 − x)·Lₙ − n·Lₙ₋₁ |
| `companion(p)` | `P -> List(List(\Q))` | the companion matrix (rows; ones below the diagonal, last column −c₀ … −cₙ₋₁) of the monic multiple of p: its characteristic polynomial is `polymonic(p)`; `[]` for degree ≤ 0 | |
| `polystr(p)` | `P -> String` | human notation, highest degree first: `"x^2 - 2*x + 1"`, `"(1 + i)*x + 3"`, `"-3/4*x^2 + 1/2"`, `"0"`; coefficients ±1 omitted, non-real coefficients parenthesised | |

## Performance notes

The evaluator costs about 10 µs per digit step.  Typical costs on Pymo: ring operations and evaluation of small
polynomials — milliseconds; Sturm counts, isolation and `ratroots` of degree ≤ 6 with small coefficients — well under a second each;
`polyfactor` of degree ≤ 7 with small coefficients — typically 0.1–5 s; `croots` element n costs O(d²·n²) digit steps per iteration.

## Tests

`tests/test_poly.py` — a human-notation program covering every public function (zero, empty, constant, negative, non-real and degenerate
inputs), decoded and compared with an independent Python reference (Fraction arithmetic, Sylvester determinants, brute-force sign changes,
explicit formulas for the orthogonal polynomials, Faddeev–LeVerrier for the companion matrix, hand-checked factorisations).
