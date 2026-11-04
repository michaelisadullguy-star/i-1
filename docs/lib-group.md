# Group theory — `lib/group.imo`

Part 18 of the prelude: permutations, finite permutation groups, subgroups, cosets, conjugacy, Sylow subgroups, all subgroups,
isomorphism, abelian invariants, actions (orbits, Burnside, colourings) and constructions (direct and semidirect products,
Cayley's theorem).  Everything is computed **in the language**, in spec notation; the host only parses, checks classes and
spells digits.  Tests: `python3 tests/test_group.py` (240 checks against independent python computations, about 35 s).

## Conventions

* **A permutation** of {0, …, n − 1} is the list of its images, class `𝔏 ℕ` (`List(\NN)`): `[1, 2, 0]` maps 0 ↦ 1, 1 ↦ 2, 2 ↦ 0.
  Composition is **right to left**: `pcompose(p, q)` is p ∘ q, (p ∘ q)(i) = p(q(i)).  A permutation of fewer points is
  extended by fixed points, so permutations of different lengths can be mixed everywhere (the *degree* of a list of
  permutations is the largest length).
* **A finite group** is the sorted list (lexicographic order) of its elements, class `𝔏 (𝔏 ℕ)`.  Every function that takes
  a group first pads its elements to one degree, sorts them and removes repetitions, so an unsorted list or a list with
  repetitions is accepted; results are always sorted.  The trivial group of degree 0 is `[[]]` (`symgroup(0)`,
  `cyclicgroup(0)`, `generate([])`).
* **Group or not.**  `isgroup(G)` tests that G is non-empty, consists of permutations and is closed under composition (closure is
  tested with a few generators: elements outside the subgroup generated so far are added until it covers G; the search stops
  as soon as it outgrows G).  Functions that need a group return a documented default for a list that is not one: `[]`
  (lists), `false` (predicates), `0` (numbers).  Functions marked *any list* need no group: they are defined for any list of
  permutations (e.g. the orbit under the group *generated* by a list of generators).
* **Inside**, a point is a unary natural (a list of ⊤) and a permutation a list of such points: an image is read off by walking
  the list, and two points are compared digit by digit.  ℕ numerals are converted at the boundary (an out-of-range entry costs
  O(n), never O(value)).  Orders, counts and positions are unary until they are spelled as ℕ.
* **Cost.**  A composition of degree n costs O(n²) steps; the closure of k generators into a group of order N costs about
  N·k compositions plus sorting.  Groups up to order ~48 and degree ~16 are practical; `subgroups` and `isomorphic` are
  meant for orders up to ~24–32 (see the table).

## Permutations

| human | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `pid(n)` | ℕ → 𝔏 ℕ | identity [0, …, n − 1] | `⍳ n` |
| `isperm(p)` | 𝔏 ℕ → 𝔹 | is p a permutation of {0, …, len − 1}? | sorted entries = 0 … len − 1 |
| `pcompose(p, q)` | 𝔏 ℕ → 𝔏 ℕ → 𝔏 ℕ | p ∘ q, (p ∘ q)(i) = p(q(i)) | shorter one padded |
| `pinverse(p)` | 𝔏 ℕ → 𝔏 ℕ | p⁻¹ | position of each point |
| `papply(p, i)` | 𝔏 ℕ → ℕ → ℕ | p(i); i itself beyond the list | |
| `porder(p)` | 𝔏 ℕ → ℕ | order: lcm of the cycle lengths | cycle walk stops at the first smaller point |
| `ppow(p, k)` | 𝔏 ℕ → ℤ → 𝔏 ℕ | pᵏ, k ∈ ℤ (negative allowed) | k mod order, square and multiply |
| `pcycles(p)` | 𝔏 ℕ → 𝔏 (𝔏 ℕ) | cycles of length ≥ 2, each from its least point, sorted by it | |
| `fromcycles(n, cs)` | ℕ → 𝔏 (𝔏 ℕ) → 𝔏 ℕ | the permutation of max(n, 1 + largest point) points with cycles cs; overlapping cycles compose as c₁ ∘ c₂ ∘ … | a cycle is a product of transpositions, so any list of points is accepted |
| `psign(p)` | 𝔏 ℕ → ℤ | sign: 1 or −1 | parity of the number of even-length cycles |
| `iseven(p)` | 𝔏 ℕ → 𝔹 | is p even? | as `psign` |
| `cycletype(p)` | 𝔏 ℕ → 𝔏 ℕ | all cycle lengths, fixed points included, decreasing (a partition of n) | |
| `pconj(p, q)` | 𝔏 ℕ → 𝔏 ℕ → 𝔏 ℕ | q p q⁻¹ | |

Preconditions: the arguments are permutations (`isperm`); for other lists the results are unspecified but every function
terminates (cycle walks carry n steps of fuel).

## Constructing groups

| human | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `generate(gens)` | 𝔏 (𝔏 ℕ) → 𝔏 (𝔏 ℕ) | all elements of the generated group, sorted; `generate([]) = [[]]` | breadth-first closure: each layer is the sorted products of the previous layer with the generators minus the known elements (sorted-set merges, no linear membership) |
| `symgroup(n)` | ℕ → 𝔏 (𝔏 ℕ) | Sₙ, all n! permutations, sorted | n! elements: n ≤ 5 in practice |
| `altgroup(n)` | ℕ → 𝔏 (𝔏 ℕ) | Aₙ, the even permutations | filter of Sₙ |
| `cyclicgroup(n)` | ℕ → 𝔏 (𝔏 ℕ) | Cₙ, the n rotations of n points | |
| `dihedralgroup(n)` | ℕ → 𝔏 (𝔏 ℕ) | the group of order 2n of the n-gon on its n vertices (n ≥ 3); D₁ = C₂ on 2 points, D₂ = V₄ on 4 points, D₀ = [[]] | rotations i ↦ i + k and reflections i ↦ k − i |
| `kleingroup` | 𝔏 (𝔏 ℕ) | V₄ = {id, (0 1)(2 3), (0 2)(1 3), (0 3)(1 2)} | literal |
| `quaterniongroup` | 𝔏 (𝔏 ℕ) | Q₈ = {±1, ±i, ±j, ±k} on 8 points (positions of 1, −1, i, −i, j, −j, k, −k) | the units of the **Cayley–Dickson tower** (`𝕛`, `𝕜` in 𝔻) multiplied with `⊠𝔻`, mapped to permutations by `regular` |
| `regular(xs, op)` | 𝔏 A → (A → A → A) → 𝔏 (𝔏 ℕ) for A = ℕ, ℤ, ℚ, ℤ[i], ℚ[i], 𝔻 (`regular𝔻`), permutations 𝔏 ℕ (`regularᵖ`), matrices 𝔏 (𝔏 ℚ[i]) (`regularᵐ`) | **Cayley's theorem**: the left multiplications x ↦ g·x as permutations of the positions of the distinct elements | `[]` unless the elements form a group: every product is in the list, every x ↦ g·x is a bijection, g ↦ (x ↦ g·x) is injective and L_a ∘ L_b = L_(a·b) (associativity); the last check is O(n⁴), small n |
| `directproduct(G, H)` | 𝔏 (𝔏 ℕ) → 𝔏 (𝔏 ℕ) → 𝔏 (𝔏 ℕ) | G × H on disjoint points: (g, h) acts as g on 0 … n − 1 and as h shifted by n | already sorted |
| `semidirect(m, n, a)` | ℕ → ℕ → ℕ → 𝔏 (𝔏 ℕ) | ℤ/m ⋊ ℤ/n, the generator of ℤ/n acting by x ↦ a·x; (b, j)(b′, j′) = (b + aʲ b′, j + j′), as its regular permutation group on m·n points ((b, j) is the point b + m j) | generated by the left multiplications by (1, 0) and (0, 1); `[]` unless m, n ≥ 1, gcd(a, m) = 1 and aⁿ ≡ 1 (mod m).  `semidirect(n, 2, n − 1)` is Dₙ, `semidirect(4, 4, 3)` is C₄ ⋊ C₄, `semidirect(3, 4, 2)` the dicyclic group of order 12 |

## Structure

| human | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `grouporder(G)` | 𝔏 (𝔏 ℕ) → ℕ | number of distinct elements | *any list* |
| `isgroup(G)` | 𝔏 (𝔏 ℕ) → 𝔹 | non-empty, permutations, closed | greedy generators, bounded closure |
| `issubgroup(H, G)` | → 𝔹 | G a group and H ⊆ G a non-empty closed subset | sorted-set inclusion, closure as `isgroup` |
| `isnormal(H, G)` | → 𝔹 | H a subgroup with g H g⁻¹ = H for every g ∈ G | normalizer = G |
| `leftcosets(H, G)` | → 𝔏 (𝔏 (𝔏 ℕ)) | the cosets gH, each sorted, in order of their least element | the least element g left, its coset sorted and removed (sorted difference); `[]` unless H ≤ G |
| `rightcosets(H, G)` | → 𝔏 (𝔏 (𝔏 ℕ)) | the cosets Hg, likewise | `[]` unless H ≤ G |
| `index(H, G)` | → ℕ | [G : H] = \|G\| / \|H\| | 0 unless H ≤ G |
| `conjclasses(G)` | → 𝔏 (𝔏 (𝔏 ℕ)) | the conjugacy classes, each sorted, in order of their least element | as cosets, with x g x⁻¹; `[]` unless a group |
| `center(G)` | → 𝔏 (𝔏 ℕ) | Z(G): elements commuting with all | *any list* (the elements that commute with every listed one) |
| `centralizer(x, G)` | 𝔏 ℕ → 𝔏 (𝔏 ℕ) → 𝔏 (𝔏 ℕ) | C_G(x) | *any list*; x and G padded to one degree |
| `normalizer(H, G)` | → 𝔏 (𝔏 ℕ) | N_G(H) = {g : g H g⁻¹ = H} | *any lists*; H any set of permutations |
| `commutatorsubgroup(G)` | → 𝔏 (𝔏 ℕ) | G′ = [G, G] | closure of all commutators a b a⁻¹ b⁻¹ (O(\|G\|²) of them); `[]` unless a group |
| `issolvable(G)` | → 𝔹 | the derived series reaches 1 | stops when G⁽ᵏ⁺¹⁾ = G⁽ᵏ⁾ ≠ 1; false unless a group.  A₅ (order 60) takes ~4 s |
| `isabelian(G)` | → 𝔹 | all elements commute | false unless a group |
| `iscyclic(G)` | → 𝔹 | an element of order \|G\| exists | false unless a group |
| `elementorders(G)` | → 𝔏 (𝔓 ℕ ℕ) | pairs (order, number of elements of that order), increasing order | `[]` unless a group |
| `exponent(G)` | → ℕ | lcm of the element orders | 0 unless a group |
| `cayleytable(G)` | → 𝔏 (𝔏 ℕ) | entry (i, j) = k with gᵢ ∘ gⱼ = g_k (positions in the sorted list) | per row two sorts (by product, then back by position) instead of searches; a row that is not a permutation of G means G is not a group → `[]` |
| `sylow(G, p)` | 𝔏 (𝔏 ℕ) → ℕ → 𝔏 (𝔏 ℕ) | one Sylow p-subgroup (order the p-part of \|G\|) | P := 1; while \|P\| < pᵃ: some x ∈ N_G(P) ∖ P with xᵖ ∈ P exists (Cauchy in N(P)/P), P := ⟨P, x⟩.  The trivial subgroup when p is not a prime or p ∤ \|G\| (a huge p is clamped to \|G\| + 1 first); `[]` unless a group |
| `subgroups(G)` | → 𝔏 (𝔏 (𝔏 ℕ)) | all subgroups, by increasing order, then lexicographically | the cyclic subgroups, then joins ⟨H, c⟩ of every new subgroup with every cyclic c (skipped when one contains the other), until nothing new; subgroups carry a few generators so a join is a small closure.  S₄ (30 subgroups) ~3 s, C₄ ⋊ C₄ (15) ~3 s, S₄ × C₂ (order 48, 98 subgroups) ~65 s; meant for orders ≲ 24 |
| `abelianinvariants(G)` | → 𝔏 ℕ | invariant factors d₁ ∣ d₂ ∣ … (all > 1) of the abelianization G/G′ (of G itself if abelian); `[]` for a perfect group | G/G′ ≅ ℤᵏ / L where k generators are chosen greedily and L is spanned by the edge relations coord(y) + e_s − coord(y s) of the Cayley graph (the Schreier generators of the relation module); a **Smith normal form** of these rows, written here on digit strings 𝔇 (Euclid on rows, column swaps when the pivot row has a remainder), then the diagonal is turned into a divisibility chain by (gcd, lcm) |

## Invariants and isomorphism

| human | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `sameinvariants(G, H)` | → 𝔹 | order, element-order statistics, centre size, and the abelian / cyclic / solvable flags agree | **not a proof of isomorphism**: C₄ ⋊ C₄ and C₂ × Q₈ agree in all of these and are not isomorphic (their abelianizations differ); false unless both are groups |
| `isomorphic(G, H)` | → 𝔹 | are G and H isomorphic? (a real test) | equal orders and element-order statistics first; then a generating list s₁ … s_k of G (greedy, elements of largest order first) and a search over images τᵢ ∈ H of the same orders, τ₁ only up to conjugacy in H, pairs pruned by ord(τᵢ τⱼ) = ord(sᵢ sⱼ); the map induced along a breadth-first spanning tree of the Cayley graph must respect **every** edge (then it is a homomorphism) and be injective.  Exponential in k; order-16 groups take seconds (the C₄ ⋊ C₄ / C₂ × Q₈ pair 2–4 s), S₄ against its regular representation on 24 points ~5 s; meant for orders ≲ 32 |

## Actions and counting

| human | class | meaning | algorithm / limits |
|:--|:--|:--|:--|
| `orbit(G, i)` | 𝔏 (𝔏 ℕ) → ℕ → 𝔏 ℕ | the orbit of i under the group generated by G, sorted; [i] beyond the degree | *any list* (generators suffice): closure of a set of points |
| `orbits(G)` | 𝔏 (𝔏 ℕ) → 𝔏 (𝔏 ℕ) | all orbits on 0 … n − 1, each sorted, by least point | *any list* |
| `stabilizer(G, i)` | 𝔏 (𝔏 ℕ) → ℕ → 𝔏 (𝔏 ℕ) | {g : g(i) = i}; all of G beyond the degree | *any list* |
| `burnside(G)` | 𝔏 (𝔏 ℕ) → ℕ | number of orbits on 0 … n − 1 by **Burnside's lemma**: (1/\|G\|) Σ fix(g) | 0 unless a group |
| `colorings(G, k)` | 𝔏 (𝔏 ℕ) → ℕ → ℕ | colourings of the n points with k colours up to G: (1/\|G\|) Σ k^c(g), c(g) the number of cycles | 0 unless a group |
| `necklaces(n, k)` | ℕ → ℕ → ℕ | necklaces of n beads, k colours (up to rotation) | `colorings` of Cₙ; necklaces(0, k) = 1 |
| `bracelets(n, k)` | ℕ → ℕ → ℕ | bracelets (up to rotation and reflection) | the dihedral action on n points (also for n ≤ 2) |

## Human names

Every function above is named in `docs/doc2.sbl` between `⍝ ==== <group>` and `⍝ ==== </group>`; `regular` is the overload set
`regular | regular𝔻 | regularᵖ | regularᵐ` (numbers, Cayley–Dickson trees, permutations, matrices).  Helpers end in `_gr`.

```text
G in List(List(\NN)) := generate([[1, 2, 3, 0], [3, 2, 1, 0]])      -- D₄ on the square's vertices
n in \NN := grouporder(G)                                            -- 8
c in List(List(List(\NN))) := conjclasses(G)                         -- 5 classes
q in Bool := isomorphic(G, quaterniongroup)                          -- false
a in List(\NN) := abelianinvariants(G)                               -- [2, 2]
b in \NN := bracelets(6, 2)                                          -- 13
Q in List(List(\NN)) := regular([(1 in \D), (-1 in \D), j, -j, k, -k, (i in \D), (-i in \D)], x in \D |-> y in \D |-> x * y)
```
