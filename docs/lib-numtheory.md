# Number theory over ℤ and ℤ[i] (`lib/numtheory.imo`)

Part 15 of the prelude: primes, factorisation, arithmetic functions, modular arithmetic, quadratic symbols, discrete logarithms,
continued fractions, combinatorial sequences, and the arithmetic of the Gaussian integers.  Like everything else in the language,
every algorithm runs **in the language** on base-(i − 1) digit strings (`𝔇`); the Python host only parses, checks classes and spells
digits.  The tests are in `tests/test_numtheory.py` (a human-notation program compared with independent Python computations).

## How base i − 1 is used

* **Parity and residues from the digits.**  A real integer has digit d₁ = 0 and d₂ = d₃, so n mod 2 = d₀, n mod 4 = d₀ + 2d₃ and,
  for odd n, n ≡ 3 or 5 (mod 8) exactly when d₃ ⊻ d₄.  The binary Jacobi algorithm, the Kronecker symbol and Tonelli–Shanks read these
  digits instead of dividing.
* **The prime above 2 is the base.**  (1 + i) = −i·(i − 1) divides z exactly when its last digit is 0, and dropping that digit divides
  by i − 1.  The power of 2 in an integer, and the exponent of 1 + i in a Gaussian factorisation, are counted from the trailing zero
  digits (two digits per factor 2, since 2 = i·(i − 1)², followed by a unit correction).
* **Montgomery arithmetic in base 4.**  Since (i − 1)⁴ = −4, dropping four zero digits of a multiple of 4 divides it by −4.  Modulo an
  odd N every product is reduced by REDC with R = (−4)ᵐ: the multiple c·N (c ∈ {0, 1, 2, 3}) that makes the value ≡ 0 (mod 4) is read
  off the digits d₀, d₃ of the value and of N, and four digits are dropped — no division and no comparison inside the loop.
  `powmod`, Miller–Rabin, the strong Lucas test, Pollard ρ, Tonelli–Shanks, orders, primitive roots and baby-step giant-step all
  multiply in this form.  Even moduli use long division (`⫽ᶻ`); modulus 0 means plain arithmetic in ℤ.
* **ℤ[i] is native.**  Gaussian gcds, factorisations into Gaussian primes and sums of two squares are computed with the same digit
  strings as the integers; normalised Gaussian integers have Re > 0, Im ≥ 0 (`⌜ᶻ`).

## Conventions

* Total functions: every public function returns a documented value for every argument of its class — 0, −1, false or the empty
  list where the mathematical object does not exist (for example `modinv(6, 9) = 0`, `sqrtmod(3, 7) = −1`, `dlog(2, 3, 8) = −1`,
  `primroot(8) = 0`, `factor(0) = []`).  None of them diverges on a valid argument.
* A modulus n is a natural number; **n = 0 means "no reduction"** (computation in ℤ) wherever that makes sense (`powmod`, `modinv`,
  `crt`, `ordmod`, `sqrtmod`, `dlog`).
* Results are canonical: integers are written with denominator 1, rationals in lowest terms.

## Performance

The evaluator costs about 10 µs per step on one digit, and an n-bit number has about 2n digits, so a modular multiplication of
40-bit numbers costs some 70 ms.  Measured on Pymo:

| task | time |
|:--|--:|
| `isprime` of a 30-bit prime / of 999999999989 (≈ 10¹²) | 7 s / 20 s |
| `isprime(n)` for n < 1849 (trial division) | about 40 ms |
| `factor(600851475143)` (71·839·1471·6857) | 20 s |
| `factor(9998000099)` (99989·99991, Pollard ρ) / `factor(999962000357)` (two 6-digit primes) | 45 s / 95 s |
| `nextprime(10¹²)` | 45 s |
| `dlog` modulo 10⁶ (baby-step giant-step, √n ≈ 1000 steps) | about a minute |
| `primepi(10⁴)` (sieve) / `nthprime(1000)` | 5 s / 5.5 s |
| `partitions(300)` / `bernoulli(40)` | 14 s / 19 s |
| `isprime(3317044064679887385961981)` = false (ψ₁₃ itself: passes all 13 Miller–Rabin bases, fails the strong Lucas test) | 560 s |

