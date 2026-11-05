# Characters and strings (`lib/strings.imo`)

Forty-seven functions on characters and strings (trusted prelude, part 24).  A string is a list of characters (`𝕊 = 𝔏 𝕮`) and a character is
a natural number, its code point (`𝕮 ⊆ ℕ`), so every list function (`reverse`, `filter`, `take`, `sortby`, …) is a string function.

| group | functions |
|:--|:--|
| classes of characters | `isdigit isuppercase islowercase isalpha isalnum isspace ispunct` |
| case | `upper lower toupper tolower capitalize` |
| trimming, splitting | `trim ltrim rtrim split splitstr words unwords lines` (`unlines` and `join` are in `lib/text.imo`) |
| searching | `startswith endswith contains indexof replace` |
| padding | `padleft padright padcenter repeatstr` |
| tests, ciphers | `ispalindrome isanagram caesar` |
| numbers as text | `showbase hex octal binary readbase readnat readint digitval` |
| Roman numerals | `roman fromroman` |
| edit distance, run lengths | `levenshtein rle unrle` |

* **Letters.**  `isuppercase`, `islowercase`, `upper`, `lower` cover ASCII, Latin-1 (with `ß`, `ÿ`), Greek and Cyrillic letters.  Case mapping is the
  offset 32 of all four alphabets; characters without a one-to-one mapping (`ß`, `ÿ`, the final sigma `ς`) stay as they are.
* **White space** is tab … carriage return, the space, the no-break space, U+2000 … U+200A and U+3000.  (`'\r'` in a literal is the letter r — the
  language has no escape for it — so the module writes code points as numerals.)
* `split(c, s)` and `splitstr(p, s)` keep empty fields, so `split(',', "a,,b")` is `["a", "", "b"]` and `split(',', "")` is `[""]`; `lines` drops the last empty
  line (`lines("a\n")` is `["a"]`).  `replace(s, p, r)` replaces the non-overlapping occurrences of `p` from the left; an empty `p` changes nothing.
* **Numbers.**  `showbase(n, b)` writes n in base 2 … 36 with lower-case digits; `readbase`, `readnat`, `readint` return maybes: `readnat("12x")` is `[]`, never an error.
* `rle("aaabcc")` is `"3a1b2c"` (decimal count, then the character); strings that contain digits are not allowed.

## Tests

`tests/test_strings.py` (767 checks): the character classes and case mappings against Python's tables on a pool of ASCII, Latin-1, Greek and Cyrillic
characters, and every other function against Python on random strings.
