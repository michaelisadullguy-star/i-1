# Compimo, the compiler of i-1

Pymo, Haskimo and Rustimo *interpret*: a program is read, class-checked and evaluated each time it runs.  **Compimo translates the program to C**, compiles it with a small run-time
system and runs the result.  It prints exactly the bytes that the interpreters print (`tests/conformance`: all 2218 cases conform) and is much faster where it matters: the arithmetic
on digit strings, which is almost all that i-1 ever does, is done on arrays of digits instead of lists of Booleans.

```
make compimo                        # cargo (std only) builds build/compimo; no Python anywhere in Compimo
build/compimo prelude               # once: the prelude (7000 definitions) is compiled into a shared library (3 minutes on 4 cores) and cached
build/compimo run examples/prove.hum.imo
build/compimo eval examples/target.hum.imo z 30          # run, check, translate, eval, text: the commands of the other cores
./i1 --impl compimo run program.hum.imo                   # through the dispatcher (named explicitly: it is not part of auto, both or all)
```
It needs a C compiler (gcc) and the Boehm collector (`libgc-dev`) at run time.  The cache is `~/.cache/compimo` (`$COMPIMO_CACHE`): `prelude-<hash>.so` for the prelude (the hash
covers the library files, the documents, the run-time system and the generator, so a changed library is recompiled automatically) and `user-<hash>.so` for a program (an unchanged
program is not compiled again).  `check` and `translate` do not compile anything: they are the front end of Rustimo, which Compimo shares.

## How it works

```
 source  ──front end (the one of Rustimo: readers, class checker, quoter)──►  de Bruijn terms, one per definition
         ──src/gen.rs──►  C   ──gcc──►  prelude-<hash>.so + user-<hash>.so  ──dlopen──►  evaluation   ──the printer of Rustimo──►  output
```
* **The front end and the printer are Rustimo's** (`compimo/src/main.rs` includes the files of `rustimo/src` by `#[path]`): the languages, the error messages and the output notations
  cannot differ.  The printer asks the run-time system for the same few things as the interpreters' decoders do (apply a value to markers, read a list, a pair, a Boolean).
* **A definition is a C function.**  A global lambda of arity n is `V pN(V a0, …)`; an application of a global to at least n arguments is a direct call.  A lazy argument is a *thunk*
  that captures exactly the variables it uses; a closed term is built once at start-up and shared.  Evaluation is call by need, as in the interpreters.
* **Constructors.**  A global of the form `λ f₁…fₙ k₁…kₘ. kⱼ f₁…fₙ` — the Booleans, the cells of lists, pairs, the constructors of the library's own data — is recognised
  (`classify`).  Applied to its n fields it is a *data object* at once (a header, a descriptor, the fields), and a pattern match is a selection: **the head applied to its
  alternatives is compiled to a switch** that enters the selected alternative as a function of the fields — no closure, no thunk, no generic application — and falls back to the
  general application when the head is not data.
* **Inlining.**  Small non-recursive functions (`∧ ¬ ⌃ ⌄ ∅ ⊻ ◀ ▶ concatmap …`) are inlined at their call sites; a variable that is moved under a binder is renumbered (the levels of
  the binders inside it shift), and a non-atomic argument is substituted only for a parameter that occurs once and not under a lambda, so that no work is repeated.  The pass walks every node once (its cost is
  linear in the size of the result) and copies a closed argument only when it is small (12 nodes): copies of a big one, made at every level of a nest of calls, make the term grow
  exponentially with the nesting (twelve nested queue operations, `tests/conformance/programs/misc/queue-chain.hum.imo`, once kept the compiler busy for more than a minute).
* **Natives.**  The functions of lib/number.imo that do the arithmetic on digit strings — `⊞ᶻ ⊟ᶻ ⊠ᶻ ⊖ᶻ ≡ ⊡ ∅ᶻ ⋚ʳ ⋚ⁱ` — have versions in the run-time system that work on arrays of
  digits (a *packed* list: one object that behaves as the cells it stands for).  They return **the same lists as the definitions, digit for digit**, zeros at the high end included:
  the adder and the subtractor are ports of the serial transducers `⊞ᶜ′` and `⊟ᶜ′` with their carry numerals, and the carry tables `⌕′ ⌕⁺ ⌕⁻` are *read from the definitions* when the
  prelude is generated; the multiplier is the recursion `⊠ᶻ ξ η = η (ζ ω ↦ ζ (⊞ᶻ ξ (𝕓 (⊠ᶻ ξ ω))) (𝕓 (⊠ᶻ ξ ω))) ⊥` run on arrays.  A native gives up — and the compiled definition
  runs — when its argument is not a plain list of Booleans (a list made by a lambda, an undetermined value, an error).  `build/compimo selftest` compares every native with the
  definition (`IMO_NONAT=1` switches the natives off) and with another core on random strings, including strings with zeros at the high end.
* **Start-up order.**  The prelude is compiled in shards (parallel C files).  Each shard first creates the objects of its globals, and **only after all the shards have done so** builds its closed terms (constants), because a constant may refer to a
  global that is defined further down the library and lives in a later shard (the list of all theories, `registry`, refers to packages that are defined in files loaded after it): built earlier, that reference would be an empty slot.
* **Memory.**  The Boehm collector; the evaluation runs on a thread with a stack of up to 16 GB (the depth of a recursion is limited by memory, as in the interpreters).

## Speed

Seconds on the same machine (4 cores), the program including its start-up (the front end alone takes 0.1 s):

| program | Rustimo | Compimo |
|:--|--:|--:|
| `checktheory("kolmogorov")` (the embedded theorems of the probability package, three events) | 10.4 | 0.7 |
| `checktheory("core")` | 1.4 | 0.2 |
| the theory suite `tests/test_theory.py` (879 checks, 6 programs of 150) | 126 | 25 (69 the first time: the six programs are compiled) |
| the container suite `tests/test_dict.py` (1357 cheap checks, 10 programs) | 5.8 | 11 (35 the first time) |

Where the time goes now (callgrind): allocation and the collector, the walk over lists that the natives still do when a list is not packed, and the thunks.

## Limits

* `serve` (the protocol of `tests/core_serve.py`) is not implemented, so the suites that need it run on the other cores; the suites that go through the command line (`lists strings dict theory classes`
  and the conformance suite) run on Compimo with `--core compimo`.
* A program is compiled when it is first run: a large one takes a few seconds of the C compiler (a batch of 150 checks: 4 to 8 s), and a cheap program that runs once is faster on an interpreter
  (the container suite above: 35 s the first time, against 5.8 s on Rustimo).  The compiled prelude is shared by all programs and the compiled program is cached by its text.
* A native handles digit strings of any length; the only limit is memory.

## Files

| file | content |
|:--|:--|
| `compimo/src/main.rs` | the command line (the commands of the other cores, `prelude`, `selftest`) |
| `compimo/src/core.rs` | the machine: translation, the C compiler, loading, the interface that the printer uses |
| `compimo/src/gen.rs` | de Bruijn terms → C: constructors, pattern matches, inlining, natives, the carry tables |
| `compimo/src/selftest.rs` | `compimo selftest` |
| `compimo/rt/imo_rt.c`, `imo_rt.h` | the run-time system: objects, thunks, application, errors, handles, packed digit strings, the natives |

Environment: `COMPIMO_CACHE` (the cache), `COMPIMO_CC` (the C compiler), `COMPIMO_CFLAGS` / `COMPIMO_PFLAGS` (flags for programs / for the prelude, default `-O1` / `-O2`), `COMPIMO_DUMP=file`
(write the C of the program), `IMO_NONAT=1` (no natives).
