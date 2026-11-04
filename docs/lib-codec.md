# Types as decoding keys (`lib/codec.imo`)

**The foundation of `.imo` is the Gaussian integers.**  Every value is stored as a binary string — the digits of a Gaussian integer in base
i − 1, which is unique and finite for every Gaussian integer.  A Gaussian rational is constructed as a pair (numerator, denominator) of Gaussian
integers, a real or complex number as a stream of Gaussian rationals, a list as a nest of pairs.  A **type is a decoding key** for such a string:
the string never changes, only the algorithm that reads it.  (Classes are erased at run time; the class the checker assigns picks the decoder.)

| the string `110101` | key | decoded as |
|:--|:--|:--|
| | ℤ[i] (the default for a number) | 1 − 6i |
| | ℤ² | the ordered pair (1, −6): **a + b·i := (a, b)** |
| | a fraction (`fracz` of the pair) | 1/(−6) = −1/6 |
| | String² | the pair of strings coded by 1 and 6 (`"\0"`, `"\5"`) |

```text
s in \Z := parsebits("110101")             -- the digits, most significant first
decode(s)                                  1 - 6*i
decode((s in Z2))                          (1, -6)
decode(fracz((s in Z2)))                   -1/6
```

A bare binary string has the class ℤ[i]; an **ascription** `(x in Z2)` assigns another key — through the automatic coercions `asz2 ∶ ℤ[i] → ℤ²` and
`asstr2 ∶ ℤ[i] → 𝕊²`, which are the identity on the string and cost 1, so that an exact match (`2 * i` is still the Gaussian product) always wins. Every
Gaussian integer decodes under every key — decoding is total; what a key can *encode* is listed below.  The keys are different classes, so the checker keeps them apart: a `String2` is not a
`Z2` (`fstz(strpair("a", "b"))` is a class error), and `gaussian` is the explicit change of key — it is the identity on the string.

## Ordered pairs of integers: a + b·i := (a, b)

The pair (a, b) of integers is **the Gaussian integer a + b·i**.  Its construction and its operations are those of the Gaussian integers:

| name | class | meaning |
|:--|:--|:--|
| `pairz(a, b)` | `\ZZ -> \ZZ -> Z2` | the pair (a, b), the Gaussian integer a + b·i |
| `fstz(p)`, `sndz(p)` | `Z2 -> \ZZ` | the components: the real and the imaginary part |
| `p + q`, `p - q`, `-p`, `k * p`, `p == q` | on `Z2` | (a + c, b + d), (a − c, b − d), (−a, −b), (ka, kb), equality: the sum, difference, negation, integer multiple and equality of the Gaussian integers (spec `addz2 subz2 negz2 scalez2 eqz2`) |
| `gaussian(p)` | `Z2 -> \Z` | the same string read as the Gaussian integer (the identity) |
| `fracz(p)` | `Z2 -> \QQ` | the pair (a, b) read as the fraction a/b; 0 for b = 0 (division is total) |
| `qpair(x)` | `\QQ -> Z2` | the rational p/q in lowest terms with q > 0 as the pair (p, q): `fracz(qpair(x)) = x` |
| `decode(p)` | `Z2 -> String` | `(1, -6)` |

The product of two Gaussian integers is *not* the componentwise product, so `*` of two pairs is not defined (a pair times an integer is).
(Why ℤ-components: the pair of two *Gaussian* integers would need four integers; nesting a pair inside a pair needs a bijection ℤ² → ℤ, which
this library does not fix.)

## Strings

A string is a list of characters, a character a code point (a natural number below 1114112).  `strnat` codes a string as a natural number
by the **bijective numeration** over the 1114112 code points, s = c₁ … cₖ ↦ Σ (cⱼ + 1)·Bᵏ⁻ʲ with B = 1114112, so that `""` is 0, `"\0"` is 1,
and `natstr` is its inverse: a bijection String ↔ ℕ.  Hence a *pair of strings* is a pair of naturals, that is a Gaussian integer:

| name | class | meaning |
|:--|:--|:--|
| `strnat(s)`, `natstr(n)` | `String -> \NN`, `\NN -> String` | the bijection |
| `strpair(s, t)` | `String -> String -> String2` | the Gaussian integer strnat(s) + strnat(t)·i |
| `strfst(p)`, `strsnd(p)` | `String2 -> String` | the strings coded by \|real part\| and \|imaginary part\| (the absolute value makes the decoding total) |
| `decode(p)` | `String2 -> String` | `("Hello, world!", "Welcome to i - 1!")` (no escapes: a double quote inside a string is not escaped) |

The pair `("Hello, world!", "Welcome to i - 1!")` is **one binary string of 658 digits** — `bits(gaussian(strpair(...)))`, the Gaussian integer
with a 75-decimal-digit real part and a 99-decimal-digit imaginary part — and `String2` decodes it back (`examples/decode.hum.imo`).

## Binary text

`bits(z)` (in `lib/text.imo`) is the digit string of a Gaussian integer, most significant digit first (`"110101"` for 1 − 6i, `"0"` for 0);
`parsebits(t)` is its inverse (leading zeros allowed).

## Cost

About 10 µs per digit step.  Decoding a string divides a number of 20·n bits by 1114112 once per character (long division in base 4):
13 characters take about 10 seconds, the whole example pair about 40 seconds; encoding is fast (0.1 s).  The alphabet size is the single
constant `10000000100000000000000000000000000000000` (= 1114112) in `strnat` and `natstr`.

## Tests

`tests/test_codec.py` (11 checks, about 75 s): the example `110101` under four keys; 17 Gaussian integers against the Python twin of the base
(`parsebits`, `bits`, `pairz`, `fstz`, `sndz`); the operations on pairs through the human `+ - * ==`; `qpair`/`fracz` on six fractions; `strnat`
against Python integer arithmetic (accents, a non-BMP character, the empty string) and `natstr` as its inverse; `("Hi", "yo")`; the example pair
of 658 digits equal to the Python expansion of strnat(s) + strnat(t)·i; four programs the class checker must reject.
