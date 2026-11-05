"""test_combin.py -- lib/combin.imo (libsrc/combin.hum.imo): enumerative combinatorics against independent oracles: math.comb and math.perm, inclusion-exclusion for the derangements, the explicit formula for the
Eulerian numbers, brute force over itertools.permutations (descents, fixed points, ranks), brute force over words (Dyck and Lyndon words, compositions, partitions), and the recurrences of Motzkin and Schroeder numbers.
python3 tests/test_combin.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import itertools, math, random, sys
from langtest import *

R = random.Random(20261112)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('enumerative combinatorics')
add = S.add
LN = ('L', 'N'); LLN = ('L', LN); LLLN = ('L', LLN); LS = ('L', 'S')
fact = math.factorial

for m in range(0, 9):
    add(f'pascalrow {m}', f'pascalrow({m})', LN, [math.comb(m, k) for k in range(m + 1)])
for m in range(0, 7):
    add(f'pascaltriangle {m}', f'pascaltriangle({m})', LLN, [[math.comb(r, k) for k in range(r + 1)] for r in range(m)])
add('pascalrow 20', 'pascalrow(20)', LN, [math.comb(20, k) for k in range(21)])
for t in range(n(12)):
    ks = [R.randint(0, 5) for _ in range(R.randint(0, 5))]
    add(f'multinomial {ks}', f'multinomial({lit(ks, LN)})', 'N', fact(sum(ks)) // math.prod(fact(k) for k in ks))
for a in range(0, 7):
    for b in range(0, 6):
        add(f'multichoose {a} {b}', f'multichoose({a}, {b})', 'N', math.comb(a + b - 1, b) if a > 0 else (1 if b == 0 else 0))
        add(f'fallingfactorial {a} {b}', f'fallingfactorial({a}, {b})', 'N', math.perm(a, b))
        add(f'risingfactorial {a} {b}', f'risingfactorial({a}, {b})', 'N', math.prod(a + i for i in range(b)))

def derange(m): return sum((-1) ** j * fact(m) // fact(j) for j in range(m + 1))
for m in list(range(0, 12)) + [20]:
    add(f'derangements {m}', f'derangements({m})', 'N', derange(m))
for m in range(0, 7):
    perms = list(itertools.permutations(range(m)))
    for k in range(0, m + 1):
        add(f'rencontres {m} {k}', f'rencontres({m}, {k})', 'N', sum(1 for p in perms if sum(1 for i in range(m) if p[i] == i) == k))
add('rencontres 3 5', 'rencontres(3, 5)', 'N', 0)

def euler(m, k): return sum((-1) ** j * math.comb(m + 1, j) * (k + 1 - j) ** m for j in range(k + 2))
for m in range(0, 8):
    add(f'eulerianrow {m}', f'eulerianrow({m})', LN, [1] if m == 0 else [euler(m, k) for k in range(m)])
    for k in range(0, m + 2):
        want = sum(1 for p in itertools.permutations(range(m)) if sum(1 for i in range(m - 1) if p[i] > p[i + 1]) == k) if m <= 6 else (euler(m, k) if k < m else 0)
        add(f'eulerian {m} {k}', f'eulerian({m}, {k})', 'N', want)
add('eulerianrow 12', 'eulerianrow(12)', LN, [euler(12, k) for k in range(12)])

def dyck(m):
    out = []
    for w in itertools.product('UD', repeat=2 * m):
        h, ok = 0, True
        for c in w:
            h += 1 if c == 'U' else -1
            if h < 0: ok = False; break
        if ok and h == 0: out.append(''.join(w))
    return sorted(out)
for m in range(0, 7):
    ws = dyck(m)
    add(f'dyckpaths {m}', f'dyckpaths({m})', LS, ws)
    for k in range(0, m + 2):
        add(f'narayana {m} {k}', f'narayana({m}, {k})', 'N', sum(1 for w in ws if w.count('UD') == k) if m > 0 else 0)
add('length of dyckpaths 8 is the Catalan number', 'length(dyckpaths(8))', 'N', math.comb(16, 8) // 9)

mot = [1, 1]
for m in range(2, 26): mot.append(((2 * m + 1) * mot[m - 1] + (3 * m - 3) * mot[m - 2]) // (m + 2))
sch = [1, 2]
for m in range(2, 26): sch.append((3 * (2 * m - 1) * sch[m - 1] - (m - 2) * sch[m - 2]) // (m + 1))
for m in list(range(0, 14)) + [25]:
    add(f'motzkin {m}', f'motzkin({m})', 'N', mot[m])
    add(f'schroeder {m}', f'schroeder({m})', 'N', sch[m])

def comps(m):
    out = []
    for mask in range(2 ** max(m - 1, 0)):
        cur, parts = 1, []
        for i in range(m - 1):
            if mask >> i & 1: parts.append(cur); cur = 1
            else: cur += 1
        out.append(parts + [cur]) if m > 0 else None
    return sorted(out) if m > 0 else [[]]
def parts(m, mx=None):
    mx = m if mx is None else mx
    if m == 0: return [[]]
    return [[k] + r for k in range(min(m, mx), 0, -1) for r in parts(m - k, k)]
def parts_indep(m):
    seen = set()
    def go(rem, mx, cur):
        if rem == 0: seen.add(tuple(cur)); return
        for k in range(1, min(rem, mx) + 1): go(rem - k, k, cur + [k])
    go(m, m, []); return sorted((list(p) for p in seen), reverse=True)
for m in range(0, 9):
    add(f'compositions {m}', f'compositions({m})', LLN, comps(m))
for m in range(0, 11):
    assert parts(m) == parts_indep(m)
    add(f'partitionlist {m}', f'partitionlist({m})', LLN, parts(m))
for m in (12, 15):
    add(f'length of partitionlist {m} is partitions {m}', f'length(partitionlist({m}))', 'N', len(parts(m)))
    add(f'partitions {m}', f'partitions({m})', 'N', len(parts(m)))

def lyndon(m, k):
    out = []
    for w in itertools.product(range(k), repeat=m):
        if m > 0 and all(w < w[i:] + w[:i] for i in range(1, m)): out.append(list(w))
    return sorted(out)
for (m, k) in [(1, 1), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (3, 3), (4, 3), (2, 4), (3, 4), (5, 3), (0, 3), (4, 0), (7, 2)]:
    add(f'lyndonwords {m} {k}', f'lyndonwords({m}, {k})', LLN, lyndon(m, k))

def lehmer(p): return [sum(1 for j in range(i + 1, len(p)) if p[j] < p[i]) for i in range(len(p))]
for t in range(n(25)):
    m = R.randint(0, 7); p = list(range(m)); R.shuffle(p)
    allp = list(itertools.permutations(range(m)))
    r = allp.index(tuple(p))
    add(f'lehmer {p}', f'lehmer({lit(p, LN)})', LN, lehmer(p))
    add(f'unlehmer of lehmer {p}', f'unlehmer(lehmer({lit(p, LN)}))', LN, p)
    add(f'permrank {p}', f'permrank({lit(p, LN)})', 'N', r)
    add(f'permunrank {m} {r}', f'permunrank({m}, {r})', LLN, [p])
    add(f'nextperm {p}', f'nextperm({lit(p, LN)})', LLN, [list(allp[r + 1])] if r + 1 < len(allp) else [])
    inv = sum(1 for i in range(m) for j in range(i + 1, m) if p[i] > p[j])
    add(f'inversions {p}', f'inversions({lit(p, LN)})', 'N', inv)
    add(f'descents {p}', f'descents({lit(p, LN)})', 'N', sum(1 for i in range(m - 1) if p[i] > p[i + 1]))
    add(f'permsign {p}', f'permsign({lit(p, LN)})', 'Z', (-1) ** inv)
add('permunrank out of range', 'permunrank(3, 6)', LLN, [])
add('permunrank 0 0', 'permunrank(0, 0)', LLN, [[]])
add('nextperm of the last', 'nextperm([3, 2, 1, 0])', LLN, [])
add('nextperm of the empty list', 'nextperm([])', LLN, [])

def setparts(xs):
    if not xs: return [[]]
    x, out = xs[0], []
    for q in setparts(xs[1:]):
        out.append([[x]] + q)
        for i in range(len(q)): out.append(q[:i] + [[x] + q[i]] + q[i + 1:])
    return out
def rgs_sets(m):
    out = set()
    def go(i, cur, mx):
        if i == m: out.add(frozenset(frozenset(j for j in range(m) if cur[j] == b) for b in range(mx))); return
        for b in range(mx + 1): go(i + 1, cur + [b], max(mx, b + 1))
    go(0, [], 0); return out
for m in range(0, 7):
    sp = setparts(list(range(m)))
    assert {frozenset(frozenset(b) for b in P) for P in sp} == rgs_sets(m) and len(sp) == len(rgs_sets(m))
    add(f'setpartitions {m}', f'setpartitions({lit(list(range(m)), LN)})', LLLN, sp)
add('length of setpartitions 7 is bell 7', f'length(setpartitions({lit(list(range(7)), LN)}))', 'N', 877)
add('setpartitions of letters', 'setpartitions(["a", "b", "c"])', ('L', ('L', LS)), setparts(['a', 'b', 'c']))

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