## Functions

Every function below has the same human name in doc 2 (`stirling1`/`stirling2` stand for the spec symbols `stirling₁`/`stirling₂`).
"ℤ[i]" overloads are chosen by the class checker when an argument is a Gaussian integer (in the human notation write e.g.
`egcd(4 + 2 * i, 3 + i)`, or `5 + 0 * i` for a real Gaussian integer).

### Modular arithmetic

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `egcd(a, b)` | ℤ → ℤ → 𝔓 ℕ (𝔓 ℤ ℤ); ℤ[i] → ℤ[i] → 𝔓 ℤ[i] (𝔓 ℤ[i] ℤ[i]) | Bézout: (g, (s, t)) with s·a + t·b = g = gcd(a, b); g ≥ 0 on ℤ, normalised on ℤ[i]; egcd(0, 0) = (0, (0, 0)) | extended Euclid (natural division on ℤ, nearest Gaussian quotient on ℤ[i]; the Gaussian gcd is normalised by a unit that also multiplies s and t) |
| `modinv(a, n)` | ℕ → ℕ → ℕ; ℤ → ℕ → ℤ; ℤ[i] → ℤ[i] → ℤ[i] | a⁻¹ mod n in [0, n); 0 when gcd(a, n) ≠ 1; modulo 0: a when a = ±1, else 0; on ℤ[i] reduced by `rem`, 0 when not invertible | extended Euclid |
| `powmod(a, e, n)` | ℕ → ℤ → ℕ → ℕ; ℤ → ℤ → ℕ → ℤ | aᵉ mod n in [0, n); e < 0 through modinv (so 0 when a is not invertible); modulo 0: aᵉ in ℤ | right-to-left square and multiply, Montgomery products for odd n |
| `crt(as, ms)` | 𝔏 ℤ → 𝔏 ℕ → 𝔓 𝔹 (𝔓 ℕ ℕ) | Chinese remainders for arbitrary (not necessarily coprime) moduli: (true, (x, M)), x ≡ aₖ (mod mₖ), 0 ≤ x < M = lcm(mₖ); (false, (0, 0)) when inconsistent; crt([], []) = (true, (0, 1)); a modulus 0 asks for equality (then M = 0) | pairwise merging with g = gcd(M, m): solvable iff g ∣ a − x; the lists are paired up to the shorter one |
| `ordmod(a, n)` | ℤ → ℕ → ℕ | multiplicative order of a mod n; 0 when gcd(a, n) ≠ 1; ordmod(a, 1) = 1; modulo 0 the order in ℤ (1 for 1, 2 for −1, else 0) | divides the prime factors out of Carmichael's λ(n) |
| `primroot(n)` | ℕ → ℕ | least primitive root mod n; 0 when none exists (n not 2, 4, pᵉ, 2pᵉ; primroot(0) = primroot(1) = 0) | test g = 1, 2, …: g^(φ/q) ≢ 1 for every prime q ∣ φ(n) |
| `primitiveroots(n)` | ℕ → 𝔏 ℕ | all primitive roots mod n, ascending; [] when none | gᵏ for k ≤ φ(n) prime to φ(n), sorted; O(n) products |
| `dlog(a, b, n)` | ℤ → ℤ → ℕ → ℤ | the least x ≥ 0 with aˣ ≡ b (mod n), −1 when none (a need not be coprime to n; modulo 0 in ℤ) | while g = gcd(a, n) > 1 the congruence is divided by g; then baby-step giant-step with sorted lists; O(√n) time and memory |
| `quadresidues(n)` | ℕ → 𝔏 ℕ | the distinct squares x² mod n, ascending (with 0); [] for n = 0 | squares by differences, merge sort; O(n) |
| `totatives(n)` | ℕ → 𝔏 ℕ | the k ∈ [1, n] with gcd(k, n) = 1 | filter |
| `iscoprime(a, b)` | ℤ → ℤ → 𝔹; ℤ[i] → ℤ[i] → 𝔹 | gcd(a, b) = 1 (a unit, on ℤ[i]) | gcd |

