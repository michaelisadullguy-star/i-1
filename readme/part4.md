
---

## 6. Numbers: base i-1, the Gaussian integers, and the Gaussian rationals built from them

### 6.1 The base

The base is **b = i − 1**, with digits `0` and `1`.  A numeral `d_n … d_1 d_0` has the value Σ d_k · bᵏ.  The first powers are

```text
b⁰ = 1     b¹ = −1 + i     b² = −2i     b³ = 2 + 2i     b⁴ = −4     b⁵ = 4 − 4i     b⁶ = 8i     b⁷ = −8 − 8i     b⁸ = 16
```

Every Gaussian integer has **exactly one** finite expansion without leading zeros (the *twindragon* system of Penney and Knuth); zero is the empty expansion, written `0`.  There is therefore no sign and no pair (real, imaginary): `−1` and `i` are ordinary numerals.

| number | numeral | number | numeral | number | numeral |
|:--|:--|:--|:--|:--|:--|
| 0 | `0` | 1 | `1` | *i* | `11` |
| 2 | `1100` | 3 | `1101` | 4 | `111010000` |
| −1 | `11101` | −2 | `11100` | −3 | `10001` |
| −1 − *i* | `110` | 1 + *i* | `1110` | 1 − *i* | `111010` |
| 2 + 3*i* | `1011` | 2*i* | `1110100` | 10 | `111001100` |

