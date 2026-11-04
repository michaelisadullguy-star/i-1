### Classes

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `𝔹` | `.1.` | `Bool` | class | Booleans ⊤ ⊥ (also the digits 1 and 0) |
| `𝔇` | `.11.` | `Digits` | class | digit strings = Gaussian integers in base i−1 (representation of ℤ[i]); ≣ 𝔏 𝔹 |
| `ℕ` | `.1010.` | `\NN` | class | natural numbers |
| `ℤ` | `.1011.` | `\ZZ` | class | integers |
| `ℚ` | `.1100.` | `\QQ` | class | real rationals |
| `ℝ` | `.1101.` | `\RR` | class | real numbers (lazy streams of ℚ[i] with imaginary part 0) |
| `ℤ[i]` | `.1110.` | `\Z` | class | **the foundation**: Gaussian integers, binary strings in base i − 1 |
| `ℚ[i]` | `.1111.` | `\Q` | class | Gaussian rationals: pairs (numerator, denominator) of Gaussian integers |
| `ℝ[i]` | `.10000.` | `\R`, `\CC` | class | lazy complex numbers = streams over ℚ[i]  (= ℂ, \R, \CC);  ≣ 𝔖 ℚ[i] |
| `𝔻` | `.10001.` | `\D` | class | Cayley–Dickson tower over ℚ[i]  (ℂ → ℍ → 𝕆 → 𝕊 → …, depth unbounded);  ≣ 𝔗 ℚ[i] |
| `𝕮` | `.10010.` | `Char` | class | characters (a code point, as a natural numeral) |
| `𝕊` | `.10011.` | `String` | class | strings;  ≣ 𝔏 𝕮 |
| `→` | `.101.` | `->` | class | function class  A → B |
| `𝔏` | `.110.` | `List` | class | lazy lists |
| `𝔖` | `.111.` | `Stream` | class | infinite streams |
| `𝔗` | `.1000.` | `Tree` | class | Cayley–Dickson trees over a class |
| `𝔄` | `.1001.` | `Alg` | class | algebra records over a class (+ × neg conj 0 1) |
| `𝔓` | `.100.` | `Pair` | class | pairs |

### Logic, pairs, lists, text

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `⊤` | `.11001.` | `true` | `𝔹` | true |
| `⊥` | `.11010.` | `false` | `𝔹` | false |
| `¬` | `.11101.` | `not (prefix)` | `𝔹 → 𝔹` | not |
| `∧` | `.11110.` | `*`, `and`, `min` | `𝔹 → 𝔹 → 𝔹` | and |
| `∨` | `.11111.` | `+`, `or`, `max` | `𝔹 → 𝔹 → 𝔹` | or |
| `⊻` | `.100000.` | `xor` | `𝔹 → 𝔹 → 𝔹` | xor |
| `⁇` | `.100011.` | `if` | `𝔹 → α → α → α` | if b then x else y |
| `⊗` | `.100100.` | `pair` | `α → β → (𝔓 α β)` | pair |
| `◀` | `.100110.` | `fst` | `(𝔓 α β) → α` | first component |
| `▶` | `.100111.` | `snd` | `(𝔓 α β) → β` | second component |
| `∷` | `.101000.` | `cons` | `α → (𝔏 α) → (𝔏 α)` | cons |
| `⊘` | `.101010.` | `nil` | `(𝔏 α)` | empty list |
| `⌃` | `.101011.` |  | `(𝔏 𝔹) → 𝔹` | head digit |
| `⌄` | `.101100.` | `tail` | `(𝔏 α) → (𝔏 α)` | tail |
| `∅` | `.101101.` | `isnil` | `(𝔏 α) → 𝔹` | is the list empty? |
| `≡` | `.101110.` |  | `𝔇 → 𝔇 → 𝔹` | digit strings equal (trailing zeros ignored) |
| `𝕓` | `.101111.` |  | `𝔇 → 𝔇` | multiply by (i−1): prepend the digit 0 |
| `⧺` | `.110000.` | `++` | `(𝔏 α) → (𝔏 α) → (𝔏 α)` | append |
| `⫶` | `.110001.` | `map` | `(α → β) → (𝔏 α) → (𝔏 β)`<br>`(α → β) → (𝔖 α) → (𝔖 β)` | map |
| `ℓ` | `.1000101.` | `length` | `(𝔏 α) → ℕ` | length |
| `ord` | `.1000100.` | `ord` | `𝕮 → ℕ` | code point of a Char |

### Numbers: ℤ[i] digit arithmetic and the field ℚ[i]

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `⊞ᶻ` | `.110111.` |  | `𝔇 → 𝔇 → 𝔇` | ℤ[i] addition on digit strings |
| `⊠ᶻ` | `.111000.` |  | `𝔇 → 𝔇 → 𝔇` | ℤ[i] multiplication (shift-and-add) |
| `∗ᶻ` | `.111001.` |  | `𝔇 → 𝔇` | ℤ[i] conjugation  z̄ = d₀ + 110·conj(z′) |
| `⊞` | `.111010.` | `+` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℤ`<br>`ℚ → ℚ → ℚ`<br>`ℤ[i] → ℤ[i] → ℤ[i]`<br>`ℚ[i] → ℚ[i] → ℚ[i]` | addition |
| `⊟` | `.1001001.` | `-` | `ℤ → ℤ → ℤ`<br>`ℚ → ℚ → ℚ`<br>`ℤ[i] → ℤ[i] → ℤ[i]`<br>`ℚ[i] → ℚ[i] → ℚ[i]` | subtraction |
| `⊠` | `.111011.` | `*` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℤ`<br>`ℚ → ℚ → ℚ`<br>`ℤ[i] → ℤ[i] → ℤ[i]`<br>`ℚ[i] → ℚ[i] → ℚ[i]` | multiplication |
| `⊖` | `.111100.` | `- (prefix)` | `ℤ → ℤ`<br>`ℚ → ℚ`<br>`ℤ[i] → ℤ[i]`<br>`ℚ[i] → ℚ[i]` | negation |
| `∗` | `.111101.` | `conj` | `ℕ → ℕ`<br>`ℤ → ℤ`<br>`ℚ → ℚ`<br>`ℤ[i] → ℤ[i]`<br>`ℚ[i] → ℚ[i]` | complex conjugation |
| `÷` | `.111110.` | `/` | `ℚ → ℚ → ℚ`<br>`ℚ[i] → ℚ[i] → ℚ[i]` | division (denominator must be non-zero) |
| `≐` | `.111111.` | `==` | `ℚ[i] → ℚ[i] → 𝔹` | equality of ℚ[i] elements (cross-multiplied) |
| `⩾` | `.1000010.` | `geq` | `ℚ → ℚ → 𝔹` | x ≥ y on ℚ |
| `⩽` | `.1000110.` | `leq` | `ℚ → ℚ → 𝔹` | x ≤ y |
| `≻` | `.1000111.` | `gt` | `ℚ → ℚ → 𝔹` | x > y |
| `≺` | `.1001000.` | `lt` | `ℚ → ℚ → 𝔹` | x < y |

### Algebras, lazy ℝ[i], series

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `⌘` | `.1001010.` |  | `(α → α → α) → (α → α → α) → (α → α) → (α → α) → α → α → (𝔄 α)` | build an algebra record |
| `Ⓐ` | `.1001100.` |  | `(𝔄 α) → α → α → α` | record: add |
| `Ⓜ` | `.1001101.` |  | `(𝔄 α) → α → α → α` | record: multiply |
| `Ⓝ` | `.1001110.` |  | `(𝔄 α) → α → α` | record: negate |
| `Ⓒ` | `.1001111.` |  | `(𝔄 α) → α → α` | record: conjugate |
| `Ⓩ` | `.1010000.` |  | `(𝔄 α) → α` | record: zero |
| `Ⓞ` | `.1010001.` |  | `(𝔄 α) → α` | record: one |
| `𝔸ℚ[i]` | `.1010010.` | `algQ` | `(𝔄 ℚ[i])` | the algebra ℚ[i] |
| `𝕃` | `.1011000.` |  | `(𝔄 α) → (𝔄 (𝔖 α))` | algebra of lazy streams over an algebra (pointwise) |
| `𝔸ℝ[i]` | `.1011001.` | `algR` | `(𝔄 ℝ[i])` | the algebra ℝ[i] = 𝕃 𝔸ℚ[i] |
| `⇡` | `.1011010.` | `embed` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | embed a constant into streams (ℚ[i] → ℝ[i]) |
| `⊕` | `.1011011.` | `+` | `ℝ → ℝ → ℝ`<br>`ℝ[i] → ℝ[i] → ℝ[i]` | ℝ[i] addition |
| `⊟ᴿ` | `.1111000.` | `-` | `ℝ → ℝ → ℝ`<br>`ℝ[i] → ℝ[i] → ℝ[i]` | ℝ[i] subtraction |
| `⊛` | `.1011100.` | `*` | `ℝ → ℝ → ℝ`<br>`ℝ[i] → ℝ[i] → ℝ[i]` | ℝ[i] multiplication |
| `⊖ᴿ` | `.1011101.` | `- (prefix)` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | ℝ[i] negation |
| `∗ᴿ` | `.1011110.` | `conj` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | ℝ[i] conjugation |
| `Σ` | `.1100010.` | `sum` | `ℚ → (ℚ → ℚ) → ℝ`<br>`ℚ[i] → (ℚ[i] → ℚ[i]) → ℝ[i]` | exact series: Σ first-term ratio  gives the stream of partial sums t₀, t₀(1+ρ₁), … |

### Cayley–Dickson tower

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `❀` | `.1100011.` | `leaf` | `α → (𝔗 α)` | Cayley–Dickson leaf |
| `❁` | `.1100100.` | `node` | `(𝔗 α) → (𝔗 α) → (𝔗 α)` | Cayley–Dickson node (a, b) |
| `↑` | `.1101101.` | `embed` | `ℚ[i] → 𝔻` | ℚ[i] → 𝔻  (a ↦ leaf a) |
| `∔` | `.1100110.` |  | `(𝔄 α) → (𝔗 α) → (𝔗 α) → (𝔗 α)` | tower addition |
| `⊠ᵀ` | `.1101001.` |  | `(𝔄 α) → (𝔗 α) → (𝔗 α) → (𝔗 α)` | tower product (a,b)(c,d) = (ac − d*b, da + bc*) |
| `⊖ᵀ` | `.1100111.` |  | `(𝔄 α) → (𝔗 α) → (𝔗 α)` | tower negation |
| `∗ᵀ` | `.1101000.` |  | `(𝔄 α) → (𝔗 α) → (𝔗 α)` | tower conjugation (a,b)* = (a*, −b) |
| `≐ᵀ` | `.1101011.` |  | `(𝔄 α) → (α → α → 𝔹) → (𝔗 α) → (𝔗 α) → 𝔹` | tower equality (up to lifting) given an equality on the base |
| `𝕋` | `.1101010.` |  | `(𝔄 α) → (𝔄 (𝔗 α))` | algebra of Cayley–Dickson trees over an algebra |
| `⊞𝔻` | `.1101110.` | `+` | `𝔻 → 𝔻 → 𝔻` | 𝔻 addition |
| `⊟𝔻` | `.1111001.` | `-` | `𝔻 → 𝔻 → 𝔻` | 𝔻 subtraction |
| `⊠𝔻` | `.1101111.` | `*` | `𝔻 → 𝔻 → 𝔻` | 𝔻 multiplication |
| `⊖𝔻` | `.1110000.` | `- (prefix)` | `𝔻 → 𝔻` | 𝔻 negation |
| `∗𝔻` | `.1110001.` | `conj` | `𝔻 → 𝔻` | 𝔻 conjugation |
| `𝕛` | `.1110010.` | `j` | `𝔻` | the generator (0, 1):  j² = −1 |
| `𝕜` | `.1110011.` | `k` | `𝔻` | i·j |

### Function spaces

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `𝔉` | `.1110100.` |  | `(𝔄 α) → (𝔄 (ℚ[i] → α))` | function-space algebra  ℚ[i] → A  (pointwise, infinite-dimensional) |
| `⟨⟩` | `.1110110.` | `inner` | `(𝔄 α) → (ℚ[i] → α) → (ℚ[i] → α) → (𝔖 α)` | inner product ⟨f,g⟩ = Σ conj(f n)·g n  as a stream of partial sums |
| `δ` | `.1110111.` | `delta` | `(𝔄 α) → ℚ[i] → ℚ[i] → α` | standard basis vector δₘ(n) = 1 if n = m else 0 |

### Bounded quantifiers and ranges

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `∀ₗ` | `.1111010.` | `forall` | `(α → 𝔹) → (𝔏 α) → 𝔹` |  |
| `∃ₗ` | `.1111011.` | `exists` | `(α → 𝔹) → (𝔏 α) → 𝔹` |  |
| `⍳` | `.1111101.` | `range` | `ℕ → (𝔏 ℕ)` |  |

### Analysis (power series)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `exp` | `.1111110.` | `exp` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` |  |
| `sin` | `.10000000.` | `sin` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` |  |
| `cos` | `.10000001.` | `cos` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` |  |

