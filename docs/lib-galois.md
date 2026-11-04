# Galois theory (`lib/galois.imo`)

Galois groups of polynomials over ℚ of degree ≤ 4, cyclotomy and unit groups, Frobenius patterns, Eisenstein's criterion and the Galois
groups of finite fields.  Every algorithm is written in spec notation in `lib/galois.imo` and runs in the language, on base-(i − 1)
digit strings.  It builds on `lib/group.imo` (permutation groups), `lib/field.imo` (factorisation modulo p, GF(pⁿ)), `lib/poly.imo`
(discriminants, factorisation over ℚ) and `lib/numtheory.imo`.

## Representation

A **Galois group is a permutation group of the roots**, in the representation of `lib/group.imo`: the sorted list of its elements, each a
permutation of the points 0, 1, …, d − 1 given as the list of images (`List(List(\NN))`), so every function of `lib/group.imo`
applies to it (`grouporder`, `isabelian`, `iscyclic`, `issolvable`, `subgroups`, `isomorphic`, `conjclasses`, `center`, `elementorders`, …).
The roots of a polynomial are numbered **by blocks**: the roots of the linear factors first, then the roots of the other irreducible
factors in order of increasing degree.  The group is determined up to a relabelling of the roots inside the blocks (so an irreducible
quartic with group D₄ is given as one of the three conjugate copies of D₄ in S₄).

## The Galois group of a polynomial of degree ≤ 4

`galoisgroup(f)` for f ∈ ℚ[x] (a coefficient list `List(\QQ)`, lowest degree first; repeated roots are ignored: the square-free part is
used; a constant gives the trivial group on 0 points).  It factors the square-free part over ℚ (`polyfactor`), then:

| factors of degree ≥ 2 | group | criterion |
|:--|:--|:--|
| none | 1 | all roots are rational |
| one quadratic | C₂ | |
| one cubic g | C₃ if disc(g) is a rational square, else S₃ | G ⊆ A₃ ⇔ disc is a square |
| one quartic g (monic form x⁴ + a x³ + b x² + c x + d) | see below | the resolvent cubic |
| two quadratics | C₂ if disc₁·disc₂ is a rational square (the same quadratic field), else V₄ = C₂ × C₂ acting on the two pairs of roots | |
| degree ≥ 5 (a factor or the total) | `[]` | outside the cases handled |

For an **irreducible quartic**, let R(y) = y³ − b y² + (ac − 4d) y − (a²d − 4bd + c²) be the resolvent cubic (roots α₁α₂ + α₃α₄,
α₁α₃ + α₂α₄, α₁α₄ + α₂α₃; `resolventcubic`; disc R = disc g) and Δ = disc g.  Then:

* R has no rational root: **S₄** if Δ is not a rational square, **A₄** if it is;
* R has three rational roots: **V₄** (the Klein four-group, transitive);
* R has exactly one rational root r: **C₄** if both quadratics x² − r x + d and x² + a x + (b − r) split over ℚ(√Δ), else **D₄**
  (Kappe–Warren; a monic quadratic x² + u x + v splits over ℚ(√Δ) iff u² − 4v or Δ(u² − 4v) is a rational square).

| name | class | meaning |
|:--|:--|:--|
| `galoisgroup(f)` | `List(\QQ) -> List(List(\NN))` | the Galois group of the splitting field of f over ℚ, as above |
| `galoisname(f)` | `... -> String` | its isomorphism type: `"1"`, `"C2"`, `"C3"`, `"S3"`, `"V4"`, `"C4"`, `"D4"`, `"A4"`, `"S4"`; `""` outside the cases handled |
| `galoisorder(f)` | `... -> \NN` | its order = the degree [K : ℚ] of the splitting field K; 0 outside the cases handled |
| `intermediatefielddegrees(f)` | `... -> List(\NN)` | the degrees [F : ℚ] = [G : H] of the intermediate fields of K/ℚ, one for each subgroup H of G (Galois correspondence), ascending |
| `isdiscsquare(f)` | `... -> Bool` | is disc(f) a rational square (then G ⊆ Aₙ)? false for disc ≤ 0 |
| `resolventcubic(f)` | `... -> List(\QQ)` | the resolvent cubic of a quartic (monic form), `[]` for other degrees |

