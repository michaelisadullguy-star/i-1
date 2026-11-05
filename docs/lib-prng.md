# Pseudo-random numbers, low-discrepancy sequences and hashes (`lib/prng.imo`)

Fifteen functions in the human notation (`libsrc/prng.hum.imo`, translated by `libsrc/build.sh`).  i-1 has no hidden state, so a **generator is a function from a state to the next state**
(natural numbers); the output is the state itself.  The same seed gives the same numbers in every implementation, and a shuffle or a sample is a pure function of the seed.

| function | class | meaning |
|:--|:--|:--|
| `minstd s` | ℕ → ℕ | the minimal standard generator of Lehmer, `48271·s mod (2³¹−1)`, for `0 < s < 2³¹−1`; all bits are good |
| `lcgansi s`, `lcgmmix s` | ℕ → ℕ | linear congruential generators modulo 2³¹ (`1103515245·s+12345`) and 2⁶⁴ (the constants of Knuth's MMIX); the low bits have short periods, use the high ones |
| `xorshift32 s`, `xorshift64 s` | ℕ → ℕ | the xorshift generators of Marsaglia (13, 17, 5 and 13, 7, 17), computed on a register of Booleans; the state is taken modulo 2³² or 2⁶⁴ and must not be 0 |
| `prngstream next seed n` | (ℕ→ℕ) → ℕ → ℕ → 𝔏 ℕ | the first `n` states after the seed: `prngstream(minstd, 7, 3)` |
| `prngbelow next seed bound n` | (ℕ→ℕ) → ℕ → ℕ → ℕ → 𝔏 ℕ | `n` numbers below `bound`, the remainders of the states |
| `shuffle next seed xs` | (ℕ→ℕ) → ℕ → 𝔏 α → 𝔏 α | a permutation by successive selection: the state `t` picks the element at the place `t mod (the length of what remains)` |
| `sample next seed k xs` | (ℕ→ℕ) → ℕ → ℕ → 𝔏 α → 𝔏 α | the first `k` elements of the shuffle |
| `choice next seed xs` | (ℕ→ℕ) → ℕ → 𝔏 α → 𝔏 α | `[x]` for one element picked by the next state, `[]` for the empty list |
| `vandercorput b n` | ℕ → ℕ → ℚ | the radical inverse of `n` in the base `b ≥ 2` (the digits of `n` mirrored about the point), exact: `vandercorput(2, 6)` is `3/8` |
| `halton n` | ℕ → ℙ ℚ ℚ | the Halton point `(vandercorput(2, n), vandercorput(3, n))` |
| `fnvhash32 bs`, `fnvhash64 bs`, `djbhash bs` | 𝔏 ℕ → ℕ | the hashes FNV-1a (32 and 64 bits) and djb2 of a list of bytes |

`tests/test_prng.py` (195 checks) compares them with models written in Python (big integers and `Fraction`) and with the known answers: the first `xorshift64` output from the seed 1,
the first `minstd` output from the seed 1, and the FNV-1a hashes of `a`.
