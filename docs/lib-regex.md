# Regular expressions (`lib/regex.imo`)

Regular expressions by **Brzozowski derivatives**: the derivative of a regular expression with respect to a character is the regular expression of what may follow it, so a string
matches when the derivative with respect to all of its characters accepts the empty string.  Twenty functions, written in the human notation (`libsrc/regex.hum.imo`) and
translated into spec notation by `libsrc/build.sh`.  An expression is a `Term` (`lib/term.imo`), so it can be compared with `teq`, printed, and taken apart like any term.

## The notation

`rxparse(pattern)` reads the usual syntax: concatenation, `|`, `*`, `+`, `?`, groups `( )`, `.` (any character but the line feed), classes `[abc] [a-z0-9_] [^…]`, the escapes `\d \w \s`
(digits, word characters, white space) and `\D \W \S` (their complements; inside a class `\d \w \s` only), `\n \t`, and a backslash before any other character for that character.
There are no counted repetitions `{m,n}`, no anchors and no groups that capture.  A pattern that does not parse (a stray `)`) is the empty set, which matches nothing.

## What is there

| group | functions |
|:--|:--|
| the expressions | `rxempty rxeps rxchar rxrange rxclass rxany` and the smart constructors `rxcat rxalt rxstar` (they simplify: ∅ and ε disappear, equal alternatives merge) |
| derivatives | `rxnullable` (does it match the empty string) `rxderiv(c, r)` `rxderivs(s, r)` `rxmatches(r, s)` |
| the parser | `rxparse` |
| matching | `rxfull(pattern, s)` (the whole string) `rxprefix` (the length of the longest matching prefix, a list of at most one number) `rxsearch` (the leftmost longest match, a list of at most one `pair(start, length)`) `rxfindall` `rxreplace(pattern, text, s)` `rxsplit` (non-empty matches only) |

The matches are the **leftmost longest** ones, as in POSIX: the language decides, not the order of the alternatives (`a|ab` finds `ab` in `xab`, where Python's `re` finds `a`).  Full
matches are the same in every implementation.

## Tests

`tests/test_regex.py` (496 checks): 60 random patterns over a grammar of atoms, classes, groups, unions and the three repetitions, each on random strings, `rxfull` against Python's
`re.fullmatch`, and the longest-match functions against definitions by brute force on top of `re.fullmatch`; the usual examples.
