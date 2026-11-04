
---

## 5. The system documents (doc 1 and doc 2)

The notations are connected by two plain-text *system documents* in `docs/`.  They are data, not code: the reader, the translators and the generated reference tables in this README are all driven by them.

```text
doc 1   [spec sbl] := [bin sbl]                     docs/doc1.sbl
doc 2   [hum sbl]  := [spec sbl] or [bin sbl]       docs/doc2.sbl
```

It is fine for a notion — even a common one — to have no specific symbol: its human symbol then points straight at a binary symbol or numeral in doc 2 (this is how `i := 11` is written: the imaginary unit is *the numeral 11*, it needs no definition and no glyph).  The goal is that most notions an undergraduate meets have a human notation; [§14](#14-standard-library-reference) lists what the prelude covers today.

### 5.1 Doc 1 — `[spec sbl] := [bin sbl]`

One line per spec symbol:

```text
{{HEAD:docs/doc1.sbl:14}}
…
```

* **Bijection.**  Every spec symbol has exactly one binary symbol and vice versa.  Class names (`ℕ`, `ℚ[i]`, `𝔏`), statement formers (`⊆`, `≣`, `↪`), library symbols and even the bound-variable names used inside the prelude (`ξ`, `η`, …) are all listed — a binary program has no other way to name them.
* **Codes are ordinals.**  The code of the *n*-th symbol is *n* written in binary: `.1.`, `.10.`, `.11.`, `.100.`, … ({{DOC1_COUNT}} symbols at the moment).
* **Append-only.**  A released code is never reassigned; new symbols get the next ordinal.  `pymo/mkdoc1.py` reads the existing doc 1 first and only appends, so a symbol keeps its code wherever in the prelude it is used first (the 129 codes of the first release are unchanged).  One entry, `main`, is not a prelude symbol: it is the entry point, listed so that a bin program can name it without a local table.
* **Reserved tokens** are not listed: `↦` = `.`, `≔` = `..`, `∶` = `...`.
* **Program-local symbols.**  Names introduced by a user program (`π`, `𝕖`, `𝕫` in the target) are *not* in doc 1; their codes live in the program's own `.sbl` file, in the same line format, always above the highest doc 1 code.

### 5.2 Doc 2 — `[hum sbl] := [spec sbl] or [bin sbl]`

```text
<human symbol> := <rhs> | <rhs> | …  ; <role> [precedence]        ⍝ comment
```

* **rhs** — a spec symbol, a bin numeral (`11`), or a bin symbol (`.B.`, which stands for the spec symbol doc 1 gives that code).
* **Several right-hand sides** form an **overload set**: the human symbol means *whichever* of them the class checker finds applicable to the arguments ([§4.4](#44-human-notation)).
* **role**

| Role | Meaning |
|:--|:--|
| `class` | the symbol is a class (`\NN`, `String`, `List`, …); class constructors take arguments in parentheses |
| `value` | a constant or function (`pi`, `sum`, `conj`, …); also the *name under which a user definition is stored* — defining `pi` in a human program defines the spec symbol `π` |
| `literal` | a constant that is a bin numeral (`i := 11`) |
| `infixl P`, `infixr P`, `infix P` | binary operator of precedence P (left-, right- or non-associative; non-associative is parsed as left) |
| `prefix P` | prefix operator of precedence P |
| `syntax` | a word of the human reader's built-in grammar, listed so that the document is complete (`:=`, `in`, `subseteq`, `\|->`, `->`) |

The whole of doc 2 as it stands, generated from `docs/doc2.sbl`:

{{DOC2TABLE}}

Notes on the table: `\R` and `\CC` are the same class ℝ[i] (`\R == \CC`); `-` appears twice because infix and prefix minus are different symbols; `embed` is the overload set of the two canonical coercions `⇡` (to streams) and `↑` (to the Cayley–Dickson tower); `+ * max min or and` are one overload family across numbers, truth values and sets ([§13.5](#135-one-system)); `==`, `!=`, `lt`, `leq`, `gt`, `geq` include the relations on ℝ[i] that the prover decides.

### 5.3 What is checked

The test-suite asserts that doc 1 is a bijection with ordinal codes and covers every prelude symbol; that `spec → bin → spec` reproduces every statement of the prelude and of the examples; that the all-binary prelude and target use only `1 0 . ( )` space and newline; that human programs compile to exactly the expected spec text; and that a doc 2 line whose right side is a bare binary symbol resolves through doc 1.
