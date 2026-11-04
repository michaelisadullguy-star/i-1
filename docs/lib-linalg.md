# Linear algebra (`lib/linalg.imo`)

Vectors and matrices over the Gaussian rationals ℚ[i], **exactly**.  A vector is a list `List(\Q)`, a matrix is a list of rows
`List(List(\Q))`.  Every algorithm is written in spec notation in `lib/linalg.imo` and runs in the language, on base-(i − 1)
digit strings; the Python host only parses, checks classes and spells digits.

Every pivot, every cofactor and every eigenvalue below is an exact ℚ[i] value, so equality tests (`rref`, `rank`, `nullspace`,
`isinvertible`, …) are decisions, not floating-point guesses.  After every elementary step the entries are brought to canonical
form `⊜` (z/m with gcd(Re z, Im z, m) = 1) — unreduced fractions grow geometrically in elimination and made `pinv` of a 3 × 4 Gaussian
matrix take hours before this was added.  Rows and columns count from 0.

## Operators

The human operators are overloaded on matrices; the class checker picks the overload from the classes of the arguments:

| expression | meaning |
|:--|:--|
| `A + B`, `A - B`, `-A` | entrywise sum, difference, negation (`madd`, `msub`, `mneg`) |
| `A * B` | matrix product (`mmul`) |
| `A * v` | matrix times vector (`mvec`) |
| `c * A` | scalar times matrix (`mscale`) |
| `A ^ n` | integer power, `A ^ -1` the inverse (`mpow`) |

Scalars keep their old meaning (`1 + 2`, `(1 + i) * (2 - i)`).  To make mixed list literals such as `[[1, 1/2], [i, 3]]` check, the class
checker (`pymo/imotypes.py`) now computes the least common superclass (`join`) of the classes of a list literal's elements.

## Functions

`M` stands for `List(List(\Q))`, `V` for `List(\Q)`.

### Vectors

| name | class | meaning |
|:--|:--|:--|
| `vadd(u, v)`, `vsub(u, v)`, `vneg(u)` | `V -> V -> V`, `V -> V` | entrywise sum, difference, negation |
| `vscale(c, v)` | `\Q -> V -> V` | c·v |
| `dot(u, v)` | `V -> V -> \Q` | Σ uₖ vₖ (no conjugation) |
| `hdot(u, v)` | `V -> V -> \Q` | Hermitian inner product ⟨u, v⟩ = Σ conj(uₖ)·vₖ |
| `vnorm2(v)` | `V -> \QQ` | Σ \|vₖ\|² (exact) |
| `vnorm(v)` | `V -> \RR` | √(Σ \|vₖ\|²) as a lazy real |
| `proj(u, v)` | `V -> V -> V` | the orthogonal projection of u onto v (0 when v = 0) |
| `outer(u, v)` | `V -> V -> M` | u vᵀ |
| `cross(u, v)` | `V -> V -> V` | cross product of two vectors of length 3 |
| `gramschmidt(vs)` | `M -> M` | Gram–Schmidt orthogonalisation of a list of vectors w.r.t. the Hermitian product; vectors that depend on the previous ones are dropped (orthogonal, not normalised: normalising needs square roots) |

### Matrix construction and arithmetic

| name | class | meaning |
|:--|:--|:--|
| `idm(n)`, `unitv(n, k)` | `\NN -> M`, `\NN -> \NN -> V` | the identity matrix, the unit vector eₖ of length n |
| `zeros(m, n)` | `\NN -> \NN -> M` | the m × n zero matrix |
| `diagm(v)`, `mdiag(A)` | `V -> M`, `M -> V` | the diagonal matrix with diagonal v; the diagonal of A |
| `transpose(A)`, `htranspose(A)` | `M -> M` | transpose, conjugate transpose |
| `madd`, `msub`, `mneg`, `mscale`, `mmul`, `mvec` | as the operators above | |
| `hadamard(A, B)` | `M -> M -> M` | entrywise product |
| `kron(A, B)` | `M -> M -> M` | Kronecker product |
| `blockdiag(A, B)` | `M -> M -> M` | diag(A, B) |
| `trace(A)` | `M -> \Q` | sum of the diagonal |
| `mpow(A, n)` | `M -> \ZZ -> M` | Aⁿ by repeated squaring; n < 0 uses the inverse (a singular A gives garbage for n < 0) |