*How to compute a numeral* (this is the division algorithm the language's tests use): for z = x + y·i take the digit d = (x + y) mod 2, then continue with z′ = (z − d) / (i − 1) until z = 0.  Multiplying by the base **prepends the digit 0** (`𝕓`).

### 6.2 ℚ[i]: constructed from the Gaussian integers

Inside the language a Gaussian integer is a lazy list of digits, **least significant first**.  The Gaussian integers are the foundation; **the Gaussian rationals are built from them**: an element of ℚ[i] is a pair (numerator, denominator) of Gaussian integers.  Every *numeral you write* is a Gaussian integer or, with a radix point, a Gaussian integer over a power of the base; the reader holds it as an element of ℚ[i] (an integer with denominator 1), so that one set of operations serves integers and fractions.

| You write | Reader produces | Value |
|:--|:--|:--|
| `1100` | `(1100)/(1)` | 2 |
| `a.b` | `(ab)/(10^len(b))` — digits `ab`, divided by bˡᵉⁿ⁽ᵇ⁾ | `0.1` = 1/(i − 1) = (−1 − i)/2 |
| `.1` | same as `0.1` | |

{{NUMTABLE}}

Arithmetic does **not** reduce fractions as it goes (that would cost a gcd per operation); numerators and denominators grow as
streams are advanced — see [§16](#16-implementation-and-tests) for sizes.  Equality of ℚ[i] elements is **cross-multiplication**
(`≐`: p/q = r/s ⇔ p·s = r·q, digit strings compared up to trailing zeros), never comparison of representations.

**Division is total.**  ℚ[i] with `x ÷ 0 = 0` is a *meadow* (Bergstra and Tucker): every operation is defined everywhere, `≐` is a
congruence, and the field axioms hold together with `x · x⁻¹ · x = x` and `0⁻¹ = 0` ([`docs/axioms.md`](docs/axioms.md)).  There is
no fraction with denominator 0 any more, so `0/0` cannot be "equal" to everything.

**Canonical form.**  `⊜ x` (`canon`) writes x = p/q as z/m with m the least natural number such that m·x ∈ ℤ[i]: with
g = gcd(Re pq̄, Im pq̄, N(q)) it is z = pq̄/g and m = N(q)/g.  Equal values have identical canonical forms, `numer`, `denom`, the
decimal printer and the `main` printer use it.  The gcd is Stein's binary gcd on the digit strings ("even" is "last digit 0"),
the divisions are exact Hensel divisions read off from the low end, and division with remainder of naturals is long division in
base 4 = `111010000` — nothing searches over values.

### 6.3 Addition with a numeral as carry

In base 2 a carry is one bit; in base i − 1 a carry is a **numeral** (a small Gaussian integer).  Addition is a left-to-right transducer over the digit lists.  At each position, with input digits x and y and carry numeral c = (d : t) (head digit d, tail t):

```text
output digit   o = x ⊕ y ⊕ d                         (⊕ = exclusive or)
m              = majority(x, y, d)                    (1 if at least two of them are 1)
next carry     = t           if m = 0
               = t + 110     if m = 1                 (110 is −1 − i; the sum is a table lookup)
```

The tails t that can occur form a finite set, so `t + 110` is a ten-entry table `κ` in the prelude:

```text
 t:    0    1    10     11     111       1110   11101      111010  1110100  1110101
 t+110: 110  111  11100  11101  11101001  0      11101011   100     10       11
```

The reachable carries are 15 numerals (`0`, `1`, `10`, `11`, `100`, `110`, `111`, `1110`, `11101`, `111010`, `1110100`, `1110101`, `11100`, `11101001`, `11101011`); once both inputs are exhausted the carry flushes in at most eight more steps.  The adder is checked against Gaussian-integer arithmetic **on every pair of digit strings of length ≤ 4 in the language itself**, and on every pair of total length ≤ 12 in its Python twin (`pymo/base_b.py`), in addition to random cases.

The table is not typed in by hand: `pymo/mkcarry.py` computes the carries that can occur, starting from carry 0, and compiles
each table into a **decision tree** on the low digits of the tail (`⌕′`), so a lookup is a few digit tests.  **Subtraction** has its
own transducer of the same shape — o = x ⊕ y ⊕ d, s = (x − y + d − o)/2 ∈ {−1, 0, 1}, next carry t + s·110 — with 47 carry numerals
and two trees `⌕⁺`, `⌕⁻`; negation is 0 − x.  Each step takes the three lists apart once, and a missing input digit is 0.

> A tempting alternative — a carry-save adder that XORs digits and shifts the majority bits — does **not** work in this base: the popcount is invariant and it does not terminate when the sums cancel (try 1 + 11101).  That is why the carry is a numeral.

**Multiplication** is shift-and-add: ξ · (d₀ + b·η′) = d₀·ξ + b·(ξ · η′), i.e. add ξ if the digit is 1 and prepend a 0 for the next digit.  **Conjugation** uses that b̄ = −1 − i = `110`: if z = d₀ + b·z′ then z̄ = d₀ + 110 · z̄′.

### 6.4 Order

The order is defined on the **real** rationals (class `ℚ`; so also ℕ and ℤ).  For x = p/q and y = r/s, sign(x − y) is the sign of
the real Gaussian integer Re((p·s − r·q) · conj(q·s)), and that sign is **read off the digits in one pass**: since b⁴ = −4, a
numeral is Σ cⱼ b⁴ʲ with 4-digit blocks cⱼ, and Re z = Σ rⱼ (−4)ʲ with rⱼ = d₀ − d₁ + 2d₃ ∈ {−1 … 3}.  The blocks below J add up to
at most 4ᴶ − 1 in absolute value, so sign(Re z) = sign(r_J)·(−1)ᴶ for the highest J with r_J ≠ 0 — a three-state automaton
(`⋚ʳ`, result `⋖ ≖ ⋗` in the class 𝔒).  `⋚` is the three-way comparison, `⩾ ⩽ ≻ ≺ max min abs sgn ⌊ ⌈ round` are derived.
Real and imaginary parts (`ℜᶻ`, `ℑᶻ`) and conjugation (`∗ᶻ z = ℜᶻ z + (−i)·ℑᶻ z`) are linear too: each block's part is a short
numeral, the even blocks and the odd blocks are laid side by side, and one addition joins them.

There is **no evaluated order on ℝ**: two lazy reals cannot be compared by evaluation.  Relations between them are decided from
their definitions, by logic ([§13](#13-predicates-relations-simplified-to-their-simplest-form)).

### 6.5 Which class does a numeral have?

The checker gives a literal the smallest class containing its *value*: ℕ if it is a non-negative integer, ℤ if an integer, ℤ[i] if a Gaussian integer, ℚ if a real fraction, otherwise ℚ[i].  So `1100` is a ℕ, `11101` a ℤ, `11` (= *i*) a ℤ[i], and `0.1` a ℚ[i]; the widening ℕ ⊆ ℤ ⊆ ℚ ⊆ ℚ[i] is automatic ([§7](#7-classes-every-symbol-is-declared-first)).

### 6.6 Types are decoding keys

A value is stored as a **binary string** — the digits of a Gaussian integer in base i − 1 — and a type is the **key that decodes it**.  The string
never changes (classes are erased at run time); a different class selects a different decoding algorithm.  The class of a bare number is the
smallest one containing its value (§6.5); an *ascription* `(x in Z2)` assigns another key.  `110101` is 1 − 6i:

| key | decodes `110101` as |
|:--|:--|
| ℤ[i] (the default) | the Gaussian integer 1 − 6i |
| ℤ² (`Z2`) | the ordered pair (1, −6) — an ordered pair of integers **is** the Gaussian integer, **a + b·i := (a, b)**, and its operations (`+ - k*`, `==`) are those of the Gaussian integers |
| a fraction (`fracz` of the pair) | 1/(−6) = −1/6 |
| `String²` | the pair of strings coded by 1 and 6 |

A pair of strings is one binary string too: a string is coded as a natural number (bijective numeration over the code points), and the pair of
naturals (a, b) is the Gaussian integer a + b·i.  The pair `("Hello, world!", "Welcome to i - 1!")` is a binary string of 658 digits, and the key
`String2` reads it back.  `examples/decode.hum.imo` (about 40 seconds: the numbers have hundreds of digits):

```text
{{FILE:examples/decode.hum.imo}}```

```text
$ python3 pymo/i1.py examples/decode.hum.imo
{{RUNOUT:run examples/decode.hum.imo}}
```

The checker keeps the keys apart (`fstz(strpair("a", "b"))` is a class error; `gaussian` changes the key without changing the string).  The
functions are in [`docs/lib-codec.md`](docs/lib-codec.md).  Ordered pairs of *arbitrary* values remain lambda terms (`pair`, [§9](#9-evaluation-model)):
the Gaussian integer holds a pair of integers.
