# Predicates — the class Prop, unknowns, statements simplified when they are evaluated

A **predicate** is a function whose value is true, false or undetermined.  A **statement** is the value of a predicate that cannot be
decided by evaluating ℚ[i] numbers: a relation between elements of ℝ[i] (series, `exp`, π …), or a relation about an **unknown** — a
symbol that is declared and never defined (`x in \RR`).  Its class is **Prop** (spec `Ω`) and its value is its **simplest form**:
`true` if it holds for every value of its unknowns, `false` if it holds for none, else (undetermined) the simplest equivalent
statement (for one unknown, its solution set).  The simplification happens whenever the statement is evaluated, output included —
nothing asks for it.  It runs in the language, on codes (`lib/solve.imo`, `simplify′`); this module is the compiler side — unknowns,
the class, the coercions, the connectives, the codes and the printer.  Relations between closed elements of ℚ[i] stay Booleans,
decided by evaluation.  Specification and the printing rules: `docs/predicates.md`.

```text
x in \RR                                   -- an unknown: declared, never defined
n in \ZZ
main in List(Prop) := [x^2 gt 7 and x^3 lt 27, n^2 lt 10, 1/3 + 1/6 == 1/2, n == 1 and true]
```

## Public names

| human | spec | class | meaning | algorithm | limits |
|:--|:--|:--|:--|:--|:--|
| `Prop` | `Ω` | class | statements in simplest form; a value is the code (`𝔔`) of the statement | — | — |
| `x in C` (no `:=`) | `x ∶ C` (no `≔`) | C a number class | declares the **unknown** x of domain C (ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], or a class below one) | domain code 0 ℂ, 1 ℝ, 2 ℚ(i), 3 ℚ, 4 ℤ[i], 5 ℤ, 6 ℕ; program-local symbol code in declaration order; table entry `⌜𝔲 k⌝` | evaluating x is a run-time error ("x is an unknown"); another class is a class error |
| `prop` | `prop` | `Bool -> Prop` | a truth value as a statement (canonical coercion 𝔹 → Ω, cost 1) | ⊤ ↦ the code of true, ⊥ ↦ the code of false | — |
| `decide` | `decide` | `Prop -> Bool` | a statement as a truth value (canonical coercion Ω → 𝔹, cost 2 — it loses information) | true ↦ ⊤, false ↦ ⊥, any other statement ↦ ⍰ (undetermined) | ⍰ is reported by the printer, never printed as true or false |
| `and` (also `*`, `min`) | `∧Ω` | `Prop -> Prop -> Prop` | conjunction of statements | with an Ω operand the whole combination is ONE statement, simplified together; as a value: true/false absorbed, otherwise the code `(∧ a b)` | — |
| `or` (also `+`, `max`) | `∨Ω` | `Prop -> Prop -> Prop` | disjunction of statements | as `and` | — |
| `not` | `¬Ω` | `Prop -> Prop` | negation of a statement | as `and` | — |
| `implies` | `⇒Ω` | `Prop -> Prop -> Prop` | implication between statements | as `and` | — |
| `iff` | `⇔Ω` | `Prop -> Prop -> Prop` | equivalence of statements | as `and` | — |
| `==` `!=` on `\R` | `≐ᴿ` `≠ᴿ` | `\R -> \R -> Prop` | (in)equality of elements of ℝ[i]: a statement | quoted with the definitions it uses, simplified by `simplify′` (rules of `docs/prove.md`) | undecidable in general: the result may be the relation itself |
| `lt` `leq` `gt` `geq` on `\RR` | `≺ᴿ` `⩽ᴿ` `≻ᴿ` `⩾ᴿ` | `\RR -> \RR -> Prop` | order of reals: a statement | as above | as above |
| `== != lt leq gt geq` about an unknown | `≐ ≠ ≺ ⩽ ≻ ⩾` | Prop | a relation whose sides mention an unknown (also any predicate of class Bool or Prop applied to an unknown) | quoted; the unknowns are symbol codes | the simplest form is the engine's (`docs/predicates.md` §4) |

Helpers (spec only): `truth_rd ∶ Ω → 𝔒` (⋗ true, ⋖ false, ≖ neither), `code_rd ∶ Ω → 𝔔` (a statement is its code).

## Class rules (pymo/imotypes.py)

* Overload resolution prefers Ω: `n == 1 and true` is `∧Ω` with `prop(true)` (cost 1), not `∧` with `decide(n == 1)` (cost 2);
  `true and false` stays `∧` on Booleans; `1 + true` is still 2 (Iverson).
* A list or pair literal is fitted element by element: `[n == 1, false]`, `[1 == 1, 2 == 3]` are `List(Prop)` where one is expected.
* A definition declared `Bool` whose body is a statement holds `decide` of it; declared `Prop`, the statement itself.

## Printing (pymo/output.py)

A Prop — alone or inside lists, pairs, streams — prints as a human statement (`x lt -sqrt(7) or (sqrt(7) lt x and x lt 3)`):
precedences or 2, and 3, relations 4, `+ -` 6, `* /` 7, prefix `-` 8, `^` 9, numbers by the language's `showc`.  In spec and bin
the text is re-read by the checker in the program's context, so the printed statement reads back.  The exact rules are in
`docs/predicates.md` §6.

## Limits

* The simplest forms are the engine's (`lib/solve.imo`); with the stub engine a decided statement becomes `true`/`false` and any
  other comes back unchanged.
* A residual statement that contains a λ, or a variable bound outside it (the parameter of a predicate whose body is undecided),
  has no human spelling yet (print error).
* A program symbol whose definition needs an unknown and that is used before it is defined is judged by a conservative estimate
  (it may be quoted where evaluation would have sufficed — never the converse).
* Inside a definition, a predicate's parameter of class ℝ or ℝ[i] is an unknown of its class.
