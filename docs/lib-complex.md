# Functions of a complex variable (`lib/complex.imo`)

The commonly used functions over the complex field ℂ = ℝ[i], computed **in the language**: every function below is a definition in
spec notation (`lib/complex.imo`, with `lib/real.imo` and `lib/analysis.imo` for the elementary ones) that runs on base-(i − 1) digit
strings.  The Python host only parses, checks classes and spells digits.

## Contract

* An exact argument `z ∈ ℚ[i]` gives a **lazy complex number** `ℝ[i]` (a stream of ℚ[i] approximants): **element n is within 2⁻ⁿ of the
  value** (absolute error).  `Pi`, `E`, `EulerGamma` and `Catalan` are lazy reals with the same contract.
* A lazy argument `ℝ[i]` is accepted by the `ᴿ` variant of each function (spec name `fᴿ`, human name: the same as the function —
  the class checker picks the overload from the class of the argument, so `Log(z)` works for both).  Element n of `fᴿ(x)` is element n
  of `f(xₙ)`, through the diagonal `⟐`; it converges to f(x) wherever f is continuous.
* **Principal branches and cuts follow C99 / Python's `cmath`**: log has Im ∈ (−π, π]; the cuts of asin/acos/acosh/atanh/atan/asinh lie
  where `cmath` puts them, and a point on a cut takes the value of the side of +0 (the limit from above for a cut on the real axis).
* **Poles and singularities return 0** — the language has no NaN and no ∞; every function is total.  The convention is stated with each
  function (`log 0 = 0`, `Γ` at 0, −1, −2, … is 0, `cot 0 = 0`, `ζ(1) = 0`, `0⁰ = 1`).  Test for the pole yourself where it matters.
* Cost: a function evaluates its argument-dependent shift or series at the precision it needs.  Typical element 14–24 costs 0.1–10 s;
  the cost grows with |z| for the series-based functions (`erf`, `besselj`, `Si`, `Ci`, `Γ`, `ζ`).

## Constants