### Quadratic symbols and square roots

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `jacobi(a, n)` | ℤ → ℕ → ℤ | Jacobi symbol for odd n > 0; 0 for even n or n = 0 | binary algorithm: factors 2 from trailing zero digits, reciprocity from d₀, d₃ |
| `legendre(a, p)` | ℤ → ℕ → ℤ | Legendre symbol for an odd prime p | the Jacobi symbol (equal for prime p) |
| `kronecker(a, n)` | ℤ → ℤ → ℤ | Kronecker symbol for all integers n: (a/0) = [a = ±1], (a/−1) = sign, (a/2) from a mod 8 | the Jacobi symbol after removing 2ᵏ and the sign |
| `eulercriterion(a, n)` | ℤ → ℕ → ℤ | a^((n−1)/2) mod n with n − 1 written −1 (the Legendre symbol for an odd prime n); a^⌊(n−1)/2⌋ mod n for other n ≥ 1, 0 for n = 0 | powmod |
| `sqrtmod(a, n)` | ℤ → ℕ → ℤ | the least x ≥ 0 with x² ≡ a (mod n), −1 when none; modulo 0 the exact integer square root or −1 | odd prime n: aʳ with r = (n+1)/4 when n ≡ 3 (mod 4), else Tonelli–Shanks with the least non-residue; then min(x, n − x).  Other n: search over x < n, O(n) |

### Primes

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `isprime(n)` | ℤ → 𝔹 | n is prime (false for n < 2) | list below 42, trial division below 43² = 1849, else gcd with 2·3·…·41 and strong (Miller–Rabin) tests to the bases 2, 3, …, 41, stopping as soon as n < ψₖ (A014233): deterministic below ψ₁₃ = 3317044064679887385961981 ≈ 3.3·10²⁴.  Above ψ₁₃: all 13 bases **and** the strong Lucas test — the Baillie–PSW test, for which no counterexample is known (not a proof of primality).  Cost: ≈ 20 s at 10¹², ≈ 10 min above ψ₁₃ (ψ₁₃ itself, a strong pseudoprime to all 13 bases, is correctly found composite by the Lucas test in 560 s) |
| `islucasprp(n)` | ℤ → 𝔹 | strong Lucas probable prime with Selfridge's parameters (D first of 5, −7, 9, −11, … with (D/n) = −1, P = 1, Q = (1 − D)/4); primes pass, squares and even n > 2 fail | U, V, Qᵏ by doubling over the bits of d (n + 1 = d·2ˢ), Montgomery products; strong pseudoprimes such as 5777 pass, as they should |
| `wilson(n)` | ℤ → 𝔹 | Wilson's test (n − 1)! ≡ −1 (mod n), n ≥ 2: exactly the primes | O(n) modular products — a demonstration, not a fast test |
| `nextprime(n)` | ℤ → ℕ | least prime > n (2 for n < 2) | isprime on odd candidates |
| `prevprime(n)` | ℤ → ℕ | greatest prime < n; 0 for n ≤ 2 | isprime on odd candidates |
| `primes(n)` | ℤ → 𝔏 ℕ | all primes ≤ n, ascending ([] for n < 2) | sieve of Eratosthenes on the odd numbers with periodic Boolean streams (no arithmetic in the inner loop); about n·π(√n) cheap steps |
| `primepi(n)` | ℤ → ℕ | π(n) | length of the sieve |
| `nthprime(k)` | ℕ → ℕ | the k-th prime (nthprime(1) = 2, nthprime(0) = 0) | sieve up to k·(L + 3), L the number of digits of k (a bound above k(ln k + ln ln k)) |
| `isprimepower(n)` | ℤ → 𝔹 | n = pᵏ, p prime, k ≥ 1 (n > 0) | factor |