### Comparisons and exact arithmetic on ℚ[i]

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `𝔒` | `.10010100.` | `Ordering` | class | comparisons: ⋖ less, ≖ same, ⋗ greater (also the three values of a predicate: false, undetermined, true) |
| `⋖` | `.10010101.` | `less` | `𝔒` | less |
| `≖` | `.10010110.` | `same` | `𝔒` | same |
| `⋗` | `.10010111.` | `greater` | `𝔒` | greater |
| `⋚` | `.10011110.` | `compare` | `ℚ → ℚ → 𝔒` | three-way comparison on ℚ (one pass over the digits) |
| `⊜` | `.10101111.` | `canon` | `ℕ → ℕ`<br>`ℤ → ℤ`<br>`ℚ → ℚ`<br>`ℤ[i] → ℤ[i]`<br>`ℚ[i] → ℚ[i]` | canonical form z/m: m the least natural with m·x ∈ ℤ[i]; equal values have identical forms |
| `numer` | `.10110001.` | `numer` | `ℚ → ℤ`<br>`ℚ[i] → ℤ[i]` | z of the canonical form |
| `denom` | `.10110010.` | `denom` | `ℚ[i] → ℕ` | m of the canonical form |
| `ℜ` | `.10110011.` | `re` | `ℚ[i] → ℚ` | real part |
| `ℑ` | `.10110100.` | `im` | `ℚ[i] → ℚ` | imaginary part |
| `𝒩` | `.10110101.` | `norm` | `ℚ[i] → ℚ` | norm x·x̄ = |x|² |
| `⌊` | `.10110110.` | `floor` | `ℚ → ℤ` | floor |
| `⌈` | `.10110111.` | `ceil` | `ℚ → ℤ` | ceiling |
| `round` | `.10111000.` | `round` | `ℚ → ℤ` | nearest integer (halves up) |
| `div` | `.10111001.` | `div` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℤ` | integer division (floor; x div 0 = 0) |
| `mod` | `.10111010.` | `mod` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℤ` | remainder (floor; x mod 0 = x) |
| `abs` | `.10111011.` | `abs` | `ℕ → ℕ`<br>`ℤ → ℕ`<br>`ℚ → ℚ` | absolute value |
| `sgn` | `.10111100.` | `sgn` | `ℚ → ℤ` | sign −1, 0, 1 |
| `max` | `.10111101.` | `max` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℤ`<br>`ℚ → ℚ → ℚ` | maximum |
| `min` | `.10111110.` | `min` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℤ`<br>`ℚ → ℚ → ℚ` | minimum |
| `gcd` | `.11000100.` | `gcd` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℕ`<br>`ℤ[i] → ℤ[i] → ℤ[i]` | gcd (binary gcd on ℤ; Gaussian Euclid on ℤ[i], normalised Re > 0, Im ≥ 0) |
| `lcm` | `.11000101.` | `lcm` | `ℕ → ℕ → ℕ`<br>`ℤ → ℤ → ℕ` | lcm |
| `quo` | `.11000110.` | `quo` | `ℤ[i] → ℤ[i] → ℤ[i]` | Gaussian quotient (nearest) |
| `rem` | `.11000111.` | `rem` | `ℤ[i] → ℤ[i] → ℤ[i]` | Gaussian remainder, N(r) ≤ N(b)/2 |
| `^` | `.11001001.` | `^` | `ℕ → ℕ → ℕ`<br>`ℤ → ℕ → ℤ`<br>`ℚ → ℕ → ℚ`<br>`ℤ[i] → ℕ → ℤ[i]`<br>`ℚ[i] → ℕ → ℚ[i]`<br>`ℚ → ℤ → ℚ`<br>`ℚ[i] → ℤ → ℚ[i]` | power (square-and-multiply on the exponent digits; negative exponents on ℚ, ℚ[i]) |
| `fact` | `.11001011.` | `factorial` | `ℕ → ℕ` | factorial |
| `choose` | `.11001101.` | `choose` | `ℕ → ℕ → ℕ` | binomial coefficient |
| `isqrt` | `.11010010.` | `isqrt` | `ℕ → ℕ` | ⌊√n⌋ (Newton) |

### Lists, streams, Booleans, digits, characters

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `⇒` | `.11010011.` | `implies` | `𝔹 → 𝔹 → 𝔹` | implies |
| `⇔` | `.11010100.` | `iff` | `𝔹 → 𝔹 → 𝔹` | iff |
| `hd` | `.11010101.` | `head` | `(𝔏 α) → α` | head (⊥ for the empty list) |
| `foldr` | `.11010110.` | `foldr` | `(α → β → β) → β → (𝔏 α) → β` | right fold |
| `foldl` | `.11010111.` | `foldl` | `(β → α → β) → β → (𝔏 α) → β` | left fold |
| `filter` | `.11011000.` | `filter` | `(α → 𝔹) → (𝔏 α) → (𝔏 α)` | filter |
| `take` | `.11011010.` | `take` | `ℕ → (𝔏 α) → (𝔏 α)`<br>`ℕ → (𝔖 α) → (𝔏 α)` | first n elements |
| `drop` | `.11011100.` | `drop` | `ℕ → (𝔏 α) → (𝔏 α)`<br>`ℕ → (𝔖 α) → (𝔖 α)` | all but the first n |
| `nth` | `.11011101.` | `nth` | `(𝔏 α) → ℕ → α`<br>`(𝔖 α) → ℕ → α` | element n (from 0) |
| `last` | `.11011110.` | `last` | `(𝔏 α) → α` | last element |
| `reverse` | `.11011111.` | `reverse` | `(𝔏 α) → (𝔏 α)` | reverse |
| `concat` | `.11100000.` | `concat` | `(𝔏 (𝔏 α)) → (𝔏 α)` | concatenation of a list of lists |
| `zip` | `.11100001.` | `zip` | `(𝔏 α) → (𝔏 β) → (𝔏 (𝔓 α β))` | pairs |
| `zipwith` | `.11100010.` | `zipwith` | `(α → β → γ) → (𝔏 α) → (𝔏 β) → (𝔏 γ)`<br>`(α → β → γ) → (𝔖 α) → (𝔖 β) → (𝔖 γ)` | zip with a function |
| `replicate` | `.11100011.` | `replicate` | `ℕ → α → (𝔏 α)` | n copies |
| `iterate` | `.11100100.` | `iterate` | `(α → α) → α → (𝔖 α)` | x, f x, f (f x), … |
| `tabulate` | `.11100101.` | `seq` | `(ℕ → α) → (𝔖 α)` | the stream f(0), f(1), … |
| `sumof` | `.11100110.` | `sumof` | `(𝔏 ℕ) → ℕ`<br>`(𝔏 ℤ) → ℤ`<br>`(𝔏 ℚ) → ℚ`<br>`(𝔏 ℚ[i]) → ℚ[i]` | sum of a list |
| `prodof` | `.11100111.` | `prodof` | `(𝔏 ℕ) → ℕ`<br>`(𝔏 ℤ) → ℤ`<br>`(𝔏 ℚ) → ℚ`<br>`(𝔏 ℚ[i]) → ℚ[i]` | product of a list |
| `elem` | `.11101000.` | `elem` | `ℚ[i] → (𝔏 ℚ[i]) → 𝔹` | membership in a list (≐) |
| `upto` | `.11101001.` | `upto` | `ℕ → ℕ → (𝔏 ℕ)`<br>`ℤ → ℤ → (𝔏 ℤ)` | a, a+1, …, b |
| `sort` | `.11101011.` | `sort` | `(𝔏 ℕ) → (𝔏 ℕ)`<br>`(𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ)` | insertion sort on ℚ |
| `eqlist` | `.11101100.` | `eqlist` | `(α → α → 𝔹) → (𝔏 α) → (𝔏 α) → 𝔹` | equality of lists given an equality of elements |
| `≐ˢ` | `.11101101.` | `==` | `𝕊 → 𝕊 → 𝔹` | equality of strings |
| `band` | `.11110001.` | `band` | `ℤ[i] → ℤ[i] → ℤ[i]` | digit-wise and of base-(i−1) expansions |
| `bor` | `.11110010.` | `bor` | `ℤ[i] → ℤ[i] → ℤ[i]` | digit-wise or |
| `bxor` | `.11110011.` | `bxor` | `ℤ[i] → ℤ[i] → ℤ[i]` | digit-wise xor |
| `shl` | `.11110100.` | `shl` | `ℤ[i] → ℕ → ℤ[i]` | z·bⁿ (prepend n zero digits) |
| `shr` | `.11110101.` | `shr` | `ℤ[i] → ℕ → ℤ[i]` | drop the n lowest digits |
| `ndigits` | `.11110110.` | `ndigits` | `ℤ[i] → ℕ` | number of digits of the expansion |
| `digit` | `.11110111.` | `digit` | `ℤ[i] → ℕ → 𝔹` | digit n of the expansion |
| `𝕔` | `.11111000.` |  | `ℕ → 𝕮` | the Char with a code point (unchecked; how bin writes a Char literal) |
| `chr` | `.11111001.` | `chr` | `ℕ → 𝕮` | the Char with a code point (U+FFFD outside Unicode) |

### Analysis on the lazy ℝ[i]

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `÷ᴿ` | `.11111010.` | `/` | `ℝ → ℝ → ℝ`<br>`ℝ[i] → ℝ[i] → ℝ[i]` | pointwise division of streams |
| `ℜᴿ` | `.11111011.` | `re` | `ℝ[i] → ℝ` | real part of a lazy complex number |
| `ℑᴿ` | `.11111100.` | `im` | `ℝ[i] → ℝ` | imaginary part |
| `⟐` | `.11111110.` | `diag` | `(α → (𝔖 β)) → (𝔖 α) → (𝔖 β)` | diagonal: element n of f(xₙ) — extends a function to lazy arguments |
| `√` | `.100000100.` | `sqrt` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | square root: element n is ⌊√(x·4ⁿ)⌋/2ⁿ (within 2⁻ⁿ); principal root on ℚ[i] |
| `log` | `.100000101.` | `log` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | logarithm (artanh series), x > 0 / Re z > 0 |
| `atan` | `.100000110.` | `atan` | `ℚ → ℝ` | arctangent (Euler's series, every real x) |
| `sinh` | `.100000111.` | `sinh` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic sine |
| `cosh` | `.100001000.` | `cosh` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic cosine |
| `tan` | `.100001001.` | `tan` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | tangent (pointwise sin/cos) |
| `tanh` | `.100001010.` | `tanh` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic tangent |
| `expᴿ` | `.100001011.` | `exp` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | exp of a lazy argument |
| `sinᴿ` | `.100001100.` | `sin` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | sin of a lazy argument |
| `cosᴿ` | `.100001101.` | `cos` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | cos of a lazy argument |
| `√ᴿ` | `.100001110.` | `sqrt` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | √ of a lazy argument |
| `logᴿ` | `.100001111.` | `log` | `ℝ → ℝ` | log of a lazy argument |
| `atanᴿ` | `.100010000.` | `atan` | `ℝ → ℝ` | atan of a lazy argument |
| `absᴿ` | `.100010001.` | `abs` | `ℝ[i] → ℝ` | |z| of a lazy complex number |
| `∂` | `.100010100.` | `deriv` | `(ℚ → ℚ) → ℚ → ℝ`<br>`(ℚ[i] → ℚ[i]) → ℚ[i] → ℝ[i]` | derivative: central differences with h = 2⁻ⁿ |
| `∫` | `.100010110.` | `integral` | `(ℚ → ℚ) → ℚ → ℚ → ℝ` | integral: midpoint rule with n + 1 parts |

### Linear algebra (exact)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `vadd` | `.100010111.` | `vadd` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | vector sum |
| `vscale` | `.100011000.` | `vscale` | `ℚ[i] → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | scalar times vector |
| `dot` | `.100011001.` | `dot` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → ℚ[i]` | dot product |
| `madd` | `.100011010.` | `+`, `madd` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | matrix sum |
| `transpose` | `.100011011.` | `transpose` | `(𝔏 (𝔏 α)) → (𝔏 (𝔏 α))` | transpose |
| `mmul` | `.100011100.` | `*`, `mmul` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | matrix product |
| `mvec` | `.100011101.` | `*`, `mvec` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | matrix times vector |
| `unitv` | `.100011110.` | `unitv` | `ℕ → ℕ → (𝔏 ℚ[i])` | unit vector |
| `idm` | `.100011111.` | `identity` | `ℕ → (𝔏 (𝔏 ℚ[i]))` | identity matrix |
| `det` | `.100100010.` | `det` | `(𝔏 (𝔏 ℚ[i])) → ℚ[i]` | determinant (exact elimination) |
| `solve` | `.100100101.` | `solve` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | solution of A x = b (A invertible) |
| `inverse` | `.100100111.` | `inverse` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | inverse matrix |

### Sets as characteristic functions

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `∈` | `.100101000.` | `member` | `α → (α → 𝔹) → 𝔹` | membership (a set is its test) |
| `∅ˢ` | `.100101001.` | `emptyset` | `α → 𝔹` | the empty set |
| `𝕌` | `.100101010.` | `univ` | `α → 𝔹` | the universal set |
| `∪` | `.100101011.` | `+`, `or`, `max`, `union` | `(α → 𝔹) → (α → 𝔹) → α → 𝔹` | union |
| `∩` | `.100101100.` | `*`, `and`, `min`, `inter` | `(α → 𝔹) → (α → 𝔹) → α → 𝔹` | intersection |
| `∖` | `.100101101.` | `setminus` | `(α → 𝔹) → (α → 𝔹) → α → 𝔹` | difference |
| `∁` | `.100101110.` | `compl` | `(α → 𝔹) → α → 𝔹` | complement |
| `setof` | `.100101111.` | `setof` | `(𝔏 ℚ[i]) → ℚ[i] → 𝔹` | the set of the elements of a list |
| `members` | `.100110000.` | `members` | `(α → 𝔹) → (𝔏 α) → (𝔏 α)` | the members of a set among a list |

### Text

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `dec` | `.101001111.` | `str` | `ℤ → 𝕊` | an integer in decimal (Horner on decimal digits, no division) |
| `bits` | `.101010000.` | `bits` | `ℤ[i] → 𝕊` | a Gaussian integer in base i − 1 |
| `showq` | `.101010001.` | `str` | `ℚ → 𝕊` | a real rational as text |
| `showc` | `.101010011.` | `str`, `decode` | `ℚ[i] → 𝕊` | a Gaussian rational as human-notation text |
| `showb` | `.101010100.` | `str` | `𝔹 → 𝕊` | true / false |
| `decimals` | `.101010101.` | `decimals` | `ℚ → ℕ → 𝕊` | x rounded to k decimal places |
| `unlines` | `.101010110.` | `unlines` | `(𝔏 𝕊) → 𝕊` | join lines |
| `join` | `.101010111.` | `join` | `𝕊 → (𝔏 𝕊) → 𝕊` | join with a separator |

### Predicates on ℝ[i]: relations decided by logic (lib/prove.imo)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `≐ᴿ` | `.101110100.` | `==` | `ℝ[i] → ℝ[i] → Ω` | equality of elements of ℝ[i]: a predicate (true, false or undetermined) |
| `≠ᴿ` | `.101110101.` | `!=` | `ℝ[i] → ℝ[i] → Ω` | ≠ on ℝ[i]: a predicate |
| `≺ᴿ` | `.101110110.` | `lt` | `ℝ → ℝ → Ω` | < on ℝ: a predicate |
| `⩽ᴿ` | `.101110111.` | `leq` | `ℝ → ℝ → Ω` | ≤ on ℝ |
| `≻ᴿ` | `.101111000.` | `gt` | `ℝ → ℝ → Ω` | > on ℝ |
| `⩾ᴿ` | `.101111001.` | `geq` | `ℝ → ℝ → Ω` | ≥ on ℝ |
| `≠` | `.101111010.` | `!=` | `ℚ[i] → ℚ[i] → 𝔹` | ≠ on ℚ[i] |
| `⍰` | `.101100011.` |  | `𝔹` | undetermined: absorbs its arguments; reported by the host, never printed as true or false |
| `ι` | `.110011.` | `iverson` | `𝔹 → ℕ` | Iverson bracket ⊤ ↦ 1, ⊥ ↦ 0 (canonical coercion 𝔹 → ℕ) |
| `supp` | `.101100111.` | `supp` | `ℕ → 𝔹` | support: n ↦ (n ≠ 0) |
| `𝔔` | `.101011000.` |  | class | codes of terms (terms written with numbers) |
| `𝔮ⁿ` | `.101011001.` |  | `α → 𝔔` | code of a value |
| `𝔮ˢ` | `.101011010.` |  | `𝔇 → 𝔔` | code of a symbol (its doc 1 code) |
| `𝔮ᵃ` | `.101011011.` |  | `𝔔 → 𝔔 → 𝔔` | code of an application |
| `𝔮ˡ` | `.101011100.` |  | `𝔔 → 𝔔` | code of a λ |
| `𝔮ᵛ` | `.101011101.` |  | `𝔇 → 𝔔` | code of a bound variable (de Bruijn) |
| `unfold` | `.101110011.` |  | `(𝔏 (𝔓 𝔇 𝔔)) → 𝔔 → (𝔓 𝔹 𝔔)` | logical expansion (definitions, β-reduction) |
| `normR` | `.111010110.` |  | `(𝔏 (𝔓 𝔇 𝔔)) → 𝔇 → 𝔔 → (𝔏 α)` | ring normal form of an ℝ[i] code |
| `evQ` | `.110011010.` |  | `(𝔏 (𝔓 𝔇 𝔔)) → 𝔇 → (𝔏 ℚ[i]) → 𝔔 → (𝔓 𝔹 ℚ[i])` | evaluation of a ℚ[i] code |
| `ratQ` | `.110110001.` |  | `(𝔏 (𝔓 𝔇 𝔔)) → 𝔇 → 𝔔 → (𝔓 𝔹 (𝔓 (𝔏 ℚ[i]) (𝔓 (𝔏 ℚ[i]) (𝔏 ℚ[i]))))` | rational form of a ratio k ↦ ρ(k) |
| `recog` | `.111010011.` |  | `𝔔 → (𝔓 (𝔏 ℚ[i]) (𝔓 (𝔏 ℚ[i]) (𝔏 ℚ[i]))) → (𝔏 α)` | proof rules: exp, sinh/cosh (sine, cosine) series as exponentials |
| `≡ˢ` | `.110111001.` |  | `(𝔓 𝔔 (𝔓 (𝔏 ℚ[i]) (𝔓 (𝔏 ℚ[i]) (𝔏 ℚ[i])))) → (𝔓 𝔔 (𝔓 (𝔏 ℚ[i]) (𝔓 (𝔏 ℚ[i]) (𝔏 ℚ[i])))) → 𝔹` | isomorphism of two series |
| `certs` | `.111100001.` |  | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 (𝔓 𝔹 (𝔓 ℚ[i] ℚ)))` | certified discs of a series (ratio test) |
| `eqᴾ` | `.111100111.` |  | `(𝔏 α) → 𝔒` | decide x = 0 |
| `sgnᴾ` | `.111101000.` |  | `(𝔏 α) → 𝔒` | decide the sign of x |
| `fo` | `.111101001.` |  | `(𝔏 (𝔓 𝔇 𝔔)) → 𝔇 → 𝔔 → 𝔒` | three-valued logic over relations |

### More of analysis on the lazy ℝ[i] (`lib/real.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `^ᴿ` | `.111101111.` | `^` | `ℝ → ℤ → ℝ`<br>`ℝ[i] → ℤ → ℝ[i]` | pointwise integer power of a lazy number |

### Vectors and matrices over ℚ[i], exactly (`lib/linalg.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `vsub` | `.10111101011.` | `vsub` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | difference of two vectors |
| `vneg` | `.10111101100.` | `vneg` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i])` | negated vector |
| `outer` | `.10111101101.` | `outer` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 (𝔏 ℚ[i]))` | outer product u vᵀ (rows indexed by u) |
| `hdot` | `.10111101110.` | `hdot` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → ℚ[i]` | Hermitian inner product ⟨u, v⟩ = Σ conj(uₖ)·vₖ |
| `vnorm2` | `.10111101111.` | `vnorm2` | `(𝔏 ℚ[i]) → ℚ` | squared Hermitian norm Σ |vₖ|² (exact) |
| `vnorm` | `.10111110000.` | `vnorm` | `(𝔏 ℚ[i]) → ℝ` | Hermitian norm √(Σ |vₖ|²) as a lazy real |
| `proj` | `.10111110001.` | `proj` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | proj(u, v): the orthogonal projection of u onto v (0 when v is 0) |
| `cross` | `.10111110010.` | `cross` | `(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | cross product of two vectors of length 3 |
| `msub` | `.10111110011.` | `-`, `msub` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | difference of two matrices |
| `mneg` | `.10111110100.` | `- (prefix)`, `mneg` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | negated matrix |
| `mscale` | `.10111110101.` | `*`, `mscale` | `ℚ[i] → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | scalar times matrix |
| `hadamard` | `.10111110110.` | `hadamard` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | entrywise (Hadamard) product |
| `htranspose` | `.10111110111.` | `htranspose` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | conjugate transpose |
| `kron` | `.10111111000.` | `kron` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | Kronecker product |
| `blockdiag` | `.10111111101.` | `blockdiag` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | block diagonal matrix diag(A, B) |
| `zeros` | `.10111111110.` | `zeros` | `ℕ → ℕ → (𝔏 (𝔏 ℚ[i]))` | the m × n zero matrix |
| `trace` | `.10111111111.` | `trace` | `(𝔏 (𝔏 ℚ[i])) → ℚ[i]` | trace (sum of the diagonal) |
| `mdiag` | `.11000000000.` | `mdiag` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i])` | the diagonal of a matrix as a vector |
| `diagm` | `.11000000001.` | `diagm` | `(𝔏 ℚ[i]) → (𝔏 (𝔏 ℚ[i]))` | the diagonal matrix with the given diagonal |
| `mpow` | `.11000000010.` | `^`, `mpow` | `(𝔏 (𝔏 ℚ[i])) → ℤ → (𝔏 (𝔏 ℚ[i]))` | A^n for a square matrix (n < 0: a power of the inverse; singular A gives garbage for n < 0) |
| `issymmetric` | `.11000000100.` | `issymmetric` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | A = Aᵀ |
| `ishermitian` | `.11000000110.` | `ishermitian` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | A = Aᴴ |
| `isunitary` | `.11000000111.` | `isunitary` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | Aᴴ A = I |
| `isdiagonal` | `.11000001000.` | `isdiagonal` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | every off-diagonal entry is 0 |
| `isupper` | `.11000001001.` | `isupper` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | every entry below the diagonal is 0 |
| `islower` | `.11000001010.` | `islower` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | every entry above the diagonal is 0 |
| `isinvertible` | `.11000001011.` | `isinvertible` | `(𝔏 (𝔏 ℚ[i])) → 𝔹` | det A ≠ 0 |
| `rref` | `.11000001111.` | `rref` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | reduced row echelon form (pivots 1, zero rows last) |
| `rank` | `.11000010100.` | `rank` | `(𝔏 (𝔏 ℚ[i])) → ℕ` | rank (number of pivots) |
| `rowspace` | `.11000010101.` | `rowspace` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | a basis of the row space (the non-zero rows of the reduced echelon form) |
| `colspace` | `.11000010110.` | `colspace` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | a basis of the column space (the pivot columns of A, as vectors) |
| `nullspace` | `.11000011000.` | `nullspace` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | a basis of the kernel {x : A x = 0} (one vector per free column) |
| `minor` | `.11000011100.` | `minor` | `(𝔏 (𝔏 ℚ[i])) → ℕ → ℕ → ℚ[i]` | minor(A, i, j): the determinant of A without row i and column j (rows and columns count from 0) |
| `cofactor` | `.11000011101.` | `cofactor` | `(𝔏 (𝔏 ℚ[i])) → ℕ → ℕ → ℚ[i]` | cofactor(A, i, j) = (−1)^(i+j)·minor(A, i, j) |
| `adjugate` | `.11000011110.` | `adjugate` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | the adjugate (transpose of the cofactor matrix): A·adj(A) = det(A)·I |
| `charpoly` | `.11000100000.` | `charpoly` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i])` | the characteristic polynomial det(xI − A) as a coefficient list, lowest degree first (monic) |
| `eigenvals` | `.11000100010.` | `eigenvals` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔓 ℚ[i] ℕ))` | the eigenvalues that lie in ℚ(i), each with its algebraic multiplicity: pairs (λ, m), sorted by (Re, Im) |
| `eigvalsR` | `.11000100011.` | `eigvals` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℝ[i])` | all eigenvalues, with multiplicity, as lazy complex numbers (element n within 2⁻ⁿ; numerical, from croots) |
| `eigvecs` | `.11000100100.` | `eigvecs` | `(𝔏 (𝔏 ℚ[i])) → ℚ[i] → (𝔏 (𝔏 ℚ[i]))` | eigvecs(A, λ): a basis of the eigenspace {x : A x = λ x} |
| `minpoly` | `.11000101001.` | `minpoly` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i])` | the minimal polynomial (monic, lowest degree first): the least-degree monic p with p(A) = 0 (Krylov on the powers of A) |
| `linsolve` | `.11000101000.` | `linsolve` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i]) → (𝔓 𝔹 (𝔓 (𝔏 ℚ[i]) (𝔏 (𝔏 ℚ[i]))))` | linsolve(A, b): all solutions of A x = b as (consistent?, (a particular solution, a basis of the kernel)); the solutions are x₀ + Σ cₖ nₖ |
| `lu` | `.11000101010.` | `lu` | `(𝔏 (𝔏 ℚ[i])) → (𝔓 (𝔏 (𝔏 ℚ[i])) (𝔓 (𝔏 (𝔏 ℚ[i])) (𝔏 (𝔏 ℚ[i]))))` |  |
| `gramschmidt` | `.11000110100.` | `gramschmidt` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` |  |
| `pinv` | `.11000110101.` | `pinv` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))` | the Moore–Penrose pseudo-inverse of any matrix (exact) |
| `lstsq` | `.11000110111.` | `lstsq` | `(𝔏 (𝔏 ℚ[i])) → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | lstsq(A, b): the least-squares solution of minimal norm, A⁺ b |
| `smith` | `.11000111010.` | `smith` | `(𝔏 (𝔏 ℤ)) → (𝔏 ℕ)` | the invariant factors of an integer matrix (Smith normal form diagonal, without the zeros); exponential in the size: small matrices only |
| `matexp` | `.11000111110.` | `matexp` | `(𝔏 (𝔏 ℚ[i])) → (𝔖 (𝔏 (𝔏 ℚ[i])))` | the matrix exponential e^A: element n is the partial sum Σ_(j ≤ n) Aʲ/j! (entries exact) |