### Predicates

`issymmetric`, `ishermitian`, `isunitary` (Aᴴ A = I), `isdiagonal`, `isupper`, `islower`, `isinvertible` (det A ≠ 0): `M -> Bool`.

### Elimination, subspaces, determinants

| name | class | meaning |
|:--|:--|:--|
| `rref(A)` | `M -> M` | the reduced row echelon form (pivots 1, zero rows last) |
| `rank(A)` | `M -> \NN` | the number of pivots |
| `rowspace(A)`, `colspace(A)` | `M -> M` | bases: the non-zero rows of the reduced form; the pivot columns of A (as vectors) |
| `nullspace(A)` | `M -> M` | a basis of {x : A x = 0}, one vector per free column |
| `det(A)` | `M -> \Q` | determinant by elimination (1 for the empty matrix) |
| `minor(A, i, j)`, `cofactor(A, i, j)` | `M -> \NN -> \NN -> \Q` | det of A without row i and column j; (−1)^(i+j) times it |
| `adjugate(A)` | `M -> M` | the transpose of the cofactor matrix: A·adj(A) = det(A)·I |
| `inverse(A)`, `solve(A, b)` | `M -> M`, `M -> V -> V` | for invertible A (garbage for singular A; test with `isinvertible`) |
| `linsolve(A, b)` | `M -> V -> Pair(Bool, Pair(V, M))` | all solutions of A x = b: (consistent?, (a particular solution, a basis of the kernel)); the solutions are x₀ + Σ cₖ nₖ |
| `lu(A)` | `M -> Pair(M, Pair(M, M))` | (P, (L, U)) with P A = L U, P a permutation matrix, L unit lower triangular, U upper triangular; works for singular matrices and zero pivots |
| `pinv(A)` | `M -> M` | the Moore–Penrose pseudo-inverse of any matrix, exact (A⁺ = Gᴴ (G Gᴴ)⁻¹ (Fᴴ F)⁻¹ Fᴴ for a rank factorisation A = F G) |
| `lstsq(A, b)` | `M -> V -> V` | the least-squares solution of minimal norm, A⁺ b |
| `smith(A)` | `List(List(\ZZ)) -> List(\NN)` | the invariant factors of an integer matrix (the non-zero diagonal of the Smith normal form, d₁ \| d₂ \| …); exponential in the size: small matrices only |

### Characteristic polynomial, eigenvalues

| name | class | meaning |
|:--|:--|:--|
| `charpoly(A)` | `M -> V` | det(xI − A) as a coefficient list, lowest degree first, monic (Faddeev–LeVerrier) |
| `minpoly(A)` | `M -> V` | the minimal polynomial: the monic polynomial of least degree annihilating A (Krylov) |
| `eigenvals(A)` | `M -> List(Pair(\Q, \NN))` | the eigenvalues in ℚ(i) with algebraic multiplicity, sorted by (Re, Im) — exact, from the rational roots of charpoly (`ratroots`); an eigenvalue like √2 is not listed |
| `eigvals(A)` | `M -> List(\R)` | **all** eigenvalues with multiplicity as lazy complex numbers (element n within 2⁻ⁿ; numerical, from `croots`) |
| `eigvecs(A, λ)` | `M -> \Q -> M` | a basis of the eigenspace {x : A x = λ x} (empty if λ is not an eigenvalue) |
| `matexp(A)` | `M -> Stream(M)` | e^A: element n is the partial sum Σ_(j ≤ n) Aʲ/j! (exact entries; the tail is bounded by ‖A‖ⁿ⁺¹/(n + 1)!) |

## Tests

`tests/test_linalg.py` — a human-notation program (128 statements) covering every public function with random exact matrices (real and
Gaussian, square and rectangular, singular, rank-deficient, with a zero leading pivot), decoded and compared with an independent Python
reference over exact fractions (Gauss–Jordan, Laplace expansion, Faddeev–LeVerrier, the four Penrose equations for `pinv`, P A = L U
for `lu`, an integer row/column reduction for `smith`, the exact partial sums of the exponential series).  About three minutes.
