# Lists, more (`lib/lists.imo`)

Sixty-five functions on lists and the combinators that go with them, written in spec notation (trusted prelude, part 23).  Inspired by the
list libraries of Haskell and of Pure (`takewhile`, `span`, `scanl`, `unfoldr`, `sortby`, `permutations`, …); every function is total,
lazy where laziness is possible, and written with the Scott encoding of lists, so it runs on base-(i − 1) digit strings like the rest of the library.

## Conventions

* A **maybe** is a list of at most one element: `[]` is nothing, `[x]` is just x.  `lookup`, `find`, `findindex`, `indexof`, `readnat`, `dget`
  return maybes, so `head`-like partial functions never fail: a program asks `isnil(r)`.
* A **predicate** `p` is `α → Bool`; an **order** `le` is `α → α → Bool` with `le(a, b)` meaning "a may stay before b".  Every function that
  compares takes the comparison as an argument (`…by`) — the language has no class of ordered types, only the classes ℕ ℤ ℚ and
  the overloads `maximum`, `minimum`, `sort`.
* Counters (`splitat`, `rotate`, `chunks`, `windows`, `applyn`, `combinations`) are natural numbers; internally they count down in base-(i − 1) digits (`∅ᶻ`, `⊟ᶻ`).
* The fold of an empty list without a start value (`foldl1`, `foldr1`) is `⊥` (false / 0), as the head of an empty list is.

## What is there

| group | functions |
|:--|:--|
| combinators | `ident const flip compose curry uncurry swap bimap until applyn` |
| taking apart | `init takewhile dropwhile span partition splitat tails inits rotate chunks windows` |
| folds, scans, unfolds | `foldl1 foldr1 scanl scanl1 scanr unfoldr concatmap intersperse intercalate count` |
| zipping | `zip3 zipwith3 unzip transposel cartesian` |
| searching | `lookup lookupby elemby find findindex nubby deleteby unionby intersectby diffby groupby isprefixby issuffixby isinfixby` |
| ordering | `sortby mergeby insertby maximumby minimumby maximum minimum` (merge sort: stable, O(n log n)) |
| combinatorics | `subsequences permutations combinations cycle` |
| numbers | `sumsq dotl mean tally` |

`permutations` lists the n! orderings in the order of the first choice (`[1,2,3]` gives `[1,2,3] [1,3,2] [2,1,3] [2,3,1] [3,1,2] [3,2,1]`), `subsequences` the
2ⁿ sublists with the first element changing fastest (`[1,2]` gives `[] [1] [2] [1,2]`), `combinations(k, xs)` the k-element sublists in order of position.
`transposel` skips short rows like Haskell's `transpose`.

## Tests

`tests/test_lists.py` (350 checks): every function against Python on random lists, edge cases included (empty lists, n = 0, n larger than the
list), through the command line of the core under test: the tests are human-notation programs, so the class declarations are checked too.