Examples (tested): x⁴ − 2 → D₄ (order 8), x⁴ + 1 → V₄, x⁴ − 4x² + 2 and x⁴ + x³ + x² + x + 1 → C₄, x⁴ − x − 1 → S₄, x⁴ + 8x + 12 → A₄,
x³ − 2 → S₃, x³ − 3x + 1 → C₃, (x² − 2)(x² − 3) → V₄, (x² − 2)(x² − 8) → C₂, x⁴ + 4 = (x² + 2x + 2)(x² − 2x + 2) → C₂.

## Frobenius and Chebotarev

For a prime p dividing neither the leading coefficient nor the discriminant of f, the degrees of the irreducible factors of f modulo p are
the cycle lengths of the Frobenius element at p, an element of the Galois group acting on the roots (Dedekind); by Chebotarev's density
theorem every element's cycle type occurs for a positive proportion of the primes.

| name | class | meaning |
|:--|:--|:--|
| `isgoodprime(f, p)` | `List(\ZZ) -> \NN -> Bool` | p is a prime not dividing lc f and disc f |
| `frobeniuspattern(f, p)` | `... -> List(\NN)` | the degrees of the irreducible factors of f mod p, with multiplicity, ascending |
| `frobeniuscensus(f, B)` | `... -> List(List(\NN))` | the distinct patterns at the good primes p ≤ B, sorted (shortest first, then lexicographically). Every pattern listed is the cycle type of an element of the Galois group: a **refutation test** for a conjectured group (a transposition-type pattern excludes C₄ and A₄; (x³ − 2 up to 40 shows 1³, 1·2 and 3: S₃; x⁴ − x − 1 up to 100 shows all five cycle types of S₄). About 0.3 s per prime for a cubic, 0.5 s for a quartic |

## Cyclotomy and finite fields

| name | class | meaning |
|:--|:--|:--|
| `unitgroup(n)`, `galoiscyclotomic(n)` | `\NN -> List(List(\NN))` | the group (ℤ/n)× as a permutation group (the regular representation on the units in increasing order) = Gal(ℚ(ζₙ)/ℚ), σₐ(ζ) = ζᵃ; order φ(n) |
| `cyclotomicfactors(p, n)` | `\NN -> \NN -> List(List(\NN))` | the irreducible factors of Φₙ over GF(p) (p ∤ n): φ(n)/ord_n(p) of them, all of degree ord_n(p), the order of the Frobenius of p in Gal(ℚ(ζₙ)/ℚ) |
| `gfgalois(F)` | `Pair(\NN, List(\NN)) -> List(List(\NN))` | Gal(GF(pⁿ)/GF(p)): the cyclic group of order n generated by the Frobenius, as permutations of the positions in `gfelements(F)` |

## Eisenstein's criterion

`eisensteinprime(f)` (`List(\ZZ) -> \NN`) is a prime p with p ∤ lc, p dividing every other coefficient and p² ∤ the constant term — then f is
irreducible over ℚ — and 0 if there is none (f may still be irreducible); `iseisenstein(f)` is the Boolean.

## What is not here

Galois groups of polynomials of degree ≥ 5 (a general algorithm needs resolvents of high degree with exactly computed roots, which this
evaluator cannot afford); `frobeniuscensus` gives a sound partial answer there (for an irreducible quintic, one prime with the pattern
(1, 1, 1, 2) proves the group is S₅, because a transitive group of prime degree that contains a transposition is symmetric).  Fixed fields of subgroups and explicit generators of the intermediate fields are not
computed; their degrees are (`intermediatefielddegrees`), and `algsum`, `algprod`, `algroot`, `nfminpoly` of `lib/field.imo` compute
minimal polynomials of elements of the splitting fields.

## Tests

`tests/test_galois.py` (12 checks, about 3.5 minutes): 32 polynomials with known groups — name, order, group axioms, the cycle-type statistics of S₄, A₄, V₄, D₄, C₄, S₃, C₃,
the Frobenius census against the cycle types of the computed group (Dedekind), the subgroup lattice found independently by closure of the
subsets of at most three elements, `isdiscsquare` against the discriminant from the numerical roots, unit groups against the element
orders of (ℤ/n)× , cyclotomic factors against a direct factorisation of Φₙ modulo p, Galois groups of four finite fields against the
Frobenius computed in Python, Frobenius patterns against trial division, Eisenstein against a direct test, the resolvent cubic against the
numerical roots.
