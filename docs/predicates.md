# Predicates: every relation is simplified to its simplest form

*Design specification (the implementation follows it; sections marked **contract** are interfaces between parts).*

## 1. Principle

A **predicate** is a function whose value is **true**, **false** or **undetermined**.  The relations (`== != lt leq gt geq`), the
connectives (`and or not implies iff`) and every function a program declares with the codomain `Bool` or `Prop` are predicates.

Nothing has to be asked for.  The output of the system is exactly the evaluated function or value, and a relation is **simplified to
its simplest form whenever it is evaluated** — by a call for its value, by `main`, by any request for output — recursively, with
operations on base-(i−1) numbers, until it cannot be simplified further.  The simplest forms include `true` and `false`:

* if the relation holds for every value of its unknowns (a tautology) its value is **`true`**;
* if it holds for none (a contradiction) its value is **`false`**;
* otherwise its value is **undetermined**: neither answer is justified (the relation depends on its unknowns, or no rule of the
  prover decides it), and what is returned is the **simplest equivalent statement** — for one unknown, its solution set written
  out.  Where a Boolean is required (`decide`, §3) an undetermined predicate is the third truth value ⍰.

A relation between closed elements of ℚ[i] needs no simplifier: it is decided by evaluation (`docs/axioms.md`).  A relation that
involves ℝ[i] ∖ ℚ[i] (series, exp, π …) or an unknown is simplified by logic, from the definitions.  There is no operator that asks for
the simplification (an earlier `reduce` was removed: a program that writes it gets "undeclared symbol reduce"), because evaluating a
relation already simplifies it.

```text
x in \RR
z in \CC
y in \CC
main in List(Prop) := [x^2 gt 7 and x^3 lt 27,  z * conj(z) + 1 == 0,  x^2 + 1 == 0,  y^2 + 1 == 0]

[x lt -sqrt(7) or (sqrt(7) lt x and x lt 3), false, false, y == -i or y == i]
```

## 2. Unknowns

A symbol that is **declared and never defined** in a program is an **unknown**; its class is its domain:

| hum | spec | domain | code k |
|:--|:--|:--|:--|
| `\CC`, `\R` | `ℝ[i]` | ℂ | 0 |
| `\RR` | `ℝ` | ℝ | 1 |
| `\Q` | `ℚ[i]` | ℚ(i) | 2 |
| `\QQ` | `ℚ` | ℚ | 3 |
| `\Z` | `ℤ[i]` | ℤ[i] | 4 |
| `\ZZ` | `ℤ` | ℤ | 5 |
| `\NN` | `ℕ` | ℕ | 6 |

Human notation: a statement `x in \RR` without `:=` declares an unknown (spec: `x ∶ ℝ` with no `≔` line).  An unknown has no
value: a definition may mention it (it is expanded when a predicate uses it), but evaluating it as a number is a run-time error
("x is an unknown").  A variable bound by an outer λ (`p(x) in \RR -> Bool := …`) is treated as an unknown of its class inside the
predicate.

* The class of an unknown must be one of the seven number classes, or a class declared below one of them (`(⊆ Foo ℕ)`); its
  domain is the first of ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] that contains it.  Anything else (`p in Prop`, `s in String`, `f in \QQ -> \QQ`,
  `t in List(\ZZ)`) is a class error: *"p is declared but never defined, so it is an unknown; an unknown must be a number …"*.
  An unknown has one class (two declarations are a class error); a declaration without `:=` takes no parameters.
* Unknowns are written in codes as their symbol codes: program-local codes, numbered in **declaration order** (so a solution
  lists `x` before `y` when `x` is declared first), and the table of definitions holds `(code of x, ⌜𝔲 k⌝)` for every unknown a
  statement mentions.  The local codes are assigned when the program is checked — the unknowns first, then the program's other
  symbols, each in declaration order — so a program re-spelled by `translate --to spec` names its symbols by the same numbers
  (a bin program carries its codes in its local table).
* A definition whose value needs an unknown (`q in \ZZ := n + 1`) is fine; it is quoted as its symbol (with its definition in the
  table) wherever a statement uses it, and evaluating it is the run-time error above.

## 3. The class Prop (spec `Ω`)

