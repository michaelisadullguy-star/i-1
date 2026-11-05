"""test_lists.py -- lib/lists.imo against Python oracles (lists, folds, scans, sorting, searching, combinatorics, combinators).
python3 tests/test_lists.py [--core pymo|haskimo|rustimo]"""
import functools, itertools, random, sys
from fractions import Fraction
from langtest import *

R = random.Random(20241104)
LZ = ('L', 'Z'); LLZ = ('L', LZ)
def zl(xs): return lit(xs, LZ)
def rnd(n_max=7, lo=-9, hi=9): return [R.randint(lo, hi) for _ in range(R.randint(0, n_max))]
def pred(k): return f'(x in \\ZZ |-> x gt {k})'
def fn2(op): return f'(a in \\ZZ |-> (b in \\ZZ |-> a {op} b))'
LE = '(a in \\ZZ |-> (b in \\ZZ |-> a leq b))'
EQ = '(a in \\ZZ |-> (b in \\ZZ |-> a == b))'
def lst(): return rnd()

S = Suite('lists, folds, scans, sorting, searching, combinatorics')
add = S.add
for t in range(6):
    xs, ys = lst(), lst(); k = R.randint(-3, 3); n = R.randint(0, 9)
    add(f'init {xs}', f'init({zl(xs)})', LZ, xs[:-1])
    add(f'takewhile {xs}', f'takewhile({pred(k)}, {zl(xs)})', LZ, list(itertools.takewhile(lambda x: x > k, xs)))
    add(f'dropwhile {xs}', f'dropwhile({pred(k)}, {zl(xs)})', LZ, list(itertools.dropwhile(lambda x: x > k, xs)))
    tw = list(itertools.takewhile(lambda x: x > k, xs)); dw = xs[len(tw):]
    add(f'span {xs}', f'span({pred(k)}, {zl(xs)})', ('P', LZ, LZ), (tw, dw))
    add(f'partition {xs}', f'partition({pred(k)}, {zl(xs)})', ('P', LZ, LZ), ([x for x in xs if x > k], [x for x in xs if not x > k]))
    add(f'splitat {n} {xs}', f'splitat({n}, {zl(xs)})', ('P', LZ, LZ), (xs[:n], xs[n:]))
    add(f'tails {xs}', f'tails({zl(xs)})', LLZ, [xs[i:] for i in range(len(xs) + 1)])
    add(f'inits {xs}', f'inits({zl(xs)})', LLZ, [xs[:i] for i in range(len(xs) + 1)])
    add(f'rotate {n} {xs}', f'rotate({n}, {zl(xs)})', LZ, xs if not xs else xs[n % len(xs):] + xs[:n % len(xs)])
    m = R.randint(0, 4)
    add(f'chunks {m} {xs}', f'chunks({m}, {zl(xs)})', LLZ, [] if m == 0 else [xs[i:i + m] for i in range(0, len(xs), m)])
    add(f'windows {m} {xs}', f'windows({m}, {zl(xs)})', LLZ, [[] for _ in range(len(xs) + 1)] if m == 0 else [xs[i:i + m] for i in range(len(xs) - m + 1)])
    if xs:
        add(f'foldl1 - {xs}', f'foldl1({fn2("-")}, {zl(xs)})', 'Z', functools.reduce(lambda a, b: a - b, xs))
        add(f'foldr1 - {xs}', f'foldr1({fn2("-")}, {zl(xs)})', 'Z', functools.reduce(lambda a, b: b - a, reversed(xs)))
        add(f'scanl1 + {xs}', f'scanl1({fn2("+")}, {zl(xs)})', LZ, list(itertools.accumulate(xs)))
    add(f'scanl - {xs}', f'scanl({fn2("-")}, 100, {zl(xs)})', LZ, list(itertools.accumulate(xs, lambda a, b: a - b, initial=100)))
    sr = [0]
    for x in reversed(xs): sr.insert(0, x - sr[0])
    add(f'scanr {xs}', f'scanr({fn2("-")}, 0, {zl(xs)})', LZ, sr)
    add(f'concatmap {xs}', f'concatmap((x in \\ZZ |-> [x, x * 2]), {zl(xs)})', LZ, [y for x in xs for y in (x, 2 * x)])
    add(f'intersperse {xs}', f'intersperse(0, {zl(xs)})', LZ, [y for i, x in enumerate(xs) for y in ((x,) if i == 0 else (0, x))])
    zs = [lst() for _ in range(R.randint(0, 3))]
    add(f'intercalate {zs}', f'intercalate([7, 8], {lit(zs, LLZ)})', LZ, [y for i, z in enumerate(zs) for y in ((z if i == 0 else [7, 8] + z))])
    add(f'count {xs}', f'count({pred(k)}, {zl(xs)})', 'N', sum(1 for x in xs if x > k))

