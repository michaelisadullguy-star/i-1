"""test_dict.py -- lib/dict.imo (binary tries: dictionaries, finite sets, multisets, heaps, queues) against Python's dict, set, Counter,
heapq and deque, on random sequences of operations.   python3 tests/test_dict.py [--core pymo|haskimo|rustimo]"""
import collections, heapq, random, sys
from langtest import *

R = random.Random(777)
PZ = ('P', 'G', 'Z')                                   # (key in ℤ[i], value in ℤ)
LPZ = ('L', PZ); LG = ('L', 'G'); LZ = ('L', 'Z'); LN = ('L', 'N')
SORT_ITEMS = lambda e: f'sortby((a in Pair(\\Z, \\ZZ) |-> (b in Pair(\\Z, \\ZZ) |-> re(fst(a)) leq re(fst(b)))), {e})'
SORT_KEYS = lambda e: f'sortby((a in \\Z |-> (b in \\Z |-> re(a) leq re(b))), {e})'
SORT_VALS = lambda e: f'sortby((a in \\ZZ |-> (b in \\ZZ |-> a leq b)), {e})'
def key(): return R.randint(-20, 20)
def val(): return R.randint(-50, 50)

S = Suite('containers')
add = S.add

# ---- dictionaries: random sequences of puts and deletes
for t in range(30):
    d, e = {}, 'emptydict'
    for _ in range(R.randint(0, 14)):
        k = key()
        if R.random() < 0.7 or not d:
            v = val(); d[k] = v; e = f'dput({k}, {v}, {e})'
        else:
            k = R.choice(list(d)) if R.random() < 0.7 else k
            d.pop(k, None); e = f'ddel({k}, {e})'
    items = sorted(d.items())
    add(f'ditems {e[:60]}', SORT_ITEMS(f'ditems({e})'), LPZ, items)
    add(f'dkeys', SORT_KEYS(f'dkeys({e})'), LG, sorted(d))
    add(f'dvals', SORT_VALS(f'dvals({e})'), LZ, sorted(d.values()))
    add(f'dsize', f'dsize({e})', 'N', len(d))
    add(f'disempty', f'disempty({e})', 'B', not d)
    for k in (key(), key()):
        add(f'dget {k}', f'dget({k}, {e})', LZ, [d[k]] if k in d else [])
        add(f'dhas {k}', f'dhas({k}, {e})', 'B', k in d)
        add(f'dgetd {k}', f'dgetd({k}, 999, {e})', 'Z', d.get(k, 999))
    k, v = key(), val()
    d2 = dict(d); d2[k] = v + d.get(k, 0) if False else (v + d[k] if k in d else v)
    add(f'dwith + {k} {v}', SORT_ITEMS(f'ditems(dwith((x in \\ZZ |-> (y in \\ZZ |-> x + y)), {k}, {v}, {e}))'), LPZ, sorted(d2.items()))
    d3 = dict(d)
    if k in d3: d3[k] = d3[k] * 2
    add(f'dupdate {k}', SORT_ITEMS(f'ditems(dupdate((x in \\ZZ |-> x * 2), {k}, {e}))'), LPZ, sorted(d3.items()))
    add(f'dmap', SORT_ITEMS(f'ditems(dmap((x in \\ZZ |-> x * x), {e}))'), LPZ, sorted((a, b * b) for a, b in d.items()))
    add(f'dfilter', SORT_ITEMS(f'ditems(dfilter((x in \\ZZ |-> x gt 0), {e}))'), LPZ, sorted((a, b) for a, b in d.items() if b > 0))
    add(f'dfoldr', f'dfoldr((x in \\ZZ |-> (y in \\ZZ |-> x + y)), 0, {e})', 'Z', sum(d.values()))
    add(f'dfromlist', SORT_ITEMS(f'ditems(dfromlist({lit(list(d.items()), LPZ)}))'), LPZ, items)