`Ω` is the class of statements in simplest form, the class of the values of predicates; `𝔹` (true, false) sits inside it through the
canonical coercion 𝔹 → Ω.  A predicate is a function into Ω (or into 𝔹, when its arguments are closed values of ℚ[i]).

* A relation (`== != lt leq gt geq`) whose sides mention an unknown, or whose sides are elements of ℝ[i] (`≐ᴿ ≺ᴿ …`), has class Ω;
  its value is the simplest form.  A relation between closed ℚ[i] values stays 𝔹 (evaluated).
* `and or not implies iff` with at least one Ω operand: the whole combination is one Ω statement (simplified together).
* Where a 𝔹 is required (a definition declared `Bool`, `if`, `showb`), an Ω becomes a Boolean by **`decide`**: true → ⊤, false → ⊥,
  any other statement → ⍰ (undetermined; the printer reports it).
* `main in Prop := …` (or a list, pair … of Props) prints the statement in the output notation.

The class checker (`pymo/imotypes.py`) makes these precise:

| term | class | example |
|:--|:--|:--|
| a relation on ℝ[i] (`≐ᴿ ≠ᴿ ≺ᴿ ⩽ᴿ ≻ᴿ ⩾ᴿ`) | Ω, a statement | `pi == e`, `x lt 1` (x ∈ ℝ) |
| an application of class 𝔹 or Ω with an argument that mentions an unknown | Ω, a statement | `n == 1`, `g(n)`, `q == 2` (q needs n) |
| `and or not implies iff` — and `+ * max min`, which are or/and on truth values — with an Ω operand | Ω, **one** statement | `n == 1 and 2 == 2` |
| a closed relation on ℚ[i] | 𝔹, evaluated | `1/3 + 1/6 == 1/2` |
| `prop(b)`, `decide(φ)` | Ω, 𝔹 — the canonical coercions 𝔹 → Ω and Ω → 𝔹 | |

* **Overload resolution prefers Ω.**  `prop` costs 1 and `decide` (which loses information) costs 2, so where both readings fit —
  `n == 1 and true` — the connective on statements wins (`∧Ω` with `prop(true)`), never `∧` on two Booleans.  Two Booleans stay
  Booleans (`true and false` is `∧`), and `1 + true` is still 2.
* A list or pair literal is made to fit element by element: `[n == 1, false]`, `[false, n == 1]` and `[1 == 1, 2 == 3]` are lists of
  statements where a `List(Prop)` is expected; `pair(n == 1, 3)` is a `Pair(Prop, \NN)`.
* A definition declared `Bool` whose body is a statement holds `decide` of it (`name in Bool := relation` means what it meant before);
  a definition declared `Prop` holds the statement itself.

## 4. Simplest forms

The result is unique for equivalent inputs of the same shape (a normal form), and as simple as the engine can make it:

* **One unknown x, polynomial relations with ℚ[i] coefficients** — the solution set, written out:
  * equations over ℂ / ℚ(i) / ℤ[i]: `x == a₁ or x == a₂ or …`; disequations: `x != a₁ and …`; points sorted by (Re, Im);
  * over ℝ / ℚ: a union of points and intervals, sorted, adjacent cells merged:
    `x lt a`, `a lt x and x lt b`, `a leq x and x leq b`, `x == a`, `b lt x` …;
  * over ℤ / ℕ: the same with integer bounds (`-3 leq n and n leq 3`), bounds implied by the domain omitted (`n leq 3` for ℕ);
  * the empty set is `false`, everything is `true`.
* **Exact roots**: a root in ℚ(i) is a numeral; a root of a quadratic factor is `u + v*sqrt(d)` (u, v ∈ ℚ(i), d a square-free
  integer, possibly negative — `sqrt(-3)`), or `u + v*sqrt(D)` for a non-real D ∈ ℚ(i); a real root of an irreducible factor p of
  higher degree is `root(p, k)` — the k-th real root of p in increasing order (p written as its coefficient list, lowest degree first).
  Non-real roots of irreducible factors of degree ≥ 3 are not written out: the factor's equation `p(x) == 0` stays.