### Polynomials in one indeterminate over ℚ[i] (coefficient lists, lowest degree first) (`lib/poly.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `poly` | `.1000001001.` | `poly` | `(𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x]` | the canonical form of a polynomial: every coefficient canonical (⊜), trailing zeros removed |
| `deg` | `.1000100101.` | `deg` | `ℚ[i][x] → ℤ` | the degree (the zero polynomial has degree −1) |
| `lc` | `.1000100110.` | `lc` | `(𝔏 ℤ) → ℤ`<br>`(𝔏 ℚ) → ℚ`<br>`(𝔏 ℤ[i]) → ℤ[i]`<br>`ℚ[i][x] → ℚ[i]` | the leading coefficient (0 for the zero polynomial) |
| `coeff` | `.1000100111.` | `coeff` | `(𝔏 ℤ) → ℕ → ℤ`<br>`(𝔏 ℚ) → ℕ → ℚ`<br>`(𝔏 ℤ[i]) → ℕ → ℤ[i]`<br>`ℚ[i][x] → ℕ → ℚ[i]` | coeff(p, k): the coefficient of xᵏ (0 beyond the degree) |
| `polyx` | `.1000101000.` | `polyx` | `(𝔏 ℤ)` | the polynomial x |
| `monomial` | `.1000101001.` | `monomial` | `ℤ → ℕ → (𝔏 ℤ)`<br>`ℚ → ℕ → (𝔏 ℚ)`<br>`ℤ[i] → ℕ → (𝔏 ℤ[i])`<br>`ℚ[i] → ℕ → ℚ[i][x]` | monomial(c, n) = c·xⁿ |
| `polyadd` | `.1000101010.` | `polyadd` | `(𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | sum of two polynomials |
| `polysub` | `.1000101011.` | `polysub` | `(𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | difference of two polynomials |
| `polyneg` | `.1000101100.` | `polyneg` | `(𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x]` | negated polynomial |
| `polyscale` | `.1000101101.` | `polyscale` | `ℤ → (𝔏 ℤ) → (𝔏 ℤ)`<br>`ℚ → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℤ[i] → (𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i] → ℚ[i][x] → ℚ[i][x]` | polyscale(c, p) = c·p |
| `polymul` | `.1000101110.` | `polymul` | `(𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | product of two polynomials (schoolbook, one reduction per coefficient) |
| `polypow` | `.1000101111.` | `polypow` | `(𝔏 ℤ) → ℕ → (𝔏 ℤ)`<br>`(𝔏 ℚ) → ℕ → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → ℕ → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℕ → ℚ[i][x]` | polypow(p, n) = pⁿ (by squaring; p⁰ = 1) |
| `polydivmod` | `.1000110000.` | `polydivmod` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔓 (𝔏 ℚ) (𝔏 ℚ))`<br>`ℚ[i][x] → ℚ[i][x] → (𝔓 ℚ[i][x] ℚ[i][x])` | polydivmod(p, q) = (quotient, remainder), deg r < deg q;  polydivmod(p, 0) = (0, p) |
| `polyquo` | `.1000110001.` | `polyquo` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | quotient of the division with remainder (0 for division by 0) |
| `polyrem` | `.1000110010.` | `polyrem` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | remainder of the division with remainder (p itself for division by 0) |
| `polypowmod` | `.1000110011.` | `polypowmod` | `(𝔏 ℚ) → ℕ → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℕ → ℚ[i][x] → ℚ[i][x]` | polypowmod(p, n, m) = pⁿ mod m (squaring, reduced at every step; m = 0: pⁿ) |
| `polyeq` | `.1000110100.` | `polyeq` | `ℚ[i][x] → ℚ[i][x] → 𝔹` | equality of polynomials (as values: trailing zeros and non-canonical coefficients do not matter) |
| `polyeval` | `.1000110101.` | `polyeval` | `(𝔏 ℕ) → ℕ → ℕ`<br>`(𝔏 ℤ) → ℤ → ℤ`<br>`(𝔏 ℚ) → ℚ → ℚ`<br>`(𝔏 ℤ[i]) → ℤ[i] → ℤ[i]`<br>`ℚ[i][x] → ℚ[i] → ℚ[i]` | polyeval(p, z) = p(z) by Horner's rule |
| `polyevalmany` | `.1000110110.` | `polyevalmany` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → (𝔏 ℚ[i]) → (𝔏 ℚ[i])` | polyevalmany(p, zs) = the list of the values p(z) (Horner at every point) |
| `polyevalR` | `.1000110111.` | `polyevalR` | `(𝔏 ℚ) → ℝ → ℝ`<br>`ℚ[i][x] → ℝ[i] → ℝ[i]` | polyevalR(p, x) for a lazy x: pointwise, element n is p(xₙ) (it converges to p(x); |p(xₙ) − p(x)| ≤ L·|xₙ − x|) |
| `polycompose` | `.1000111000.` | `polycompose` | `(𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | polycompose(p, q) = p(q(x)) (Horner in polynomials) |
| `polyshift` | `.1000111001.` | `polyshift` | `(𝔏 ℤ) → ℤ → (𝔏 ℤ)`<br>`(𝔏 ℚ) → ℚ → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → ℤ[i] → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i] → ℚ[i][x]` | polyshift(p, a) = p(x + a) |
| `polyderiv` | `.1000111010.` | `polyderiv` | `(𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`ℚ[i][x] → ℚ[i][x]` | the derivative |
| `polyinteg` | `.1000111100.` | `polyinteg` | `(𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x]` | the antiderivative with constant term 0 |
| `polyconj` | `.1000111101.` | `polyconj` | `ℚ[i][x] → ℚ[i][x]` | the polynomial with conjugated coefficients |
| `polymonic` | `.1000111110.` | `polymonic` | `(𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x]` | the monic multiple (leading coefficient 1; 0 stays 0) |
| `polygcd` | `.1000111111.` | `polygcd` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | the monic greatest common divisor (fraction-free primitive remainder sequence over ℤ, or over ℤ[i] for non-real coefficients); gcd(0, 0) = 0 |
| `polyegcd` | `.1001000000.` | `polyegcd` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔓 (𝔏 ℚ) (𝔓 (𝔏 ℚ) (𝔏 ℚ)))`<br>`ℚ[i][x] → ℚ[i][x] → (𝔓 ℚ[i][x] (𝔓 ℚ[i][x] ℚ[i][x]))` | polyegcd(p, q) = (g, (s, t)) with s·p + t·q = g = polygcd(p, q) (fraction-free: the extended subresultant sequence over ℤ or ℤ[i]); (0, (0, 0)) for p = q = 0 |
| `polylcm` | `.1001000010.` | `polylcm` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | the monic least common multiple (0 if either is 0) |
| `polycontent` | `.1001001000.` | `polycontent` | `(𝔏 ℚ) → ℚ` | the content: a positive rational c with p = ±c·polyprimitive(p) (0 for the zero polynomial) |
| `polyprimitive` | `.1001001001.` | `polyprimitive` | `(𝔏 ℚ) → (𝔏 ℤ)` | the primitive part: coprime integer coefficients, positive leading coefficient |
| `sqfree` | `.1001101000.` | `sqfree` | `(𝔏 ℚ) → (𝔏 ℚ)`<br>`ℚ[i][x] → ℚ[i][x]` | the square-free part p / gcd(p, p′), monic (0 stays 0) |
| `sqfreefactor` | `.1001101011.` | `sqfreefactor` | `(𝔏 ℚ) → (𝔏 (𝔓 (𝔏 ℚ) ℕ))`<br>`ℚ[i][x] → (𝔏 (𝔓 ℚ[i][x] ℕ))` | Yun's square-free factorisation: pairs (factor, multiplicity), factors monic, square-free, coprime; p = lc·Π fᵏ |
| `resultant` | `.1001101101.` | `resultant` | `(𝔏 ℤ) → (𝔏 ℤ) → ℤ`<br>`(𝔏 ℚ) → (𝔏 ℚ) → ℚ`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i]) → ℤ[i]`<br>`ℚ[i][x] → ℚ[i][x] → ℚ[i]` | the resultant Res(p, q) (subresultant algorithm on integer polynomials over ℤ or ℤ[i], fraction-free; 0 if either is 0; Res of two non-zero constants is 1) |
| `discriminant` | `.1001101110.` | `disc` | `(𝔏 ℤ) → ℤ`<br>`(𝔏 ℚ) → ℚ`<br>`(𝔏 ℤ[i]) → ℤ[i]`<br>`ℚ[i][x] → ℚ[i]` | the discriminant (−1)^(n(n−1)/2)·Res(p, p′)/lc(p); 1 for degree 1, 0 for a constant |
| `sturm` | `.1001110111.` | `sturm` | `(𝔏 ℚ) → (𝔏 (𝔏 ℤ))` | the Sturm sequence p, p′, −rem(p, p′), …, each scaled by a positive factor to a primitive integer polynomial |
| `nrealroots` | `.1001111000.` | `nrealroots` | `(𝔏 ℚ) → ℕ` | the number of distinct real roots (Sturm: V(−∞) − V(+∞)); 0 for the zero polynomial |
| `countroots` | `.1001111001.` | `countroots` | `(𝔏 ℚ) → ℚ → ℚ → ℕ` | countroots(p, a, b): the number of distinct real roots in (a, b] (Sturm on the square-free part); 0 if a ≥ b or p = 0 |
| `isolate` | `.1010000011.` | `isolate` | `(𝔏 ℚ) → (𝔏 (𝔓 ℚ ℚ))` | isolating intervals of the distinct real roots, sorted: pairs (a, b), a < b, one root in (a, b), none at b — or (r, r) for a rational root r met exactly |
| `refine` | `.1010000111.` | `refine` | `(𝔏 ℚ) → ℚ → ℚ → ℕ → (𝔓 ℚ ℚ)` | refine(p, a, b, n): bisect the interval (a, b] isolating one real root of p until its width is ≤ 2⁻ⁿ (a root hit exactly gives (r, r)); (a, b) unchanged if (a, b] does not contain exactly one distinct root |
| `root` | `.1010001011.` | `root` | `(𝔏 ℚ) → ℕ → ℝ` | root(p, k): the k-th distinct real root of p in increasing order (k ≥ 1) as a lazy real, element n within 2⁻ⁿ; 0 if there is no such root |
| `realroots` | `.1010001100.` | `realroots` | `(𝔏 ℚ) → (𝔏 ℝ)` | all distinct real roots as lazy reals, in increasing order (element n within 2⁻ⁿ) |
| `signat` | `.1010010000.` | `signat` | `(𝔏 ℚ) → (𝔏 ℚ) → ℚ → ℚ → ℤ` | signat(q, p, a, b): the sign −1/0/1 of q at the root of p isolated by (a, b] (exact: gcd and Sturm counts decide q(root) = 0); a = b stands for the rational root a; 0 if (a, b] does not isolate one root of p (or p(a) ≠ 0 for a = b) |
| `ratroots` | `.1010110001.` | `ratroots` | `ℚ[i][x] → (𝔏 ℚ[i])` | the distinct roots of p in ℚ(i), sorted by (Re, Im): exact (Sturm isolation + aₙ·r ∈ ℤ for the rational ones, positive Kronecker quadratics for the non-real ones; non-real coefficients: the rational root theorem in ℤ[i] over Gaussian divisors of P(0) and lc P); [] for p = 0 |
| `polyfactor` | `.1011011111.` | `polyfactor` | `(𝔏 ℚ) → (𝔓 ℚ (𝔏 (𝔓 (𝔏 ℤ) ℕ)))` | complete factorisation over ℚ: (c, [(f, k)]) with p = c·Π fᵏ, every f irreducible, primitive, with positive leading coefficient (Yun + rational roots + Zassenhaus: distinct-degree factorisation mod three small primes with a degree sieve, Cantor–Zassenhaus splitting, Hensel lifting, recombination of subsets — exponential only in the number of modular factors) |
| `isirreducible` | `.1011100000.` | `isirreducible` | `(𝔏 ℚ) → 𝔹` | irreducible over ℚ (degree ≥ 1 and no factorisation; constants are not irreducible) |
| `interpolate` | `.1011100110.` | `interpolate` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℚ[i]) → (𝔏 ℚ[i]) → ℚ[i][x]` | interpolate(xs, ys): the polynomial of degree < n through the n points (xⱼ, yⱼ) (Newton's divided differences; a repeated node is ignored) |
| `polyfromroots` | `.1011100111.` | `polyfromroots` | `(𝔏 ℤ) → (𝔏 ℤ)`<br>`(𝔏 ℚ) → (𝔏 ℚ)`<br>`(𝔏 ℤ[i]) → (𝔏 ℤ[i])`<br>`(𝔏 ℚ[i]) → ℚ[i][x]` | polyfromroots(rs) = Π (x − r)  (1 for the empty list) |
| `cyclotomic` | `.1011101010.` | `cyclotomic` | `ℕ → (𝔏 ℤ)` | the cyclotomic polynomial Φₙ (cyclotomic(0) = 1) |
| `chebyshevT` | `.1011101101.` | `chebyshevT` | `ℕ → (𝔏 ℤ)` | the Chebyshev polynomial Tₙ (T₀ = 1, T₁ = x, Tₙ₊₁ = 2x·Tₙ − Tₙ₋₁) |
| `chebyshevU` | `.1011101110.` | `chebyshevU` | `ℕ → (𝔏 ℤ)` | the Chebyshev polynomial of the second kind Uₙ (U₀ = 1, U₁ = 2x, same recurrence) |
| `legendreP` | `.1011101111.` | `legendreP` | `ℕ → (𝔏 ℚ)` | the Legendre polynomial Pₙ ((n+1)Pₙ₊₁ = (2n+1)x·Pₙ − n·Pₙ₋₁) |
| `hermiteH` | `.1011110000.` | `hermiteH` | `ℕ → (𝔏 ℤ)` | the (physicists') Hermite polynomial Hₙ (H₀ = 1, H₁ = 2x, Hₙ₊₁ = 2x·Hₙ − 2n·Hₙ₋₁) |
| `laguerreL` | `.1011110001.` | `laguerreL` | `ℕ → (𝔏 ℚ)` | the Laguerre polynomial Lₙ ((n+1)Lₙ₊₁ = (2n+1−x)·Lₙ − n·Lₙ₋₁) |
| `companion` | `.1011110010.` | `companion` | `(𝔏 ℚ) → (𝔏 (𝔏 ℚ))`<br>`ℚ[i][x] → (𝔏 (𝔏 ℚ[i]))` | the companion matrix (list of rows: ones below the diagonal, last column −c₀ … −cₙ₋₁) of the monic multiple of p: its characteristic polynomial is polymonic(p); [] for degree ≤ 0 |
| `polystr` | `.1011110110.` | `polystr` | `ℚ[i][x] → 𝕊` | the polynomial in human notation, highest degree first: "x^2 - 2*x + 1", "(1 + i)*x + 3", "0" |
| `croots` | `.1100000001.` | `croots` | `ℚ[i][x] → (𝔏 ℝ[i])` | all complex roots with multiplicity, as lazy complex numbers (numerical: Weierstrass/Durand–Kerner iteration in fixed point on Yun's square-free factors, simple roots first; element n within about 2⁻ⁿ once converged, see lib/poly.imo) |

### Functions of a complex variable: elementary functions with principal branches, special functions, constants (`lib/complex.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `𝜋` | `.11010110001.` | `Pi` | `ℝ` | π = 3.14159…, by Machin's formula 16·atan(1/5) − 4·atan(1/239); element n is within 2⁻ⁿ |
| `ℯ` | `.11010110010.` | `E` | `ℝ` | Euler's number e = 2.71828…; element n is within 2⁻ⁿ |
| `logc` | `.11010110011.` | `Log` | `ℚ[i] → ℝ[i]` | principal logarithm log z = log|z| + i·arg z, Im in (−π, π] (log(−x) = log x + iπ); log 0 = 0; element n within 2⁻ⁿ |
| `logcᴿ` | `.11010110100.` | `log`, `Log` | `ℝ[i] → ℝ[i]` | principal logarithm of a lazy argument (through the diagonal ⟐; converges off the negative real axis) |
| `logb` | `.11010110101.` | `logb` | `ℚ[i] → ℚ[i] → ℝ[i]` | logarithm to base b: logb(b, z) = log z / log b (principal logs); 0 when b is 0 or 1 |
| `log₁p` | `.11010110110.` | `log1p` | `ℚ[i] → ℝ[i]` | log(1 + z) (principal); 0 at z = −1 |
| `log₁pᴿ` | `.11010110111.` | `log1p` | `ℝ[i] → ℝ[i]` | log(1 + z) of a lazy argument |
| `expm₁` | `.11010111000.` | `expm1` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | eᶻ − 1 (absolute error: element n is within 2⁻ⁿ) |
| `expm₁ᴿ` | `.11010111001.` | `expm1` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | eᶻ − 1 of a lazy argument |
| `pow` | `.11010111010.` | `pow` | `ℚ[i] → ℚ[i] → ℝ[i]` | principal power z^w = e^(w·log z); exact (a constant stream) for an integer w; 0^w = 0 for w ≠ 0, 0⁰ = 1 |
| `powᴿ` | `.11010111100.` | `pow` | `ℝ[i] → ℝ[i] → ℝ[i]` | principal power of lazy arguments (element n of pow(xₙ, yₙ)) |
| `nthroot` | `.11010111110.` | `nthroot` | `ℚ[i] → ℤ → ℝ[i]` | principal n-th root z^(1/n) = e^(log z / n) (n may be negative); 0 for z = 0 or n = 0 |
| `cbrt` | `.11010111111.` | `cbrt` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | cube root: the real root of a real x (cbrt(−8) = −2), the principal root e^(log z / 3) of a non-real z |
| `cbrtᴿ` | `.11011000000.` | `cbrt` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | cube root of a lazy argument |
| `rootsofunity` | `.11011000010.` | `rootsofunity` | `ℤ → (𝔏 ℝ[i])` | the n-th roots of unity e^(2πik/n), k = 0 … n − 1 (empty for n ≤ 0) |
| `arg` | `.11011000011.` | `arg` | `ℚ[i] → ℝ` | principal argument of z, in (−π, π]; arg 0 = 0 |
| `argᴿ` | `.11011000100.` | `arg` | `ℝ[i] → ℝ` | principal argument of a lazy argument |
| `atan2` | `.11011000101.` | `atan2` | `ℚ → ℚ → ℝ` | atan2(y, x): the angle of the point (x, y), in (−π, π]; atan2(0, 0) = 0 |
| `cis` | `.11011000110.` | `cis` | `ℚ → ℝ[i]`<br>`ℚ[i] → ℝ[i]` | cis t = cos t + i·sin t = e^(it) |
| `cisᴿ` | `.11011000111.` | `cis` | `ℝ[i] → ℝ[i]` | e^(it) of a lazy argument |
| `polar` | `.11011001000.` | `polar` | `ℚ → ℚ → ℝ[i]`<br>`ℚ[i] → ℚ[i] → ℝ[i]` | polar(r, t) = r·e^(it) |
| `csgn` | `.11011001001.` | `csgn` | `ℚ[i] → ℝ[i]` | complex sign z/|z|; 0 at 0 |
| `csgnᴿ` | `.11011001010.` | `csgn` | `ℝ[i] → ℝ[i]` | z/|z| of a lazy argument |
| `hypot` | `.11011001011.` | `hypot` | `ℚ → ℚ → ℝ`<br>`ℚ[i] → ℚ[i] → ℝ` | hypot(x, y) = √(x² + y²) (for complex arguments √(|x|² + |y|²)) |
| `cot` | `.11011001111.` | `cot` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | cotangent cos z / sin z = i·(e^(2iz) + 1)/(e^(2iz) − 1); cot 0 = 0 (pole) |
| `cotᴿ` | `.11011010000.` | `cot` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | cotangent of a lazy argument |
| `sec` | `.11011010001.` | `sec` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | secant 1/cos z |
| `secᴿ` | `.11011010010.` | `sec` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | secant of a lazy argument |
| `csc` | `.11011010011.` | `csc` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | cosecant 1/sin z; csc 0 = 0 (pole) |
| `cscᴿ` | `.11011010100.` | `csc` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | cosecant of a lazy argument |
| `tanᴿ` | `.11011010101.` | `tan` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | tangent of a lazy argument (the series quotient of lib/real.imo through the diagonal) |
| `coth` | `.11011011000.` | `coth` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic cotangent cosh z / sinh z = 1 + 2/(e^(2z) − 1); coth 0 = 0 (pole) |
| `cothᴿ` | `.11011011001.` | `coth` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | hyperbolic cotangent of a lazy argument |
| `sech` | `.11011011010.` | `sech` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic secant 1/cosh z |
| `sechᴿ` | `.11011011011.` | `sech` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | hyperbolic secant of a lazy argument |
| `csch` | `.11011011100.` | `csch` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic cosecant 1/sinh z; csch 0 = 0 (pole) |
| `cschᴿ` | `.11011011101.` | `csch` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | hyperbolic cosecant of a lazy argument |
| `sinhᴿ` | `.11011011110.` | `sinh` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | hyperbolic sine of a lazy argument (the series of lib/real.imo through the diagonal) |
| `coshᴿ` | `.11011011111.` | `cosh` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | hyperbolic cosine of a lazy argument |
| `tanhᴿ` | `.11011100000.` | `tanh` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | hyperbolic tangent of a lazy argument |
| `sinc` | `.11011100001.` | `sinc` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | sinc z = sin z / z, sinc 0 = 1 (unnormalised) |
| `sincᴿ` | `.11011100010.` | `sinc` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | sinc of a lazy argument |
| `asinh` | `.11011101101.` | `asinh` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | inverse hyperbolic sine (principal; cuts on the imaginary axis beyond ±i, as in cmath) |
| `asinhᴿ` | `.11011101110.` | `asinh` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | inverse hyperbolic sine of a lazy argument |
| `asin` | `.11011101111.` | `asin` | `ℚ[i] → ℝ[i]` | inverse sine (principal; cuts (−∞, −1) and (1, ∞) as in cmath: asin x = sgn x·π/2 + i·acosh|x| there) |
| `asinᴿ` | `.11011110000.` | `asin` | `ℝ[i] → ℝ[i]` | inverse sine of a lazy argument |
| `acos` | `.11011110001.` | `acos` | `ℚ[i] → ℝ[i]` | inverse cosine (principal; cuts as asin: acos x = −i·acosh x for x > 1, π − i·acosh|x| for x < −1) |
| `acosᴿ` | `.11011110010.` | `acos` | `ℝ[i] → ℝ[i]` | inverse cosine of a lazy argument |
| `atanc` | `.11011110011.` | `atan` | `ℚ[i] → ℝ[i]` | inverse tangent of a complex z (principal; cuts on the imaginary axis beyond ±i, as in cmath); 0 at the poles ±i |
| `atancᴿ` | `.11011110100.` | `atan` | `ℝ[i] → ℝ[i]` | inverse tangent of a lazy complex argument |
| `acot` | `.11011110101.` | `acot` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | inverse cotangent atan(1/z) (principal; acot 0 = π/2; 0 at the poles ±i) |
| `acotᴿ` | `.11011110110.` | `acot` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | inverse cotangent of a lazy argument |
| `asec` | `.11011110111.` | `asec` | `ℚ[i] → ℝ[i]` | inverse secant acos(1/z); 0 at z = 0 (pole) |
| `asecᴿ` | `.11011111000.` | `asec` | `ℝ[i] → ℝ[i]` | inverse secant of a lazy argument |
| `acsc` | `.11011111001.` | `acsc` | `ℚ[i] → ℝ[i]` | inverse cosecant asin(1/z); 0 at z = 0 (pole) |
| `acscᴿ` | `.11011111010.` | `acsc` | `ℝ[i] → ℝ[i]` | inverse cosecant of a lazy argument |
| `acosh` | `.11011111011.` | `acosh` | `ℚ[i] → ℝ[i]` | inverse hyperbolic cosine (principal; cut (−∞, 1) as in cmath: acosh x = i·acos x on [−1, 1), acosh|x| + iπ below −1) |
| `acoshᴿ` | `.11011111100.` | `acosh` | `ℝ[i] → ℝ[i]` | inverse hyperbolic cosine of a lazy argument |
| `atanh` | `.11011111101.` | `atanh` | `ℚ[i] → ℝ[i]` | inverse hyperbolic tangent (principal; cuts (−∞, −1) and (1, ∞), value with Im = +π/2 there, as in cmath); 0 at ±1 |
| `atanhᴿ` | `.11011111110.` | `atanh` | `ℝ[i] → ℝ[i]` | inverse hyperbolic tangent of a lazy argument |
| `acoth` | `.11011111111.` | `acoth` | `ℚ[i] → ℝ[i]` | inverse hyperbolic cotangent atanh(1/z) = ¼·log(|z + 1|²/|z − 1|²) + i·½·atan2(−2y, |z|² − 1); acoth 0 = iπ/2; 0 at ±1 |
| `acothᴿ` | `.11100000000.` | `acoth` | `ℝ[i] → ℝ[i]` | inverse hyperbolic cotangent of a lazy argument |
| `asech` | `.11100000001.` | `asech` | `ℚ[i] → ℝ[i]` | inverse hyperbolic secant acosh(1/z); 0 at z = 0 (pole) |
| `asechᴿ` | `.11100000010.` | `asech` | `ℝ[i] → ℝ[i]` | inverse hyperbolic secant of a lazy argument |
| `acsch` | `.11100000011.` | `acsch` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | inverse hyperbolic cosecant asinh(1/z); 0 at z = 0 (pole) |
| `acschᴿ` | `.11100000100.` | `acsch` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | inverse hyperbolic cosecant of a lazy argument |
| `𝛾` | `.11100100011.` | `EulerGamma` | `ℝ` | Euler's constant γ = 0.57721…, as −ψ(1) (asymptotic series of the digamma function after a shift); element n is within 2⁻ⁿ |
| `Catalan` | `.11100100100.` | `Catalan` | `ℝ` | Catalan's constant G = Σ (−1)ᵏ/(2k + 1)² = 0.91596…, by Ramanujan's series; element n is within 2⁻ⁿ |
| `absc` | `.11101010011.` | `abs` | `ℚ[i] → ℝ` | modulus |z| = √(x² + y²) of an exact complex number; element n within 2⁻ⁿ |
| `Γ` | `.11101010100.` | `gamma` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | gamma function Γ(z): Stirling's series (exact Bernoulli numbers, remainder ≤ first omitted term) after the shift Γ(z) = Γ(z + N)/(z(z + 1)⋯(z + N − 1)); 0 at the poles 0, −1, −2, …; element n within 2⁻ⁿ; the cost grows with |z| |
| `Γᴿ` | `.11101010101.` | `gamma` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | gamma function of a lazy argument (through the diagonal; converges away from the poles) |
| `lgamma` | `.11101010110.` | `lgamma` | `ℚ → ℝ` | log|Γ(x)| of a real x (as C's lgamma): Stirling's series after a shift; 0 at the poles; element n within 2⁻ⁿ |
| `digamma` | `.11101010111.` | `digamma` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | digamma function ψ(z) = Γ′(z)/Γ(z): asymptotic series after the shift ψ(z) = ψ(z + N) − Σ 1/(z + j); 0 at the poles; element n within 2⁻ⁿ |
| `beta` | `.11101011000.` | `beta` | `ℚ → ℚ → ℝ`<br>`ℚ[i] → ℚ[i] → ℝ[i]` | beta function B(a, b) = Γ(a)Γ(b)/Γ(a + b) = e^(log Γ(a) + log Γ(b) − log Γ(a + b)) (one exponential); 0 when a or b is a pole of Γ, and when a + b is one (1/Γ(a + b) = 0); element n within 2⁻ⁿ |
| `erf` | `.11101011001.` | `erf` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | error function erf z = (2/√π)·Σ (−1)ᵏ z^(2k+1)/(k!(2k + 1)) (all terms carried at the precision the largest one needs); for real |x| ≥ 1 with x² ≥ 0.7n element n is ±1 (erfc|x| < e^(−x²)); element n within 2⁻ⁿ; the cost grows with |z|² |
| `erfᴿ` | `.11101011010.` | `erf` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | error function of a lazy argument |
| `erfc` | `.11101011011.` | `erfc` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | complementary error function 1 − erf z (absolute error: element n within 2⁻ⁿ) |
| `erfcᴿ` | `.11101011100.` | `erfc` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | complementary error function of a lazy argument |
| `zeta` | `.11101011101.` | `zeta` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | Riemann zeta function ζ(s): Euler–Maclaurin summation (Re s ≥ −8; exact powers for an integer s), the functional equation below; exact at 0 and the negative integers (−B₍ₙ₊₁₎/(n + 1)); ζ(1) = 0 (pole); element n within 2⁻ⁿ; the cost grows with |s| |
| `polylog` | `.11101011110.` | `polylog` | `ℤ → ℚ[i] → ℝ[i]` | polylogarithm Liₛ(z) for an integer s: the rational function z·Aₜ(z)/(1 − z)^(t+1) for s = −t ≤ 0 (Eulerian polynomials, every z ≠ 1), −log(1 − z) for s = 1 (z ≠ 1), Σ zᵏ/kˢ for s ≥ 2 and |z| < 1, ζ(s) at z = 1 and −(1 − 2^(1−s))·ζ(s) at z = −1; 0 elsewhere (|z| ≥ 1) and at the pole z = 1; element n within 2⁻ⁿ |
| `lambertw` | `.11101011111.` | `lambertw` | `ℚ → ℝ` | Lambert W function, principal branch: W(x)·e^W(x) = x for a real x ≥ −1/e (Newton's method with a certified residual bound); 0 for x < −1/e; element n within 2⁻ⁿ |
| `lambertwᴿ` | `.11101100000.` | `lambertw` | `ℝ → ℝ` | Lambert W function of a lazy argument |
| `besselj` | `.11101100001.` | `besselj` | `ℤ → ℚ → ℝ`<br>`ℤ → ℚ[i] → ℝ[i]` | Bessel function of the first kind Jₙ(z) of integer order n (power series; J₋ₙ = (−1)ⁿJₙ); element n within 2⁻ⁿ; the cost grows with |z| |
| `besseli` | `.100001110000.` | `besseli` | `ℤ → ℚ → ℝ`<br>`ℤ → ℚ[i] → ℝ[i]` | modified Bessel function of the first kind Iₙ(z) of integer order n (power series; I₋ₙ = Iₙ); element n within 2⁻ⁿ; the cost grows with |z| |
| `erfi` | `.100001110001.` | `erfi` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | imaginary error function erfi z = −i·erf(iz) = (2/√π)·Σ z^(2k+1)/(k!(2k + 1)); element n within 2⁻ⁿ; the cost grows with |z|² |
| `agm` | `.11101100010.` | `agm` | `ℚ → ℚ → ℝ` | arithmetic–geometric mean M(a, b) of reals of one sign (M(−a, −b) = −M(a, b)), with outward rounding; 0 when a·b ≤ 0; element n within 2⁻ⁿ |
| `ellipk` | `.11101100011.` | `ellipk` | `ℚ → ℝ` | complete elliptic integral of the first kind K(m) = ∫₀^(π/2) dθ/√(1 − m·sin²θ) (parameter m < 1) = π/(2·M(1, √(1 − m))); 0 for m ≥ 1 (pole at 1); element n within 2⁻ⁿ |
| `ellipe` | `.11101100100.` | `ellipe` | `ℚ → ℝ` | complete elliptic integral of the second kind E(m) = ∫₀^(π/2) √(1 − m·sin²θ) dθ (m ≤ 1) = K(m)·(1 − Σ 2^(n−1)cₙ²) (Gauss' AGM method, outward rounding); E(1) = 1; 0 for m > 1; element n within 2⁻ⁿ |
| `Ei` | `.11101100101.` | `expint` | `ℚ → ℝ` | exponential integral Ei(x) = γ + log|x| + Σ xᵏ/(k·k!) (principal value for x > 0); 0 at x = 0 (pole); element n within 2⁻ⁿ |
| `li` | `.11101100110.` | `li` | `ℚ → ℝ` | logarithmic integral li(x) = Ei(log x) for x > 0 (principal value for x > 1); 0 at x = 1 (pole) and for x ≤ 0; element n within 2⁻ⁿ |
| `Si` | `.11101100111.` | `Si` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | sine integral Si(z) = ∫₀ᶻ sin t/t dt (power series); element n within 2⁻ⁿ |
| `Siᴿ` | `.11101101000.` | `Si` | `ℝ → ℝ`<br>`ℝ[i] → ℝ[i]` | sine integral of a lazy argument |
| `Ci` | `.11101101001.` | `Ci` | `ℚ[i] → ℝ[i]` | cosine integral Ci(z) = γ + log z + Σ (−1)ᵏ z^(2k)/(2k(2k)!) (principal log: Ci(−x) = Ci(x) + iπ for x > 0); 0 at z = 0 (pole); element n within 2⁻ⁿ |
| `Shi` | `.100001110100.` | `Shi` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | hyperbolic sine integral Shi(z) = ∫₀ᶻ sinh t/t dt (power series); element n within 2⁻ⁿ; the cost grows with |z| |
| `Chi` | `.100001110101.` | `Chi` | `ℚ[i] → ℝ[i]` | hyperbolic cosine integral Chi(z) = γ + log z + Σ z^(2k)/(2k(2k)!) (principal log); 0 at z = 0 (pole); element n within 2⁻ⁿ |
| `dawson` | `.100001110111.` | `dawson` | `ℚ → ℝ`<br>`ℚ[i] → ℝ[i]` | Dawson's integral D(z) = e^(−z²)·∫₀ᶻ e^(t²) dt = (√π/2)·e^(−z²)·erfi(z) (power series); element n within 2⁻ⁿ; the cost grows with |z|² |

### Number theory over ℤ and ℤ[i] (`lib/numtheory.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `egcd` | `.1100100000.` | `egcd` | `ℤ → ℤ → (𝔓 ℕ (𝔓 ℤ ℤ))`<br>`ℤ[i] → ℤ[i] → (𝔓 ℤ[i] (𝔓 ℤ[i] ℤ[i]))` | Bézout: (g, (s, t)) with s·a + t·b = g = gcd(a, b) ≥ 0 (extended Euclid; egcd(0, 0) = (0, (0, 0))) |
| `modinv` | `.1100100011.` | `modinv` | `ℕ → ℕ → ℕ`<br>`ℤ → ℕ → ℤ`<br>`ℤ[i] → ℤ[i] → ℤ[i]` | the inverse of a modulo n, in [0, n); 0 when gcd(a, n) ≠ 1 (modulo 0: a itself when a = ±1, else 0); on ℤ[i] reduced by rem (0 when not invertible) |
| `powmod` | `.1100100100.` | `powmod` | `ℕ → ℤ → ℕ → ℕ`<br>`ℤ → ℤ → ℕ → ℤ` | aᵉ mod n in [0, n), square and multiply (Montgomery multiplication in base 4 = −(i−1)⁴ for odd n); e < 0 through modinv(a, n) (so 0 when a is not invertible); modulo 0 it is aᵉ in ℤ |
| `islucasprp` | `.1100110010.` | `islucasprp` | `ℤ → 𝔹` | n passes the strong Lucas probable prime test with Selfridge's parameters (D the first of 5, −7, 9, … with (D/n) = −1, P = 1, Q = (1 − D)/4): every prime does; with Miller–Rabin it is the Baillie–PSW test |
| `isprime` | `.1100111001.` | `isprime` | `ℤ → 𝔹` | n is a prime (negative n: false); trial division below 1849, else a gcd with 2·3·…·41 and Miller–Rabin with the bases 2, 3, 5, …, 41, deterministic below ψ₁₃ ≈ 3.3·10²⁴ (A014233); above, all 13 bases and the strong Lucas test (Baillie–PSW: no counterexample is known); about 20 s at 10¹² |
| `nextprime` | `.1100111100.` | `nextprime` | `ℤ → ℕ` | the least prime > n (odd candidates tested with isprime) |
| `prevprime` | `.1100111111.` | `prevprime` | `ℤ → ℕ` | the greatest prime < n; 0 when n ≤ 2 |
| `factor` | `.1101010100.` | `factor` | `ℤ → (𝔏 (𝔓 ℕ ℕ))` | the prime factorisation of |n|: list of (p, e), p ascending; factor(0) = factor(±1) = []; trial division to 47, Miller–Rabin, Brent–Pollard ρ (practical to about 10¹²: a minute or two for a product of two 6-digit primes) |
| `primefactors` | `.1101010101.` | `primefactors` | `ℤ → (𝔏 ℕ)` | the distinct primes dividing |n|, ascending |
| `divisors` | `.1101011000.` | `divisors` | `ℤ → (𝔏 ℕ)` | the positive divisors of |n|, ascending (divisors(0) = []) |
| `numdivisors` | `.1101011001.` | `numdivisors` | `ℤ → ℕ` | τ(n): the number of divisors of |n|  (τ(0) = 0) |
| `sigma` | `.1101011010.` | `sigma` | `ℕ → ℤ → ℕ` | σₖ(n): the sum of the k-th powers of the divisors of |n|, as Π (1 + pᵏ + … + pᵏᵉ)  (σₖ(0) = 0) |
| `totient` | `.1101011011.` | `totient` | `ℤ → ℕ` | Euler's φ(|n|) = Π pᵉ⁻¹(p − 1)  (φ(0) = 0) |
| `carmichael` | `.1101011101.` | `carmichael` | `ℤ → ℕ` | Carmichael's λ(|n|): the exponent of (ℤ/n)ˣ, the lcm of the λ(pᵉ)  (λ(0) = 0, λ(1) = 1) |
| `mobius` | `.1101011110.` | `mobius` | `ℤ → ℤ` | Möbius μ(|n|): 0 when a square divides n, else (−1)^(number of primes)  (μ(0) = 0) |
| `liouville` | `.1101011111.` | `liouville` | `ℤ → ℤ` | Liouville λ(|n|) = (−1)^Ω(n)  (0 for n = 0) |
| `omega` | `.1101100000.` | `omega` | `ℤ → ℕ` | ω(n): the number of distinct primes dividing |n|  (ω(0) = ω(1) = 0) |
| `bigomega` | `.1101100001.` | `bigomega` | `ℤ → ℕ` | Ω(n): the number of prime factors of |n| with multiplicity  (Ω(0) = 0) |
| `radical` | `.1101100010.` | `radical` | `ℤ → ℕ` | rad(n): the product of the distinct primes dividing |n|  (rad(0) = 0, rad(1) = 1) |
| `issquarefree` | `.1101100011.` | `issquarefree` | `ℤ → 𝔹` | no square > 1 divides n  (false for 0) |
| `isperfect` | `.1101100100.` | `isperfect` | `ℤ → 𝔹` | n > 0 and σ₁(n) = 2n |
| `jacobi` | `.1101101001.` | `jacobi` | `ℤ → ℕ → ℤ` | the Jacobi symbol (a/n) for odd n > 0 (binary algorithm with reciprocity); 0 when n is even or 0 |
| `legendre` | `.1101101010.` | `legendre` | `ℤ → ℕ → ℤ` | the Legendre symbol (a/p) ∈ {−1, 0, 1} for an odd prime p (computed as the Jacobi symbol, which it is for any odd p) |
| `kronecker` | `.1101101011.` | `kronecker` | `ℤ → ℤ → ℤ` | the Kronecker symbol (a/n), the extension of the Jacobi symbol to every integer n |
| `eulercriterion` | `.1101101100.` | `eulercriterion` | `ℤ → ℕ → ℤ` | Euler's criterion a^((p−1)/2) mod p, with the residue p − 1 written −1: the Legendre symbol when p is an odd prime (for any n ≥ 1 it is a^⌊(n−1)/2⌋ mod n; 0 for n = 0) |
| `sqrtmod` | `.1101110101.` | `sqrtmod` | `ℤ → ℕ → ℤ` | the least x ≥ 0 with x² ≡ a (mod n), −1 when there is none; Tonelli–Shanks for an odd prime n, a search over x < n otherwise (O(n)); modulo 0 the exact square root |
| `crt` | `.1101110111.` | `crt` | `(𝔏 ℤ) → (𝔏 ℕ) → (𝔓 𝔹 (𝔓 ℕ ℕ))` | Chinese remainder theorem for any moduli (not necessarily coprime): (true, (x, M)) with x ≡ aₖ mod mₖ, 0 ≤ x < M = lcm(mₖ); (false, (0, 0)) when inconsistent; a modulus 0 asks for equality (M = 0); the lists are paired up to the shorter one |
| `ordmod` | `.1101111100.` | `ordmod` | `ℤ → ℕ → ℕ` | the multiplicative order of a modulo n (least k ≥ 1 with aᵏ ≡ 1), 0 when gcd(a, n) ≠ 1; from Carmichael's λ(n); modulo 0: the order in ℤ (1 for 1, 2 for −1, else 0) |
| `primroot` | `.1110000001.` | `primroot` | `ℕ → ℕ` | the least primitive root modulo n (a generator of (ℤ/n)ˣ), 0 when there is none (n not 1, 2, 4, pᵉ, 2pᵉ; also primroot(0) = primroot(1) = 0) |
| `dlog` | `.1110001110.` | `dlog` | `ℤ → ℤ → ℕ → ℤ` | the discrete logarithm: the least x ≥ 0 with aˣ ≡ b (mod n), −1 when there is none (any n, a not necessarily coprime to n); baby-step giant-step, O(√n) steps and memory |
| `quadresidues` | `.1110010000.` | `quadresidues` | `ℕ → (𝔏 ℕ)` | the quadratic residues modulo n: the distinct values x² mod n, ascending (including 0; [] for n = 0) |
| `primes` | `.1110010111.` | `primes` | `ℤ → (𝔏 ℕ)` | all primes ≤ n, ascending (sieve of Eratosthenes on the odd numbers; about n·π(√n) cheap steps) |
| `primepi` | `.1110011000.` | `primepi` | `ℤ → ℕ` | π(n): the number of primes ≤ n (by the sieve) |
| `nthprime` | `.1110011001.` | `nthprime` | `ℕ → ℕ` | the k-th prime (nthprime(1) = 2; nthprime(0) = 0), by sieving up to k·(L + 3) (L = digits of k), a bound for pₖ |
| `fib` | `.1110011100.` | `fib` | `ℤ → ℤ`<br>`ℕ → ℕ` | the Fibonacci number F(n) (fast doubling); F(−n) = (−1)ⁿ⁺¹F(n) |
| `lucas` | `.1110011101.` | `lucas` | `ℤ → ℤ`<br>`ℕ → ℕ` | the Lucas number L(n) = 2F(n+1) − F(n) (fast doubling); L(−n) = (−1)ⁿL(n) |
| `catalan` | `.1110011110.` | `catalan` | `ℕ → ℕ` | the Catalan number C(n) = (2n choose n)/(n + 1) |
| `bell` | `.1110100001.` | `bell` | `ℕ → ℕ` | the Bell number Bₙ (set partitions of n elements), by the Bell triangle: O(n²) additions |
| `stirling₁` | `.1110100110.` | `stirling1` | `ℕ → ℕ → ℤ` | the signed Stirling number of the first kind s(n, k) (coefficient of xᵏ in x(x−1)…(x−n+1)), by rows: O(n·k) |
| `stirling₂` | `.1110100111.` | `stirling2` | `ℕ → ℕ → ℕ` | the Stirling number of the second kind S(n, k) (partitions of n elements into k blocks), by rows: O(n·k) |
| `partitions` | `.1110101010.` | `partitions` | `ℕ → ℕ` | the partition number p(n), by Euler's pentagonal number recurrence: O(n^1.5) additions |
| `bernoulli` | `.1110110000.` | `bernoulli` | `ℕ → ℚ` | the Bernoulli number Bₙ, exactly, with B₁ = −1/2 (from the integer tangent numbers: O(n²) integer operations) |
| `zetaeven` | `.1110110001.` | `zetaeven` | `ℕ → ℚ` | ζ(2n)/π²ⁿ, an exact rational (ζ(2) = π²/6, ζ(4) = π⁴/90, …; −1/2 for n = 0), from the tangent number Tₙ |
| `harmonic` | `.1110110101.` | `harmonic` | `ℕ → ℚ` | the harmonic number Hₙ = 1 + 1/2 + … + 1/n, exactly, in lowest terms (H₀ = 0) |
| `digitsum` | `.1110110111.` | `digitsum` | `ℤ → ℕ → ℕ` | the sum of the digits of |n| in base b ≥ 2 (base 1: |n|, base 0: 0) |
| `iroot` | `.1110111010.` | `iroot` | `ℕ → ℕ → ℕ` | ⌊n^(1/k)⌋, the integer k-th root (Newton's method from above); iroot(n, 0) = 0 |
| `ispower` | `.1110111100.` | `ispower` | `ℤ → 𝔹` | n = aᵏ for an integer a and some k ≥ 2 (true for 0, 1, −1; a negative n needs an odd k); a k-th root test for every prime k ≤ log₂|n| |
| `contfrac` | `.1110111110.` | `contfrac` | `ℚ → (𝔏 ℤ)` | the continued fraction [a₀; a₁, …, aₖ] of a rational (Euclid with floor quotients; aₖ ≥ 2 unless k = 0) |
| `convergents` | `.1111000001.` | `convergents` | `(𝔏 ℤ) → (𝔏 ℚ)` | the convergents hₖ/kₖ of [a₀; a₁, …] (hₖ = aₖhₖ₋₁ + hₖ₋₂, kₖ = aₖkₖ₋₁ + kₖ₋₂) |
| `cfsqrt` | `.1111000100.` | `cfsqrt` | `ℕ → (𝔓 ℕ (𝔏 ℕ))` | √n = [a₀; a₁, …, aᵣ, a₁, …]: (a₀, the period a₁ … aᵣ); the period is empty when n is a square |
| `pell` | `.1111000101.` | `pell` | `ℕ → (𝔓 ℕ ℕ)` | the fundamental solution (x, y), y > 0 least, of x² − D·y² = 1, from the continued fraction of √D; (1, 0) when D is 0 or a square |
| `gaussfactor` | `.1111001111.` | `gaussfactor` | `ℤ[i] → (𝔓 ℤ[i] (𝔏 (𝔓 ℤ[i] ℕ)))` | z = u·Π πᵉ: (the unit u, the list of (π, e)), π Gaussian primes with Re > 0, Im ≥ 0, by norm then imaginary part; (0, []) for 0. Through the factorisation of N(z) and Gaussian gcds; 1 + i from the trailing zero digits |
| `isgaussprime` | `.1111010010.` | `isgaussprime` | `ℤ[i] → 𝔹` | z is a Gaussian prime: N(z) a prime when Re z·Im z ≠ 0, else |Re z| or |Im z| a prime ≡ 3 (mod 4) |
| `sumtwosquares` | `.1111010111.` | `sumtwosquares` | `ℤ → (𝔏 (𝔓 ℕ ℕ))` | every way to write n = a² + b² with a ≥ b ≥ 0, by increasing b; from the Gaussian factorisation of n ([] when n < 0 or a prime ≡ 3 mod 4 divides n to an odd power) |
| `gaussprimes` | `.1111011001.` | `gaussprimes` | `ℕ → (𝔏 ℤ[i])` | the Gaussian primes of norm ≤ n (normalised: Re > 0, Im ≥ 0), by norm then imaginary part |
| `gcdlist` | `.1111011010.` | `gcdlist` | `(𝔏 ℤ) → ℕ`<br>`(𝔏 ℤ[i]) → ℤ[i]` | the gcd of a list of integers (0 for the empty list); of Gaussian integers, normalised to Re > 0, Im ≥ 0 |
| `lcmlist` | `.1111011100.` | `lcmlist` | `(𝔏 ℤ) → ℕ` | the least common multiple of a list of integers (1 for the empty list, 0 when an element is 0) |
| `issquare` | `.1111011101.` | `issquare` | `ℤ → 𝔹` | n is a perfect square (false for n < 0; through the integer square root) |
| `isprimepower` | `.1111011110.` | `isprimepower` | `ℤ → 𝔹` | n = pᵏ for a prime p and k ≥ 1 (n > 0; from the factorisation) |
| `iscoprime` | `.1111011111.` | `iscoprime` | `ℤ → ℤ → 𝔹`<br>`ℤ[i] → ℤ[i] → 𝔹` | gcd(a, b) = 1; for Gaussian integers: the gcd is a unit |
| `totatives` | `.1111100000.` | `totatives` | `ℕ → (𝔏 ℕ)` | the k in 1 … n with gcd(k, n) = 1, ascending (φ(n) of them; [] for n = 0) |
| `primitiveroots` | `.1111100010.` | `primitiveroots` | `ℕ → (𝔏 ℕ)` | all primitive roots modulo n, ascending: gᵏ mod n for the k ≤ φ(n) prime to φ(n), g = primroot(n); [] when there is none (O(n) products) |
| `ramanujansum` | `.1111100011.` | `ramanujansum` | `ℕ → ℤ → ℤ` | Ramanujan's sum c_q(n) = Σ μ(q/d)·d over the divisors d of gcd(q, n): the sum of the n-th powers of the primitive q-th roots of unity (c₀(n) = 0) |
| `wilson` | `.1111100101.` | `wilson` | `ℤ → 𝔹` | Wilson's theorem as a primality test: n ≥ 2 and (n − 1)! ≡ −1 (mod n), true exactly for the primes (O(n) modular products: a demonstration, not a fast test) |
| `nextgaussprime` | `.1111101000.` | `nextgaussprime` | `ℤ[i] → ℤ[i]` | the next Gaussian prime after z in the order of gaussprimes: the normalised (Re > 0, Im ≥ 0) π with (N(π), Im π) > (N(z), Im z) least |
| `isgausspower` | `.1111101001.` | `isgausspower` | `ℤ[i] → 𝔹` | z = wᵏ for a Gaussian integer w and some k ≥ 2 (true for 0 and the units): with z = u·Π πᵉ, g = gcd of the e has an odd prime factor, or g is even and u = ±1 |

### Rings: ℤ/n, ideals, quotient rings, generic ring algorithms, multivariate polynomials and Gröbner bases (`lib/ring.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `addmod` | `.11101101010.` | `addmod` | `ℤ → ℤ → ℕ → ℕ` | (a + b) mod n, in [0, n)  (n ≥ 1) |
| `submod` | `.11101101011.` | `submod` | `ℤ → ℤ → ℕ → ℕ` | (a − b) mod n, in [0, n) |
| `mulmod` | `.11101101100.` | `mulmod` | `ℤ → ℤ → ℕ → ℕ` | (a · b) mod n, in [0, n) |
| `negmod` | `.11101101101.` | `negmod` | `ℤ → ℕ → ℕ` | (−a) mod n, in [0, n) |
| `zunits` | `.11101101110.` | `zunits` | `ℕ → (𝔏 ℕ)` | the units of ℤ/n: the a in [0, n) with gcd(a, n) = 1, ascending (ℤ/1 is the zero ring: its unit is 0) |
| `zzerodivisors` | `.11101101111.` | `zzerodivisors` | `ℕ → (𝔏 ℕ)` | the zero divisors of ℤ/n: the a in [1, n) with gcd(a, n) > 1, ascending |
| `znilpotents` | `.11101110000.` | `znilpotents` | `ℕ → (𝔏 ℕ)` | the nilpotent elements of ℤ/n: the multiples of rad(n) in [0, n), ascending (the nilradical) |
| `zidempotents` | `.11101110001.` | `zidempotents` | `ℕ → (𝔏 ℕ)` | the idempotents of ℤ/n: the a in [0, n) with a² ≡ a, ascending (2ᵏ of them for k distinct primes) |
| `zideal` | `.11101110010.` | `zideal` | `ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | the ideal of ℤ/n generated by a list of integers: its elements, ascending (the multiples of d = gcd(n, generators)) |
| `zideals` | `.11101110011.` | `zideals` | `ℕ → (𝔏 (𝔏 ℕ))` | all ideals of ℤ/n, one per divisor d of n (the ideal (d)), by increasing d |
| `zmaxideals` | `.11101110100.` | `zmaxideals` | `ℕ → (𝔏 (𝔏 ℕ))` | the maximal ideals of ℤ/n (= the prime ideals): (p) for every prime p dividing n, by increasing p |
| `zprimeideals` | `.11101110101.` | `zprimeideals` | `ℕ → (𝔏 (𝔏 ℕ))` | the prime ideals of ℤ/n: the same as the maximal ideals, as ℤ/n is finite |
| `idealsum` | `.11101110110.` | `idealsum` | `ℤ → ℤ → ℕ` | (a) + (b) = (gcd(a, b)), the ideals of ℤ given by generators |
| `idealintersect` | `.11101110111.` | `idealintersect` | `ℤ → ℤ → ℕ` | (a) ∩ (b) = (lcm(a, b)) |
| `idealproduct` | `.11101111000.` | `idealproduct` | `ℤ → ℤ → ℕ` | (a)(b) = (|ab|) |
| `idealcontains` | `.11101111001.` | `idealcontains` | `ℤ → ℤ → 𝔹` | (a) ⊇ (b), that is a | b  (0 divides only 0) |
| `idealradical` | `.11101111010.` | `idealradical` | `ℤ → ℕ` | the radical of the ideal (n) of ℤ: (rad n) |
| `polyidealsum` | `.11101111011.` | `polyidealsum` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | (f) + (g) in ℚ[i][x]: the monic gcd (a zero generator is ignored) |
| `polyidealintersect` | `.11101111100.` | `polyidealintersect` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | (f) ∩ (g): the monic lcm |
| `polyidealproduct` | `.11101111101.` | `polyidealproduct` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | (f)(g): the monic product |
| `polyidealcontains` | `.11101111110.` | `polyidealcontains` | `ℚ[i][x] → ℚ[i][x] → 𝔹` | (f) ⊇ (g), that is f divides g  (the zero polynomial divides only itself) |
| `polyidealradical` | `.11101111111.` | `polyidealradical` | `ℚ[i][x] → ℚ[i][x]` | the radical of the ideal (f): the square-free part, monic |
| `polyidealgen` | `.11110000000.` | `polyidealgen` | `(𝔏 ℚ[i][x]) → ℚ[i][x]` | the monic generator of the ideal of ℚ[i][x] generated by the polynomials of the list ([] for the zero ideal) |
| `polyidealmember` | `.11110000001.` | `polyidealmember` | `ℚ[i][x] → (𝔏 ℚ[i][x]) → 𝔹` | does p lie in the ideal generated by the polynomials of the list? |
| `qrreduce` | `.11110000010.` | `qrreduce` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | qrreduce(f, a) = a mod f, the representative of a in ℚ[i][x]/(f) |
| `qradd` | `.11110000011.` | `qradd` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | qradd(f, a, b) = a + b in ℚ[i][x]/(f) |
| `qrsub` | `.11110000100.` | `qrsub` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | a − b in ℚ[i][x]/(f) |
| `qrneg` | `.11110000101.` | `qrneg` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | −a in ℚ[i][x]/(f) |
| `qrmul` | `.11110000110.` | `qrmul` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | a · b in ℚ[i][x]/(f) |
| `qrinv` | `.11110000111.` | `qrinv` | `ℚ[i][x] → ℚ[i][x] → ℚ[i][x]` | the inverse of a in ℚ[i][x]/(f), [] when a is not a unit (gcd(a, f) is not constant) or a = 0 |
| `qrisunit` | `.11110001000.` | `qrisunit` | `ℚ[i][x] → ℚ[i][x] → 𝔹` | is a a unit of ℚ[i][x]/(f)?  (gcd(a, f) = 1) |
| `qrpow` | `.11110001001.` | `qrpow` | `ℚ[i][x] → ℚ[i][x] → ℤ → ℚ[i][x]` | aⁿ in ℚ[i][x]/(f) by squaring (n < 0: the power of the inverse; [] if a is not a unit) |
| `qrdimension` | `.11110001010.` | `qrdimension` | `ℚ[i][x] → ℕ` | the dimension of ℚ[i][x]/(f) over ℚ[i]: deg f |
| `qrisfield` | `.11110001011.` | `qrisfield` | `(𝔏 ℚ) → 𝔹` | is ℚ[x]/(f) a field?  (f irreducible over ℚ) |
| `polycrt` | `.11110001100.` | `polycrt` | `(𝔏 ℚ[i][x]) → (𝔏 ℚ[i][x]) → ℚ[i][x]` | polycrt(rs, ms): p ≡ rₖ (mod mₖ) for all k, of degree < Σ deg mₖ ([] if the moduli are not pairwise coprime) |
| `mpoly` | `.11110011110.` | `mpoly` | `ℕ → ℚ[i][𝐱] → ℚ[i][𝐱]` | mpoly(o, p): the canonical form of a list of terms in the monomial order o (0 lex, 1 grlex, 2 grevlex): sorted decreasingly, like terms merged, zero terms dropped, exponent lists padded |
| `mpadd` | `.11110100110.` | `mpadd` | `ℕ → ℚ[i][𝐱] → ℚ[i][𝐱] → ℚ[i][𝐱]` | p + q in the monomial order o |
| `mpsub` | `.11110100111.` | `mpsub` | `ℕ → ℚ[i][𝐱] → ℚ[i][𝐱] → ℚ[i][𝐱]` | p − q |
| `mpneg` | `.11110101000.` | `mpneg` | `ℕ → ℚ[i][𝐱] → ℚ[i][𝐱]` | −p |
| `mpscale` | `.11110101001.` | `mpscale` | `ℕ → ℚ[i] → ℚ[i][𝐱] → ℚ[i][𝐱]` | c·p |
| `mpmul` | `.11110101010.` | `mpmul` | `ℕ → ℚ[i][𝐱] → ℚ[i][𝐱] → ℚ[i][𝐱]` | p · q |
| `mppow` | `.11110101011.` | `mppow` | `ℕ → ℚ[i][𝐱] → ℕ → ℚ[i][𝐱]` | pⁿ (p⁰ = 1) |
| `mpeval` | `.11110101100.` | `mpeval` | `ℚ[i][𝐱] → (𝔏 ℚ[i]) → ℚ[i]` | the value of p at a point (a list of values for the variables) |
| `mpdegree` | `.11110101101.` | `mpdegree` | `ℚ[i][𝐱] → ℤ` | the total degree of p (−1 for the zero polynomial) |
| `mpderiv` | `.11110101110.` | `mpderiv` | `ℕ → ℚ[i][𝐱] → ℕ → ℚ[i][𝐱]` | the partial derivative of p with respect to variable j (0-based) |
| `mpsubst` | `.11110101111.` | `mpsubst` | `ℕ → ℚ[i][𝐱] → ℕ → ℚ[i][𝐱] → ℚ[i][𝐱]` | mpsubst(o, p, j, q): p with the variable j replaced by the polynomial q |
| `mplc` | `.11110110000.` | `mplc` | `ℕ → ℚ[i][𝐱] → ℚ[i]` | the leading coefficient of p in the order o (0 for the zero polynomial) |
| `mplm` | `.11110110001.` | `mplm` | `ℕ → ℚ[i][𝐱] → (𝔏 ℕ)` | the exponent list of the leading monomial of p in the order o ([] for the zero polynomial) |
| `mpdivide` | `.11110110111.` | `mpdivide` | `ℕ → ℚ[i][𝐱] → (𝔏 ℚ[i][𝐱]) → (𝔓 (𝔏 ℚ[i][𝐱]) ℚ[i][𝐱])` | mpdivide(o, p, F): (quotients, remainder) with p = Σ qₖ·fₖ + r, no term of r divisible by a leading monomial of F, lm(qₖ fₖ) ≤ lm(p) (the division algorithm: the divisors in the order given; a zero divisor never divides) |
| `mpreduce` | `.11110111000.` | `mpreduce` | `ℕ → ℚ[i][𝐱] → (𝔏 ℚ[i][𝐱]) → ℚ[i][𝐱]` | the remainder of p on division by the list F |
| `spoly` | `.11110111010.` | `spoly` | `ℕ → ℚ[i][𝐱] → ℚ[i][𝐱] → ℚ[i][𝐱]` | the S-polynomial of two polynomials: (m/lt f)·f − (m/lt g)·g, m the lcm of the leading monomials ([] if either is zero) |
| `groebner` | `.11111000001.` | `groebner` | `ℕ → (𝔏 ℚ[i][𝐱]) → (𝔏 ℚ[i][𝐱])` | a Gröbner basis of the ideal generated by the polynomials, in the monomial order o (Buchberger's algorithm, product criterion; monic elements, in the order found; not minimal in general — use reducedgroebner for the canonical basis) |
| `reducedgroebner` | `.11111000110.` | `reducedgroebner` | `ℕ → (𝔏 ℚ[i][𝐱]) → (𝔏 ℚ[i][𝐱])` | the reduced Gröbner basis of the ideal in the monomial order o: monic, minimal, every term of every element reduced by the others, sorted by increasing leading monomial — unique for the ideal and the order ([] for the zero ideal, [1] for the unit ideal) |
| `idealmember` | `.11111000111.` | `idealmember` | `ℕ → ℚ[i][𝐱] → (𝔏 ℚ[i][𝐱]) → 𝔹` | does p lie in the ideal generated by the polynomials (its remainder on a Gröbner basis is zero)? |
| `idealequal` | `.11111001000.` | `idealequal` | `ℕ → (𝔏 ℚ[i][𝐱]) → (𝔏 ℚ[i][𝐱]) → 𝔹` | do two lists of polynomials generate the same ideal? (equal reduced Gröbner bases) |
| `isgroebner` | `.11111001001.` | `isgroebner` | `ℕ → (𝔏 ℚ[i][𝐱]) → 𝔹` | is the list a Gröbner basis of the ideal it generates? (every S-polynomial reduces to zero) |
| `eliminate` | `.11111001010.` | `eliminate` | `ℕ → (𝔏 ℚ[i][𝐱]) → (𝔏 ℚ[i][𝐱])` | eliminate(k, F): a basis of the polynomials of the ideal generated by F that do not involve the first k variables (the elements free of x₀ … xₖ₋₁ of the reduced lexicographic Gröbner basis) |
| `mpstr` | `.11111010000.` | `mpstr` | `ℕ → ℚ[i][𝐱] → 𝕊` | the polynomial in human notation in the order o, leading term first: "x^2*y - 3*z + 1/2", "0" |

### Fields: finite fields GF(p) and GF(pⁿ), number fields ℚ(α), algebraic numbers (`lib/field.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `fpoly` | `.11111100011.` | `fpoly` | `ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | fpoly(p, f): the coefficients reduced modulo p, trailing zeros removed — the canonical form over GF(p) |
| `fpadd` | `.11111100100.` | `fpadd` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | f + g over GF(p) |
| `fpneg` | `.11111100101.` | `fpneg` | `ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | −f over GF(p) |
| `fpsub` | `.11111100110.` | `fpsub` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | f − g over GF(p) |
| `fpscale` | `.11111100111.` | `fpscale` | `ℕ → ℤ → (𝔏 ℤ) → (𝔏 ℕ)` | c·f over GF(p) |
| `fpmul` | `.11111101000.` | `fpmul` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | f · g over GF(p) |
| `fpdegree` | `.11111100000.` | `fpdegree` | `(𝔏 ℕ) → ℤ` | the degree of a polynomial in canonical form (−1 for the zero polynomial) |
| `fpmonic` | `.11111101001.` | `fpmonic` | `ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | the monic multiple of f over GF(p) (the zero polynomial stays) |
| `fpdivmod` | `.11111101010.` | `fpdivmod` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔓 (𝔏 ℕ) (𝔏 ℕ))` | fpdivmod(p, f, g): (quotient, remainder) with f = q·g + r, deg r < deg g; (0, f) for g = 0 |
| `fpquo` | `.11111101011.` | `fpquo` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | the quotient of f by g over GF(p) |
| `fprem` | `.11111101100.` | `fprem` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | the remainder of f modulo g over GF(p) |
| `fpgcd` | `.11111101110.` | `fpgcd` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | the monic gcd over GF(p) (gcd(0, 0) = 0) |
| `fpegcd` | `.11111110111.` | `fpegcd` | `ℕ → (𝔏 ℤ) → (𝔏 ℤ) → (𝔓 (𝔏 ℕ) (𝔓 (𝔏 ℕ) (𝔏 ℕ)))` | fpegcd(p, f, g): (d, (s, t)) with s·f + t·g = d = gcd(f, g) monic |
| `fppowmod` | `.11111111001.` | `fppowmod` | `ℕ → (𝔏 ℤ) → ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | fppowmod(p, f, n, m): fⁿ mod m over GF(p) by squaring (m = 0: fⁿ itself is not computed — the result is []) |
| `fpderiv` | `.11111111010.` | `fpderiv` | `ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | the derivative f′ over GF(p) |
| `fpeval` | `.11111111011.` | `fpeval` | `ℕ → (𝔏 ℤ) → ℤ → ℕ` | f(a) over GF(p) |
| `fproots` | `.11111111100.` | `fproots` | `ℕ → (𝔏 ℤ) → (𝔏 ℕ)` | the roots of f in GF(p), ascending (every element for f = 0) |
| `fpirreducible` | `.11111111111.` | `fpirreducible` | `ℕ → (𝔏 ℤ) → 𝔹` | is f irreducible over GF(p)? (degree ≥ 1; Ben-Or's test) |
| `fpfactor` | `.100000010011.` | `fpfactor` | `ℕ → (𝔏 ℤ) → (𝔓 ℕ (𝔏 (𝔓 (𝔏 ℕ) ℕ)))` | fpfactor(p, f): the complete factorisation over GF(p): (c, [(g, k)]) with f = c·Π gᵏ, c the leading coefficient, every g monic and irreducible, sorted by degree then coefficients; (0, []) for f = 0, (c, []) for a constant |
| `numirreducible` | `.100000010100.` | `numirreducible` | `ℕ → ℕ → ℕ` | the number of monic irreducible polynomials of degree n over GF(p): (1/n)·Σ_(d | n) μ(d) p^(n/d) |
| `irreduciblepoly` | `.100000010111.` | `irreduciblepoly` | `ℕ → ℕ → (𝔏 ℕ)` | irreduciblepoly(p, n): the first monic irreducible polynomial of degree n ≥ 1 over GF(p), the candidates xⁿ + Σ aⱼxʲ taken in the order of Σ aⱼpʲ (x² + x + 1 over GF(2), x³ + x + 1, x⁴ + x + 1, …) |
| `isprimitivepoly` | `.100000011001.` | `isprimitivepoly` | `ℕ → (𝔏 ℤ) → 𝔹` | is f a primitive polynomial over GF(p) — monic, irreducible, and x generates the multiplicative group of GF(p)[x]/(f)? |
| `primitivepoly` | `.100000011010.` | `primitivepoly` | `ℕ → ℕ → (𝔏 ℕ)` | primitivepoly(p, n): the first monic primitive polynomial of degree n ≥ 1 over GF(p), in the order of irreduciblepoly (x² + x + 1 and x³ + x + 1 over GF(2); for n = 1 the first x + a whose root −a is a primitive root modulo p) |
| `gf` | `.10101010000.` | `gf` | `ℕ → ℕ → (𝔓 ℕ (𝔏 ℕ))` | gf(p, n): the field GF(pⁿ) as the pair (p, m), m = primitivepoly(p, n) (so that x is a generator of the multiplicative group); another irreducible modulus m can be used as the pair (p, m) |
| `gfchar` | `.100000011011.` | `gfchar` | `(𝔓 ℕ (𝔏 ℕ)) → ℕ` | the characteristic p of the field |
| `gfmodulus` | `.100000011100.` | `gfmodulus` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℕ)` | the defining polynomial m of the field |
| `gfdegree` | `.100000011101.` | `gfdegree` | `(𝔓 ℕ (𝔏 ℕ)) → ℕ` | the degree n of the field over GF(p) |
| `gfsize` | `.100000011110.` | `gfsize` | `(𝔓 ℕ (𝔏 ℕ)) → ℕ` | the number of elements pⁿ |
| `gfelement` | `.100000011111.` | `gfelement` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℕ)` | the element of the field represented by a polynomial over GF(p) (reduced modulo p and m) |
| `gfadd` | `.100000100000.` | `gfadd` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | a + b in GF(pⁿ) |
| `gfsub` | `.100000100001.` | `gfsub` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | a − b in GF(pⁿ) |
| `gfneg` | `.100000100010.` | `gfneg` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℕ)` | −a in GF(pⁿ) |
| `gfmul` | `.100000100011.` | `gfmul` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | a · b in GF(pⁿ) |
| `gfinv` | `.100000100100.` | `gfinv` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℕ)` | the inverse of a in GF(pⁿ) (extended Euclid with the modulus); [] for a = 0 |
| `gfdiv` | `.100000100101.` | `gfdiv` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℤ) → (𝔏 ℕ)` | a / b in GF(pⁿ) ([] for b = 0) |
| `gfpow` | `.100000100110.` | `gfpow` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → ℤ → (𝔏 ℕ)` | aᵉ in GF(pⁿ) by squaring (e < 0: a power of the inverse; 0⁰ = 1) |
| `gfelements` | `.100000100111.` | `gfelements` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | all pⁿ elements, in the order of Σ aⱼpʲ (0 = [] first) |
| `gforder` | `.100000101001.` | `gforder` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → ℕ` | the multiplicative order of a in GF(pⁿ) (0 for a = 0) |
| `gfisprimitive` | `.100000101010.` | `gfisprimitive` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → 𝔹` | does a generate the multiplicative group of GF(pⁿ)? |
| `gfprimitive` | `.100000101011.` | `gfprimitive` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℕ)` | the first primitive element of GF(pⁿ) in the order of gfelements |
| `gflog` | `.100000101110.` | `gflog` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℤ) → ℤ` | gflog(F, g, a): the least k ≥ 0 with gᵏ = a (the discrete logarithm by repeated multiplication), −1 if there is none |
| `gffrob` | `.100000101111.` | `gffrob` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℕ)` | the Frobenius map a ↦ aᵖ |
| `gftrace` | `.100000110001.` | `gftrace` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → ℕ` | Tr(a) = a + aᵖ + … + aᵖ^(n−1), an element of GF(p) |
| `gfnorm` | `.100000110010.` | `gfnorm` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → ℕ` | N(a) = a·aᵖ·…·aᵖ^(n−1) = a^((pⁿ − 1)/(p − 1)), an element of GF(p) |
| `gfconjugates` | `.100000110011.` | `gfconjugates` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 (𝔏 ℕ))` | the distinct conjugates of a over GF(p): a, aᵖ, … until a repeats |
| `gfminpoly` | `.100000110101.` | `gfminpoly` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 ℕ)` | the minimal polynomial of a over GF(p) — monic, irreducible, of degree dividing n: Π (y − c) over the conjugates c of a |
| `gfsqrt` | `.100000110110.` | `gfsqrt` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → (𝔏 (𝔏 ℕ))` | all square roots of a in GF(pⁿ): [] if a is a non-square, [0] for 0, two roots (±r) otherwise, one in characteristic 2 |
| `gfissquare` | `.100000110111.` | `gfissquare` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 ℤ) → 𝔹` | is a a square in GF(pⁿ)? (Euler's criterion a^((q−1)/2) = 1 for odd characteristic; every element in characteristic 2) |
| `gfroots` | `.100000111000.` | `gfroots` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 (𝔏 ℤ)) → (𝔏 (𝔏 ℕ))` | the roots in GF(pⁿ) of a polynomial whose coefficients are elements of the field (lowest degree first), in the order of gfelements |
| `gfsubfields` | `.100000111001.` | `gfsubfields` | `ℕ → (𝔏 ℕ)` | the degrees of the subfields of GF(pⁿ) over GF(p): the divisors of n (one subfield of each such degree) |
| `nfmatrix` | `.100000111010.` | `nfmatrix` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | nfmatrix(f, a): the matrix of the multiplication by a in ℚ[x]/(f) in the basis 1, x, …, xⁿ⁻¹ (column j: the coordinates of a·xʲ) |
| `nfcharpoly` | `.100000111011.` | `nfcharpoly` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)` | the characteristic polynomial of a over ℚ (degree n; a power of the minimal polynomial) |
| `nfminpoly` | `.100000111100.` | `nfminpoly` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 ℚ)` | the minimal polynomial of a over ℚ (monic; of degree dividing n) |
| `nfdegree` | `.100000111101.` | `nfdegree` | `(𝔏 ℚ) → (𝔏 ℚ) → ℕ` | the degree [ℚ(a) : ℚ] of the element a (the degree of its minimal polynomial) |
| `nftrace` | `.100000111110.` | `nftrace` | `(𝔏 ℚ) → (𝔏 ℚ) → ℚ` | the trace Tr(a) of a ∈ ℚ(α) over ℚ (the trace of the multiplication matrix: the sum of the conjugates of a) |
| `nfnorm` | `.100000111111.` | `nfnorm` | `(𝔏 ℚ) → (𝔏 ℚ) → ℚ` | the norm N(a) of a ∈ ℚ(α) over ℚ (the determinant of the multiplication matrix: the product of the conjugates of a) |
| `nfisintegral` | `.100001000000.` | `nfisintegral` | `(𝔏 ℚ) → (𝔏 ℚ) → 𝔹` | is a an algebraic integer? (its minimal polynomial has integer coefficients) |
| `nfdiscriminant` | `.100001000001.` | `nfdiscriminant` | `(𝔏 ℚ) → ℚ` | the discriminant of the polynomial f — the discriminant of the basis 1, α, …, αⁿ⁻¹ of ℚ(α) (the field discriminant divides it) |
| `algsum` | `.100001000110.` | `algsum` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | algsum(f, g): the irreducible factors of the polynomial with the roots α + β (α a root of f, β of g); f, g non-constant |
| `algneg` | `.100001000111.` | `algneg` | `(𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | algneg(f): the irreducible factors of the polynomial with the roots −α |
| `algdiff` | `.100001001000.` | `algdiff` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | algdiff(f, g): the polynomial with the roots α − β |
| `algprod` | `.100001001001.` | `algprod` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | algprod(f, g): the irreducible factors of the polynomial with the roots α·β; [x] when f or g has the root 0 (f(0) = 0 or g(0) = 0: take f, g without the factor x) |
| `alginv` | `.100001001010.` | `alginv` | `(𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | alginv(f): the irreducible factors of the polynomial with the roots 1/α (the reversed polynomial; the root 0 is dropped) |
| `algquot` | `.100001001011.` | `algquot` | `(𝔏 ℚ) → (𝔏 ℚ) → (𝔏 (𝔏 ℚ))` | algquot(f, g): the polynomial with the roots α/β |
| `algpow` | `.100001001100.` | `algpow` | `(𝔏 ℚ) → ℕ → (𝔏 (𝔏 ℚ))` | algpow(f, k): the polynomial with the roots αᵏ (k ≥ 1) |
| `algroot` | `.100001001101.` | `algroot` | `(𝔏 ℚ) → ℕ → (𝔏 (𝔏 ℚ))` | algroot(f, k): the irreducible factors of f(xᵏ), the polynomials with the roots α^(1/k) (k ≥ 1) |

### Groups: permutations, finite groups as sorted lists, subgroups, cosets, conjugacy, actions (`lib/group.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `pid` | `.10000101000.` | `pid` | `ℕ → (𝔏 ℕ)` | the identity permutation of n points [0, 1, …, n − 1] |
| `isperm` | `.10000101001.` | `isperm` | `(𝔏 ℕ) → 𝔹` | is the list a permutation of {0, …, n − 1} (n its length)? |
| `pcompose` | `.10000101010.` | `pcompose` | `(𝔏 ℕ) → (𝔏 ℕ) → (𝔏 ℕ)` | composition (p ∘ q)(i) = p(q(i)); the shorter permutation is extended by fixed points |
| `pinverse` | `.10000101011.` | `pinverse` | `(𝔏 ℕ) → (𝔏 ℕ)` | the inverse permutation p⁻¹ |
| `papply` | `.10000101100.` | `papply` | `(𝔏 ℕ) → ℕ → ℕ` | the image p(i) of a point (a point beyond the list is fixed) |
| `porder` | `.10000101101.` | `porder` | `(𝔏 ℕ) → ℕ` | the order of a permutation: the lcm of its cycle lengths |
| `ppow` | `.10000101110.` | `ppow` | `(𝔏 ℕ) → ℤ → (𝔏 ℕ)` | the power pᵏ, k ∈ ℤ (k is reduced modulo the order, then square and multiply) |
| `pcycles` | `.10000101111.` | `pcycles` | `(𝔏 ℕ) → (𝔏 (𝔏 ℕ))` | the cycles of length ≥ 2, each starting at its least point, sorted by that point |
| `fromcycles` | `.10000110010.` | `fromcycles` | `ℕ → (𝔏 (𝔏 ℕ)) → (𝔏 ℕ)` | the permutation of max(n, 1 + largest point) points with the given cycles; cycles that overlap are composed, the first one last applied: c₁ ∘ c₂ ∘ … |
| `psign` | `.10000110011.` | `psign` | `(𝔏 ℕ) → ℤ` | the sign of a permutation: 1 (even) or −1 (odd) |
| `iseven` | `.10000110100.` | `iseven` | `(𝔏 ℕ) → 𝔹` | is the permutation even (a product of an even number of transpositions)? |
| `cycletype` | `.10000110101.` | `cycletype` | `(𝔏 ℕ) → (𝔏 ℕ)` | the cycle type: the lengths of all cycles, fixed points included, in decreasing order (a partition of n) |
| `pconj` | `.10000110110.` | `pconj` | `(𝔏 ℕ) → (𝔏 ℕ) → (𝔏 ℕ)` | the conjugate q p q⁻¹ of p by q |
| `generate` | `.10000110111.` | `generate` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the group generated by a list of permutations: all its elements, sorted lexicographically (closure by search) |
| `symgroup` | `.10000111001.` | `symgroup` | `ℕ → (𝔏 (𝔏 ℕ))` | the symmetric group Sₙ: all n! permutations of n points, sorted (S₀ = [[]]) |
| `altgroup` | `.10000111010.` | `altgroup` | `ℕ → (𝔏 (𝔏 ℕ))` | the alternating group Aₙ: the even permutations of n points, sorted |
| `cyclicgroup` | `.10001000001.` | `cyclicgroup` | `ℕ → (𝔏 (𝔏 ℕ))` | the cyclic group Cₙ: the n rotations of n points, sorted (C₀ is the trivial group [[]]) |
| `kleingroup` | `.10001000010.` | `kleingroup` | `(𝔏 (𝔏 ℕ))` | the Klein four-group V₄ = {id, (0 1)(2 3), (0 2)(1 3), (0 3)(1 2)} on 4 points |
| `dihedralgroup` | `.10001000011.` | `dihedralgroup` | `ℕ → (𝔏 (𝔏 ℕ))` | the dihedral group of order 2n: the symmetries of the n-gon on its n vertices (n ≥ 3); D₁ = C₂ on 2 points, D₂ = V₄ on 4 points, D₀ = [[]] |
| `regular` | `.10001001100.` | `regular` | `(𝔏 ℕ) → (ℕ → ℕ → ℕ) → (𝔏 (𝔏 ℕ))`<br>`(𝔏 ℤ) → (ℤ → ℤ → ℤ) → (𝔏 (𝔏 ℕ))`<br>`(𝔏 ℚ) → (ℚ → ℚ → ℚ) → (𝔏 (𝔏 ℕ))`<br>`(𝔏 ℤ[i]) → (ℤ[i] → ℤ[i] → ℤ[i]) → (𝔏 (𝔏 ℕ))`<br>`(𝔏 ℚ[i]) → (ℚ[i] → ℚ[i] → ℚ[i]) → (𝔏 (𝔏 ℕ))` | Cayley's theorem: the group of the left multiplications x ↦ g·x, as permutations of the positions of the (distinct) elements; [] unless the elements form a group under the operation (closed, every x ↦ g·x a bijection, g ↦ (x ↦ g·x) injective, associative; O(n⁴) checks, small n) |
| `regular𝔻` | `.10001001101.` | `regular` | `(𝔏 𝔻) → (𝔻 → 𝔻 → 𝔻) → (𝔏 (𝔏 ℕ))` | Cayley's theorem for elements of the Cayley–Dickson tower (e.g. the quaternion units under ⊠𝔻) |
| `regularᵖ` | `.10001001110.` | `regular` | `(𝔏 (𝔏 ℕ)) → ((𝔏 ℕ) → (𝔏 ℕ) → (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | Cayley's theorem for elements that are lists (e.g. permutations under pcompose; compared entry by entry) |
| `regularᵐ` | `.10001001111.` | `regular` | `(𝔏 (𝔏 (𝔏 ℚ[i]))) → ((𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i])) → (𝔏 (𝔏 ℚ[i]))) → (𝔏 (𝔏 ℕ))` | Cayley's theorem for matrices (e.g. under mmul) |
| `quaterniongroup` | `.10001010000.` | `quaterniongroup` | `(𝔏 (𝔏 ℕ))` | the quaternion group Q₈ = {±1, ±i, ±j, ±k} of the Cayley–Dickson tower, by Cayley's theorem on 8 points (1, −1, i, −i, j, −j, k, −k) |
| `grouporder` | `.10010001111.` | `grouporder` | `(𝔏 (𝔏 ℕ)) → ℕ` | the order |G|: the number of distinct elements of the list |
| `isgroup` | `.10010010000.` | `isgroup` | `(𝔏 (𝔏 ℕ)) → 𝔹` | is the list a group: non-empty, permutations (padded to one degree), closed under composition? |
| `issubgroup` | `.10010010001.` | `issubgroup` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → 𝔹` | is H a subgroup of G (G a group, H ⊆ G non-empty and closed)? |
| `isnormal` | `.10010010010.` | `isnormal` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → 𝔹` | is H a normal subgroup of the group G (g H g⁻¹ = H for every g ∈ G)? |
| `leftcosets` | `.10010010011.` | `leftcosets` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 (𝔏 ℕ)))` | the left cosets gH of the subgroup H in G, each sorted, in order of their least element; [] unless H is a subgroup of the group G |
| `rightcosets` | `.10010010100.` | `rightcosets` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 (𝔏 ℕ)))` | the right cosets Hg of the subgroup H in G, each sorted, in order of their least element; [] unless H is a subgroup of the group G |
| `index` | `.10010010101.` | `index` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → ℕ` | the index [G : H] = |G| / |H| of the subgroup H; 0 unless H is a subgroup of the group G |
| `conjclasses` | `.10010010110.` | `conjclasses` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 (𝔏 ℕ)))` | the conjugacy classes {x g x⁻¹} of the group G, each sorted, in order of their least element; [] unless G is a group |
| `center` | `.10010010111.` | `center` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the centre Z(G): the elements that commute with every element (sorted) |
| `centralizer` | `.10010011000.` | `centralizer` | `(𝔏 ℕ) → (𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the centralizer C_G(x): the elements of G that commute with x (sorted; x and G padded to one degree) |
| `normalizer` | `.10010011001.` | `normalizer` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the normalizer N_G(H): the elements g of G with g H g⁻¹ = H (H any set of permutations; sorted) |
| `commutatorsubgroup` | `.10010011010.` | `commutatorsubgroup` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the derived subgroup G′ = [G, G], generated by the commutators a b a⁻¹ b⁻¹ (sorted); [] unless G is a group |
| `issolvable` | `.10010011011.` | `issolvable` | `(𝔏 (𝔏 ℕ)) → 𝔹` | is the group solvable (its derived series G ⊇ G′ ⊇ G″ ⊇ … reaches the trivial group)? ⊥ unless G is a group |
| `isabelian` | `.10010011100.` | `isabelian` | `(𝔏 (𝔏 ℕ)) → 𝔹` | is G an abelian group (a b = b a for all elements)? ⊥ unless G is a group |
| `iscyclic` | `.10010011101.` | `iscyclic` | `(𝔏 (𝔏 ℕ)) → 𝔹` | is G a cyclic group (it has an element of order |G|)? ⊥ unless G is a group |
| `elementorders` | `.10010011110.` | `elementorders` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔓 ℕ ℕ))` | the element-order statistics: the pairs (order, number of elements of that order), by increasing order; [] unless G is a group |
| `exponent` | `.10010011111.` | `exponent` | `(𝔏 (𝔏 ℕ)) → ℕ` | the exponent of G: the lcm of the orders of its elements; 0 unless G is a group |
| `orbit` | `.10010100000.` | `orbit` | `(𝔏 (𝔏 ℕ)) → ℕ → (𝔏 ℕ)` | the orbit of the point i under the group generated by the list (a group or generators), sorted; [i] for a point beyond the degree |
| `orbits` | `.10010100001.` | `orbits` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the orbits on 0 … n − 1 (n the degree) of the group generated by the list, each sorted, in order of their least point |
| `stabilizer` | `.10010100010.` | `stabilizer` | `(𝔏 (𝔏 ℕ)) → ℕ → (𝔏 (𝔏 ℕ))` | the stabilizer of the point i: the elements g with g(i) = i (sorted; all of G for a point beyond the degree) |
| `burnside` | `.10010100011.` | `burnside` | `(𝔏 (𝔏 ℕ)) → ℕ` | the number of orbits of the group on its points 0 … n − 1, by Burnside's lemma (the mean number of fixed points); 0 unless G is a group |
| `cayleytable` | `.10010100100.` | `cayleytable` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the Cayley table: entry (i, j) is the position k of gᵢ∘gⱼ = g_k in the sorted element list; [] unless G is a group |
| `directproduct` | `.10010100101.` | `directproduct` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the direct product G × H acting on disjoint points: (g, h) acts as g on 0 … n − 1 and as h on n, n + 1, … (sorted) |
| `sylow` | `.10010100110.` | `sylow` | `(𝔏 (𝔏 ℕ)) → ℕ → (𝔏 (𝔏 ℕ))` | a Sylow p-subgroup of G (order the largest power of p dividing |G|; sorted), grown inside normalizers; the trivial subgroup when p is not a prime or does not divide |G|; [] unless G is a group |
| `subgroups` | `.10010100111.` | `subgroups` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 (𝔏 ℕ)))` | all subgroups of G, by increasing order then lexicographically (cyclic subgroups joined until closure; small groups: S₄ ~3 s, order 48 ~1 min); [] unless G is a group |
| `sameinvariants` | `.10010101001.` | `sameinvariants` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → 𝔹` | do the groups agree in order, element-order statistics, centre size, and being abelian, cyclic, solvable? A necessary condition for isomorphism, NOT a proof of it (⊥ unless both are groups) |
| `isomorphic` | `.10010101010.` | `isomorphic` | `(𝔏 (𝔏 ℕ)) → (𝔏 (𝔏 ℕ)) → 𝔹` | are the groups isomorphic? A real test: images of a generating list of G (same orders) are searched for a map that respects every edge of the Cayley graph and is injective; exponential in the number of generators (small groups, order ≲ 32) |
| `abelianinvariants` | `.10010101011.` | `abelianinvariants` | `(𝔏 (𝔏 ℕ)) → (𝔏 ℕ)` | the invariant factors d₁ | d₂ | … (all > 1) of the abelianization G/G′ ≅ ℤ/d₁ × ℤ/d₂ × … (of G itself when G is abelian), by a Smith normal form of the Cayley-graph relations; [] for a perfect group or a list that is not a group |
| `colorings` | `.10010101100.` | `colorings` | `(𝔏 (𝔏 ℕ)) → ℕ → ℕ` | the number of colourings of the n points with k colours up to the group (orbits on the kⁿ colourings, by Burnside: the mean of k^(number of cycles)); 0 unless G is a group |
| `necklaces` | `.10010101101.` | `necklaces` | `ℕ → ℕ → ℕ` | the number of necklaces of n beads in k colours (colourings up to rotation) |
| `bracelets` | `.10010101110.` | `bracelets` | `ℕ → ℕ → ℕ` | the number of bracelets of n beads in k colours (colourings up to rotation and reflection) |
| `semidirect` | `.10010101111.` | `semidirect` | `ℕ → ℕ → ℕ → (𝔏 (𝔏 ℕ))` | the semidirect product ℤ/m ⋊ ℤ/n, the generator of ℤ/n acting by x ↦ a x, as its regular permutation group on m n points ((b, j) is the point b + m j, (b, j)(b′, j′) = (b + aʲ b′, j + j′)); [] unless m, n ≥ 1, gcd(a, m) = 1 and aⁿ ≡ 1 (mod m) |

### Galois theory: Galois groups of polynomials over ℚ, cyclotomy, Frobenius (`lib/galois.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `unitgroup` | `.100001001110.` | `unitgroup` | `ℕ → (𝔏 (𝔏 ℕ))` | the group (ℤ/n)× of the units of ℤ/n under multiplication, as a permutation group (Cayley's regular representation of the units of zunits(n)); it is also the Galois group of ℚ(ζₙ) over ℚ |
| `galoiscyclotomic` | `.100001001111.` | `galoiscyclotomic` | `ℕ → (𝔏 (𝔏 ℕ))` | the Galois group Gal(ℚ(ζₙ)/ℚ) ≅ (ℤ/n)×, of order φ(n): σₐ(ζ) = ζᵃ for a coprime to n, acting regularly on the primitive n-th roots of unity (the points of the group are the units of ℤ/n in increasing order) |
| `cyclotomicfactors` | `.100001010000.` | `cyclotomicfactors` | `ℕ → ℕ → (𝔏 (𝔏 ℕ))` | cyclotomicfactors(p, n): the irreducible factors of the cyclotomic polynomial Φₙ over GF(p) (p ∤ n): φ(n)/ord_n(p) factors, all of degree ord_n(p) — the order of the Frobenius of p in Gal(ℚ(ζₙ)/ℚ); sorted |
| `gfgalois` | `.100001010001.` | `gfgalois` | `(𝔓 ℕ (𝔏 ℕ)) → (𝔏 (𝔏 ℕ))` | the Galois group Gal(GF(pⁿ)/GF(p)) as a permutation group of the elements of gfelements(F) (the points are positions in that list): the cyclic group of order n generated by the Frobenius a ↦ aᵖ |
| `isgoodprime` | `.100001010010.` | `isgoodprime` | `(𝔏 ℤ) → ℕ → 𝔹` | isgoodprime(f, p): p is a prime that divides neither the leading coefficient nor the discriminant of f (f ∈ ℤ[x] of degree ≥ 1): the factorisation mod p is then square-free and describes the Frobenius element |
| `frobeniuspattern` | `.100001010011.` | `frobeniuspattern` | `(𝔏 ℤ) → ℕ → (𝔏 ℕ)` | frobeniuspattern(f, p): the degrees of the irreducible factors of f modulo p, with multiplicity, ascending — the cycle type of the Frobenius at p when p is a good prime |
| `frobeniuscensus` | `.100001010110.` | `frobeniuscensus` | `(𝔏 ℤ) → ℕ → (𝔏 (𝔏 ℕ))` | frobeniuscensus(f, B): the distinct cycle types met by the Frobenius elements at the good primes p ≤ B, sorted. Every pattern listed is the cycle type of an element of the Galois group; by Chebotarev's density theorem every type of the group occurs for a positive proportion of primes (a lower bound for the group, and an upper bound on the elements: the pattern of a good prime is never outside the group) |
| `eisensteinprime` | `.100001010111.` | `eisensteinprime` | `(𝔏 ℤ) → ℕ` | a prime p for which Eisenstein's criterion applies to the integer polynomial f (p divides every coefficient but the leading one, p ∤ the leading coefficient, p² ∤ the constant term), so that f is irreducible over ℚ; 0 if there is none (the polynomial may still be irreducible) |
| `iseisenstein` | `.100001011000.` | `iseisenstein` | `(𝔏 ℤ) → 𝔹` | does Eisenstein's criterion apply for some prime? |
| `isdiscsquare` | `.100001011001.` | `isdiscsquare` | `(𝔏 ℚ) → 𝔹` | is the discriminant of f a square of a rational number? (then the Galois group of f is contained in the alternating group Aₙ; false when the discriminant is 0 or negative) |
| `resolventcubic` | `.100001011011.` | `resolventcubic` | `(𝔏 ℚ) → (𝔏 ℚ)` | the resolvent cubic of a quartic: for the monic x⁴ + a x³ + b x² + c x + d it is y³ − b y² + (ac − 4d) y − (a²d − 4bd + c²), whose roots are α₁α₂ + α₃α₄, α₁α₃ + α₂α₄, α₁α₄ + α₂α₃ and which has the same discriminant as the quartic; [] unless the degree is 4 |
| `galoisgroup` | `.100001101001.` | `galoisgroup` | `(𝔏 ℚ) → (𝔏 (𝔏 ℕ))` | the Galois group of the splitting field of f over ℚ (f of degree ≤ 4; repeated roots are ignored) as a permutation group of its roots, up to relabelling of the roots: S₄, A₄, V₄, D₄, C₄ for an irreducible quartic (discriminant and resolvent cubic; D₄ against C₄ by Kappe–Warren), S₃ or C₃ for an irreducible cubic, C₂ for a quadratic, and for a reducible polynomial the group of the product of its factors (two quadratics with the same quadratic field give C₂, otherwise V₄ = C₂ × C₂); [] for degree ≥ 5 and for the zero polynomial |
| `galoisname` | `.100001101100.` | `galoisname` | `(𝔏 ℚ) → 𝕊` | the isomorphism type of the Galois group of f (degree ≤ 4): "1", "C2", "C3", "S3", "V4" (the Klein four-group), "C4", "D4" (the dihedral group of order 8), "A4", "S4"; "" outside the cases handled |
| `galoisorder` | `.100001101101.` | `galoisorder` | `(𝔏 ℚ) → ℕ` | the order of the Galois group of f (degree ≤ 4) — the degree [K : ℚ] of the splitting field K of f over ℚ; 0 outside the cases handled |
| `intermediatefielddegrees` | `.100001101110.` | `intermediatefielddegrees` | `(𝔏 ℚ) → (𝔏 ℕ)` | the degrees [F : ℚ] of the intermediate fields ℚ ⊆ F ⊆ K of the splitting field K of f (degree ≤ 4), one for each subgroup H of the Galois group G (the Galois correspondence: [F : ℚ] = |G|/|H|), ascending |

### The predicates on ℝ[i] — relations decided by logic (true, false, undetermined) (`lib/prove.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `truth_rd` | `.10010110001.` |  | `Ω → 𝔒` | the truth of a statement in simplest form: ⋗ true, ⋖ false, ≖ neither (helper) |
| `prop` | `.10010110010.` | `prop` | `𝔹 → Ω` | a truth value as a statement: ⊤ is the statement true, ⊥ the statement false (canonical coercion 𝔹 → Ω) |
| `decide` | `.10010110011.` | `decide` | `Ω → 𝔹` | a statement as a truth value: ⊤ if it is true, ⊥ if it is false, ⍰ (undetermined) otherwise (canonical coercion Ω → 𝔹) |
| `∧Ω` | `.10010110100.` | `*`, `and`, `min` | `Ω → Ω → Ω` | and of two statements (simplified together) |
| `∨Ω` | `.10010110101.` | `+`, `or`, `max` | `Ω → Ω → Ω` | or of two statements (simplified together) |
| `¬Ω` | `.10010110110.` | `not (prefix)` | `Ω → Ω` | negation of a statement (simplified) |
| `⇒Ω` | `.10010110111.` | `implies` | `Ω → Ω → Ω` | implication between statements (simplified together) |
| `⇔Ω` | `.10010111000.` | `iff` | `Ω → Ω → Ω` | equivalence of statements (simplified together) |
| `code_rd` | `.10010111001.` |  | `Ω → 𝔔` | the code of a statement (a statement is its code; helper of the compiler) |

### The simplifier — every statement reduced to its simplest form (`lib/solve.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `simplify′` | `.111110001.` |  | `(𝔏 (𝔓 𝔇 𝔔)) → 𝔔 → Ω` | the simplest form of the statement ξ (a code), given the table ε of the definitions it uses |

### Types as decoding keys (`lib/codec.imo`)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `asz2` | `.100010001110.` |  | `ℤ[i] → ℤ²` | the key ℤ²: a Gaussian integer a + b·i read as the pair (a, b) — the identity on the string (an automatic coercion, cost 1) |
| `asstr2` | `.100010001111.` |  | `ℤ[i] → 𝕊²` | the key String²: a Gaussian integer read as a pair of strings — the identity on the string (an automatic coercion, cost 1) |
| `pairz` | `.100001111010.` | `pairz` | `ℤ → ℤ → ℤ²` | pairz(a, b): the ordered pair (a, b) of integers, stored as the Gaussian integer a + b·i |
| `fstz` | `.100001111011.` | `fstz` | `ℤ² → ℤ` | the first component a of the pair (a, b) = a + b·i: the real part |
| `sndz` | `.100001111100.` | `sndz` | `ℤ² → ℤ` | the second component b: the imaginary part |
| `addz2` | `.100001111101.` | `+` | `ℤ² → ℤ² → ℤ²` | (a, b) + (c, d) = (a + c, b + d): the sum of the Gaussian integers |
| `subz2` | `.100001111110.` | `-` | `ℤ² → ℤ² → ℤ²` | (a, b) − (c, d) |
| `negz2` | `.100001111111.` | `- (prefix)` | `ℤ² → ℤ²` | −(a, b) |
| `scalez2` | `.100010000000.` | `*` | `ℤ → ℤ² → ℤ²` | k·(a, b) = (k a, k b): an integer times the Gaussian integer |
| `eqz2` | `.100010000001.` | `==` | `ℤ² → ℤ² → 𝔹` | (a, b) = (c, d) |
| `gaussian` | `.100010000010.` | `gaussian` | `ℤ² → ℤ[i]`<br>`𝕊² → ℤ[i]` | the same binary string read as the Gaussian integer (the identity: the key changes, the string does not) |
| `fracz` | `.100010000011.` | `fracz` | `ℤ² → ℚ` | the pair (a, b) decoded as the fraction a/b (0 for b = 0, as x ÷ 0 = 0) |
| `qpair` | `.100010000100.` | `qpair` | `ℚ → ℤ²` | the rational p/q in lowest terms with q > 0 encoded as the pair (p, q); fracz (qpair x) = x |
| `strnat` | `.100010000101.` | `strnat` | `𝕊 → ℕ` | the natural number that codes a string (bijective base 1114112; "" is 0) |
| `natstr` | `.100010000110.` | `natstr` | `ℕ → 𝕊` | the string coded by a natural number (the inverse of strnat); the absolute value of an integer is taken first by strfst / strsnd |
| `strpair` | `.100010000111.` | `strpair` | `𝕊 → 𝕊 → 𝕊²` | strpair(s, t): the pair of strings (s, t) stored as one binary string, the Gaussian integer strnat(s) + strnat(t)·i |
| `strfst` | `.100010001000.` | `strfst` | `𝕊² → 𝕊` | the first string of a pair: the string coded by |real part| |
| `strsnd` | `.100010001001.` | `strsnd` | `𝕊² → 𝕊` | the second string of a pair: the string coded by |imaginary part| |
| `showz` | `.100010001010.` | `decode` | `ℤ[i] → 𝕊` | the default key: a Gaussian integer as text, 1 - 6*i (an unascribed binary string is a Gaussian integer) |
| `showz2` | `.100010001011.` | `decode` | `ℤ² → 𝕊` | the pair as text:  (1, -6) |
| `showstr2` | `.100010001100.` | `decode` | `𝕊² → 𝕊` | a pair of strings as text, each in double quotes (no escapes):  ("Hello, world!", "Welcome to i - 1!") |
| `parsebits` | `.100010001101.` | `parsebits` | `𝕊 → ℤ[i]` | the Gaussian integer written by a string of 1 and 0 (most significant digit first; `bits` is the inverse): "110101" is 1 − 6i |

### Internal helpers (trusted, not meant to be called directly)

| spec | bin | human | class | meaning |
|:--:|:--|:--|:--|:--|
| `⊼` | `.100001.` |  | `𝔹 → 𝔹 → 𝔹 → 𝔹` | majority of three (carry bit) |
| `⌕` | `.110100.` |  | `𝔇 → (𝔏 (𝔓 ℚ[i] ℚ[i])) → 𝔇` | table lookup used by the carry rule |
| `κ` | `.110101.` |  | `(𝔏 (𝔓 ℚ[i] ℚ[i]))` | carry table: tail ↦ tail + 110 |
| `⊞ᶜ` | `.110110.` |  | `𝔇 → 𝔇 → 𝔇 → 𝔇` | serial adder with a numeral as carry |
| `⩾ᶻ′` | `.1000000.` |  | `𝔇 → 𝔇 → 𝔹` | sign search (helper) |
| `⩾ᶻ` | `.1000001.` |  | `𝔇 → 𝔇 → 𝔹` | order on real Gaussian integers |
| `⫴` | `.1010011.` |  | `(α → β → γ) → (𝔖 α) → (𝔖 β) → (𝔖 γ)` | zip-with on streams |
| `⁂` | `.1010111.` |  | `α → (𝔖 α)` | constant stream |
| `Σ′` | `.1011111.` |  | `(ℚ[i] → ℚ[i]) → 𝔇 → 𝔇 → 𝔇 → ℚ[i] → (𝔖 ℚ[i])` | series driver (helper) |
| `↥` | `.1100101.` |  | `(𝔄 α) → (𝔗 α) → (𝔗 α) → (𝔗 α)` | lift a ↦ (a, 0) (the only way depths are reconciled) |
| `⟨⟩′` | `.1110101.` |  | `(𝔄 α) → (ℚ[i] → α) → (ℚ[i] → α) → ℚ[i] → α → (𝔖 α)` | inner-product partial sums (helper) |
| `⍳′` | `.1111100.` |  | `ℕ → ℕ → (𝔏 ℕ)` |  |
| `⋚ʳ` | `.10011011.` |  | `𝔇 → 𝔒` | sign of Re z, read off the digits (blocks of four) |
| `⋚ⁱ` | `.10011101.` |  | `𝔇 → 𝔒` | sign of Im z |
| `ℜᶻ` | `.10010001.` |  | `𝔇 → 𝔇` | Re z as a real Gaussian integer (linear time) |
| `ℑᶻ` | `.10010011.` |  | `𝔇 → 𝔇` | Im z as a real Gaussian integer |
| `⊟ᶻ` | `.10001011.` |  | `𝔇 → 𝔇 → 𝔇` | ℤ[i] subtraction (serial transducer, 47 carry numerals) |
| `⊖ᶻ` | `.10001100.` |  | `𝔇 → 𝔇` | ℤ[i] negation |
| `∅ᶻ` | `.10001111.` |  | `𝔇 → 𝔹` | is the Gaussian integer 0? |
| `⌕′` | `.10000010.` |  | `𝔇 → 𝔇` | adder carry table as a decision tree (generated) |
| `⌕⁺` | `.10000011.` |  | `𝔇 → 𝔇` | subtractor carry table t + 110 (generated) |
| `⌕⁻` | `.10000100.` |  | `𝔇 → 𝔇` | subtractor carry table t − 110 (generated) |
| `÷ᶻ` | `.10100111.` |  | `𝔇 → 𝔇 → 𝔇` | exact division in ℤ[i] (Hensel, from the low digits) |
| `gcdᶻ` | `.10101001.` |  | `𝔇 → 𝔇 → 𝔇` | binary gcd of real integers |
| `⫽ᶻ` | `.10101100.` |  | `𝔇 → 𝔇 → (𝔓 𝔇 𝔇)` | division with remainder of naturals (long division in base 4) |
| `⊡` | `.10100000.` |  | `𝔇 → 𝔇` | canonical digit string (trailing zeros removed, one pass) |
| `↓ᶻ` | `.10101110.` |  | `ℚ[i] → 𝔇` | the Gaussian integer of an integral value |
| `decⁿ` | `.101001110.` |  | `𝔇 → 𝕊 → 𝕊` | decimal digits of a natural (generated tables) |

**Further helpers** (named in doc 1, described in the source files): `+ˡ` `+ᵈ` `=ᶻ` `abel_gr` `abinv_gr` `absᶻ` `acosF_cx` `acoshF_cx` `acoshX_cx` `acoshq_cx` `ad_fd` `ad_pl` `add_pl` `add_rg` `add_sv` `addb_sv` `addf_sv` `adds_sv` `adm_pl` `adr_pl` `adv_nt` `adz_pl` `aff_sv` `agl_cx` `agmq_cx` `allreal_sv` `andl_sv` `ap_gr` `apps` `apr_sv` `ap′_gr` `ar_rg` `args²` `args¹` `arl_rg` `asinhC_cx` `asinhF_cx` `asinhR_cx` `asinhX_cx` `asinhq_cx` `asl_cx` `asm_sv` `assoc_gr` `at2S_cx` `atF_sv` `atS_cx` `at_cx` `atan2R_cx` `atan2q_cx` `atanR_cx` `atanq_cx` `atom_sv` `atomᴾ` `atp_cx` `atpos_cx` `ats_sv` `atser_cx` `b32_nt` `back′` `bat_nt` `bby_nt` `bern_cx` `berns_cx` `bfsn_gr` `bfsn′_gr` `bgen′_gr` `biS_cx` `bi_sv` `bits_nt` `bjS_cx` `bk_nt` `blc_sv` `blen_cx` `blf_sv` `blk_sv` `blz_cx` `bo_fd` `bpv_gr` `bq_sv` `bre_sv` `brw_nt` `bsc_nt` `bsgs_nt` `btq_cx` `buch_rg` `burn_gr` `bz_cx` `cands_gr` `cat_sv` `cauchyᵖ` `cb_pl` `ccl_gr` `ccl′_gr` `cd_pl` `cells_sv` `cent_gr` `cf_fd` `cf_nt` `cfq_nt` `cfs_nt` `chiS_cx` `choose′` `chz_pl` `ciS_cx` `cj_fd` `cj_sv` `cl_fd` `cl_gl` `clen_gr` `clen′_gr` `clo_sv` `clos_gr` `cm_fd` `cmb_pl` `cmd_pl` `cmp_nt` `cmp_pl` `cmp_sv` `cmpl_sv` `cmpo_gr` `cmpp_gr` `cmps_gr` `cmpu_gr` `cn_pl` `cn_sv` `cnd_fd` `cnt_sv` `cof_sv` `colr_gr` `comm_gr` `comp_gr` `conjR_cx` `conj_gr` `constᴾ` `cop_rg` `cosR_cx` `cosS_cx` `coshS_cx` `coshᴾ` `cos′_gr` `cp_la` `cp_pl` `cplx_sv` `cpr_pl` `cpxR_cx` `crf_pl` `crow_gr` `crs_nt` `cst_sv` `ctg_pl` `ctl_pl` `ctx_nt` `ctz_pl` `cvp_nt` `cyc_gr` `cyc_nt` `cycap_gr` `cycl_gr` `cycs_gr` `cycz_gr` `cyc′_gr` `cysub_gr` `cz_sv` `czr_sv` `czz_sv` `d^` `daS_cx` `dd_fd` `dd_la` `ddf_pl` `ddh_pl` `ddp_nt` `ddp_pl` `dd′_gr` `decᵈ` `dec⁸` `degs_gr` `dep_sv` `der_pl` `dfb_sv` `dg_pl` `dgq_cx` `dgs_pl` `diag2_cx` `difR_cx` `diff_gr` `dih_gr` `disc` `divR_cx` `divu_gr` `dk_pl` `dks_pl` `dl_fd` `dlz_nt` `dlz_pl` `dlz′_nt` `dmm_pl` `dn_cx` `dnr_cx` `domU_sv` `dpp_nt` `dprod_gr` `dq_pl` `dr_fd` `dr_nt` `dr_pl` `dred_nt` `dropj4_cx` `dropj_cx` `dropl_cx` `dropl_pl` `dropn4_cx` `dropn_cx` `dropu_gr` `dropz′` `drop′` `drw_nt` `drz_pl` `dsm_nt` `dstu_gr` `dv_fd` `dv_nt` `dv_pl` `dvd_rg` `dvdu_gr` `dvg_nt` `dvm_pl` `dvn_pl` `dvo_nt` `dvq_pl` `dvr_pl` `dvs_pl` `dvs′_pl` `dz⁰` `d²ˡ` `d×` `d⁺` `ech_sv` `ed_fd` `edf_pl` `edg_gr` `eds_pl` `edv_pl` `edz_pl` `eeq_cx` `eg_fd` `eg_nt` `egg_nt` `egi_nt` `egm_pl` `egz_nt` `egz_pl` `eiS_cx` `einR_cx` `einS_cx` `ekl_cx` `ekq_cx` `el2u_cx` `elim′` `elm_sv` `emq_cx` `encᴾ` `encᵃ` `encᵐ` `eord_gr` `epos_sv` `eqe_rg` `eql_gr` `eqo_gr` `eqs_gr` `eqterm_rg` `equ_gr` `equp_gr` `eqz_nt` `erfS_cx` `es_pl` `eul_cx` `eur_cx` `evQ′` `ev_pl` `evl_gr` `evs_sv` `evz_sv` `ev²` `ev¹` `evᵖ` `excess_cx` `expR_cx` `expS_cx` `exp_sv` `expd_sv` `expq_cx` `expqz_cx` `expᴾ` `fA_sv` `fAnd_sv` `fC_sv` `fO_sv` `fOr_sv` `fa_fd` `fa_sv` `fact′` `fb_sv` `fbp_nt` `fc_fd` `fc_sv` `fcl_sv` `fcq_nt` `fcr_nt` `fct_nt` `fdb_nt` `fi_la` `fi_nt` `fi_sv` `fin_sv` `first_sv` `fixΦ_sv` `fix′_gr` `fl_cx` `fl_sv` `flip_sv` `flo_sv` `fls_nt` `fnde_gr` `fnz_gr` `fo′` `fr_pl` `frc_nt` `fs_pl` `fsf_pl` `fsm_pl` `fst_rg` `fuel` `fwd′` `fxc_pl` `fxm_pl` `fxq_pl` `fy_nt` `gamS_cx` `gb_rg` `gc_fd` `gcd_pl` `gcdᶻ′` `gcmp_nt` `gcp_pl` `gdv_pl` `gen_gr` `gent_nt` `gen′_gr` `geu_gr` `gf_sv` `gfa_nt` `gfdeg_fd` `ggcdᶻ` `ggen_gr` `ggen′_gr` `gi_pl` `gl_sv` `gminv_nt` `gmq_cx` `gp3_nt` `gpe_nt` `gpi_nt` `gpm_nt` `gpq_pl` `gpr_pl` `gps_nt` `gpw_pl` `grp_gr` `grp_sv` `grp′_gr` `gz_pl` `gzi_pl` `hasO_sv` `hasop_sv` `hb_cx` `hfx_pl` `hl_pl` `hla_pl` `hlf_nt` `hlp_cx` `hm_gr` `hp_fd` `hpr_nt` `hs_pl` `hsum_cx` `hsum_nt` `hv_pl` `idx_la` `idx_sv` `idx′_gr` `idz_sv` `ieg_pl` `ig_pl` `igp_nt` `imR_cx` `in_fd` `ing2_gr` `ing_gr` `inl_gr` `inp_gr` `ins_gr` `ins_rg` `ins_sv` `insk_sv` `insl_rg` `insp_sv` `insr_sv` `insᴾ` `insᵐ` `ins′` `invR_cx` `inv_gr` `inv_pl` `invs_gr` `iotau_gr` `iotau′_gr` `ip_pl` `ipr_pl` `ipw_nt` `irc_sv` `irt_nt` `irt′_nt` `irun_sv` `isC_sv` `isU_sv` `isaff_sv` `isc_sv` `isd_pl` `isg_gl` `isg_nt` `isint_cx` `isneg_cx` `isneg_sv` `iso_gr` `iso_pl` `isol_pl` `ispr_nt` `isreal_cx` `issq_nt` `it_pl` `ivl_cx` `jac_nt` `jn_cx` `jn_nt` `kdec_nt` `kenc_nt` `kle_sv` `kmerge_gr` `kmul_nt` `knrm_nt` `ko_sv` `kone_nt` `kpw_nt` `kpw′_nt` `ksort_gr` `lAdd_sv` `lCnj_sv` `lDiv_sv` `lEmb_sv` `lEq_sv` `lGe_sv` `lGt_sv` `lIm_sv` `lLe_sv` `lLt_sv` `lMul_sv` `lNe_sv` `lNeg_sv` `lNoUnf_sv` `lPow_sv` `lRe_sv` `lSplit_sv` `lSqrt_sv` `lSub_sv` `lastrun_sv` `lb_cx` `lbk_cx` `lbq_cx` `lcl_nt` `lcmu_gr` `lcmu′_gr` `lcn_nt` `lco_sv` `lcode_sv` `ldv_sv` `le_cx` `lens_gr` `lenu_gr` `leq_cx` `lex_rg` `lex_sv` `lfa_sv` `lfb_sv` `lg2_cx` `lg2d_cx` `lg2u_cx` `lg_fd` `lgl_cx` `lgq_cx` `lgs_cx` `lgw_cx` `lgz_cx` `lhs_sv` `liS_cx` `lin_pl` `lku_sv` `ll_sv` `lmul_cx` `ln2_cx` `ln2a_cx` `logR_cx` `logS_cx` `logcR_cx` `logpos_cx` `logq_cx` `look` `lpS_cx` `lpe_nt` `lsp_nt` `lst_nt` `lt_cx` `lt_nt` `ltc_pl` `lub_la` `lud_la` `luf_la` `lug_la` `lun_la` `lup_la` `lv_pl` `lwS_cx` `lwdom_cx` `lwl_cx` `lwn_cx` `lwq_cx` `m35_nt` `m3_nt` `mag_cx` `magp_cx` `maxu_gr` `mb_pl` `mcmp_rg` `mctx_nt` `md_fd` `mdp_pl` `mdv_rg` `mem_gr` `mem_sv` `meq_la` `mexp_la` `mfac_pl` `mflat_la` `mid′` `minim_rg` `minv_nt` `mir_sv` `mk_cx` `mkq_cx` `ml_fd` `mlm_pl` `mlr_pl` `mlt_nt` `mlz_pl` `mm_pl` `mn_nt` `mnc_fd` `mnm_pl` `mo_fd` `mod_nt` `mon_pl` `mon_rg` `mono_rg` `mono_sv` `mp_fd` `mp_la` `mpadd_sv` `mpc_sv` `mpconst_sv` `mpl_pl` `mpmap_sv` `mpmul_sv` `mpneg_sv` `mpow_la` `mppow_sv` `mpscale_sv` `mpv_sv` `mpw_nt` `mr_nt` `mrb_nt` `mrg_nt` `mrg_rg` `mrg_sv` `mrgc_nt` `mrgl_nt` `mrl_nt` `msim_sv` `msort_nt` `mtm_rg` `mu_fd` `mu_sv` `mulR_cx` `mul_pl` `mul_rg` `mult_la` `mulu_gr` `mv_sv` `mz_cx` `n2_rg` `n_gr` `nats_cx` `nc_pl` `ndv_pl` `negR_cx` `neg_cx` `neg_pl` `negΦ_sv` `nf_rg` `nfc_pl` `ng_fd` `ng_pl` `ngp_nt` `nl_rg` `nm_gl` `nn_rg` `nocst_sv` `normR_cx` `normR′` `norm_gr` `norm_sv` `npi_cx` `nr_sv` `nrm_nt` `nrm_rg` `nsr_pl` `nt_sv` `nthu_gr` `nums_gr` `nw_cx` `nwt_cx` `nxo_nt` `nxp_nt` `nz_nt` `nz_pl` `nzr_gr` `nzr_la` `n′_gr` `odd_gr` `odd_nt` `odl_nt` `okb_sv` `ol_pl` `olp_pl` `one_rg` `opr_pl` `or_gl` `orb_gr` `orbs_gr` `orbs′_gr` `orb′_gr` `ord_nt` `ordu_gr` `orl_sv` `orq_nt` `orth_pl` `ot_pl` `outA_sv` `outI_sv` `outR_sv` `out_sv` `outg_gr` `outp_gr` `p2_pl` `p4_nt` `pa_sv` `pad_gr` `pad_rg` `pad′_gr` `pairs_rg` `pat_nt` `pb_sv` `pch_cx` `pchain_pl` `pctx_nt` `pdq_pl` `perm_gl` `permi_gr` `permm_la` `perms_gr` `pf_sv` `pfa_sv` `pfb_sv` `pf′_pl` `pi_cx` `pia_cx` `pick′` `pih_cx` `pin_gl` `plS_cx` `pld_cx` `plneg_cx` `plq_cx` `pm_sv` `pmd_nt` `pol_sv` `polysqfree_pl` `pos_cx` `posr_gr` `pos′_gr` `pow_rg` `powu_gr` `powᶻ′` `pp_pl` `ppl_nt` `ppos_pl` `pps_nt` `ppw_cx` `ppw_gr` `pr_fd` `prep` `primeu_gr` `prl_nt` `prm_nt` `prs_nt` `prt_nt` `prz_pl` `ps_pl` `ps_rg` `psr_pl` `pst_pl` `psum` `psw_cx` `pts_sv` `pvo_nt` `pvp_nt` `pvt_la` `pw2_cx` `pw_fd` `pw_gr` `pw_nt` `pw_pl` `pw_rg` `pwl_pl` `pwm_pl` `pwq_pl` `pwr_sv` `pwz_nt` `q4_gl` `qa_pl` `qadd_cx` `qd_sv` `qdiv_cx` `qk_sv` `qmul_cx` `qnr_nt` `qo_fd` `qr_sv` `qrc_sv` `qrl_nt` `qs_pl` `qsub_cx` `quo_pl` `quoᶻ` `qz_pl` `qzi_pl` `ratQ′` `rb_pl` `rb_sv` `rc_pl` `rcd_pl` `rcf_sv` `rcn_sv` `rd_pl` `rdc_nt` `reR_cx` `realᶻ` `red_la` `red_rg` `redr_gr` `refls_gr` `reg_gr` `regs_sv` `reg′_gr` `rel_cx` `rel_sv` `relsym_sv` `relt_sv` `rem_pl` `remᶻ` `reqs′_gr` `res_pl` `rf_pl` `rfc_pl` `rg_pl` `rgc_pl` `rgp_pl` `rgq_cx` `rgt_pl` `rhc_nt` `rhi_sv` `rhl_sv` `rho_nt` `rhu_sv` `rkl_sv` `rl_pl` `rl_sv` `rle_gr` `rle′_gr` `rlo_sv` `rm_fd` `rm_pl` `rmm_pl` `rmv_la` `rmv_pl` `rnd_nt` `rnd²` `rndᶻ` `ro_fd` `rootS_cx` `rootu_cx` `rots_gr` `rq_pl` `rq_sv` `rqf_sv` `rqg_sv` `rr_gl` `rr_pl` `rrefp_la` `rr²` `rr¹` `rs_pl` `rsc_pl` `rsf_pl` `rsix_cx` `rst_nt` `rsz_pl` `rt_fd` `rt_pl` `rts_sv` `ru_sv` `rul2_cx` `ruler_cx` `runc_sv` `runs_sv` `r×` `r÷` `r⁺` `r⁻` `r∗` `s2c_nt` `s2p_nt` `s2s_nt` `sEs_cx` `sa_pl` `sb_fd` `sbm_pl` `sbq_fd` `sbz_pl` `sc4_cx` `sc_fd` `sca_rg` `sched` `sclR_cx` `scl_cx` `scl_pl` `scm_pl` `scz_pl` `serE_cx` `serEl_cx` `serN_cx` `serNl_cx` `ser_cx` `serl_cx` `sf_fd` `sfd_nt` `sfl_nt` `sfr_nt` `sg_nt` `sg_pl` `sg_sv` `sgn_pl` `sgn_sv` `sgp_gr` `sgrs_gr` `sgr′_gr` `shiS_cx` `shn_cx` `showⁱ` `siS_cx` `sim_sv` `simp′` `sinR_cx` `sinS_cx` `single_sv` `sinhS_cx` `sinhᴾ` `sinv_gr` `sl_pl` `slm_pl` `slq_nt` `slr_nt` `snf_gr` `snp_gr` `solv_gr` `sorted_rg` `sosD_sv` `sosF_sv` `sosG_sv` `spS_cx` `sp_fd` `spf_cx` `spine` `spine′` `spl_gl` `spl_nt` `split_gr` `spoly_rg` `spr_nt` `spr_pl` `spsp_nt` `spt_gl` `sq2_cx` `sq_fd` `sqchain_pl` `sqfp_sv` `sqj_cx` `sqm_nt` `sqn_nt` `sqp_pl` `sqq_gl` `sqr_nt` `sqrtR_cx` `sqrtS_cx` `sqrtpos_cx` `sqrtq_cx` `sqs_nt` `sqz_nt` `sq⁺` `sr2_sv` `sr3_sv` `sr_sv` `srs_pl` `srt_gl` `srt_sv` `ssl_nt` `ssr_nt` `st_pl` `stp_nt` `sub_pl` `sub_rg` `sub_sv` `subs_gr` `subs_la` `subu_gr` `subΦ_sv` `sumR_cx` `sum_gl` `sv_nt` `sv_sv` `swap_gr` `swp_gr` `sy_pl` `syl_gr` `syl′_gr` `symᶜ` `sz_pl` `ta_sv` `tab_gl` `takeu_gr` `take′` `tan_nt` `tang_cx` `tb_sv` `tcj_sv` `td_nt` `tdp_nt` `tds_nt` `tdv_sv` `tg_nt` `tk_nt` `tm_pl` `tm_rg` `tm_sv` `tmp_sv` `tmpa_sv` `tmpb_sv` `tpo_sv` `tpw_sv` `tr2_fd` `tr3_fd` `tr_cx` `tr_fd` `tr_sv` `tre_gr` `trim_pl` `trimᵖ` `trj_cx` `trows_cx` `trp_cx` `trz_pl` `ts_nt` `tsc_cx` `tsc_nt` `tsp_cx` `tsq_pl` `tsq_sv` `tsr_nt` `tups_gr` `tval_gr` `tz_nt` `u_gr` `ub_cx` `ube_cx` `ubs_cx` `uc_gr` `uc′_gr` `ud_nt` `ukh_cx` `ul_nt` `um_nt` `umerge_gr` `un_sv` `unary_cx` `unk_sv` `up_cx` `up_nt` `up_pl` `upl_nt` `up²` `use_sv` `usort_gr` `uvec_gr` `u′_gr` `v2_nt` `v2′_nt` `valid` `varof_sv` `vat_pl` `vmi_pl` `vn_rg` `vpi_pl` `vr_pl` `vuse_sv` `wil_nt` `wix_gr` `wix′_gr` `xeg_pl` `xm_pl` `xs_pl` `yl_pl` `yun_pl` `z_pl` `zemS_cx` `zem_cx` `zer_sv` `zetaS_cx` `zf_pl` `zfe_cx` `zis_cx` `zl_cx` `zl_fd` `zm_pl` `zm_sv` `zneg_cx` `zpl_cx` `zq_pl` `zs_pl` `zset_sv` `zw_gr` `¬³` `·ᴾ` `·ᵖ` `½ᶻ` `×⁴ᵈ` `÷ᴴ` `Σᴾ` `Ω` `βs` `βᶜ` `λᶜ` `ᶜ^` `ᶜ^ᴿ` `ᶜatan` `ᶜcos` `ᶜcosh` `ᶜexp` `ᶜlog` `ᶜroot` `ᶜsin` `ᶜsinh` `ᶜ¬` `ᶜ÷` `ᶜ÷ᴿ` `ᶜΣ` `ᶜℑ` `ᶜℑᴿ` `ᶜℜ` `ᶜℜᴿ` `ᶜ⇒` `ᶜ⇔` `ᶜ⇡` `ᶜ∗` `ᶜ∗ᴿ` `ᶜ√` `ᶜ∧` `ᶜ∨` `ᶜ∷` `ᶜ≐` `ᶜ≐ᴿ` `ᶜ≠` `ᶜ≠ᴿ` `ᶜ≺` `ᶜ≺ᴿ` `ᶜ≻` `ᶜ≻ᴿ` `ᶜ⊕` `ᶜ⊖` `ᶜ⊖ᴿ` `ᶜ⊘` `ᶜ⊛` `ᶜ⊞` `ᶜ⊟` `ᶜ⊟ᴿ` `ᶜ⊠` `ᶜ⊤` `ᶜ⊥` `ᶜ⩽` `ᶜ⩽ᴿ` `ᶜ⩾` `ᶜ⩾ᴿ` `ᶜ𝔲` `‖` `⁴ᴸ` `⁴ᶻ` `ℑᶻ′` `ℚ[i][x]` `ℚ[i][𝐱]` `ℜᶻ′` `ℤ²` `⇑ᶜ` `⇓ᶜ` `∂′` `∅ᵖ` `∗ᴾ` `∗ᵃ` `∗ᵖ` `√?ᶜ` `√merge` `√ᑫ` `√ᶜ′` `√ᶻ` `√ᶻ′` `√ᶻⁱ` `√⁺?ᵃ` `√⁺′` `∧³` `∧ᵈ` `∨³` `∨ᵈ` `≡ᵃ` `≡ᵐ` `≡ᶜ` `⊖ᴾ` `⊖ᵖ` `⊞ᴾ` `⊞ᵖ` `⊞ᶜ′` `⊟ᶜ` `⊟ᶜ′` `⊠ᴾ` `⊠ᵐ` `⊠ᵖ` `⊡′` `⊻ᵈ` `⋚ʳ′` `⋚ⁱ′` `⌄⁴` `⌊½⌋ᶻ` `⌊ᶻ` `⌜ᶻ` `①` `②` `③` `④` `⑤` `⑥` `⑦` `⑧` `⑨` `⓪` `⟐′` `⩾⁰` `⫽ᶻ′` `𝒦` `𝒮` `𝔡` `𝔲` `𝕊²` `𝕓⁴`