# ---- two dictionaries
for t in range(15):
    da = {key(): val() for _ in range(R.randint(0, 9))}; db = {key(): val() for _ in range(R.randint(0, 9))}
    ea = f'dfromlist({lit(list(da.items()), LPZ)})'; eb = f'dfromlist({lit(list(db.items()), LPZ)})'
    add('dunion (left wins)', SORT_ITEMS(f'ditems(dunion({ea}, {eb}))'), LPZ, sorted({**db, **da}.items()))
    add('dunionwith -', SORT_ITEMS(f'ditems(dunionwith((x in \\ZZ |-> (y in \\ZZ |-> x - y)), {ea}, {eb}))'), LPZ, sorted({**db, **da, **{k: da[k] - db[k] for k in da if k in db}}.items()))
    add('dinter', SORT_ITEMS(f'ditems(dinter({ea}, {eb}))'), LPZ, sorted((k, v) for k, v in da.items() if k in db))
    add('ddiff', SORT_ITEMS(f'ditems(ddiff({ea}, {eb}))'), LPZ, sorted((k, v) for k, v in da.items() if k not in db))
    add('deq same', f'deq((x in \\ZZ |-> (y in \\ZZ |-> x == y)), {ea}, dfromlist({lit(list(reversed(list(da.items()))), LPZ)}))', 'B', True)
    add('deq different', f'deq((x in \\ZZ |-> (y in \\ZZ |-> x == y)), {ea}, {eb})', 'B', da == db)

# ---- arrays, string keys
for t in range(6):
    xs = [val() for _ in range(R.randint(0, 9))]
    add(f'dtovals (dfromvals {xs})', f'dtovals(dfromvals({lit(xs, LZ)}))', LZ, xs)
    add(f'dget in an array {xs}', f'dget(2, dfromvals({lit(xs, LZ)}))', LZ, xs[2:3])
words = ['alpha', 'beta', 'gamma', 'δ', 'ε-ζ', '', 'a b', 'λx']
for t in range(8):
    ws = R.sample(words, R.randint(0, 6)); e = 'emptydict'
    d = {}
    for w in ws:
        v = val(); d[w] = v; e = f'dputs({lit(w, "S")}, {v}, {e})'
    add(f'dkeyss {ws}', f'sortby((a in String |-> (b in String |-> length(a) leq length(b))), dkeyss({e}))', ('L', 'S'), sorted(d, key=len) if len(set(map(len, d))) == len(d) else None)
    for w in R.sample(words, 3):
        add(f'dgets {w!r}', f'dgets({lit(w, "S")}, {e})', LZ, [d[w]] if w in d else [])
        add(f'dhass {w!r}', f'dhass({lit(w, "S")}, {e})', 'B', w in d)
    if ws:
        w = ws[0]
        d.pop(w); add(f'ddels {w!r}', f'dhass({lit(w, "S")}, ddels({lit(w, "S")}, {e}))', 'B', False)
S.tests = [t for t in S.tests if t[3] is not None]

# ---- finite sets
for t in range(25):
    A = {key() for _ in range(R.randint(0, 10))}; B = {key() for _ in range(R.randint(0, 10))}
    ea = f'fsfromlist({lit(list(A), LG)})'; eb = f'fsfromlist({lit(list(B), LG)})'
    S_ = lambda e: SORT_KEYS(f'fselems({e})')
    add('fselems', S_(ea), LG, sorted(A)); add('fssize', f'fssize({ea})', 'N', len(A)); add('fsempty', f'fsempty({ea})', 'B', not A)
    x = key()
    add(f'fshas {x}', f'fshas({x}, {ea})', 'B', x in A)
    add(f'fsadd {x}', S_(f'fsadd({x}, {ea})'), LG, sorted(A | {x}))
    add(f'fsdel {x}', S_(f'fsdel({x}, {ea})'), LG, sorted(A - {x}))
    add('fsunion', S_(f'fsunion({ea}, {eb})'), LG, sorted(A | B))
    add('fsinter', S_(f'fsinter({ea}, {eb})'), LG, sorted(A & B))
    add('fsdiff', S_(f'fsdiff({ea}, {eb})'), LG, sorted(A - B))
    add('fssubset', f'fssubset({ea}, {eb})', 'B', A <= B)
    add('fssubset (of a union)', f'fssubset({ea}, fsunion({ea}, {eb}))', 'B', True)
    add('fseq', f'fseq({ea}, {eb})', 'B', A == B)
    add('fseq (reordered)', f'fseq({ea}, fsfromlist({lit(sorted(A, reverse=True), LG)}))', 'B', True)
    add('fsfilter', S_(f'fsfilter((x in \\Z |-> re(x) gt 0), {ea})'), LG, sorted(a for a in A if a > 0))
    add('fsmap', S_(f'fsmap((x in \\Z |-> x * x), {ea})'), LG, sorted({a * a for a in A}))
