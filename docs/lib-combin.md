# Enumerative combinatorics (`lib/combin.imo`)

Twenty-six functions in the human notation (`libsrc/combin.hum.imo`, translated by `libsrc/build.sh`).  They add the objects themselves, and more counts, to what `lib/numtheory.imo` already has
(`choose`, `factorial`, `catalan`, `bell`, `partitions`, `necklaces`).  **Permutations are lists that contain 0 to n−1 once each**; a function that can fail returns a list of at most one element.

| function | class | meaning |
|:--|:--|:--|
| `pascalrow n`, `pascaltriangle n` | ℕ → 𝔏 ℕ, ℕ → 𝔏 (𝔏 ℕ) | row `n` of Pascal's triangle, and the first `n` rows; built by additions only |
| `multinomial ks` | 𝔏 ℕ → ℕ | `(Σks)! / Πkᵢ!` |
| `multichoose n k` | ℕ → ℕ → ℕ | the multisets of size `k` from `n` kinds, `C(n+k−1, k)` |
| `fallingfactorial n k`, `risingfactorial n k` | ℕ → ℕ → ℕ | `n(n−1)…(n−k+1)` (0 when `k > n`) and `n(n+1)…(n+k−1)` |
| `derangements n` | ℕ → ℕ | the permutations without a fixed point, `Dₙ = n·Dₙ₋₁ + (−1)ⁿ` |
| `rencontres n k` | ℕ → ℕ → ℕ | the permutations of `n` with exactly `k` fixed points |
| `eulerianrow n`, `eulerian n k` | ℕ → 𝔏 ℕ, ℕ → ℕ → ℕ | the Eulerian numbers: permutations of `n` with `k` descents |
| `narayana n k` | ℕ → ℕ → ℕ | the Narayana numbers (Dyck words of semilength `n` with `k` peaks), 0 outside `1 ≤ k ≤ n` |
| `motzkin n`, `schroeder n` | ℕ → ℕ | the Motzkin numbers and the large Schröder numbers |
| `compositions n` | ℕ → 𝔏 (𝔏 ℕ) | all ordered sums of positive parts, in lexicographic order (2ⁿ⁻¹ of them) |
| `partitionlist n` | ℕ → 𝔏 (𝔏 ℕ) | all partitions of `n` with the parts in decreasing order, the largest first: `[n]`, `[n−1, 1]`, …; their number is `partitions(n)` |
| `dyckpaths n` | ℕ → 𝔏 𝕊 | the Dyck words of semilength `n` in the letters `U` and `D`, in lexicographic order with `D` before `U` (Catalan(n) of them) |
| `lyndonwords n k` | ℕ → ℕ → 𝔏 (𝔏 ℕ) | the Lyndon words of length `n` over the letters 0 to `k−1`, in lexicographic order (Duval's algorithm) |
| `lehmer p`, `unlehmer code` | 𝔏 ℕ → 𝔏 ℕ | the Lehmer code of a permutation (how many later entries are smaller) and its inverse |
| `permrank p`, `permunrank n r` | 𝔏 ℕ → ℕ, ℕ → ℕ → 𝔏 (𝔏 ℕ) | the position of a permutation in the lexicographic order, and the permutation of that position (`[]` when `r ≥ n!`) |
| `nextperm p` | 𝔏 ℕ → 𝔏 (𝔏 ℕ) | the next permutation in the lexicographic order, `[]` for the last |
| `inversions p`, `descents p`, `permsign p` | 𝔏 ℕ → ℕ, ℕ, ℤ | the number of inversions, the number of descents and the sign `(−1)^inversions` |
| `setpartitions xs` | 𝔏 α → 𝔏 (𝔏 (𝔏 α)) | all partitions of a list into blocks (`bell(n)` of them): the first element is a block of its own, or joins a block of a partition of the rest |

`tests/test_combin.py` (575 checks) uses oracles that do not share the algorithm: `math.comb` and `math.perm`; inclusion–exclusion for derangements; the explicit sum for the Eulerian numbers and brute force
over `itertools.permutations` for descents, fixed points and ranks; brute force over all words for Dyck words (and, from them, the Narayana numbers) and for Lyndon words (smaller than every rotation); a set of cuts for the compositions; the
recurrences of the Motzkin and Schröder numbers; and restricted growth strings for the set partitions.
