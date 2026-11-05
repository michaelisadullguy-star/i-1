# Containers (`lib/dict.imo`)

Dictionaries, finite sets, multisets, priority queues and queues (trusted prelude, part 25) — persistent, purely functional, and built on the
isomorphism that the language is about: **a key is its string of base-(i − 1) digits**.

## The trie

A dictionary is a binary trie over the digits of its keys, least significant digit first: the digit 0 goes to the left child, the digit 1 to the
right one, and a node holds the value of the key that ends there.  Lookup, insertion and deletion walk the digits and **compare nothing** — no order on
keys is needed and no arithmetic is done.  Empty branches are pruned, so a given set of keys has exactly one trie (equal contents are
structurally equal).  A key is a Gaussian integer (`ℤ[i]`: naturals, integers and Gaussian integers); strings go through `strnat`
(`dputs`, `dgets`, `dhass`, `ddels`, `dkeyss`).  Iteration (`ditems`, `dkeys`, `dvals`) is in trie order: the least significant digit decides first.

| class | meaning | operations |
|:--|:--|:--|
| `Dict(A)` | keys in ℤ[i], values in A | `emptydict dput dget dgetd dhas ddel dsize disempty ditems dkeys dvals dfromlist dmap dfilter dfoldr dwith dupdate dunion dunionwith dinter ddiff deq dfromvals dtovals` and the string-key versions |
| `FSet` | finite set of elements of ℤ[i] | `emptyfset fsadd fsdel fshas fssize fsempty fselems fsfromlist fsunion fsinter fsdiff fssubset fseq fsfilter fsmap fspowerset` |
| `Bag` | multiset: element → multiplicity | `emptybag bagadd bagdel bagcount bagsize bagfromlist bagitems bagunion` |
| `Heap(A)` | priority queue (leftist heap), smallest priority first | `emptyheap hpush hpeek hpop hsize hempty hfromlist htolist` |
| `Queue(A)` | first in, first out (front list + reversed rear list) | `emptyqueue qpush qpeek qpop qsize qempty qtolist qfromlist` |

* `dget` returns a **maybe** (`[]` or `[x]`); `dgetd(k, default, d)` returns the value or the default.
* `Dict`, `Heap` and `Queue` are **covariant** in their value class: the statement `(↗ Dict)` of `lib/dict.imo` declares it (the checkers of all cores accept `(↗ C)` for
  a class constructor C, and `Dict(\NN)` then fits where `Dict(\ZZ)` is expected).  `emptydict`, `emptyheap` and `emptyqueue` are polymorphic constants (`Dict α`).
* `dunion` keeps the value of the first dictionary on a common key, `dunionwith(f, a, b)` combines the two with `f`; `dfromvals(xs)` is an immutable array (key k holds the
  k-th element) and `dtovals` its inverse.
* Costs: an operation on a key of n digits takes O(n) steps (n = log₂ of the key); `dunion`, `dinter`, `ddiff` and `deq` are linear in the size of the smaller trie's
  shape; `hpush` and `hpop` are O(log n); `qpush` is O(1) and `qpop` is amortised O(1).

## Tests

`tests/test_dict.py` (1357 checks): random sequences of operations against Python's `dict`, `set`, `Counter`, `heapq` and `deque`, through the command
line of the core under test.