# zipping, transposing, products
for t in range(4):
    a, b, c = lst(), lst(), lst()
    add(f'zip3 {a} {b} {c}', f'zip3({zl(a)}, {zl(b)}, {zl(c)})', ('L', ('P', 'Z', ('P', 'Z', 'Z'))), [(x, (y, z)) for x, y, z in zip(a, b, c)])
    add(f'zipwith3 {a} {b} {c}', f'zipwith3((x in \\ZZ |-> (y in \\ZZ |-> (z in \\ZZ |-> x + y * z))), {zl(a)}, {zl(b)}, {zl(c)})', LZ, [x + y * z for x, y, z in zip(a, b, c)])
    ps = [(R.randint(-3, 3), R.randint(0, 5)) for _ in range(R.randint(0, 5))]
    add(f'unzip {ps}', f'unzip({lit(ps, ("L", ("P", "Z", "N")))})', ('P', LZ, ('L', 'N')), ([p for p, _ in ps], [q for _, q in ps]))
    rows = [lst() for _ in range(R.randint(0, 4))]
    exp = []
    i = 0
    while True:
        col = [r[i] for r in rows if len(r) > i]
        if not col: break
        exp.append(col); i += 1
    add(f'transposel {rows}', f'transposel({lit(rows, LLZ)})', LLZ, exp)
    a2, b2 = rnd(3), rnd(3)
    add(f'cartesian {a2} {b2}', f'cartesian({zl(a2)}, {zl(b2)})', ('L', ('P', 'Z', 'Z')), [(x, y) for x in a2 for y in b2])

# searching
for t in range(6):
    xs = lst(); k = R.randint(-3, 3); x0 = R.randint(-9, 9)
    kv = [(R.randint(-3, 3), R.randint(0, 20)) for _ in range(R.randint(0, 5))]
    hit = [v for key, v in kv if key == x0 % 5 - 2]
    add(f'lookup {kv}', f'lookup({x0 % 5 - 2}, {lit(kv, ("L", ("P", "Z", "N")))})', ('L', 'N'), hit[:1])
    add(f'lookupby {kv}', f'lookupby({EQ}, {x0 % 5 - 2}, {lit(kv, ("L", ("P", "Z", "N")))})', ('L', 'N'), hit[:1])
    add(f'elemby {xs} {x0}', f'elemby({EQ}, {x0}, {zl(xs)})', 'B', x0 in xs)
    add(f'findindex {xs}', f'findindex({pred(k)}, {zl(xs)})', ('L', 'N'), [i for i, x in enumerate(xs) if x > k][:1])
    add(f'find {xs}', f'find({pred(k)}, {zl(xs)})', LZ, [x for x in xs if x > k][:1])
    nb = []
    for x in xs:
        if x not in nb: nb.append(x)
    add(f'nubby {xs}', f'nubby({EQ}, {zl(xs)})', LZ, nb)
    d = list(xs)
    if x0 in d: d.remove(x0)
    add(f'deleteby {xs} {x0}', f'deleteby({EQ}, {x0}, {zl(xs)})', LZ, d)
    ys = lst()
    add(f'unionby {xs} {ys}', f'unionby({EQ}, {zl(xs)}, {zl(ys)})', LZ, xs + [y for y in dict.fromkeys(ys) if y not in xs])
    add(f'intersectby {xs} {ys}', f'intersectby({EQ}, {zl(xs)}, {zl(ys)})', LZ, [x for x in xs if x in ys])
    add(f'diffby {xs} {ys}', f'diffby({EQ}, {zl(xs)}, {zl(ys)})', LZ, [x for x in xs if x not in ys])
    xs2 = [R.randint(0, 2) for _ in range(R.randint(0, 9))]
    add(f'groupby {xs2}', f'groupby({EQ}, {zl(xs2)})', LLZ, [list(g) for _, g in itertools.groupby(xs2)])
    pre = xs[:R.randint(0, len(xs))] if xs else []
    add(f'isprefixby {pre} {xs}', f'isprefixby({EQ}, {zl(pre)}, {zl(xs)})', 'B', xs[:len(pre)] == pre)
    add(f'isprefixby {ys} {xs}', f'isprefixby({EQ}, {zl(ys)}, {zl(xs)})', 'B', xs[:len(ys)] == ys)
    add(f'issuffixby {ys} {xs}', f'issuffixby({EQ}, {zl(ys)}, {zl(xs)})', 'B', len(ys) <= len(xs) and xs[len(xs) - len(ys):] == ys)
    sub = xs[1:3]
    add(f'isinfixby {sub} {xs}', f'isinfixby({EQ}, {zl(sub)}, {zl(xs)})', 'B', any(xs[i:i + len(sub)] == sub for i in range(len(xs) - len(sub) + 1)))