### Factorisation and arithmetic functions

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `factor(n)` | ℤ → 𝔏 (𝔓 ℕ ℕ) | prime factorisation of \|n\|: (p, e), p ascending; factor(0) = factor(±1) = [] | power of 2 from the digits; trial division by 3 … 47 (stops at p² > rest); a rest < 53² is prime; isprime; Brent's variant of Pollard ρ (x ↦ x² + c in Montgomery form, 32 differences per gcd, back-tracking on collapse, next c on failure); practical to about 10¹² |
| `primefactors(n)` | ℤ → 𝔏 ℕ | the distinct primes dividing \|n\| | factor |
| `divisors(n)` | ℤ → 𝔏 ℕ | positive divisors of \|n\| ascending; [] for 0 | merging the sorted lists L·pʲ |
| `numdivisors(n)` | ℤ → ℕ | τ(\|n\|); τ(0) = 0 | Π (e + 1) |
| `sigma(k, n)` | ℕ → ℤ → ℕ | σₖ(\|n\|) = Σ dᵏ; σₖ(0) = 0 | Π (1 + pᵏ + … + pᵏᵉ) |
| `totient(n)` | ℤ → ℕ | Euler's φ(\|n\|); φ(0) = 0 | Π pᵉ⁻¹(p − 1) |
| `carmichael(n)` | ℤ → ℕ | Carmichael's λ(\|n\|); λ(0) = 0 | lcm of λ(pᵉ) (λ(2ᵉ) = 2ᵉ⁻² for e ≥ 3) |
| `mobius(n)` | ℤ → ℤ | μ(\|n\|); μ(0) = 0 | factor |
| `liouville(n)` | ℤ → ℤ | (−1)^Ω(n); 0 for 0 | factor |
| `omega(n)`, `bigomega(n)` | ℤ → ℕ | number of distinct / all prime factors | factor |
| `radical(n)` | ℤ → ℕ | product of the distinct primes; rad(0) = 0 | factor |
| `issquarefree(n)` | ℤ → 𝔹 | no square > 1 divides n (false for 0) | factor |
| `isperfect(n)` | ℤ → 𝔹 | n > 0 and σ(n) = 2n | sigma |
| `ramanujansum(q, n)` | ℕ → ℤ → ℤ | Ramanujan's sum c_q(n) = Σ_{d ∣ gcd(q,n)} μ(q/d)·d; c₀ = 0 | divisor sum |
| `gcdlist(xs)` | 𝔏 ℤ → ℕ; 𝔏 ℤ[i] → ℤ[i] | gcd of a list (0 for []) | fold of gcd |
| `lcmlist(xs)` | 𝔏 ℤ → ℕ | lcm of a list (1 for [], 0 if an element is 0) | fold on digits |

### Integer roots, powers, digits

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `iroot(n, k)` | ℕ → ℕ → ℕ | ⌊n^(1/k)⌋; iroot(n, 0) = 0 | Newton from above, start 2^(⌊(L+4)/2k⌋+1) |
| `ispower(n)` | ℤ → 𝔹 | n = aᵏ with k ≥ 2 (true for 0, ±1; negative n needs odd k) | k-th root test for every prime k ≤ log₂ \|n\| |
| `issquare(n)` | ℤ → 𝔹 | n is a perfect square (false for n < 0) | integer square root |
| `digitsum(n, b)` | ℤ → ℕ → ℕ | sum of the base-b digits of \|n\| (b = 1: \|n\|, b = 0: 0) | repeated division |

### Continued fractions and Pell's equation

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `contfrac(q)` | ℚ → 𝔏 ℤ | [a₀; a₁, …, aₖ] of a rational (aₖ ≥ 2 unless k = 0) | Euclid with floor quotients |
| `convergents(as)` | 𝔏 ℤ → 𝔏 ℚ | hₖ/kₖ of [a₀; a₁, …] (a convergent with kₖ = 0 is 0) | the recurrences hₖ = aₖhₖ₋₁ + hₖ₋₂ |
| `cfsqrt(n)` | ℕ → 𝔓 ℕ (𝔏 ℕ) | √n = [a₀; period]: (a₀, period); period [] for squares | m ← da − m, d ← (n − m²)/d, a ← ⌊(a₀ + m)/d⌋ until a = 2a₀ |
| `pell(D)` | ℕ → 𝔓 ℕ ℕ | fundamental solution of x² − Dy² = 1; (1, 0) for D = 0 or a square | convergent number r − 1 (r even) or 2r − 1 (r odd) of √D, r the period length |

