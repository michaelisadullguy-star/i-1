# Theories: axiomatic packages and a fast decision of statements (`lib/term.imo` … `lib/th_prob.imo`)

i-1 is not a theorem prover.  It is a language that should be able to say *quickly* whether a statement is true for all values, false for all values, or neither — and to write an
expression in its simplest form — so that larger programs do not stumble over logic.  This part of the library does that with **packages of axioms** (theories) that are switched on
and off, each with its axioms and theorems written down as data, and a simplifier whose decision procedures are exact for what each package is about.

Everything is written in i-1 (trusted prelude, parts 26–37), on the same foundation as the rest: a term is a Scott value, a symbol is a string of base-(i − 1) digits, a dictionary is a
trie over digits (`lib/dict.imo`), and the Boolean connectives of the diagrams are the digit operations.

```
main in String := simpe(defaultenv, "x * 1 + 0 * y")        -- prints  x
```

## The interface

| name | meaning |
|:--|:--|
| `simpe(env, "text")` | the simplest form of a statement or an expression, as text (the text itself if it does not parse) |
| `holdsv(env, "text")` | the verdict as a number: **1** true for all values, **0** false for all values, **2** undetermined |
| `holdse(env, "text")` | the same as a three-valued Boolean: `true`, `false`, `⍰` |
| `simp("text")`, `holds("text")` | the same under the default theories |
| `defaultenv`, `envwith(names)` | the default theories; the default theories followed by `use` of each name |
| `use(name, env)`, `unuse(name, env)`, `usetheories(names, env)` | switch a package on (with what it requires; what conflicts with it goes off) or off (and what needs it) |
| `activetheories(env)`, `isactive(name, env)`, `theorynames` | which packages are on; all packages |
| `axiomsof(name)`, `theoremsof(name)`, `describe(name)` | the axioms and theorems that a package embeds, and a line about it |
| `checktheory(name)` | the embedded theorems that the simplifier cannot prove under that package alone (the empty list: all hold — this is what the tests run) |
| `simplifyt(env, term)`, `parseterm`, `tprint`, `mkenv`, `mksig`, `mkrules`, `normalize` | the parts, for building other environments |

A statement is text in the notation of the packages that are on (below).  Variables are the names that no package declares (`x`, `A`, `p`); `f(x)` is the application of a symbol; `{a, b}`
and `[a, b]` are the symbols `set` and `list`; numbers are decimal.  Whether a statement holds *for all values of its variables* is what the verdict says.

```
holdsv(defaultenv, "(x + y)^2 = x^2 + 2*x*y + y^2")   -- 1
holdsv(defaultenv, "x^2 + 1 = 0")                       -- 0   (no real number)
holdsv(defaultenv, "x = y")                             -- 2   (true for some values)
holdsv(envwith(["kolmogorov"]), "P(A ∪ B) <= P(A) + P(B)")      -- 1
holdsv(use("intuitionistic", defaultenv), "p || ¬p")    -- 2   (no excluded middle)
holdsv(envwith(["zfc"]), "card(powerset({1, 2, 3})) = 8")        -- 1
```

## Packages

A package is a value (`Theory`) with a name, the names it **requires**, the names it **conflicts** with, whether it is a **default**, a signature (operators), rewrite rules, hooks (decision procedures),
and its **axioms** and **theorems** as text.  `use` switches it on together with what it requires and switches off what conflicts with it (and whatever needed that); `unuse` switches it off together
with what needs it.

