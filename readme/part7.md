
---

## 14. Standard library reference

The prelude is twenty-four spec files in `lib/`, listed in `lib/MANIFEST` (the one list every core reads) and loaded in this order — `logic` (classes, Booleans, pairs, lists), `number` (base-(i−1) arithmetic, ℚ[i], order), `algebra` (algebras, lazy ℝ[i], series, Cayley–Dickson, function spaces), `bounded` (bounded quantifiers), `analysis` (exp, sin, cos), `arith` (exact division, gcd, canonical form, floor, powers, factorial, integer roots), `list` (list functions, sorting, digit-wise operations, characters), `real` (√, log, atan, hyperbolic functions, tan, derivative, integral), `linalg` (vectors, matrices, determinant, solving, inverse — and §14.1), `set` (sets as membership tests), `text` (decimal output), `poly`, `complex`, `numtheory`, `ring`, `field`, `group`, `galois` (§14.1), `prove` (§13), `solve` (the simplifier of §13), `codec` (§6.6), `lists` (folds, scans, sorting, searching, combinatorics), `strings` (characters, case, splitting, bases, Roman numerals, edit distance) and `dict` (dictionaries, finite sets, multisets, heaps, queues as tries over the digits of the keys) — and their all-binary form `lib/prelude.bin.imo`.  The tables below are **generated** from doc 1, doc 2 and the declared classes (`pymo/mkref.py`), so they cannot drift from the implementation.  *Class* lists every declaration of the symbol (an overload set has several); *human* lists the human symbols that can resolve to it; *bin* is its doc 1 code.

### 14.1 The mathematical library by area

Everything below is written in the language (spec notation, in `lib/`) and runs on base-(i−1) digit strings; the Python host only parses,
checks classes and spells digits.  Each area has a document with the representation, every function with its class and algorithm, the
limits, and the tests.  "Any operation with an output is a function": predicates return `Bool`, constructions return lists, groups and
fields are values (a group is the sorted list of its permutations, `GF(pⁿ)` the pair `(p, m)`).