| name | meaning |
|:--|:--|
| `Pi` | π by Machin's formula 16·atan(1/5) − 4·atan(1/239) |
| `E` | e |
| `EulerGamma` | γ = −ψ(1) (asymptotic series of the digamma function after a shift) |
| `Catalan` | G = Σ (−1)ᵏ/(2k + 1)² (Ramanujan's series) |

(`i` is the numeral `11`, base i − 1.)

## Elementary functions, powers and logarithms

Already in the prelude before this module: `exp`, `sin`, `cos`, `tan`, `sinh`, `cosh`, `tanh`, `sqrt`, `abs`, `conj`, `re`, `im`, `log`
(real), `atan`, and their `ᴿ` variants.  Added here:

| name | meaning |
|:--|:--|
| `Log(z)` | principal logarithm log\|z\| + i·arg z; log 0 = 0.  **`log` is the older real logarithm** (class ℚ → ℝ, 0 for x ≤ 0), chosen by the class of its argument; write `Log` for a complex or negative argument: `Log(-1)` is iπ, `log(-1)` is 0 |
| `logb(b, z)` | log z / log b; 0 when b ∈ {0, 1} |
| `log1p(z)` | log(1 + z) (0 at z = −1) |
| `expm1(z)` | eᶻ − 1, absolute error |
| `pow(z, w)` | principal power e^(w·log z); **exact** (a constant stream) for an integer w; 0^w = 0 for w ≠ 0, 0⁰ = 1 |
| `nthroot(z, n)` | principal n-th root e^(log z / n); n may be negative; 0 for z = 0 or n = 0 |
| `cbrt(z)` | the real cube root of a real x (cbrt(−8) = −2), the principal root of a non-real z |
| `rootsofunity(n)` | the list e^(2πik/n), k = 0 … n − 1 (empty for n ≤ 0) |
| `arg(z)` | principal argument in (−π, π]; arg 0 = 0 |
| `atan2(y, x)` | the angle of the point (x, y); atan2(0, 0) = 0 |
| `cis(t)`, `polar(r, t)` | e^(it); r·e^(it) |
| `csgn(z)` | z/\|z\|; 0 at 0 |
| `hypot(x, y)` | √(x² + y²) (for complex arguments √(\|x\|² + \|y\|²)) |
| `absc(z)` (`abs`) | modulus of an exact complex number |

## Trigonometric and hyperbolic functions and their inverses

| name | meaning |
|:--|:--|
| `cot`, `sec`, `csc`, `coth`, `sech`, `csch` | reciprocal functions (`cot 0 = csc 0 = coth 0 = csch 0 = 0`: poles) |
| `sinc(z)` | sin z / z, sinc 0 = 1 |
| `asin`, `acos` | inverse sine and cosine; cuts (−∞, −1) and (1, ∞) |
| `atan` | inverse tangent (real and complex arguments); cuts on the imaginary axis beyond ±i; 0 at the poles ±i |
| `acot`, `asec`, `acsc` | atan(1/z), acos(1/z), asin(1/z); `acot 0 = π/2`, 0 at z = 0 for asec and acsc |
| `asinh`, `acosh`, `atanh` | inverse hyperbolic functions; atanh has cuts (−∞, −1) and (1, ∞), value with Im = +π/2 there; 0 at ±1 |
| `acoth`, `asech`, `acsch` | atanh(1/z), acosh(1/z), asinh(1/z) |

The inverse functions use formulas written so that the square roots, logarithms and atan2 take exact arguments (Kahan's formulas for
asinh, acos and acosh; the derivations are in the comments of the source), so cancellation does not cost digits near the cuts.

## Special functions

| name | meaning | limits |
|:--|:--|:--|
| `gamma(z)` | Γ(z): Stirling's series with exact Bernoulli numbers after the shift Γ(z) = Γ(z + N)/(z(z + 1)⋯(z + N − 1)); 0 at 0, −1, −2, … | cost grows with \|z\| |
| `lgamma(x)` | log\|Γ(x)\| of a real x | 0 at the poles |
| `digamma(z)` | ψ(z) = Γ′/Γ, asymptotic series after the shift ψ(z) = ψ(z + N) − Σ 1/(z + j) | 0 at the poles |
| `beta(a, b)` | B(a, b) = Γ(a)Γ(b)/Γ(a + b) through one exponential | 0 when a or b is a pole of Γ |
| `erf(z)`, `erfc(z)` | error function (Maclaurin series with all terms carried at the precision the largest one needs); real \|x\| ≥ 1 with x² ≥ 0.7n gives ±1 | cost grows with \|z\|² |
| `zeta(s)` | Riemann zeta: Euler–Maclaurin summation, the functional equation for Re s < −8; exact at 0 and the negative integers (−B₍ₙ₊₁₎/(n + 1)); ζ(1) = 0 (pole) | cost grows with \|s\| |
| `polylog(s, z)` | Liₛ(z) for an integer s: rational function z·Aₜ(z)/(1 − z)^(t+1) for s = −t ≤ 0 (Eulerian polynomials), −log(1 − z) for s = 1, Σ zᵏ/kˢ for s ≥ 2 and \|z\| < 1, ζ(s) at z = 1 and −(1 − 2^(1−s))·ζ(s) at z = −1; **0 elsewhere** (\|z\| ≥ 1 except z = ±1) and at the pole z = 1 | |
| `lambertw(x)` | principal branch W(x)·e^W(x) = x for real x ≥ −1/e (Newton with a certified residual bound); 0 below −1/e | |
| `besselj(n, z)` | Jₙ(z) for integer order (power series; J₋ₙ = (−1)ⁿJₙ) | cost grows with \|z\| |
| `agm(a, b)` | arithmetic–geometric mean of reals of one sign (outward rounding); 0 when a·b ≤ 0 | |
| `ellipk(m)`, `ellipe(m)` | complete elliptic integrals K(m), E(m) with parameter m (K via π/(2·agm(1, √(1 − m))), E by Gauss' AGM sum); 0 outside the domain (m ≥ 1 for K, m > 1 for E); E(1) = 1 | |
| `expint(x)` | Ei(x) = γ + log\|x\| + Σ xᵏ/(k·k!) (principal value for x > 0); 0 at 0 | |
| `li(x)` | logarithmic integral Ei(log x) for x > 0 (principal value for x > 1); 0 at x = 1 and for x ≤ 0 | |
| `Si(z)`, `Ci(z)` | sine and cosine integrals (power series; Ci(−x) = Ci(x) + iπ) | Ci 0 = 0 (pole) |
| `Shi(z)`, `Chi(z)` | hyperbolic sine and cosine integrals (the series of Si and Ci without the alternating sign) | Chi 0 = 0 (pole) |
| `besseli(n, z)` | modified Bessel function Iₙ(z) of integer order (power series; I₋ₙ = Iₙ) | cost grows with \|z\| |
| `erfi(z)` | imaginary error function −i·erf(iz) | cost grows with \|z\|² |
| `dawson(z)` | Dawson's integral e^(−z²)∫₀ᶻ e^(t²)dt (power series) | cost grows with \|z\|² |

## Tests

`tests/test_complex.py` evaluates **396 cases** in the human notation — every function at several points (real, negative, complex,
purely imaginary, near cuts and poles) at element N = 14–24 — and compares with an independent Python reference (`math`, `cmath`,
Lanczos Γ, Euler–Maclaurin ζ, Gauss' AGM, power series with plenty of terms for erf, Bessel J, Si, Ci, Ei, li).  The test
checks the modulus-of-convergence contract (|element N − reference| ≤ 2⁻ᴺ + 10⁻¹²).  The cases run in parallel worker processes
(`--jobs=N`, default 4; `--only=asin,erf` restricts to some functions, `--first` takes one case per function); a full run takes
about 25 minutes on 3 cores, `--first` about 40 seconds.
