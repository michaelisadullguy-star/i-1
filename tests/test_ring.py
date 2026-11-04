"""test_ring.py -- ring theory (lib/ring.imo) used from the HUMAN notation: every statement goes through doc 2, overload resolution and the
class checker, is evaluated in the language, decoded, and compared with an independent python computation (brute force over Z/n, Fraction
polynomial arithmetic, a dictionary-based multivariate division algorithm and Buchberger's algorithm written here, textbook examples).
python3 tests/test_ring.py"""
import os, sys, random, itertools, math
from math import gcd
from functools import reduce
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()
rng = random.Random(20261026)

# ------------------------------------------------------------------------------------------------ python reference: Z/n
def r_units(n): return [a for a in range(n) if gcd(a, n) == 1]
def r_zd(n): return [a for a in range(1, n) if gcd(a, n) != 1]
def rad(n):
    r, m, p = 1, n, 2
    while m > 1:
        if m % p == 0:
            r *= p
            while m % p == 0: m //= p
        p += 1
    return r
def r_nil(n): return [a for a in range(n) if a % rad(n) == 0]
def r_idem(n): return [a for a in range(n) if (a * a - a) % n == 0]
def r_ideal(n, gens): d = reduce(gcd, gens, n); return [k * d for k in range(n // d)]
def r_primes(n): return [p for p in range(2, n + 1) if n % p == 0 and all(p % q for q in range(2, p))]

# ------------------------------------------------------------------------------------------------ python reference: polynomials in one variable (lowest degree first)
def F(x): return Fr(x)
def trim(p):
    p = [F(c) for c in p]
    while p and p[-1] == 0: p.pop()
    return p
def padd(p, q):
    n = max(len(p), len(q)); p, q = [F(c) for c in p], [F(c) for c in q]
    return trim([(p[k] if k < len(p) else 0) + (q[k] if k < len(q) else 0) for k in range(n)])
def pneg(p): return [-F(c) for c in trim(p)]
def pmul(p, q):
    p, q = trim(p), trim(q)
    if not p or not q: return []
    out = [Fr(0)] * (len(p) + len(q) - 1)
    for a, x in enumerate(p):
        for b, y in enumerate(q): out[a + b] += x * y
    return trim(out)
def pdivmod(p, q):
    p, q = trim(p), trim(q)
    if not q: return [], p
    quo = [Fr(0)] * max(len(p) - len(q) + 1, 0); r = list(p); inv = 1 / q[-1]
    while len(r) >= len(q):
        c = r[-1] * inv; k = len(r) - len(q); quo[k] = c
        for j, y in enumerate(q): r[k + j] -= c * y
        r = trim(r)
    return trim(quo), r
def pmonic(p): p = trim(p); return [c / p[-1] for c in p] if p else []
def pgcd(p, q):
    p, q = trim(p), trim(q)
    while q: p, q = q, pdivmod(p, q)[1]
    return pmonic(p)
def plcm(p, q):
    if not trim(p) or not trim(q): return []
    return pmonic(pdivmod(pmul(p, q), pgcd(p, q))[0])
def ppow_mod(p, n, m):
    r = [Fr(1)]
    for _ in range(n): r = pdivmod(pmul(r, p), m)[1]
    return r
def pinv_mod(a, f):
    """the inverse of a modulo f, [] if there is none (extended Euclid with exact fractions)"""
    r0, r1, s0, s1 = trim(f), pdivmod(a, f)[1], [], [Fr(1)]
    while r1:
        q, r = pdivmod(r0, r1)
        r0, r1, s0, s1 = r1, r, s1, padd(s0, pneg(pmul(q, s1)))
    if len(r0) != 1: return []
    return pdivmod([c / r0[0] for c in s0], f)[1]
def ph(p):
    """a python polynomial as a human list literal"""
    def one(c):
        c = F(c); t = str(c.numerator) + (f"/{c.denominator}" if c.denominator != 1 else "")
        return f"({t} in \\Q)" if c.denominator != 1 else (f"({t})" if c < 0 else t)
    return "[" + ", ".join(one(c) for c in p) + "]"
def rpoly(deg_max=3, lo=-3, hi=3):
    d = rng.randint(1, deg_max)
    p = [rng.randint(lo, hi) for _ in range(d)] + [rng.choice([1, 2, 3, -1, -2])]
    return p

# ------------------------------------------------------------------------------------------------ python reference: multivariate polynomials
# a polynomial is a dict {exponent tuple: Fraction}; orders as keys (decreasing = greater)
def key(o, e):
    if o == 0: return tuple(e)
    if o == 1: return (sum(e), tuple(e))
    return (sum(e), tuple(-x for x in reversed(e)))
def mnorm(d): return {e: c for e, c in d.items() if c != 0}
def madd(p, q):
    r = dict(p)
    for e, c in q.items(): r[e] = r.get(e, 0) + c
    return mnorm(r)
def mscale(c, p): return mnorm({e: c * x for e, x in p.items()})
def mmulterm(c, e, p): return {tuple(a + b for a, b in zip(e, f)): c * x for f, x in p.items()}
def mmul(p, q):
    r = {}
    for e, c in p.items():
        for f, x in q.items():
            k = tuple(a + b for a, b in zip(e, f)); r[k] = r.get(k, 0) + c * x
    return mnorm(r)
def lm(o, p): return max(p, key=lambda e: key(o, e))
def mdiv_ref(o, p, Fs):
    p = dict(p); q = [dict() for _ in Fs]; r = {}
    while p:
        e = lm(o, p); c = p[e]
        for i, f in enumerate(Fs):
            if not f: continue
            g = lm(o, f)
            if all(a <= b for a, b in zip(g, e)):
                t = tuple(b - a for a, b in zip(g, e)); k = c / f[g]
                q[i] = madd(q[i], {t: k}); p = madd(p, mscale(-1, mmulterm(k, t, f))); break
        else:
            r[e] = c; del p[e]
    return q, r
def spoly_ref(o, f, g):
    a, b = lm(o, f), lm(o, g); m = tuple(max(x, y) for x, y in zip(a, b))
    return madd(mmulterm(1 / f[a], tuple(x - y for x, y in zip(m, a)), f), mscale(-1, mmulterm(1 / g[b], tuple(x - y for x, y in zip(m, b)), g)))
def groebner_ref(o, Fs):
    G = [mscale(1 / f[lm(o, f)], f) for f in Fs if f]
    pairs = [(i, j) for j in range(len(G)) for i in range(j)]
    while pairs:
        i, j = pairs.pop(0)
        s = mdiv_ref(o, spoly_ref(o, G[i], G[j]), G)[1]
        if s:
            G.append(mscale(1 / s[lm(o, s)], s)); pairs += [(k, len(G) - 1) for k in range(len(G) - 1)]
    # minimal
    keep = []
    for k, g in enumerate(G):
        if not any(j != k and all(a <= b for a, b in zip(lm(o, h), lm(o, g))) and (lm(o, h) != lm(o, g) or j < k) for j, h in enumerate(G)): keep.append(g)
    red = []
    for k, g in enumerate(keep):
        others = keep[:k] + keep[k + 1:]
        r = mdiv_ref(o, g, others)[1]; red.append(mscale(1 / r[lm(o, r)], r))
    return sorted(red, key=lambda g: key(o, lm(o, g)))
def mh(p, o):
    """a python multivariate polynomial as a human list of terms"""
    def one(c): t = str(c.numerator) + (f"/{c.denominator}" if c.denominator != 1 else ""); return f"({t})" if c < 0 else t
    return "[" + ", ".join(f"pair({one(c)}, [{', '.join(map(str, e))}])" for e, c in sorted(p.items(), key=lambda t: key(o, t[0]), reverse=True)) + "]"
def mstr(o, p):
    if not p: return "0"
    names = "xyzwuv"; out = ""
    for k, e in enumerate(sorted(p, key=lambda e: key(o, e), reverse=True)):
        c = p[e]
        mono = "*".join((names[j] if x == 1 else f"{names[j]}^{x}") for j, x in enumerate(e) if x)
        a = abs(c); cs = str(a.numerator) + (f"/{a.denominator}" if a.denominator != 1 else "")
        body = cs if not mono else (mono if a == 1 else f"{cs}*{mono}")
        out += ("-" if c < 0 else "") + body if k == 0 else (" - " if c < 0 else " + ") + body
    return out
def rmp(nv, nt=3, deg=3, coef=3):
    p = {}
    for _ in range(nt):
        e = tuple(rng.randint(0, deg) for _ in range(nv))
        if sum(e) <= deg: p[e] = p.get(e, 0) + Fr(rng.choice([c for c in range(-coef, coef + 1) if c]))
    return mnorm(p) or {tuple([0] * nv): Fr(1)}

# ------------------------------------------------------------------------------------------------ the program
STM = []
def st(name, cls, expr): STM.append((name, cls, expr))

ZN = [1, 2, 6, 8, 12, 16, 30, 36]
for n in ZN:
    st(f'zu{n}', "List(\\NN)", f"zunits({n})"); st(f'zd{n}', "List(\\NN)", f"zzerodivisors({n})")
    st(f'zn{n}', "List(\\NN)", f"znilpotents({n})"); st(f'zi{n}', "List(\\NN)", f"zidempotents({n})")
    st(f'zs{n}', "List(List(\\NN))", f"zideals({n})"); st(f'zm{n}', "List(List(\\NN))", f"zmaxideals({n})")
st('zg1', "List(\\NN)", "zideal(12, [8, 18])"); st('zg2', "List(\\NN)", "zideal(30, [])"); st('zg3', "List(\\NN)", "zideal(30, [7])")
st('am1', "\\NN", "addmod(7, 9, 12)"); st('am2', "\\NN", "submod(3, 9, 12)"); st('am3', "\\NN", "mulmod(7, 9, 12)"); st('am4', "\\NN", "negmod(5, 12)")
st('am5', "\\NN", "addmod(-7, -9, 12)"); st('am6', "\\NN", "mulmod(-7, 9, 12)")
st('is1', "\\NN", "idealsum(12, 18)"); st('is2', "\\NN", "idealintersect(12, 18)"); st('is3', "\\NN", "idealproduct(12, -18)")
st('is4', "Bool", "idealcontains(3, 12)"); st('is5', "Bool", "idealcontains(12, 3)"); st('is6', "\\NN", "idealradical(72)")
# ideals of polynomials, quotient rings, CRT
PP = []
for _ in range(6):
    PP.append((rpoly(), rpoly()))
PP.append(([-1, 0, 1], [1, 2, 1])); PP.append(([0, 0, 1], [0, 1])); PP.append(([1, 1], []))
for k, (a, b) in enumerate(PP):
    st(f'ps{k}', "List(\\Q)", f"polyidealsum({ph(a)}, {ph(b)})"); st(f'pt{k}', "List(\\Q)", f"polyidealintersect({ph(a)}, {ph(b)})")
    st(f'pp{k}', "List(\\Q)", f"polyidealproduct({ph(a)}, {ph(b)})"); st(f'pc{k}', "Bool", f"polyidealcontains({ph(a)}, {ph(b)})")
    st(f'pr{k}', "List(\\Q)", f"polyidealradical({ph(pmul(a, b))})")
st('pg1', "List(\\Q)", "polyidealgen([[-1, 0, 1], [1, 2, 1]])"); st('pg2', "List(\\Q)", "polyidealgen([])")
st('pm1', "Bool", "polyidealmember([0, 1, 1], [[-1, 0, 1], [1, 2, 1]])"); st('pm2', "Bool", "polyidealmember([-1, 1], [[-1, 0, 1], [1, 2, 1]])")
QF = [([-2, 0, 1], [1, 1]), ([-2, 0, 1], [3, -1, 2]), ([-1, 0, 1], [1, 1]), ([1, 0, 1], [0, 1]), ([2, 0, 0, 1], [1, 1, 1]), ([-2, 0, 1], []), ([1, 0, 1], [(Fr(1, 2))])]
for k, (f, a) in enumerate(QF):
    st(f'qa{k}', "List(\\Q)", f"qradd({ph(f)}, {ph(a)}, {ph([1, 2, 3, 4])})"); st(f'qm{k}', "List(\\Q)", f"qrmul({ph(f)}, {ph(a)}, {ph([1, 2, 3, 4])})")
    st(f'qi{k}', "List(\\Q)", f"qrinv({ph(f)}, {ph(a)})"); st(f'qu{k}', "Bool", f"qrisunit({ph(f)}, {ph(a)})")
    st(f'qp{k}', "List(\\Q)", f"qrpow({ph(f)}, {ph(a)}, 5)"); st(f'qn{k}', "List(\\Q)", f"qrpow({ph(f)}, {ph(a)}, -2)")
    st(f'qr{k}', "List(\\Q)", f"qrreduce({ph(f)}, {ph([1, 2, 3, 4, 5])})"); st(f'qs{k}', "List(\\Q)", f"qrsub({ph(f)}, {ph(a)}, {ph([1, 2, 3, 4])})")
    st(f'qg{k}', "List(\\Q)", f"qrneg({ph(f)}, {ph(a)})"); st(f'qd{k}', "\\NN", f"qrdimension({ph(f)})")
st('qf1', "Bool", "qrisfield([-2, 0, 1])"); st('qf2', "Bool", "qrisfield([-1, 0, 1])"); st('qf3', "Bool", "qrisfield([1, 0, 0, 1])")
CRT = [([[1], [2]], [[-1, 1], [-2, 1]]), ([[3], [1, 1], [0]], [[1, 1], [-1, 0, 1], [0, 1]]), ([[0, 1], [1]], [[1, 0, 1], [1, 1]]),
       ([[1], [2]], [[-1, 1], [-1, 1]])]
for k, (rs, ms) in enumerate(CRT):
    st(f'cr{k}', "List(\\Q)", f"polycrt([{', '.join(ph(r) for r in rs)}], [{', '.join(ph(m) for m in ms)}])")
# multivariate
MP = [{(2, 0): Fr(3), (0, 1): Fr(-1), (0, 0): Fr(1, 2), (1, 1): Fr(2)}, {(1, 0, 2): Fr(1), (0, 3, 0): Fr(-2), (1, 1, 1): Fr(1, 3)}, {}, {(0, 0): Fr(5)}]
st('ms1', "String", f"mpstr(1, {mh(MP[0], 1)})"); st('ms2', "String", f"mpstr(0, {mh(MP[1], 0)})"); st('ms3', "String", "mpstr(1, [])")
st('ms4', "String", f"mpstr(2, {mh(MP[1], 2)})"); st('ms5', "String", f"mpstr(1, {mh(MP[3], 1)})")
st('ms6', "String", "mpstr(1, [pair(1, [1, 0]), pair(-1, [0, 0])])"); st('ms7', "String", "mpstr(1, [pair(-1, [1, 0]), pair(i, [0, 1])])")
st('ms8', "String", "mpstr(1, [pair(1, [0, 0, 0, 0, 0, 0, 7])])")
st('mo1', "List(Pair(\\Q, List(\\NN)))", "mpoly(0, [pair(1, [0, 1]), pair(2, [1, 0]), pair(3, [1, 0]), pair(-5, [1, 0])])")
st('mo2', "List(Pair(\\Q, List(\\NN)))", "mpoly(1, [pair(1, [1]), pair(1, [0, 2]), pair(2, [2, 0])])")
RMP = []
for k in range(5):
    nv = rng.choice([2, 3]); a, b = rmp(nv), rmp(nv); o = rng.choice([0, 1, 2]); RMP.append((nv, o, a, b))
    st(f'ma{k}', "List(Pair(\\Q, List(\\NN)))", f"mpadd({o}, {mh(a, o)}, {mh(b, o)})"); st(f'mb{k}', "List(Pair(\\Q, List(\\NN)))", f"mpsub({o}, {mh(a, o)}, {mh(b, o)})")
    st(f'mc{k}', "List(Pair(\\Q, List(\\NN)))", f"mpmul({o}, {mh(a, o)}, {mh(b, o)})"); st(f'md{k}', "List(Pair(\\Q, List(\\NN)))", f"mppow({o}, {mh(a, o)}, 2)")
    st(f'me{k}', "List(Pair(\\Q, List(\\NN)))", f"mpneg({o}, {mh(a, o)})"); st(f'mf{k}', "List(Pair(\\Q, List(\\NN)))", f"mpscale({o}, 1/3, {mh(a, o)})")
    st(f'mg{k}', "\\Q", f"mpeval({mh(a, o)}, {ph([2, -1, Fr(1, 2)][:nv])})"); st(f'mh{k}', "\\ZZ", f"mpdegree({mh(a, o)})")
    st(f'mi{k}', "List(Pair(\\Q, List(\\NN)))", f"mpderiv({o}, {mh(a, o)}, {rng.randrange(nv)})")
    st(f'mj{k}', "\\Q", f"mplc({o}, {mh(a, o)})"); st(f'mk{k}', "List(\\NN)", f"mplm({o}, {mh(a, o)})")
    st(f'ml{k}', "List(Pair(\\Q, List(\\NN)))", f"mpsubst({o}, {mh(a, o)}, 0, {mh(b, o)})")
st('mz1', "\\ZZ", "mpdegree([])"); st('mz2', "\\Q", "mplc(1, [])"); st('mz3', "List(\\NN)", "mplm(1, [])")
# division
DIV = []
for k in range(5):
    nv = rng.choice([2, 3]); o = rng.choice([0, 1, 2]); p = rmp(nv, 5, 4); Fs = [rmp(nv, 2, 2) for _ in range(rng.choice([1, 2, 3]))]
    DIV.append((nv, o, p, Fs))
    st(f'dv{k}', "Pair(List(List(Pair(\\Q, List(\\NN)))), List(Pair(\\Q, List(\\NN))))", f"mpdivide({o}, {mh(p, o)}, [{', '.join(mh(f, o) for f in Fs)}])")
    st(f'dr{k}', "List(Pair(\\Q, List(\\NN)))", f"mpreduce({o}, {mh(p, o)}, [{', '.join(mh(f, o) for f in Fs)}])")
st('dv9', "Pair(List(List(Pair(\\Q, List(\\NN)))), List(Pair(\\Q, List(\\NN))))",
   "mpdivide(1, [pair(1, [2, 1]), pair(1, [1, 2]), pair(1, [0, 2])], [[pair(1, [1, 1]), pair(-1, [0, 0])], [pair(1, [0, 2]), pair(-1, [0, 0])]])")
# S-polynomials and Groebner bases
SP = [(0, {(2, 1): Fr(1), (0, 0): Fr(-1)}, {(1, 2): Fr(1), (0, 0): Fr(-1)}), (1, {(3, 0): Fr(1), (1, 1): Fr(-2)}, {(2, 1): Fr(1), (0, 2): Fr(-2), (1, 0): Fr(1)})]
for k, (o, f, g) in enumerate(SP): st(f'sp{k}', "List(Pair(\\Q, List(\\NN)))", f"spoly({o}, {mh(f, o)}, {mh(g, o)})")
st('sp9', "List(Pair(\\Q, List(\\NN)))", f"spoly(1, [], {mh(SP[0][1], 1)})")
GBS = [(0, [{(2, 0): Fr(1), (0, 2): Fr(1), (0, 0): Fr(-1)}, {(1, 0): Fr(1), (0, 1): Fr(-1)}]),
       (1, [{(2, 0): Fr(1), (0, 1): Fr(1)}, {(1, 1): Fr(1), (0, 0): Fr(1)}]),
       (1, [{(3, 0): Fr(1), (1, 1): Fr(-2)}, {(2, 1): Fr(1), (0, 2): Fr(-2), (1, 0): Fr(1)}]),
       (0, [{(2, 0, 0): Fr(1), (0, 1, 0): Fr(1), (0, 0, 1): Fr(1), (0, 0, 0): Fr(-1)}, {(0, 2, 0): Fr(1), (1, 0, 0): Fr(1), (0, 0, 1): Fr(1), (0, 0, 0): Fr(-1)},
            {(0, 0, 2): Fr(1), (1, 0, 0): Fr(1), (0, 1, 0): Fr(1), (0, 0, 0): Fr(-1)}]),
       (2, [{(2, 0, 0): Fr(1), (0, 1, 0): Fr(1), (0, 0, 1): Fr(1), (0, 0, 0): Fr(-1)}, {(0, 2, 0): Fr(1), (1, 0, 0): Fr(1), (0, 0, 1): Fr(1), (0, 0, 0): Fr(-1)},
            {(0, 0, 2): Fr(1), (1, 0, 0): Fr(1), (0, 1, 0): Fr(1), (0, 0, 0): Fr(-1)}]),
       (0, [{(1, 0): Fr(1), (0, 2): Fr(-1)}, {(0, 1): Fr(1), (0, 2): Fr(-1), (0, 0): Fr(1)}]),
       (1, [{(1, 1): Fr(1), (0, 0): Fr(-1)}, {(1, 0): Fr(1), (0, 1): Fr(1)}, {(0, 1): Fr(1), (0, 0): Fr(1)}]),
       (0, [{(1, 0): Fr(1), (0, 0): Fr(1)}, {(1, 0): Fr(2), (0, 0): Fr(2)}]),
       (1, [{(1, 0): Fr(1)}, {(0, 0): Fr(1)}]), (1, [{}])]
for _ in range(2):
    nv = 2; o = rng.choice([0, 1, 2]); GBS.append((o, [rmp(nv, 3, 3, 2) for _ in range(2)]))
for k, (o, Fs) in enumerate(GBS):
    lit = "[" + ", ".join(mh(f, o) for f in Fs) + "]"
    st(f'gb{k}', "List(List(Pair(\\Q, List(\\NN))))", f"groebner({o}, {lit})"); st(f'rg{k}', "List(List(Pair(\\Q, List(\\NN))))", f"reducedgroebner({o}, {lit})")
    st(f'ig{k}', "Bool", f"isgroebner({o}, groebner({o}, {lit}))"); st(f'is{k}x', "Bool", f"isgroebner({o}, {lit})")
st('im1', "Bool", "idealmember(1, [pair(1, [3, 0]), pair(-1, [1, 0])], [[pair(1, [2, 0]), pair(-1, [0, 0])]])")
st('im2', "Bool", "idealmember(1, [pair(1, [1, 0]), pair(-1, [0, 0])], [[pair(1, [2, 0]), pair(-1, [0, 0])]])")
st('im3', "Bool", "idealmember(0, [pair(1, [1, 0, 0]), pair(-1, [0, 0, 1])], [[pair(1, [1, 0, 0]), pair(-1, [0, 1, 0])], [pair(1, [0, 1, 0]), pair(-1, [0, 0, 1])]])")
st('im4', "Bool", "idealmember(0, [pair(1, [1, 0, 0]), pair(-1, [0, 0, 0])], [[pair(1, [1, 0, 0]), pair(-1, [0, 1, 0])], [pair(1, [0, 1, 0]), pair(-1, [0, 0, 1])]])")
st('im5', "Bool", "idealmember(1, [], [[pair(1, [1, 0])]])")
st('ie1', "Bool", "idealequal(1, [[pair(1, [1, 0]), pair(1, [0, 0])]], [[pair(1, [1, 0]), pair(1, [0, 0])], [pair(1, [2, 0]), pair(-1, [0, 0])]])")
st('ie2', "Bool", "idealequal(1, [[pair(1, [1, 0]), pair(1, [0, 0])]], [[pair(1, [2, 0]), pair(-1, [0, 0])]])")
st('el1', "List(List(Pair(\\Q, List(\\NN))))", "eliminate(1, [[pair(1, [1, 0]), pair(-1, [0, 2])], [pair(1, [0, 1]), pair(-1, [0, 2]), pair(1, [0, 0])]])")
st('el2', "List(List(Pair(\\Q, List(\\NN))))", "eliminate(1, [[pair(1, [1, 0, 0]), pair(-1, [0, 1, 0])], [pair(1, [0, 1, 0]), pair(-1, [0, 0, 1])]])")
st('el3', "List(List(Pair(\\Q, List(\\NN))))", "eliminate(2, [[pair(1, [1, 0, 0]), pair(-1, [0, 1, 0])], [pair(1, [0, 1, 0]), pair(-1, [0, 0, 1])]])")

def main():
    SRC = "\n".join(f"{n} in {c} := {e}" for n, c, e in STM)
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'ring.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("the test program passes the class checker", not errs, str(errs[:2]))
    if errs: return rep.done()
    P.build(); E = Env(P)
    V = lambda n: E.V(P.hum.spec_name(n))
    nat = lambda v: int(E.dq(v).r)
    def tx(n): return ''.join(chr(int(E.dq(c).r)) for c in E.lst(V(n)))
    def ql(n): return trim([E.dq(c).r for c in E.lst(V(n))])
    def ns(n): return [nat(c) for c in E.lst(V(n))]
    def nss(n): return [[nat(c) for c in E.lst(l)] for l in E.lst(V(n))]
    def term(v): p, d = to_pair(v); return tuple(nat(x) for x in E.lst(d)), E.dq(p).r
    def mp(v): return {e: c for e, c in (term(t) for t in E.lst(v))}
    def mpn(n): return mp(V(n))
    def eqp(a, b): return all(x == y for x, y in zip(a, b)) and len(a) == len(b)
    # ---- Z/n
    bad = []
    for n in ZN:
        if ns(f'zu{n}') != r_units(n): bad.append(('units', n))
        if ns(f'zd{n}') != r_zd(n): bad.append(('zerodivisors', n))
        if ns(f'zn{n}') != r_nil(n): bad.append(('nilpotents', n))
        if ns(f'zi{n}') != r_idem(n): bad.append(('idempotents', n))
        divs = [d for d in range(1, n + 1) if n % d == 0]
        if nss(f'zs{n}') != [r_ideal(n, [d]) for d in divs]: bad.append(('ideals', n))
        if nss(f'zm{n}') != [r_ideal(n, [p]) for p in r_primes(n)]: bad.append(('maximal ideals', n))
    rep("zunits, zzerodivisors, znilpotents, zidempotents, zideals, zmaxideals for n in " + str(ZN) + " (brute force)", not bad, str(bad[:4]))
    rep("zideal: the ideal of Z/n generated by integers (gcd with n); no generators: the zero ideal", ns('zg1') == r_ideal(12, [8, 18]) and ns('zg2') == [0] and ns('zg3') == r_ideal(30, [7]))
    rep("addmod, submod, mulmod, negmod (negative arguments too)", [nat(V(k)) for k in ('am1', 'am2', 'am3', 'am4', 'am5', 'am6')] == [4, 6, 3, 7, 8, 9])
    rep("idealsum, idealintersect, idealproduct, idealcontains, idealradical on Z", [nat(V('is1')), nat(V('is2')), nat(V('is3'))] == [6, 36, 216] and E.b(V('is4')) is True and E.b(V('is5')) is False and nat(V('is6')) == 6)
    # ---- ideals of polynomials, quotient rings
    bad = []
    for k, (a, b) in enumerate(PP):
        if not eqp(ql(f'ps{k}'), pgcd(a, b) if trim(a) and trim(b) else pmonic(a if trim(a) else b)): bad.append(('sum', k))
        if not eqp(ql(f'pt{k}'), plcm(a, b)): bad.append(('intersect', k))
        if not eqp(ql(f'pp{k}'), pmonic(pmul(a, b))): bad.append(('product', k))
        want = (not trim(b)) if not trim(a) else not pdivmod(b, a)[1]
        if E.b(V(f'pc{k}')) != want: bad.append(('contains', k))
        pr = pmul(a, b)
        if not eqp(ql(f'pr{k}'), pmonic(pdivmod(pr, pgcd(pr, [i * c for i, c in enumerate(pr)][1:]))[0]) if trim(pr) else []): bad.append(('radical', k))
    rep("polyidealsum / intersect / product / contains / radical against gcd, lcm, product, remainder, f / gcd(f, f') on 9 pairs", not bad, str(bad[:4]))
    rep("polyidealgen of a list; polyidealmember", eqp(ql('pg1'), [Fr(1), Fr(1)]) and ql('pg2') == [] and E.b(V('pm1')) is True and E.b(V('pm2')) is False)
    bad = []
    for k, (f, a) in enumerate(QF):
        a4 = [1, 2, 3, 4]
        if not eqp(ql(f'qa{k}'), pdivmod(padd(a, a4), f)[1]): bad.append(('add', k))
        if not eqp(ql(f'qs{k}'), pdivmod(padd(a, pneg(a4)), f)[1]): bad.append(('sub', k))
        if not eqp(ql(f'qg{k}'), pdivmod(pneg(a), f)[1]): bad.append(('neg', k))
        if not eqp(ql(f'qm{k}'), pdivmod(pmul(a, a4), f)[1]): bad.append(('mul', k))
        inv = pinv_mod(a, f)
        if not eqp(ql(f'qi{k}'), inv): bad.append(('inv', k))
        if E.b(V(f'qu{k}')) != bool(inv): bad.append(('isunit', k))
        if not eqp(ql(f'qp{k}'), ppow_mod(a, 5, f)): bad.append(('pow', k))
        if not eqp(ql(f'qn{k}'), ppow_mod(inv, 2, f) if inv else []): bad.append(('neg pow', k))
        if not eqp(ql(f'qr{k}'), pdivmod([1, 2, 3, 4, 5], f)[1]): bad.append(('reduce', k))
        if nat(V(f'qd{k}')) != len(f) - 1: bad.append(('dim', k))
    rep("qradd, qrsub, qrneg, qrmul, qrinv, qrisunit, qrpow (also negative), qrreduce, qrdimension in Q[x]/(f) for 7 (f, a)", not bad, str(bad[:4]))
    rep("qrisfield: x^2 - 2 and x^3 + 1... irreducibility of the modulus", [E.b(V('qf1')), E.b(V('qf2')), E.b(V('qf3'))] == [True, False, False])
    bad = []
    for k, (rs, ms) in enumerate(CRT):
        got = ql(f'cr{k}'); coprime = all(len(pgcd(ms[i], ms[j])) == 1 for i in range(len(ms)) for j in range(i))
        if not coprime: ok = got == []
        else:
            ok = all(not pdivmod(padd(got, pneg(r)), m)[1] for r, m in zip(rs, ms)) and len(got) <= sum(len(m) - 1 for m in ms)
        if not ok: bad.append(k)
    rep("polycrt: the residues are met modulo every modulus, degree below the sum of the degrees; [] for moduli that are not coprime", not bad, str(bad))
    # ---- multivariate polynomials
    rep("mpstr: signs, coefficients +-1 omitted, powers, fractions, the constant, the zero polynomial, a complex coefficient, the variable x6",
        tx('ms1') == mstr(1, MP[0]) and tx('ms2') == mstr(0, MP[1]) and tx('ms3') == "0" and tx('ms4') == mstr(2, MP[1]) and tx('ms5') == "5"
        and tx('ms6') == "x - 1" and tx('ms8') == "x6^7" and tx('ms7') == "-x + (i)*y", str([tx(k) for k in ('ms1', 'ms2', 'ms3', 'ms4', 'ms5', 'ms6', 'ms7', 'ms8')]))
    rep("mpoly: like terms merged, zero terms dropped, sorted decreasingly, exponents padded", mpn('mo1') == {(0, 1): Fr(1)} and mpn('mo2') == {(1, 0): Fr(1), (0, 2): Fr(1), (2, 0): Fr(2)}
        and [t[0] for t in map(term, E.lst(V('mo2')))] == [(2, 0), (0, 2), (1, 0)])
    bad = []
    for k, (nv, o, a, b) in enumerate(RMP):
        if mpn(f'ma{k}') != madd(a, b): bad.append(('add', k))
        if mpn(f'mb{k}') != madd(a, mscale(-1, b)): bad.append(('sub', k))
        if mpn(f'mc{k}') != mmul(a, b): bad.append(('mul', k))
        if mpn(f'md{k}') != mmul(a, a): bad.append(('pow', k))
        if mpn(f'me{k}') != mscale(-1, a): bad.append(('neg', k))
        if mpn(f'mf{k}') != mscale(Fr(1, 3), a): bad.append(('scale', k))
        pt = [Fr(2), Fr(-1), Fr(1, 2)][:nv]
        if E.dq(V(f'mg{k}')).r != sum(c * math.prod(x ** n for x, n in zip(pt, e)) for e, c in a.items()): bad.append(('eval', k))
        if nat(V(f'mh{k}')) != max(sum(e) for e in a): bad.append(('degree', k))
        lme = lm(o, a)
        if E.dq(V(f'mj{k}')).r != a[lme] or [nat(x) for x in E.lst(V(f'mk{k}'))] != list(lme): bad.append(('lc/lm', k))
        # the derivative with respect to the variable named in the statement (read back from the text of the statement)
        stmt = [s for s in STM if s[0] == f'mi{k}'][0][2]; j = int(stmt.rsplit(',', 1)[1].strip(' )'))
        der = mnorm({tuple(x - (1 if i == j else 0) for i, x in enumerate(e)): c * e[j] for e, c in a.items() if e[j]})
        if mpn(f'mi{k}') != der: bad.append(('deriv', k))
        # substitution of x0 by b
        sub = {}
        for e, c in a.items():
            base = mmulterm(c, tuple(0 if i == 0 else x for i, x in enumerate(e)), {tuple([0] * nv): Fr(1)})
            pw = {tuple([0] * nv): Fr(1)}
            for _ in range(e[0]): pw = mmul(pw, b)
            sub = madd(sub, mmul(base, pw))
        if mpn(f'ml{k}') != sub: bad.append(('subst', k))
    rep("mpadd, mpsub, mpmul, mppow, mpneg, mpscale, mpeval, mpdegree, mplc, mplm, mpderiv, mpsubst against dictionary arithmetic (5 random pairs in 2-3 variables, all three orders)", not bad, str(bad[:4]))
    rep("mpdegree of the zero polynomial is -1; its leading coefficient 0 and leading monomial []", int(E.dq(V('mz1')).r) == -1 and E.dq(V('mz2')).r == 0 and [nat(x) for x in E.lst(V('mz3'))] == [])
    # ---- division
    bad = []
    for k, (nv, o, p, Fs) in enumerate(DIV):
        qs, r = to_pair(V(f'dv{k}')); qs = [mp(q) for q in E.lst(qs)]; r = mp(r)
        total = dict(r)
        for q, f in zip(qs, Fs): total = madd(total, mmul(q, f))
        rem_ok = all(not any(all(a <= b for a, b in zip(lm(o, f), e)) for f in Fs) for e in r)
        lm_ok = all(not q or key(o, tuple(a + b for a, b in zip(lm(o, q), lm(o, f)))) <= key(o, lm(o, p)) for q, f in zip(qs, Fs))
        ref_q, ref_r = mdiv_ref(o, p, Fs)
        if not (total == p and rem_ok and lm_ok and r == ref_r and qs == ref_q and mpn(f'dr{k}') == ref_r): bad.append((k, total == p, rem_ok, lm_ok))
    rep("mpdivide / mpreduce: p = sum q_k f_k + r, no term of r divisible by a leading monomial, lm(q_k f_k) <= lm(p), equal to the reference division algorithm (5 random cases)", not bad, str(bad))
    q9, r9 = to_pair(V('dv9'))
    rep("mpdivide: Cox-Little-O'Shea example x^2 y + x y^2 + y^2 by (x y - 1, y^2 - 1): quotients x + y and 1, remainder x + y + 1",
        [mp(q) for q in E.lst(q9)] == [{(1, 0): Fr(1), (0, 1): Fr(1)}, {(0, 0): Fr(1)}] and mp(r9) == {(1, 0): Fr(1), (0, 1): Fr(1), (0, 0): Fr(1)})
    # ---- S-polynomials and Groebner bases
    ok = all(mpn(f'sp{k}') == spoly_ref(o, f, g) for k, (o, f, g) in enumerate(SP)) and mpn('sp9') == {}
    rep("spoly: two textbook pairs against the reference; a zero polynomial gives []", ok)
    bad = []
    for k, (o, Fs) in enumerate(GBS):
        ref = groebner_ref(o, Fs)
        got = [mp(g) for g in E.lst(V(f'rg{k}'))]
        if got != ref: bad.append(('reduced', k, len(got), len(ref)))
        gb = [mp(g) for g in E.lst(V(f'gb{k}'))]
        if not E.b(V(f'ig{k}')): bad.append(('isgroebner(groebner)', k))
        # every generator reduces to 0 modulo the computed basis, and the basis is contained in the ideal (all elements reduce to 0 modulo the reference basis)
        if not all(not mdiv_ref(o, f, gb)[1] for f in Fs): bad.append(('F in <G>', k))
        if not all(not mdiv_ref(o, g, ref)[1] for g in gb): bad.append(('G in <F>', k))
    rep("groebner / reducedgroebner / isgroebner: 11 ideals in 2-3 variables, all three orders (reduced basis equal to Buchberger's algorithm in the reference, the unit ideal, the zero ideal, redundant generators)", not bad, str(bad[:4]))
    # a non-Groebner generating set is recognised, a Groebner one is
    rep("isgroebner: {x^2 + y, x y + 1} is not a Groebner basis (grlex), the reduced basis is", E.b(V('is1x')) is False and E.b(V('ig1')) is True)
    rep("idealmember / idealequal: x^3 - x in (x^2 - 1); x - 1 is not; x - z in (x - y, y - z); x - 1 is not; 0 is in every ideal; (x + 1) = (x + 1, x^2 - 1) but not (x^2 - 1)",
        [E.b(V(k)) for k in ('im1', 'im2', 'im3', 'im4', 'im5', 'ie1', 'ie2')] == [True, False, True, False, True, True, False])
    el1 = [mp(g) for g in E.lst(V('el1'))]; el2 = [mp(g) for g in E.lst(V('el2'))]; el3 = [mp(g) for g in E.lst(V('el3'))]
    rep("eliminate: x = y^2, y = y^2 - 1... eliminating x leaves y^2 - y - 1; for (x - y, y - z) eliminating x leaves y - z, eliminating x and y leaves nothing",
        el1 == [{(0, 2): Fr(1), (0, 1): Fr(-1), (0, 0): Fr(-1)}] and el2 == [{(0, 1, 0): Fr(1), (0, 0, 1): Fr(-1)}] and el3 == [])
    return rep.done()

sys.exit(0 if run_big(main) else 1)