| area | file | document | what it computes |
|:--|:--|:--|:--|
| complex functions | `lib/complex.imo` | [`docs/lib-complex.md`](docs/lib-complex.md) | π, e, γ, Catalan; `Log`, `pow`, `nthroot`, `arg`, `atan2`, `cis`; the reciprocal, inverse circular and inverse hyperbolic families with `cmath`'s branch cuts; Γ, `lgamma`, ψ, B, `erf`, ζ, polylogarithms, Lambert W, Bessel J, AGM, complete elliptic integrals, `Ei`, `li`, `Si`, `Ci`.  Exact argument in, lazy complex number out (element n within 2⁻ⁿ) |
| linear algebra | `lib/linalg.imo` | [`docs/lib-linalg.md`](docs/lib-linalg.md) | exact over ℚ[i]: operators on matrices, `rref`, `rank`, subspaces, `det`, adjugate, `charpoly`, `minpoly`, eigenvalues (exact in ℚ(i), numerical, eigenvectors), `linsolve`, `lu`, Gram–Schmidt, `pinv`, `lstsq`, Smith normal form, `matexp` |
| polynomials | `lib/poly.imo` | [`docs/lib-poly.md`](docs/lib-poly.md) | arithmetic, gcd, resultants, discriminants, Sturm sequences, isolated real roots, exact roots in ℚ(i), numerical complex roots, factorisation over ℚ, interpolation, cyclotomic and orthogonal polynomials |
| number theory | `lib/numtheory.imo` | [`docs/lib-numtheory.md`](docs/lib-numtheory.md) | primality, factoring, congruences and CRT, primitive roots, quadratic residues, arithmetic functions, continued fractions and Pell, Fibonacci/Bernoulli/partition numbers, Gaussian primes and sums of two squares |
| group theory | `lib/group.imo` | [`docs/lib-group.md`](docs/lib-group.md) | permutations, generated groups, symmetric/alternating/dihedral/quaternion groups, products, cosets, normality, conjugacy classes, centre, Sylow subgroups, subgroup lattice, isomorphism, actions, Burnside, necklaces |
| ring theory | `lib/ring.imo` | [`docs/lib-ring.md`](docs/lib-ring.md) | ℤ/n (units, zero divisors, nilpotents, idempotents, ideals), principal ideals, ℚ[x]/(f), polynomial CRT, multivariate polynomials, the division algorithm, **Gröbner bases** (Buchberger, reduced bases, membership, elimination) |
| field theory | `lib/field.imo` | [`docs/lib-field.md`](docs/lib-field.md) | polynomials over GF(p) and their factorisation (Yun, Cantor–Zassenhaus), irreducible and primitive polynomials, GF(pⁿ) (order, primitive element, logarithm, Frobenius, trace, norm, minimal polynomial), number fields ℚ(α), minimal polynomials of α+β, αβ, αᵏ, α^(1/k) |
| types as decoding keys | `lib/codec.imo` | [`docs/lib-codec.md`](docs/lib-codec.md) | ordered pairs of integers as Gaussian integers (**a + b·i := (a, b)**, with `+ - * ==`), fractions as pairs, strings as natural numbers (bijective numeration), pairs of strings as one Gaussian integer; `decode` reads one binary string by the key its class names ([§6.6](#66-types-are-decoding-keys)) |
| Galois theory | `lib/galois.imo` | [`docs/lib-galois.md`](docs/lib-galois.md) | Galois groups of polynomials of degree ≤ 4 over ℚ (as permutation groups, with the subfield degrees), Gal(ℚ(ζₙ)/ℚ) = (ℤ/n)×, Gal(GF(pⁿ)/GF(p)), Frobenius patterns (Dedekind), Eisenstein |
| lists, more | `lib/lists.imo` | [`docs/lib-lists.md`](docs/lib-lists.md) | folds, scans, unfolds, zips and transposes, searching with a given equality, stable merge sort on any order, subsequences, permutations, combinations, combinators |
| characters and strings | `lib/strings.imo` | [`docs/lib-strings.md`](docs/lib-strings.md) | classes of characters and case (ASCII, Latin-1, Greek, Cyrillic), trim, split, words, lines, replace, search, padding, numbers in bases 2–36, Roman numerals, Levenshtein distance, run lengths |
| theories | `lib/term.imo` … `lib/th_topo.imo` | [`docs/lib-theory.md`](docs/lib-theory.md) | 23 packages of axioms (logic, arithmetic, Peano, groups, monoids, sets, lattices, topology, ZFC, ETCS, Kolmogorov, piecewise functions, Euclidean, Hilbert, hyperbolic and elliptic geometry) that are switched on and off, with their conflicts, and the fast decision of a statement as true / false / undetermined or its simplest form: diagrams, polynomial normal forms, Fourier–Motzkin, positive semidefiniteness of quadratics, G4ip |
| containers | `lib/dict.imo` | [`docs/lib-dict.md`](docs/lib-dict.md) | dictionaries, finite sets, multisets, leftist heaps, queues — persistent binary tries over the base-(i − 1) digits of the keys, covariant classes `(↗ Dict)` |
| the calendar | `lib/calendar.imo` | [`docs/lib-calendar.md`](docs/lib-calendar.md) | the proleptic Gregorian calendar: leap years, month lengths, day numbers (`date.toordinal`) and their inverse, weekdays, differences, the ISO year and week, Easter, month and day names, ISO date strings |
| graphs | `lib/graph.imo` | [`docs/lib-graph.md`](docs/lib-graph.md) | directed and undirected graphs as dictionaries of neighbour lists: breadth- and depth-first search, distances, shortest paths, components, topological order, bipartiteness, Dijkstra, Kruskal |
| statistics | `lib/stats.imo` | [`docs/lib-stats.md`](docs/lib-stats.md) | exact descriptive statistics on lists of rationals: median, modes, variance, quantiles, covariance, least-squares line, ranks, moving averages |
| plane geometry | `lib/geom.imo` | [`docs/lib-geom.md`](docs/lib-geom.md) | exact plane geometry on rational points: orientation, segment and line intersection, circumcentres, polygon areas, point in polygon, convex hulls, closest pair (no square roots: squared distances) |
| regular expressions | `lib/regex.imo` | [`docs/lib-regex.md`](docs/lib-regex.md) | regular expressions by Brzozowski derivatives, with a parser for the usual notation: full match, longest prefix, leftmost-longest search, find all, replace, split |
| encodings and checksums | `lib/encode.imo` | [`docs/lib-encode.md`](docs/lib-encode.md) | UTF-8, hexadecimal, Base 64 and percent-encoding, binary and Gray-code operations on naturals, Adler-32, CRC-32, Luhn, English names of numbers, the Vigenère cipher |
| pseudo-random numbers | `lib/prng.imo` | [`docs/lib-prng.md`](docs/lib-prng.md) | generators as functions of an explicit state (minstd, LCG, xorshift), streams, shuffle, sample, choice, exact Van der Corput and Halton sequences, FNV-1a and djb2 hashes |
| enumerative combinatorics | `lib/combin.imo` | [`docs/lib-combin.md`](docs/lib-combin.md) | Pascal, Eulerian, Narayana, Motzkin and Schröder numbers, derangements, lists of compositions, partitions, Dyck words, Lyndon words and set partitions, Lehmer codes and the rank and unrank of permutations |

{{REF}}

**Notions without a symbol yet.**  General roots beyond what `lib/poly.imo` isolates, relations and functions as sets of pairs, Galois groups of
polynomials of degree ≥ 5, limits as values, and unbounded quantifiers (they are not decidable; bounded ones over lists are provided, and a statement treats a
variable bound outside a relation as an unknown).  A notion may be added with a spec symbol, with only a human symbol that points at a bin numeral/symbol, or with both — see [§18](#18-extending-the-language).

---

## 15. Worked examples

All outputs below are produced by the commands shown (`$` lines), run on the files in `examples/`.

### 15.1 π + e·i

```text
$ python3 pymo/i1.py eval examples/target.hum.imo pi 14
{{RUNOUT:eval examples/target.hum.imo pi 14}}
$ python3 pymo/i1.py eval examples/target.hum.imo e 14
{{RUNOUT:eval examples/target.hum.imo e 14}}
$ python3 pymo/i1.py eval examples/target.hum.imo z 14
{{RUNOUT:eval examples/target.hum.imo z 14}}
```

The fractions are exact (they are the partial sums of the two series); the decimal approximations are only for reading.

### 15.2 The exponential, sine, cosine — and Euler's formula, numerically and proved

`examples/analysis.hum.imo`

```text
{{FILE:examples/analysis.hum.imo}}```

```text
$ python3 pymo/i1.py eval examples/analysis.hum.imo euler 14
{{RUNOUT:eval examples/analysis.hum.imo euler 14}}
```

`exp(i/2)` has real part ≈ cos ½ = 0.8775825619 and imaginary part ≈ sin ½ = 0.4794255386.  `i / 2` is the ℚ[i] element 11/1100, so the argument is a genuine complex fraction; the result lives in `\R` = ℝ[i].  The numbers illustrate Euler's formula; `exp(i / 2) == cos(1/2) + i * sin(1/2)` **proves** it: the prover recognises the three series as exponentials and the identity becomes exp(i/2) = (exp(i/2) + exp(−i/2))/2 + i·(exp(i/2) − exp(−i/2))/(2i) in the ring normal form ([§13](#13-predicates-relations-simplified-to-their-simplest-form)).

### 15.3 Quaternions, written in human notation

`examples/quaternion.hum.imo`

```text
{{FILE:examples/quaternion.hum.imo}}```

```text
$ python3 pymo/i1.py eval examples/quaternion.hum.imo q1
{{RUNOUT:eval examples/quaternion.hum.imo q1}}
$ python3 pymo/i1.py eval examples/quaternion.hum.imo q2
{{RUNOUT:eval examples/quaternion.hum.imo q2}}
$ python3 pymo/i1.py eval examples/quaternion.hum.imo q3
{{RUNOUT:eval examples/quaternion.hum.imo q3}}
$ python3 pymo/i1.py eval examples/quaternion.hum.imo q4
{{RUNOUT:eval examples/quaternion.hum.imo q4}}
```

`⟨a, b⟩` is the tree (a, b).  `j * j` is `⟨-1, 0⟩`: the quaternion −1, **still of depth 1**.  `j * k + 1`: the checker widens `1` to the tree ⟨1, 0⟩ with the coercion `↑`; the result ⟨1 + i, 0⟩ is `jk + 1 = i + 1`.  `(1 + 2 * i) * j` shows the ℚ[i]-scalar acting on `j`, and `conj` of ⟨0, a⟩ is ⟨0, −a⟩.

### 15.4 A sequence space

`examples/spaces.hum.imo`

```text
{{FILE:examples/spaces.hum.imo}}```

```text
$ python3 pymo/i1.py eval examples/spaces.hum.imo ip 6
{{RUNOUT:eval examples/spaces.hum.imo ip 6}}
$ python3 pymo/i1.py eval examples/spaces.hum.imo norm2 6
{{RUNOUT:eval examples/spaces.hum.imo norm2 6}}
```

`f` and `g` are two vectors of the infinite-dimensional space of functions ℚ[i] → ℚ[i] (indexed by n = 0, 1, 2, …); `inner(algQ, f, g)` is the stream of partial sums of ⟨f, g⟩.  Element 6 of ⟨f, g⟩ is 6/7 = N/(N+1), and ‖f‖²₆ = 1 + 1/4 + … + 1/36 = 5369/3600 → π²/6.

### 15.5 Cayley–Dickson over the lazy reals

`examples/tower.spec.imo`, loaded together with `examples/target.spec.imo`

```text
{{FILE:examples/tower.spec.imo}}```

```text
$ python3 pymo/i1.py eval examples/target.spec.imo examples/tower.spec.imo w 14
{{RUNOUT:eval examples/target.spec.imo examples/tower.spec.imo w 14}}
```

`w = (z, π)·(e, z)` where z = π + e·i.  By the product formula the first component is e·z − π·z̄ = π(e − π) + e(e + π)·i ≈ −1.3298 + 15.9287 i and the second is z² + πe ≈ 11.0200 + 17.0793 i; the output agrees.  Each leaf is a *stream*; the CLI shows element 14 of every leaf.

### 15.6 Text

`examples/hello.hum.imo`

```text
{{FILE:examples/hello.hum.imo}}```

```text
$ python3 pymo/i1.py eval examples/hello.hum.imo greeting
{{RUNOUT:eval examples/hello.hum.imo greeting}}
```

### 15.7 A program the checker rejects

`examples/bad.hum.imo`

```text
{{FILE:examples/bad.hum.imo}}```

```text
$ python3 pymo/i1.py check examples/bad.hum.imo
{{RUNOUT:check examples/bad.hum.imo}}
```

`1 - 2` lands in ℤ (subtraction is declared on ℤ, ℚ, ℤ[i], ℚ[i], not on ℕ), so even `2 - 1` is a ℤ to the checker: the class system tracks *which class an operation lands in*, not the value.  Declare the result `\ZZ`.

### 15.8 A glance at the binary program

The first lines of `lib/prelude.bin.imo` (declarations, then the definitions of ⊤ and ⊥):

```text
{{HEAD:lib/prelude.bin.imo:6}}
```

Everything above — classes, facts, definitions — is made of `1`, `0`, `.`, spaces, parentheses and newlines.