### Sequences and special numbers

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `fib(n)` | ℤ → ℤ; ℕ → ℕ | Fibonacci F(n), F(−n) = (−1)ⁿ⁺¹F(n) | fast doubling over the bits of n |
| `lucas(n)` | ℤ → ℤ; ℕ → ℕ | Lucas L(n) = 2F(n+1) − F(n), L(−n) = (−1)ⁿL(n) | fast doubling |
| `catalan(n)` | ℕ → ℕ | C(n) = binom(2n, n)/(n + 1) | choose |
| `bell(n)` | ℕ → ℕ | Bell number (set partitions) | Bell triangle, O(n²) additions |
| `stirling1(n, k)` | ℕ → ℕ → ℤ | signed Stirling numbers of the first kind | rows s(n+1, j) = s(n, j−1) − n·s(n, j) |
| `stirling2(n, k)` | ℕ → ℕ → ℕ | Stirling numbers of the second kind | rows S(n+1, j) = j·S(n, j) + S(n, j−1) |
| `partitions(n)` | ℕ → ℕ | partition number p(n) | Euler's pentagonal recurrence, O(n^1.5) additions |
| `bernoulli(n)` | ℕ → ℚ | Bₙ exactly, B₁ = −1/2 | integer tangent numbers (Brent–Harvey): B₂ₘ = (−1)ᵐ⁻¹·2m·Tₘ/(4ᵐ(4ᵐ − 1)) |
| `zetaeven(n)` | ℕ → ℚ | ζ(2n)/π²ⁿ exactly (1/6, 1/90, …; −1/2 for n = 0) | Tₙ/(2(4ⁿ − 1)(2n − 1)!) |
| `harmonic(n)` | ℕ → ℚ | Hₙ = Σ 1/k exactly (H₀ = 0) | over the common denominator lcm(1 … n) |

### Gaussian integers

| function | class | meaning | algorithm, limits |
|:--|:--|:--|:--|
| `gaussfactor(z)` | ℤ[i] → 𝔓 ℤ[i] (𝔏 (𝔓 ℤ[i] ℕ)) | z = u·Π πᵉ: (unit u, [(π, e)]), π normalised (Re > 0, Im ≥ 0), ordered by norm then imaginary part; (0, []) for 0 | 1 + i from the trailing zero digits; the rest from the factorisation of N(z): q ≡ 3 (mod 4) is prime in ℤ[i], p ≡ 1 (mod 4) splits as π = gcd(p, t + i), π̄, with t² ≡ −1 (t = c^((p−1)/4), c the least non-residue) |
| `isgaussprime(z)` | ℤ[i] → 𝔹 | z is a Gaussian prime | N(z) prime when Re·Im ≠ 0, else \|Re\| or \|Im\| a prime ≡ 3 (mod 4) |
| `gaussprimes(n)` | ℕ → 𝔏 ℤ[i] | normalised Gaussian primes of norm ≤ n, by norm then imaginary part | from the primes ≤ n |
| `nextgaussprime(z)` | ℤ[i] → ℤ[i] | the least normalised Gaussian prime π with (N(π), Im π) > (N(z), Im z) | Gaussian primes norm by norm |
| `isgausspower(z)` | ℤ[i] → 𝔹 | z = wᵏ with w ∈ ℤ[i], k ≥ 2 (true for 0 and units) | from gaussfactor: the gcd g of the exponents has an odd prime factor, or g is even and u = ±1 |
| `sumtwosquares(n)` | ℤ → 𝔏 (𝔓 ℕ ℕ) | all (a, b), a ≥ b ≥ 0, a² + b² = n, by increasing b ([] for n < 0 or when a prime ≡ 3 mod 4 has odd exponent) | the Gaussian integers of norm n, built from the Gaussian primes over the factors of n |

## Not included

Dirichlet characters (their values lie in cyclotomic fields beyond ℚ[i] in general) and general-purpose factoring beyond Pollard ρ
(the elliptic-curve method or the quadratic sieve would not pay off at 10 µs per digit step).
