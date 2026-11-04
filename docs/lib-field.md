# Fields (`lib/field.imo`)

Polynomials and fields over a prime field GF(p); the finite fields GF(pⁿ); number fields ℚ(α); algebraic numbers.  Every algorithm is
written in spec notation in `lib/field.imo` and runs in the language, on base-(i − 1) digit strings; the Python host only parses,
checks classes and spells digits.  Arithmetic of the number field ℚ(α) = ℚ[x]/(f) is `qradd`, `qrmul`, `qrinv`, `qrpow` of `lib/ring.imo`.

## Representation

* A polynomial over GF(p) (p a prime) is the list of its coefficients, **lowest degree first**, each a natural number in [0, p),
  without trailing zeros; the zero polynomial is `[]`.  Every function accepts any list of integers (reduced modulo p first) and returns
  the canonical form.  Class `List(\NN)`.
* The finite field GF(pⁿ) is the **pair `(p, m)`** (class `Pair(\NN, List(\NN))`) of the prime and a monic irreducible polynomial m of
  degree n over GF(p).  `gf(p, n)` builds it with m = `primitivepoly(p, n)`, so that x is a generator of the multiplicative group; any
  other irreducible modulus can be given as `pair(p, m)`.  The elements are the polynomials of degree < n (the zero element is `[]`).
* A number field element is a polynomial of degree < deg f over ℚ; f is given as a coefficient list (`List(\QQ)`).

## Polynomials over GF(p)

| name | class | meaning |
|:--|:--|:--|
| `fpoly(p, f)` | `\NN -> List(\ZZ) -> List(\NN)` | the canonical form: coefficients mod p, trailing zeros removed |
| `fpadd`, `fpsub`, `fpmul` `(p, f, g)`; `fpneg(p, f)`; `fpscale(p, c, f)` | | ring operations |
| `fpdegree(f)` | | the degree (−1 for `[]`) |
| `fpmonic(p, f)` | | the monic multiple |
| `fpdivmod(p, f, g)`, `fpquo`, `fprem` | | division with remainder (`([], f)` for g = 0) |
| `fpgcd(p, f, g)`, `fpegcd(p, f, g)` | | the monic gcd; `(d, (s, t))` with s·f + t·g = d |
| `fppowmod(p, f, n, m)` | | fⁿ mod m by squaring |
| `fpderiv(p, f)`, `fpeval(p, f, a)`, `fproots(p, f)` | | derivative; value; the roots in GF(p) (all of them for f = 0) |
| `fpirreducible(p, f)` | `... -> Bool` | irreducible over GF(p)? (Ben-Or: gcd(x^(pᵏ) − x, f) = 1 for k ≤ deg f / 2) |
| `fpfactor(p, f)` | `... -> Pair(\NN, List(Pair(List(\NN), \NN)))` | the complete factorisation `(c, [(g, k)])`: f = c·Π gᵏ, c the leading coefficient, g monic irreducible, sorted by degree then coefficients. Yun's square-free decomposition **in characteristic p** (including p-th powers, f′ = 0), distinct-degree factorisation, equal-degree splitting (Cantor–Zassenhaus for odd p with a deterministic enumeration of the splitting polynomials, the trace map for p = 2) |
| `irreduciblepoly(p, n)` | `\NN -> \NN -> List(\NN)` | the first monic irreducible polynomial of degree n, the candidates taken in the order of Σ aⱼpʲ (x² + x + 1, x³ + x + 1, x⁴ + x + 1 over GF(2)) |
| `isprimitivepoly(p, f)`, `primitivepoly(p, n)` | | monic, irreducible and x of order pⁿ − 1 modulo f; the first such polynomial |
| `numirreducible(p, n)` | | the number of monic irreducible polynomials of degree n: (1/n)·Σ_(d\|n) μ(d)p^(n/d) |

## The finite field GF(pⁿ)

`F` is the pair `(p, m)`; `a`, `b` are elements (any polynomials are reduced first).