# order
for t in range(6):
    xs = lst(); ys = sorted(lst())
    add(f'sortby {xs}', f'sortby({LE}, {zl(xs)})', LZ, sorted(xs))
    add(f'sortby > {xs}', f'sortby((a in \\ZZ |-> (b in \\ZZ |-> a geq b)), {zl(xs)})', LZ, sorted(xs, reverse=True))
    ps = [(R.randint(0, 3), i) for i in range(R.randint(0, 8))]          # stability: sort pairs by the first component only
    add(f'sortby stable {ps}', f'sortby((a in Pair(\\ZZ, \\NN) |-> (b in Pair(\\ZZ, \\NN) |-> fst(a) leq fst(b))), {lit(ps, ("L", ("P", "Z", "N")))})', ('L', ('P', 'Z', 'N')), sorted(ps, key=lambda p: p[0]))
    add(f'mergeby {xs} {ys}', f'mergeby({LE}, {zl(sorted(xs))}, {zl(ys)})', LZ, sorted(xs + ys))
    x0 = R.randint(-9, 9)
    add(f'insertby {x0} {ys}', f'insertby({LE}, {x0}, {zl(ys)})', LZ, sorted(ys + [x0]))
    if xs:
        add(f'maximumby {xs}', f'maximumby({LE}, {zl(xs)})', 'Z', max(xs))
        add(f'minimumby {xs}', f'minimumby({LE}, {zl(xs)})', 'Z', min(xs))
        add(f'maximum {xs}', f'maximum({zl(xs)})', 'Z', max(xs))
        add(f'minimum {xs}', f'minimum({zl(xs)})', 'Z', min(xs))

# combinatorics
for xs in ([], [1], [1, 2], [1, 2, 3], [3, 1, 2, 4], [1, 1, 2]):
    add(f'subsequences {xs}', f'subsequences({zl(xs)})', LLZ, [[xs[i] for i in range(len(xs)) if m >> i & 1] for m in range(2 ** len(xs))])
    add(f'permutations {xs}', f'permutations({zl(xs)})', LLZ, [list(p) for p in itertools.permutations(xs)])
    for k in range(0, len(xs) + 2):
        add(f'combinations {k} {xs}', f'combinations({k}, {zl(xs)})', LLZ, [list(c) for c in itertools.combinations(xs, k)])
for xs in ([1], [1, 2], [3, 1, 2]):
    add(f'cycle {xs}', f'take(8, cycle({zl(xs)}))', LZ, [xs[i % len(xs)] for i in range(8)])
add('cycle []', 'take(3, cycle([]))', LZ, [])

# numbers
for t in range(5):
    xs, ys = lst(), lst()
    add(f'sumsq {xs}', f'sumsq({zl(xs)})', 'Z', sum(x * x for x in xs))
    add(f'dotl {xs} {ys}', f'dotl({zl(xs)}, {zl(ys)})', 'Z', sum(x * y for x, y in zip(xs, ys)))
    add(f'mean {xs}', f'mean({zl(xs)})', 'Q', Fraction(sum(xs), len(xs)) if xs else 0)
    add(f'tally {xs}', f'tally({zl(xs)})', ('L', ('P', 'Z', 'N')), [(v, xs.count(v)) for v in sorted(set(xs))])

# combinators
add('ident', 'ident(7)', 'N', 7)
add('const', 'const(3, "x")', 'N', 3)
add('flip', 'flip((a in \\ZZ |-> (b in \\ZZ |-> a - b)), 2, 10)', 'Z', 8)
add('compose', 'compose((a in \\ZZ |-> a * 2), (b in \\ZZ |-> b + 1), 5)', 'Z', 12)
add('curry', 'curry((p in Pair(\\ZZ, \\ZZ) |-> fst(p) - snd(p)), 9, 4)', 'Z', 5)
add('uncurry', 'uncurry((a in \\ZZ |-> (b in \\ZZ |-> a - b)), pair(9, 4))', 'Z', 5)
add('swap', 'swap(pair(1, "a"))', ('P', 'S', 'N'), ('a', 1))
add('bimap', 'bimap((a in \\ZZ |-> a + 1), (b in \\ZZ |-> b * 2), pair(3, 4))', ('P', 'Z', 'Z'), (4, 8))
add('until', 'until((a in \\ZZ |-> a gt 100), (b in \\ZZ |-> b * 2), 3)', 'Z', 192)
for n in (0, 1, 5):
    add(f'applyn {n}', f'applyn({n}, (a in \\ZZ |-> a * 2), 3)', 'Z', 3 * 2 ** n)
add('unfoldr', 'unfoldr((n in \\NN |-> if(n == 0, [], [pair(n * n, n - 1)])), 5)', ('L', 'N'), [25, 16, 9, 4, 1])

sys.exit(0 if report(S) else 1)