for A in ([], [1], [1, 2, 3], [4, 5, 6, 7]):
    add(f'fspowerset size {A}', f'length(fspowerset(fsfromlist({lit(A, LG)})))', 'N', 2 ** len(A))
add('fspowerset members are subsets', 'forall(s in FSet |-> fssubset(s, fsfromlist([1, 2, 3])), fspowerset(fsfromlist([1, 2, 3])))', 'B', True)

# ---- multisets
for t in range(12):
    xs = [R.randint(-4, 4) for _ in range(R.randint(0, 14))]; c = collections.Counter(xs)
    eb = f'bagfromlist({lit(xs, LG)})'
    add(f'bagitems {xs}', SORT_ITEMS(f'bagitems({eb})').replace('Pair(\\Z, \\ZZ)', 'Pair(\\Z, \\NN)'), ('L', ('P', 'G', 'N')), sorted(c.items()))
    add('bagsize', f'bagsize({eb})', 'N', len(xs))
    x = R.randint(-4, 4); n = R.randint(0, 3)
    add(f'bagcount {x}', f'bagcount({x}, {eb})', 'N', c[x])
    add(f'bagadd {x} {n}', f'bagcount({x}, bagadd({x}, {n}, {eb}))', 'N', c[x] + n)
    add(f'bagdel {x} {n}', f'bagcount({x}, bagdel({x}, {n}, {eb}))', 'N', max(0, c[x] - n))
    add(f'bagdel keeps the others', f'bagsize(bagdel({x}, {n}, {eb}))', 'N', len(xs) - min(n, c[x]))
    ys = [R.randint(-4, 4) for _ in range(R.randint(0, 8))]
    add('bagunion', f'bagsize(bagunion({eb}, bagfromlist({lit(ys, LG)})))', 'N', len(xs) + len(ys))

# ---- priority queues
for t in range(20):
    es = [(R.randint(-9, 9), R.randint(0, 99)) for _ in range(R.randint(0, 12))]
    eh = 'emptyheap'
    for p, v in es: eh = f'hpush({p}, {v}, {eh})'
    ps = sorted(p for p, _ in es)
    fstl = lambda e: f'map((x in Pair(\\QQ, \\NN) |-> fst(x)), {e})'
    add(f'htolist priorities {es}', fstl(f'htolist({eh})'), ('L', 'Q'), ps)
    add('htolist keeps the multiset of pairs', f'sortby((a in Pair(\\QQ, \\NN) |-> (b in Pair(\\QQ, \\NN) |-> fst(a) * 1000 + snd(a) leq fst(b) * 1000 + snd(b))), htolist({eh}))', ('L', ('P', 'Q', 'N')), sorted(es))
    add('hsize', f'hsize({eh})', 'N', len(es)); add('hempty', f'hempty({eh})', 'B', not es)
    add('hpeek', fstl(f'hpeek({eh})'), ('L', 'Q'), ps[:1])
    add('hpop', fstl(f'htolist(hpop({eh}))'), ('L', 'Q'), ps[1:])
    add('hfromlist', fstl(f'htolist(hfromlist({lit(es, ("L", ("P", "Q", "N")))}))'), ('L', 'Q'), ps)

# ---- queues
for t in range(20):
    ops, q, dq = [], 'emptyqueue', collections.deque()
    for _ in range(R.randint(0, 16)):
        if R.random() < 0.65 or not dq:
            v = R.randint(0, 99); dq.append(v); q = f'qpush({v}, {q})'
        else:
            dq.popleft(); q = f'qpop({q})'
    add('qtolist', f'qtolist({q})', LN, list(dq)); add('qsize', f'qsize({q})', 'N', len(dq)); add('qempty', f'qempty({q})', 'B', not dq)
    add('qpeek', f'qpeek({q})', LN, list(dq)[:1])
xs = [3, 1, 4]
add('qfromlist', f'qtolist(qfromlist({lit(xs, LN)}))', LN, xs)

sys.exit(0 if report(S) else 1)