| name | meaning |
|:--|:--|
| `gf(p, n)`, `gfchar(F)`, `gfmodulus(F)`, `gfdegree(F)`, `gfsize(F)` | construction and the data p, m, n, pⁿ |
| `gfelement(F, f)` | the element represented by a polynomial |
| `gfadd`, `gfsub`, `gfmul`, `gfdiv` `(F, a, b)`; `gfneg(F, a)`; `gfinv(F, a)` | arithmetic; `gfinv(F, [])` and division by 0 are `[]` |
| `gfpow(F, a, e)` | aᵉ by squaring; e < 0 uses the inverse; 0⁰ = 1 |
| `gfelements(F)` | all pⁿ elements in the order of Σ aⱼpʲ |
| `gforder(F, a)` | the multiplicative order (0 for a = 0): from pⁿ − 1 removing each prime r while a^(o/r) = 1 |
| `gfisprimitive(F, a)`, `gfprimitive(F)` | a generates the multiplicative group; the first such element |
| `gflog(F, g, a)` | the least k ≥ 0 with gᵏ = a, **−1** if there is none (repeated multiplication: for small fields) |
| `gffrob(F, a)`, `gftrace(F, a)`, `gfnorm(F, a)` | a ↦ aᵖ; Tr(a) = a + aᵖ + … + aᵖ^(n−1) and N(a) = a·aᵖ⋯aᵖ^(n−1), elements of GF(p) (as naturals) |
| `gfconjugates(F, a)`, `gfminpoly(F, a)` | the distinct conjugates of a; its minimal polynomial over GF(p) (monic, irreducible, degree dividing n) |
| `gfsqrt(F, a)`, `gfissquare(F, a)` | all square roots (a list of 0, 1 or 2 elements); Euler's criterion |
| `gfroots(F, f)` | the roots in the field of a polynomial whose coefficients are field elements |
| `gfsubfields(n)` | the degrees of the subfields of GF(pⁿ): the divisors of n |

The Galois group of GF(pⁿ) over GF(p) (`gfgalois`) and the factorisation of cyclotomic polynomials modulo p are in `lib/galois.imo`.

## Number fields ℚ(α) = ℚ[x]/(f)

| name | meaning |
|:--|:--|
| `nfmatrix(f, a)` | the matrix of the multiplication by a in the basis 1, α, …, αⁿ⁻¹ (column j: the coordinates of a·αʲ) |
| `nfcharpoly(f, a)`, `nfminpoly(f, a)`, `nfdegree(f, a)` | characteristic polynomial (degree n), minimal polynomial (monic), and [ℚ(a) : ℚ] |
| `nftrace(f, a)`, `nfnorm(f, a)` | trace and norm of a over ℚ (trace and determinant of `nfmatrix`) |
| `nfisintegral(f, a)` | is a an algebraic integer (integer coefficients of the minimal polynomial)? |
| `nfdiscriminant(f)` | the discriminant of f = of the basis 1, α, …, αⁿ⁻¹ (the field discriminant divides it) |

## Algebraic numbers

Each function returns the **monic irreducible factors over ℚ of the polynomial whose roots are the combinations of all roots of f and g**:
the minimal polynomial of the combination of two given roots is one of them (all of them when the conjugates give different values; for
`x² − 2` with itself `algsum` returns `x` and `x² − 8`, because √2 + √2 = 2√2 but √2 − √2 = 0).  The polynomial is the resultant
Res_y(f(y), G(x, y)) evaluated at as many integers x as its degree plus one and interpolated, then factored with `polyfactor`.

| name | roots of the polynomial |
|:--|:--|
| `algsum(f, g)`, `algdiff(f, g)` | α + β, α − β |
| `algprod(f, g)`, `algquot(f, g)` | α·β, α/β (`[x]` when f or g has the root 0) |
| `algneg(f)`, `alginv(f)` | −α, 1/α |
| `algpow(f, k)`, `algroot(f, k)` | αᵏ; α^(1/k) (the factors of f(xᵏ)) |

Examples (tested): `algsum([-2,0,1], [-3,0,1])` is `[[1,0,-10,0,1]]` (√2 + √3 has minimal polynomial x⁴ − 10x² + 1);
`algprod([-2,0,1], [-3,0,1])` is `x² − 6`; `algdiff` of ∛2 and √2 is the sextic x⁶ − 6x⁴ − 4x³ + 12x² − 24x − 4.

## Performance

About 10 µs per digit step.  The primitives over GF(p) carry sums of products unreduced and reduce once per coefficient, and divide with
only the leading entry reduced at each step (the method of `lib/poly.imo`); the residue is the digit-level remainder.  Typical costs: a
product or a remainder of degree-6 polynomials 0.1 s; `x⁸ + 1` over GF(7) factored in 2 s; a degree-6 polynomial over GF(101) factored in
4 s; `gf(5, 2)` 1 s and `gf(2, 10)` 2 s (mostly the search for a primitive polynomial: bind a field once, `F in ... := gf(5, 2)`, a bound
name is evaluated once); `algsum` of ∛2 and √3 (a degree-6 resultant, interpolated and factored) 2 s.  `gflog`, `gfsqrt` and
`gfelements` enumerate the field: for fields with up to a few hundred elements.

## Tests

`tests/test_field.py` (15 checks, about 70 seconds): trial-division references for GF(p)[x] (division, gcd, Bézout, irreducibility, the
complete factorisation of 21 polynomials including p-th powers and repeated factors), a polynomial-arithmetic implementation of GF(pⁿ)
for eight fields (including two with a non-primitive modulus), Fraction linear algebra and Sylvester determinants for the number-field
data, and the numerical roots of f and g (Durand–Kerner in Python) for the algebraic numbers.