| package | requires | conflicts | default | decides |
|:--|:--|:--|:-:|:--|
| `core` | — | — | ✓ | the language of logic (`and or not imp iff xor ite true false`) and equality |
| `classical` | core | intuitionistic | ✓ | propositional logic by canonical diagrams (BDDs): tautologies, contradictions, the simplest form |
| `intuitionistic` | core | classical | | propositional logic without excluded middle, by Dyckhoff's calculus G4ip (Glivenko's theorem lets the classical diagram decide all but the classical tautologies that are not negations) |
| `arith` | core | — | ✓ | commutative rings and fields: every polynomial identity by normal forms; order and linear arithmetic by Fourier–Motzkin elimination inside the diagram of the statement (DPLL(T)) |
| `reals` | arith | peano, integers | ✓ | variables are real: even powers are ≥ 0, so `x^2 + 1 > 0`, `x^2 = -1` is false |
| `peano` | arith | reals, integers | | variables are natural numbers: ≥ 0, successor `S(x)`, `<` is discrete; the integer rows are tightened (`x = 0 ∨ x > 0` holds) |
| `integers` | arith | reals, peano | | variables are integers: `<` is discrete, rows are tightened |
| `group` | core | — | | the word problem of groups (`·`, `inv`, `e`, `⁻¹`): the complete rewriting system |
| `abelian` | group | — | | commutative groups: `·` is also commutative |
| `sets` | core | — | | the algebra of sets (`∪ ∩ ᶜ \ ∅ U ⊆ ∈`): identities and inclusions, exactly, by witnesses |
| `lattice` | core | — | | lattices (`⊔ ⊓ ⊑`): Whitman's condition decides what holds in every lattice |
| `zfc` | core | etcs, sets | | Zermelo–Fraenkel on hereditarily finite sets, evaluated: `∪ ∩ \ 𝒫 ⋃ × card ord`, `∈ ⊆ =`, foundation |
| `etcs` | core | zfc, sets | | Lawvere's elementary theory of the category of sets: the equations of a cartesian closed category with a terminal object, normalised |
| `kolmogorov` | arith | sets, zfc | | probability on finitely many events: inclusion–exclusion by Möbius inversion, the axioms as exact linear constraints on the minterms |
| `piecewise` | arith | — | | `abs min max sgn` as definitions by cases: the cases are lifted out of the arithmetic and decided path by path (the triangle inequality, `max(x, y) = (x + y + abs(x - y)) / 2`, …) |
| `incidence` | arith | — | | points `pt(x, y)`, collinearity and lines in coordinates (Hilbert's group I): the incidence geometry that the three geometries share |
| `euclid` | incidence | hyperbolic, elliptic | | Euclid's Elements, Book I, in Cartesian coordinates: `dist2 dot perp par cong rightangle between oncircle` and the constructions `midpoint centroid fourth reflect rot` |
| `hilbert` | euclid | — | | the 20 axioms of Hilbert's *Grundlagen* (incidence, order, congruence, parallels, continuity) and the theorems that hold in the coordinate model |
| `hyperbolic` | incidence | euclid, elliptic | | the Beltrami–Klein disc: the parallel postulate fails; `rightangle` and `cong` mean the hyperbolic ones (`coshsq` is cosh² of the distance) |
| `elliptic` | incidence | euclid, hyperbolic | | the projective (spherical) plane: no parallels; `cossq` is cos² of the distance |
| `topology` | sets | — | | the Kuratowski closure axioms: `cl int bd ext open closed` rewritten into closures and complements with the normal forms of the 14-set theorem |
| `monoid` | core | cmonoid | | an associative operation `⋆` with a neutral `ε`: the words of the free monoid, no commutativity, no cancellation |
| `cmonoid` | core | monoid | | the same, commutative: the words are multisets |

`zfc` and `etcs` are alternative foundations; `kolmogorov` and `sets` write events and sets with the same tokens; `peano`, `integers` and `reals` are alternative domains for the variables; `classical`
and `intuitionistic` are alternative logics; `euclid`, `hyperbolic` and `elliptic` are the three plane geometries (the parallel postulate, its negation with many parallels, and its negation with none); `monoid` and `cmonoid` differ by commutativity.
Switching one on switches its rivals off, and whatever needed them:

```
activetheories(defaultenv)                              -- [core, classical, arith, reals]
activetheories(use("peano", defaultenv))                -- [core, classical, arith, peano]
activetheories(use("etcs", use("zfc", defaultenv)))     -- [core, classical, arith, reals, etcs]
activetheories(unuse("arith", defaultenv))              -- [core, classical]        (reals needed arith)
activetheories(use("hyperbolic", envwith(["hilbert"])))  -- [core, classical, arith, reals, incidence, hyperbolic]   (euclid and hilbert go)
```

The same words, three geometries (`rightangle(A, B, C)`: the angle at B is a right angle):

```
R = "rightangle(pt(3/4, 1/4), pt(1/2, 1/4), pt(1/2, 1/2))"           -- a horizontal and a vertical segment, neither through the centre of the disc
holdsv(envwith(["euclid"]), R)       -- 1        holdsv(envwith(["hyperbolic"]), R)   -- 0        holdsv(envwith(["elliptic"]), R)   -- 0
-- a rectangle (four right angles) exists in the Euclidean plane and not in the other two
```

### Notation

Every package declares its operators with lines `kind precedence token symbol [properties]`: the kind is `const fn infixl infixr infix prefix postfix binder`; the properties `A C I` say
that the symbol is associative, commutative, idempotent (the terms are flattened and sorted: *modulo* those laws).  The core has `∧ && and`, `∨ || or`, `¬ ~ not`, `⇒ => implies`, `⇔ <=> iff`, `⊻ xor`,
`⊤ true`, `⊥ false`, `ite`, `=`, `≠ !=`; arithmetic `+ - * / ^`, `< <= ≤ > >= ≥`; the others are in the table of their package (`axiomsof`, `describe`).  A rule is `lhs ==> rhs` with
variables for patterns; rules are applied bottom-up, with matching modulo the declared laws, until nothing changes.

## How a statement is decided

1. **Parse** with the operators of the active packages (a Pratt parser driven by the signature) into a term.
2. **Rewrite** to a normal form: the rules of the packages, the laws `A C I`, and the *hooks* — arithmetic terms go to polynomial normal forms (an identity of rings is equality of normal forms), numbers are
   computed exactly in ℚ, sets of ZFC are normalised (extensionality is sorting and merging), the probability of an event is expanded by inclusion–exclusion.
3. **Decide the Boolean skeleton**: the statement becomes a reduced ordered binary decision diagram over its atoms (relations, memberships, propositional variables).  A diagram that is the constant true or false is a
   theorem or a contradiction.  When the atoms are relations of an ordered domain, each path of the diagram is a conjunction of constraints and is **kept only if the constraints are consistent**: linear ones by
   Fourier–Motzkin elimination (exact over ℚ for conjunctions of linear equations and inequalities: rows are scaled and the implied ones dropped; a variable with one sign is removed with its rows; the variable
   with the fewest new rows goes first; integer variables tighten rows), set atoms by witnesses (an element for every non-inclusion).  A statement with no consistent path is false, one whose negation has none is true,
   and otherwise the statement is rewritten to the formula of its consistent paths.
4. **Print** in the notation of the packages.

The verdict is `2` when the engine cannot tell.  It is *never* wrong: every `1` and `0` is a proof.  The engine is complete for: propositional logic, polynomial identities, closed numerical statements,
linear arithmetic over ℚ (and over ℤ / ℕ for the problems that tightening solves), identities and inclusions of Boolean algebras of sets, the word problem of groups and abelian groups, equations of
free lattices, linear statements about the probabilities of finitely many events (up to five), and statements about hereditarily finite sets with known elements.

### Where it is incomplete (and says so with 2)

* nonlinear order reasoning is exact for polynomials of degree 2 in any number of atoms (a positive semidefiniteness test, below) and otherwise limited to the signs of monomials: `(x + 1)^2 ≥ 0` and `x^2 + y^2 ≥ 2xy` are proved, `x^4 + 2*x^2 + 1 ≥ 0` is (even powers) but `x^4 - 2*x^2*y^2 + y^4 ≥ 0` is undetermined (a sum of squares of degree 4);
* `A = B` between two bare variables is an arithmetic equation when `arith` is on; write a set expression (`A ∪ B = A ∩ B`) or switch `arith` off to have the algebra of sets read it;
* a system of more than 200 rows during the elimination stops with "consistent" (sound: only fewer statements are decided);
* integer reasoning is rows tightening, not a complete integer decision procedure;
* ZFC is evaluated on hereditarily finite sets: `powerset` of up to ten elements, `bigunion`, products; there is no infinity and no choice in the simplifier (the axioms are listed);
* the intuitionistic package decides propositional logic only.

## Kolmogorov in detail

Events are Boolean terms (`∪ ∩ ᶜ \ ∅ Ω` are `or and not diff false true`).  `P(S)` is expanded by Möbius inversion of the truth table of `S`: if `S` is the sum `Σ c_J ∏_{j ∈ J} e_j` of indicator functions then
`P(S) = Σ c_J P(∩ J)` (inclusion–exclusion, for any number of events).  The axioms — `P ≥ 0`, `P(Ω) = 1`, additivity — say that the probabilities `m_K` of the minterms (the events in `K` occur and the others do not)
are ≥ 0 and add up to 1; each `P(∩ J)` is the sum of the `m_K` with `K ⊇ J`.  The rows of a path are rewritten over the `m_K` and given to the elimination above, which is then exact: a linear statement
about probabilities is true exactly when it holds at the point masses (the vertices of the simplex), false exactly when it fails at all of them.  `P(A | B) · P(B) = P(A ∩ B)` and independence
`indep(A, B)` are rules.

## ZFC and ETCS

`{a, b, …}` is a set (the symbol `set`, commutative and idempotent: extensionality is the normal form); elements are sets or numbers (urelements).  `∪ ∩ \ 𝒫 ⋃ × card ord opair succ` are computed on sets
whose elements are known, `x ∈ {a, b}` is `x = a ∨ x = b`, `{a, b} ⊆ B` is `a ∈ B ∧ b ∈ B`, two different known sets are different, foundation (`A ∉ A`, no 2-cycle of membership) is a rule.  The von Neumann ordinal `ord(n) = {0, …, n−1}`.
In ETCS morphisms compose with `∘` (associative), `id` is neutral, `pr(f, g)` is the pairing with the projections `p1 p2`, `lam` and `ev` the exponential, `bang` the map to the terminal object; the rules are
the equations of a cartesian closed category.

## Quadratic polynomials

A polynomial of degree 2 in any number of atoms is `(x, 1) M (x, 1)ᵀ` for a symmetric matrix `M` of rationals, and it is non-negative for all values exactly when `M` is positive semidefinite.  `lib/psd.imo` decides that by an
exact `LDLᵀ` elimination (Schur complements with rational pivots; a zero pivot needs a zero row), and it finds the minimum `s` of the polynomial when it is bounded below, so that `p ≥ 0` iff `s ≥ 0` and `p > 0` iff `s > 0`.
`pfsign` calls it when the signs of the monomials cannot tell.  `x^2 + x + 1 > 0` is true, `x^2 + 2*x + 1 > 0` is undetermined (it is 0 at −1), `x^2 + 2*x + 2 < 0` is false, `x^2 - 1 ≥ 0` is undetermined.

## Piecewise definitions

`piecewise` defines `abs`, `min`, `max` and `sgn` by cases, `abs(x) = ite(x ≥ 0, x, -x)`, and has rules that lift an `ite` out of sums, products, powers, quotients and relations.  What is left is a Boolean skeleton over relations: the diagram decides it and each path
is a system of linear (or polynomial) constraints that the elimination checks.  The triangle inequality `abs(x + y) <= abs(x) + abs(y)`, `max(x, y) = (x + y + abs(x - y)) / 2` and 30 other theorems are proved this way.

## Geometry

Points are terms: variables, or `pt(x, y)`; `px` and `py` are the coordinates.  `incidence` rewrites `collinear(A, B, C)` into `cross(A, B, C) = 0`, a polynomial equation; `euclid` adds the metric (`dist2(A, B) = (xA - xB)^2 + (yA - yB)^2`, `perp`, `par`, `cong`,
`rightangle`, `between`, `oncircle`) and constructions with rational coordinates (`midpoint centroid fourth reflect rot`), so that Thales, Pythagoras and its converse, Apollonius, the parallelogram law, Varignon's theorem, the midline theorem, the medians
and the orthocentre are polynomial identities, or *linear consequences of the hypotheses over the monomials*, which the arithmetic of the package arith decides.  `hyperbolic` and `elliptic` replace the metric by the Cayley–Klein forms `<P, Q> = xP xQ + yP yQ ∓ 1`:
`cong` compares `coshsq(A, B) = <A, B>^2 / (<A, A> <B, B>)` (or the same with `cossq`), computed exactly for points with known coordinates, and the angle at B is right when `<A, C> <B, B> = <A, B> <B, C>`.
`hilbert` embeds the 20 axioms and the theorems that the coordinate model decides.  What the geometries do not do is decide statements that need an ideal membership (a conclusion that is a polynomial multiple of the hypotheses) or the order of the reals beyond degree 2.

## Topology and monoids

`topology` (requires `sets`) takes the Kuratowski closure axioms as rules (`cl(∅) = ∅`, `cl(A ∪ B) = cl(A) ∪ cl(B)`, `cl(cl(A)) = cl(A)`, and `k c k c k c k = k c k`, with `k` the closure and `c` the complement), and rewrites `int`, `bd`, `ext` into closures and complements.  Every word in `cl` and `ᶜ` has one of 14 normal forms
(Kuratowski's theorem), so identities between such words are decided; inclusions are decided where the embedded inclusions (`A ⊆ cl(A)`, `int(A) ⊆ A`, `cl(A ∩ B) ⊆ cl(A) ∩ cl(B)`, …) and the algebra of sets suffice, and `open`/`closed` are the predicates `A ⊆ int(A)` and `cl(A) ⊆ A`.
`monoid` and `cmonoid` are the free monoid and the free commutative monoid on the variables.

## Files

| file | content |
|:--|:--|
| `lib/term.imo` | terms (variable, number, application), equality, a total order, substitution, matching |
| `lib/parse.imo` | tokenizer, signatures, Pratt parser, printer |
| `lib/rewrite.imo` | environments, rules, matching modulo `A C I`, normal forms |
| `lib/boolalg.imo` | binary decision diagrams, Boolean canonical forms |
| `lib/polynf.imo` | polynomial normal forms, sign analysis, relations |
| `lib/fm.imo` | Fourier–Motzkin elimination, sets by witnesses, the paths of a diagram modulo an order |
| `lib/intuit.imo` | G4ip |
| `lib/theory.imo`, `lib/theories.imo` | theories as values, the packages and their conflicts, `simpe`, `holdsv`, `checktheory` |
| `lib/th_algebra.imo`, `lib/th_found.imo`, `lib/th_prob.imo` | classical and intuitionistic logic, groups, sets, lattices; ZFC and ETCS; Kolmogorov |
| `lib/psd.imo`, `lib/th_piece.imo`, `lib/th_geom.imo`, `lib/th_topo.imo` | the sign of quadratic polynomials; piecewise; the geometries; topology and monoids (written in human notation in `libsrc/*.hum.imo`; the geometry and topology packages are generated by `libsrc/gen/*.py`) |

## Tests

`tests/test_theory.py` (1945 checks on the fast cores, a sample on Pymo): the embedded theorems of every package, the mechanism of packages, curated statements with their exact verdicts, and random statements against
exact oracles in Python — truth tables for propositional logic, dictionary polynomials for identities, `Fraction` arithmetic for closed statements, Fourier–Motzkin written separately for implications between
linear inequalities, free reduction and exponent sums for words of groups, truth tables over membership types for sets, the vertices of the simplex for probabilities, frozensets for hereditarily finite sets,
associativity for chains of morphisms, Glivenko's theorem for intuitionistic logic, the principal-minor criterion for quadratic polynomials, a case-by-case Fourier–Motzkin expansion of `abs`/`min`/`max`, exact
rational arithmetic and linear forms for the geometries, and 60 random finite topological spaces (the 14 operations of Kuratowski are told apart by them).