* **Several unknowns**: conjunctions of linear equations are solved (`x == 2 and y == 1`, or pivot unknowns in terms of free ones);
  sums of squares are decided (`x^2 + y^2 + 1 gt 0` is true, `x^2 + y^2 == 0` is `x == 0 and y == 0`); a complex unknown z under
  `conj` is split into real and imaginary parts when that decides the relation (`z * conj(z) + 1 == 0` is false).  Anything else
  is left as a relation `P rel c` with P expanded, primitive, leading coefficient positive, and the constant c on the right.
* **No unknowns** (relations on ℝ[i]): proved → `true`, refuted → `false` (rules of `docs/prove.md`); otherwise the relation in
  its normal form.
* Connectives: flattened, duplicates removed, `true`/`false` absorbed, complementary literals detected, `not` pushed onto relations
  (`not (x == a)` is `x != a`).

## 5. The simplifier (**contract**)

The simplifier runs **in the language** (`lib/solve.imo`), on codes (`docs/prove.md` §2):

```text
simplify′ ∶ 𝔏 (𝔓 𝔇 𝔔) → 𝔔 → Ω          simplify′ ε φ  =  the simplest form of φ
𝔲 ∶ ℕ → α                             an unknown of domain k is the entry (code of x, ⌜𝔲 k⌝) of ε
```

* **Input** φ: a code as written by `pymo/quote.py` — relations (`≐ ≠ ≺ ⩽ ≻ ⩾` and `≐ᴿ ≠ᴿ ≺ᴿ ⩽ᴿ ≻ᴿ ⩾ᴿ`), connectives
  (`∧ ∨ ¬ ⇒ ⇔`), arithmetic on ℚ[i] (`⊞ ⊟ ⊠ ⊖ ÷ ^ ∗ ℜ ℑ`) and on ℝ[i] (`⊕ ⊟ᴿ ⊛ ⊖ᴿ ∗ᴿ ÷ᴿ ^ᴿ ⇡ ℜᴿ ℑᴿ`), series and functions
  (`Σ exp sin cos √ log …`), symbols with definitions in ε, unknowns, values `𝔮ⁿ v` (v a ℚ[i] number in a term position, a Boolean
  in a formula position).  The connectives on statements `∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω` are written as the plain `∧ ∨ ¬ ⇒ ⇔`; the coercions
  `prop` and `decide` are transparent (the code of their argument); a statement passed to a function as a value (a parameter of
  class Ω) is spliced in as its code; a variable bound outside φ whose class is not a number is a free `𝔮ᵛ k` (k beyond φ's own
  binders).  A closed sub-term of a number class that mentions no unknown is a value `𝔮ⁿ`, computed at run
  time; one that mentions an unknown is written out (`𝔮ᵃ …`).
* **Output**: a code built only from
  * `𝔮ˢ ᶜ⊤`, `𝔮ˢ ᶜ⊥` (true, false);
  * `∧ ∨ ¬` (binary ∧ and ∨, nested to the right), relations `≐ ≠ ≺ ⩽ ≻ ⩾` (the plain ℚ[i]-level symbols, whatever the domain);
  * terms: `𝔮ⁿ q` with q ∈ ℚ[i] in canonical form `⊜` (never a Boolean), the unknowns' symbol codes, `⊞ ⊟ ⊠ ⊖ ÷ ^ √ ∗ ℜ ℑ`,
    `root` applied to a coefficient list (a list code built with `∷`/`⊘` of `𝔮ⁿ` numbers) and an index, and the codes of closed
    symbols that remain (π, user constants) in residual relations.
* The printer (`pymo/output.py`) spells such a code in hum (reverse doc 2, infix with precedences), and for spec / bin re-reads the
  hum text in the program's context (the class checker chooses `≐` or `≐ᴿ`, inserts `⇡`), so the output reads back.

## 6. Printing a statement (**contract**: the engine's tests use these rules)

A value of class Prop — also inside lists, pairs, streams — is spelled from its code in the **human notation**:

| code | hum | code | hum |
|:--|:--|:--|:--|
| `⊤` / `⊥` (symbol or `𝔮ⁿ` Boolean) | `true` / `false` | `(∨ a b)` | `A or B` (an ∧ directly inside is parenthesised: `(A and B)`) |
| `(∧ a b)` | `A and B` (an ∨ inside is parenthesised) | `(¬ a)` | `not A` |
| `≐ ≠ ≺ ⩽ ≻ ⩾` (and their ᴿ forms) | `== != lt leq gt geq` | `(⊞ a b)` `(⊟ a b)` | `A + B`, `A - B` |
| `(⊠ a b)` `(÷ a b)` | `A*B`, `A/B` | `(⊖ a)` | `-A` |
| `(^ a n)` | `A^N` | `(√ a)` `(∗ a)` `(ℜ a)` `(ℑ a)` | `sqrt(A)` `conj(A)` `re(A)` `im(A)` |
| `(root p k)`, p a list code | `root([c0, c1, …], k)` | `(⇡ a)` | `A` (the embedding is implicit) |
| an unknown, a program symbol | its own (human) name | any other symbol | its human name (reverse doc 2), `f(A, B)` |

* **Precedences**: or 2, and 3, relations 4, `+ -` 6 (left), `* /` 7 (left), prefix `-` 8, `^` 9 (right), `not` 4, atoms and calls 10.
  An operand is parenthesised when its precedence is lower than required — the left operand of a left-associative operator needs
  its precedence, the right operand of `-` and `/` one more (of `+` and `*` the same), the base of `^` must be atomic.  `-(-3)` is
  written so, never `--3` (`--` starts a comment).
* **Numbers** (`𝔮ⁿ q` in a term position) are spelled by the language's own `showc` (`3`, `-3`, `1/2`, `i`, `-i`, `2*i`,
  `-1/2 + 1/2*i`); a number's precedence is 10 for a non-negative real integer, 8 for a negative real integer, 7 for a real
  fraction or a pure imaginary, 6 when both parts are non-zero.
* **spec and bin**: the hum text is read again in the program's context (unknowns declared) by the human reader and the class
  checker; the resulting spec term (its statement marks dropped, made to fit Ω — `true` is `(prop ⊤)`) is printed, and for bin
  re-spelled through doc 1 (unknowns by their program-local codes).  So every printed statement reads back in its notation.
* A Bool that is undetermined (`decide` of a statement that is neither true nor false) is still reported as undetermined.
* Not spelled (a print error): a residual statement that contains a λ (`sum(1, k in \QQ |-> x / k) gt 0`) or a variable bound
  outside it (a statement about the parameter of a predicate whose body is undecided), whose binder classes the code does not
  carry.

## 7. Where it is implemented

| part | file | what it does |
|:--|:--|:--|
| unknowns | `pymo/hum.py`, `pymo/imo.py` | `x in \RR` without `:=` is a declaration; a symbol declared and defined nowhere is an unknown; its run-time value raises `UnknownError` ("x is an unknown") |
| statements | `pymo/imotypes.py` | the table of §3; statements are marked `('quote', φ, …)`; `prop`/`decide` coercions with costs 1/2; list/pair literals fitted element by element |
| codes | `pymo/quote.py`, `haskimo/src/I1/Quote.hs` | φ ↦ `(simplify′ ε⌜⌝ ⌜φ⌝)`; unknowns as symbol codes (declaration order) with `⌜𝔲 k⌝` entries |
| Prop | `lib/prove.imo` | `Ω`, `prop`, `decide`, `∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω` (true/false absorbed when used as values), the prover of `docs/prove.md` |
| engine | `lib/solve.imo` | `simplify′` (§4, §5) |
| printing | `pymo/output.py` | §6: `Speller` (hum), `Printer.reread` (spec, bin) |

`examples/predicates.hum.imo` is the program of §1 with the further cases of §4; `tests/test_predicates.py` tests the compiler side
with any engine and the simplest forms end to end once the engine is merged.

## 8. Why this is the right place for the line between evaluation and logic

On ℚ[i] every closed relation is decided by evaluation, in time polynomial in the number of digits.  On ℝ[i] equality is undecidable
in general and with unknowns a statement denotes a *set*; the most that can be returned is an equivalent statement in a form from
which the answer can be read off — exactly true or false when it is a tautology or a contradiction.  The engine is a growing
collection of decision procedures (each sound); what it cannot decide it returns simplified, never guessed.
