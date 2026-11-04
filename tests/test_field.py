"""test_field.py -- field theory (lib/field.imo) used from the HUMAN notation: every statement goes through doc 2, overload resolution and
the class checker, is evaluated in the language, decoded, and compared with an independent python computation (polynomials over GF(p) by
lists and trial division, GF(p^n) by polynomial arithmetic modulo the modulus, number-field norms by Sylvester determinants, algebraic
numbers by the numerical roots of f and g).
python3 tests/test_field.py"""
import os, sys, random, itertools, math, cmath
from math import gcd
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()
rng = random.Random(20261027)

# ------------------------------------------------------------------------------------------------ reference: polynomials over GF(p)
def tr(f):
    f = list(f)
    while f and f[-1] == 0: f.pop()
    return f
def P(p, f): return tr([c % p for c in f])
def padd(p, f, g):
    n = max(len(f), len(g)); return tr([((f[i] if i < len(f) else 0) + (g[i] if i < len(g) else 0)) % p for i in range(n)])
def pneg(p, f): return tr([(-c) % p for c in f])
def psub(p, f, g): return padd(p, f, pneg(p, g))
def pmul(p, f, g):
    if not f or not g: return []
    r = [0] * (len(f) + len(g) - 1)
    for i, a in enumerate(f):
        for j, b in enumerate(g): r[i + j] = (r[i + j] + a * b) % p
    return tr(r)
def pdivmod(p, f, g):
    f, g = P(p, f), P(p, g)
    if not g: return [], f
    q = [0] * max(len(f) - len(g) + 1, 0); inv = pow(g[-1], -1, p)
    while len(f) >= len(g) and f:
        c = f[-1] * inv % p; k = len(f) - len(g); q[k] = c
        f = psub(p, f, [0] * k + [c * x % p for x in g])
    return tr(q), f
def pmonic(p, f):
    f = P(p, f); return [c * pow(f[-1], -1, p) % p for c in f] if f else []
def pgcd(p, f, g):
    f, g = P(p, f), P(p, g)
    while g: f, g = g, pdivmod(p, f, g)[1]
    return pmonic(p, f)
def ppowmod(p, f, n, m):
    r = pdivmod(p, [1], m)[1]; b = pdivmod(p, f, m)[1]
    while n:
        if n & 1: r = pdivmod(p, pmul(p, r, b), m)[1]
        b = pdivmod(p, pmul(p, b, b), m)[1]; n >>= 1
    return r
def pder(p, f): return tr([i * c % p for i, c in enumerate(f)][1:])
def peval(p, f, a):
    r = 0
    for c in reversed(f): r = (r * a + c) % p
    return r
def monics(p, d):
    for t in itertools.product(range(p), repeat=d): yield list(t) + [1]
def is_irred_ref(p, f):
    f = P(p, f); n = len(f) - 1
    if n < 1: return False
    for d in range(1, n // 2 + 1):
        for g in monics(p, d):
            if not pdivmod(p, f, g)[1]: return False
    return True
IRR = {}
def irreds(p, d):
    if (p, d) not in IRR: IRR[(p, d)] = [g for g in monics(p, d) if is_irred_ref(p, g)]
    return IRR[(p, d)]
def factor_ref(p, f):
    f = P(p, f)
    if not f: return 0, []
    c = f[-1]; f = pmonic(p, f); out = []
    for d in range(1, len(f)):
        for g in irreds(p, d):
            k = 0
            while len(f) >= len(g) and not pdivmod(p, f, g)[1] and len(f) > 1:
                f = pdivmod(p, f, g)[0]; k += 1
            if k: out.append((g, k))
        if len(f) == 1: break
    out.sort(key=lambda t: (len(t[0]), list(reversed(t[0]))))
    return c, out
def ph(f): return "[" + ", ".join(str(c) for c in f) + "]"
def poly_value(k, p, n): return [(k // p ** j) % p for j in range(n)]

# ------------------------------------------------------------------------------------------------ reference: GF(p^n)
class GFr:
    def __init__(self, p, m): self.p, self.m, self.n = p, list(m), len(m) - 1
    def red(self, a): return pdivmod(self.p, a, self.m)[1]
    def add(self, a, b): return padd(self.p, a, b)
    def sub(self, a, b): return psub(self.p, a, b)
    def mul(self, a, b): return self.red(pmul(self.p, a, b))
    def pw(self, a, e):
        if e < 0: a = self.inv(a); e = -e
        r = [1]
        for _ in range(e): r = self.mul(r, a)
        return r
    def inv(self, a):
        for b in self.elements():
            if self.mul(a, b) == [1]: return b
        return []
    def elements(self):
        if not hasattr(self, '_el'): self._el = [tr(poly_value(k, self.p, self.n)) for k in range(self.p ** self.n)]
        return self._el
    def order(self, a):
        if not a: return 0
        x, k = a, 1
        while x != [1]: x = self.mul(x, a); k += 1
        return k
    def conj(self, a): return [self.pw(a, self.p ** k) for k in range(self.n)]

def ref_irreducible_poly(p, n):
    k = 0
    while True:
        f = poly_value(k, p, n) + [1]
        if is_irred_ref(p, f): return f
        k += 1
def ref_primitive_poly(p, n):
    k = 0
    while True:
        f = poly_value(k, p, n) + [1]
        if is_irred_ref(p, f) and (n > 1 or True):
            x = [0, 1] if n > 1 else [(-f[0]) % p]
            if n == 1 and not x[0]: k += 1; continue
            F = GFr(p, f)
            if F.order(F.red([0, 1])) == p ** n - 1: return f
        k += 1

# ------------------------------------------------------------------------------------------------ the program
STM = []
def st(name, cls, expr): STM.append((name, cls, expr))
NN, LN = "\\NN", "List(\\NN)"

# ---- polynomials over GF(p)
FPP = [2, 3, 5, 7]
POLY = []
for k in range(8):
    p = rng.choice(FPP); f = P(p, [rng.randrange(p) for _ in range(rng.randint(2, 6))]); g = P(p, [rng.randrange(p) for _ in range(rng.randint(1, 5))])
    if not f: f = [1, 1]
    if not g: g = [1]
    POLY.append((p, f, g))
    st(f'pa{k}', LN, f"fpadd({p}, {ph(f)}, {ph(g)})"); st(f'ps{k}', LN, f"fpsub({p}, {ph(f)}, {ph(g)})"); st(f'pm{k}', LN, f"fpmul({p}, {ph(f)}, {ph(g)})")
    st(f'pd{k}', f"Pair({LN}, {LN})", f"fpdivmod({p}, {ph(f)}, {ph(g)})"); st(f'pq{k}', LN, f"fpquo({p}, {ph(f)}, {ph(g)})"); st(f'pr{k}', LN, f"fprem({p}, {ph(f)}, {ph(g)})")
    st(f'pg{k}', LN, f"fpgcd({p}, {ph(f)}, {ph(g)})"); st(f'pe{k}', f"Pair({LN}, Pair({LN}, {LN}))", f"fpegcd({p}, {ph(f)}, {ph(g)})")
    st(f'pw{k}', LN, f"fppowmod({p}, {ph(f)}, {rng.randint(0, 40)}, {ph(g)})"); st(f'pv{k}', LN, f"fpderiv({p}, {ph(f)})")
    st(f'px{k}', NN, f"fpeval({p}, {ph(f)}, {rng.randrange(p)})"); st(f'py{k}', LN, f"fproots({p}, {ph(f)})")
    st(f'pn{k}', LN, f"fpscale({p}, {rng.randrange(1, p)}, {ph(f)})"); st(f'po{k}', LN, f"fpneg({p}, {ph(f)})"); st(f'pp{k}', LN, f"fpmonic({p}, {ph(f)})")
st('pz1', LN, "fpoly(5, [7, 10, -3, 5])"); st('pz2', LN, "fpadd(3, [1, 2], [2, 1])"); st('pz3', "\\ZZ", "fpdegree(fpoly(3, [3, 6]))")
st('pz4', f"Pair({LN}, {LN})", "fpdivmod(5, [1, 2, 3], [])"); st('pz5', LN, "fpgcd(5, [], [])"); st('pz6', LN, "fpgcd(7, [2, 4], [])")
# irreducibility
IRR_CASES = []
for p in (2, 3, 5):
    for n in range(1, 5 if p < 5 else 4):
        for _ in range(3):
            f = [rng.randrange(p) for _ in range(n)] + [1]
            IRR_CASES.append((p, f))
IRR_CASES += [(2, [1, 1, 1]), (2, [1, 0, 1]), (2, [1, 1, 0, 0, 1]), (2, [1, 0, 1, 0, 1]), (3, [1, 0, 1]), (3, [2, 0, 1]), (7, [0, 1]), (5, [1]), (5, [])]
for k, (p, f) in enumerate(IRR_CASES): st(f'ir{k}', "Bool", f"fpirreducible({p}, {ph(f)})")
# factorisation
FAC = []
for p in (2, 3, 5, 7):
    for _ in range(3):
        fs = [monics_ for monics_ in (rng.choice(irreds(p, rng.randint(1, 3))) for _ in range(rng.randint(1, 3)))]
        f = [rng.randrange(1, p)]
        for g in fs: f = pmul(p, f, g)
        if rng.random() < 0.5: f = pmul(p, f, fs[0])
        FAC.append((p, f))
FAC += [(2, [1, 0, 0, 0, 0, 0, 0, 1]), (3, [1, 0, 0, 0, 0, 0, 1]), (2, [1, 0, 0, 0, 1]), (2, pmul(2, pmul(2, [1, 1, 1], [1, 1, 1]), [1, 1])), (5, [0, 0, 0, 1]), (3, [2, 1, 1, 2, 0, 1, 1]),
        (7, [3]), (7, []), (2, [1, 0, 0, 0, 0, 1])]
for k, (p, f) in enumerate(FAC): st(f'fa{k}', f"Pair({NN}, List(Pair({LN}, {NN})))", f"fpfactor({p}, {ph(f)})")
# irreducible and primitive polynomials, counting
IP = [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (3, 1), (3, 2), (3, 3), (5, 1), (5, 2), (7, 2)]
for k, (p, n) in enumerate(IP):
    st(f'ip{k}', LN, f"irreduciblepoly({p}, {n})"); st(f'pp{k}x', LN, f"primitivepoly({p}, {n})")
    st(f'ni{k}', NN, f"numirreducible({p}, {n})")
st('ipp1', "Bool", "isprimitivepoly(2, [1, 1, 0, 0, 1])"); st('ipp2', "Bool", "isprimitivepoly(2, [1, 1, 1, 1, 1])"); st('ipp3', "Bool", "isprimitivepoly(2, [1, 0, 1])")
st('ipp4', "Bool", "isprimitivepoly(3, [2, 1, 1])"); st('ipp5', "Bool", "isprimitivepoly(5, [])"); st('ipp6', "Bool", "isprimitivepoly(5, [0, 1])")
# ---- the finite fields
FIELDS = [('A', 2, 3, None), ('B', 2, 4, None), ('C', 3, 2, None), ('D', 3, 3, None), ('E', 5, 2, None), ('G', 2, 3, [1, 1, 0, 1]), ('H', 3, 2, [1, 0, 1]), ('I', 7, 1, None)]
FREF = {}
for nm, p, n, m in FIELDS:
    if m is None:
        st(f'F{nm}', f"Pair({NN}, {LN})", f"gf({p}, {n})")
    else:
        st(f'F{nm}', f"Pair({NN}, {LN})", f"pair({p}, {ph(m)})")
GFE = {}
def run_field_statements():
    for nm, p, n, m in FIELDS:
        mm = m if m is not None else ref_primitive_poly(p, n)
        F = GFr(p, mm); FREF[nm] = F
        els = F.elements()
        trio = [rng.choice(els) for _ in range(3)]
        trio[2] = rng.choice([e for e in els if e])
        a, b, c = trio
        GFE[nm] = (a, b, c)
        st(f'ga{nm}', LN, f"gfadd(F{nm}, {ph(a)}, {ph(b)})"); st(f'gs{nm}', LN, f"gfsub(F{nm}, {ph(a)}, {ph(b)})"); st(f'gm{nm}', LN, f"gfmul(F{nm}, {ph(a)}, {ph(b)})")
        st(f'gn{nm}', LN, f"gfneg(F{nm}, {ph(a)})"); st(f'gi{nm}', LN, f"gfinv(F{nm}, {ph(c)})"); st(f'gd{nm}', LN, f"gfdiv(F{nm}, {ph(a)}, {ph(c)})")
        e = rng.randint(0, 20); st(f'gp{nm}', LN, f"gfpow(F{nm}, {ph(a)}, {e})"); st(f'gq{nm}', LN, f"gfpow(F{nm}, {ph(c)}, -{rng.randint(1, 9)})")
        st(f'ge{nm}', f"List({LN})", f"gfelements(F{nm})"); st(f'go{nm}', NN, f"gforder(F{nm}, {ph(c)})"); st(f'gz{nm}', NN, f"gforder(F{nm}, [])")
        st(f'gI{nm}', "Bool", f"gfisprimitive(F{nm}, {ph(c)})"); st(f'gP{nm}', LN, f"gfprimitive(F{nm})")
        st(f'gl{nm}', "\\ZZ", f"gflog(F{nm}, {ph(F.elements()[p if n > 1 else 1] if False else gfprim_ref(F))}, {ph(c)})")
        st(f'gf{nm}', LN, f"gffrob(F{nm}, {ph(a)})"); st(f'gt{nm}', NN, f"gftrace(F{nm}, {ph(a)})"); st(f'gN{nm}', NN, f"gfnorm(F{nm}, {ph(a)})")
        st(f'gM{nm}', LN, f"gfminpoly(F{nm}, {ph(a)})"); st(f'gC{nm}', f"List({LN})", f"gfconjugates(F{nm}, {ph(a)})")
        st(f'gr{nm}', f"List({LN})", f"gfsqrt(F{nm}, {ph(a)})"); st(f'gS{nm}', "Bool", f"gfissquare(F{nm}, {ph(a)})")
        poly = [rng.choice(els) for _ in range(3)] + [[1]]
        st(f'gR{nm}', f"List({LN})", f"gfroots(F{nm}, [{', '.join(ph(x) for x in poly)}])")
        GFE[nm] = (a, b, c, e, poly)
def gfprim_ref(F):
    for a in F.elements():
        if F.order(a) == F.p ** F.n - 1: return a
run_field_statements()
st('gc1', f"Pair({NN}, {LN})", "gf(3, 1)"); st('gc2', NN, "gfchar(FA)"); st('gc3', LN, "gfmodulus(FA)"); st('gc4', NN, "gfdegree(FB)"); st('gc5', NN, "gfsize(FC)")
st('gc6', LN, "gfelement(FB, [1, 1, 1, 1, 1, 1])"); st('gc7', LN, "gfelement(FC, [5, 7, 4])"); st('gc8', LN, "gfsubfields(12)")
st('gc9', LN, "gfpow(FA, [0, 1], 0)"); st('gcA', LN, "gfinv(FA, [])"); st('gcB', LN, "gfdiv(FA, [1], [])"); st('gcC', "\\ZZ", "gflog(FA, [0, 1], [])")
# ---- number fields
NF = [([-2, 0, 1], [1, 1]), ([-2, 0, 1], [3, 5]), ([-2, 0, 0, 1], [0, 1, 1]), ([1, 1, 1], [2, 3]), ([-5, 0, 1], [(Fr(1, 2)), (Fr(1, 2))]), ([-3, 0, 0, 0, 1], [1, 0, 1, 1]),
      ([-2, 0, 0, 1], [Fr(1, 3), 0, 2]), ([-1, 0, 1], [2, 1]), ([2, 0, 3], [1, 1])]
def qh(c):
    c = Fr(c); t = str(c.numerator) + (f"/{c.denominator}" if c.denominator != 1 else "")
    return f"({t} in \\QQ)" if c.denominator != 1 else (f"({t})" if c < 0 else t)
def qlh(f): return "[" + ", ".join(qh(c) for c in f) + "]"
for k, (f, a) in enumerate(NF):
    st(f'nm{k}', "List(List(\\Q))", f"nfmatrix({qlh(f)}, {qlh(a)})"); st(f'nc{k}', "List(\\Q)", f"nfcharpoly({qlh(f)}, {qlh(a)})"); st(f'nq{k}', "List(\\Q)", f"nfminpoly({qlh(f)}, {qlh(a)})")
    st(f'nd{k}', NN, f"nfdegree({qlh(f)}, {qlh(a)})"); st(f'nt{k}', "\\Q", f"nftrace({qlh(f)}, {qlh(a)})"); st(f'nn{k}', "\\Q", f"nfnorm({qlh(f)}, {qlh(a)})")
    st(f'ni{k}x', "Bool", f"nfisintegral({qlh(f)}, {qlh(a)})"); st(f'nx{k}', "\\Q", f"nfdiscriminant({qlh(f)})")
# ---- algebraic numbers
ALG = [([-2, 0, 1], [-3, 0, 1]), ([-2, 0, 1], [-2, 0, 1]), ([-2, 0, 0, 1], [-2, 0, 1]), ([1, 1, 1], [1, 0, 1]), ([-2, 0, 1], [1, 1, 1]), ([-5, 0, 1], [-3, 0, 1]), ([-3, 1], [-2, 0, 1])]
for k, (f, g) in enumerate(ALG):
    for nm, fn in (('s', 'algsum'), ('d', 'algdiff'), ('p', 'algprod'), ('q', 'algquot')):
        st(f'a{nm}{k}', "List(List(\\QQ))", f"{fn}({qlh(f)}, {qlh(g)})")
UN = [[-2, 0, 1], [-2, 0, 0, 1], [1, 1, 1], [-6, 1, 1], [-1, 0, 0, 0, 1]]
for k, f in enumerate(UN):
    st(f'an{k}', "List(List(\\QQ))", f"algneg({qlh(f)})"); st(f'ai{k}', "List(List(\\QQ))", f"alginv({qlh(f)})")
    st(f'aw{k}', "List(List(\\QQ))", f"algpow({qlh(f)}, 2)"); st(f'ax{k}', "List(List(\\QQ))", f"algpow({qlh(f)}, 3)"); st(f'ar{k}', "List(List(\\QQ))", f"algroot({qlh(f)}, 2)")
st('az1', "List(List(\\QQ))", "algprod([0, 1], [-2, 0, 1])")

# ------------------------------------------------------------------------------------------------ numeric helpers for the algebraic numbers
def croots(f):
    f = [complex(Fr(c)) for c in f]
    n = len(f) - 1
    if n < 1: return []
    lead = f[-1]; f = [c / lead for c in f]
    z = [(0.4 + 0.9j) ** k for k in range(n)]
    def ev(x):
        r = 0
        for c in reversed(f): r = r * x + c
        return r
    for _ in range(2000):
        d = 0
        for i in range(n):
            den = 1
            for j in range(n):
                if i != j: den *= (z[i] - z[j])
            w = ev(z[i]) / den; z[i] -= w; d = max(d, abs(w))
        if d < 1e-14: break
    return z
def residual(f, x):
    r = 0
    for c in reversed(f): r = r * x + complex(Fr(c))
    s = sum(abs(complex(Fr(c))) * abs(x) ** k for k, c in enumerate(f))
    return abs(r) / (1 + s)
def same_roots(factors, combos, tol=1e-6):
    """every combination is a root of some factor, and every root of every factor is a combination"""
    ok1 = all(any(residual(f, g) < tol for f in factors) for g in combos)
    ok2 = True
    for f in factors:
        for r in croots(f):
            if not any(abs(r - g) < tol * (1 + abs(r)) for g in combos): ok2 = False
    return ok1 and ok2
def monic_irreducible_form(f):
    f = [Fr(c) for c in f]
    return f[-1] == 1

# ---- linear algebra helpers for the number-field references
def pmulq(f, g):
    f = [Fr(c) for c in f]; g = [Fr(c) for c in g]
    if not f or not g: return []
    r = [Fr(0)] * (len(f) + len(g) - 1)
    for i, a in enumerate(f):
        for j, b in enumerate(g): r[i + j] += a * b
    return r
def trq(f):
    f = [Fr(c) for c in f]
    while f and f[-1] == 0: f.pop()
    return f
def pdivmodq(f, g):
    f, g = trq(f), trq(g)
    q = [Fr(0)] * max(len(f) - len(g) + 1, 0)
    while len(f) >= len(g) and f:
        c = f[-1] / g[-1]; k = len(f) - len(g); q[k] = c
        for j, y in enumerate(g): f[k + j] -= c * y
        f = trq(f)
    return trq(q), f
def mat_mult_by(f, a):
    f = trq(f); n = len(f) - 1; cols = []
    for j in range(n):
        v = pdivmodq(pmulq(a, [0] * j + [1]), f)[1]
        cols.append(v + [Fr(0)] * (n - len(v)))
    return [[cols[j][i] for j in range(n)] for i in range(n)]
def det_q(M):
    M = [r[:] for r in M]; n = len(M); d = Fr(1)
    for i in range(n):
        p = next((r for r in range(i, n) if M[r][i] != 0), None)
        if p is None: return Fr(0)
        if p != i: M[i], M[p] = M[p], M[i]; d = -d
        d *= M[i][i]
        for r in range(i + 1, n):
            c = M[r][i] / M[i][i]
            M[r] = [x - c * y for x, y in zip(M[r], M[i])]
    return d
def charpoly_q(M):
    n = len(M)
    # Faddeev-LeVerrier
    I = [[Fr(int(i == j)) for j in range(n)] for i in range(n)]
    c = [Fr(1)]; Mk = [[Fr(0)] * n for _ in range(n)]
    for k in range(1, n + 1):
        Mk = [[sum(M[i][l] * Mk[l][j] for l in range(n)) + c[-1] * I[i][j] for j in range(n)] for i in range(n)]
        AM = [[sum(M[i][l] * Mk[l][j] for l in range(n)) for j in range(n)] for i in range(n)]
        c.append(-sum(AM[i][i] for i in range(n)) / k)
    return list(reversed(c))
def sylvester_res(f, g):
    f, g = trq(f), trq(g); m, n = len(f) - 1, len(g) - 1
    if m < 0 or n < 0: return Fr(0)
    N = m + n
    if N == 0: return Fr(1)
    rows = []
    fr, gr = list(reversed(f)), list(reversed(g))
    for i in range(n): rows.append([Fr(0)] * i + fr + [Fr(0)] * (N - m - 1 - i))
    for i in range(m): rows.append([Fr(0)] * i + gr + [Fr(0)] * (N - n - 1 - i))
    return det_q(rows)

def main():
    SRC = "\n".join(f"{n} in {c} := {e}" for n, c, e in STM)
    P_ = imo.Program()
    for f in imo.PRELUDE: P_.add_file(f, trusted=True)
    P_.add_text(SRC, 'field.hum.imo', notation='hum')
    errs = P_.check(collect=True)
    rep("the test program passes the class checker", not errs, str(errs[:2]))
    if errs: return rep.done()
    P_.build(); E = Env(P_)
    V = lambda n: E.V(P_.hum.spec_name(n))
    nat = lambda v: int(E.dq(v).r)
    ns = lambda n: [nat(c) for c in E.lst(V(n))]
    nss = lambda n: [[nat(c) for c in E.lst(l)] for l in E.lst(V(n))]
    def ql(n): return trq([E.dq(c).r for c in E.lst(V(n))])
    def qq(n): return E.dq(V(n)).r
    def qll(n): return [trq([E.dq(c).r for c in E.lst(l)]) for l in E.lst(V(n))]
    def mat(n): return [[E.dq(c).r for c in E.lst(r)] for r in E.lst(V(n))]
    # ---- GF(p) polynomials
    bad = []
    for k, (p, f, g) in enumerate(POLY):
        if ns(f'pa{k}') != padd(p, f, g): bad.append(('add', k))
        if ns(f'ps{k}') != psub(p, f, g): bad.append(('sub', k))
        if ns(f'pm{k}') != pmul(p, f, g): bad.append(('mul', k))
        q, r = pdivmod(p, f, g); a, b = to_pair(V(f'pd{k}'))
        if ([nat(x) for x in E.lst(a)], [nat(x) for x in E.lst(b)]) != (q, r): bad.append(('divmod', k))
        if ns(f'pq{k}') != q or ns(f'pr{k}') != r: bad.append(('quo/rem', k))
        if ns(f'pg{k}') != pgcd(p, f, g): bad.append(('gcd', k))
        d, st_ = to_pair(V(f'pe{k}')); s, t = to_pair(st_); d, s, t = [[nat(x) for x in E.lst(z)] for z in (d, s, t)]
        if not (d == pgcd(p, f, g) and padd(p, pmul(p, s, f), pmul(p, t, g)) == d): bad.append(('egcd', k))
        n_ = int([s_ for s_ in STM if s_[0] == f'pw{k}'][0][2].split(',')[-2 if False else 1].strip()) if False else None
        stmt = [s_ for s_ in STM if s_[0] == f'pw{k}'][0][2]
        e_ = int(stmt[stmt.index(']') + 2:].split(',')[0])
        if ns(f'pw{k}') != (ppowmod(p, f, e_, g) if g and len(g) > 1 else ([] if not g else [])): bad.append(('powmod', k, ns(f'pw{k}'), ppowmod(p, f, e_, g) if g else None))
        if ns(f'pv{k}') != pder(p, f): bad.append(('deriv', k))
        stmt = [s_ for s_ in STM if s_[0] == f'px{k}'][0][2]; a_ = int(stmt.rsplit(',', 1)[1].strip(' )'))
        if nat(V(f'px{k}')) != peval(p, f, a_): bad.append(('eval', k))
        if ns(f'py{k}') != [a for a in range(p) if peval(p, f, a) == 0]: bad.append(('roots', k))
        if ns(f'po{k}') != pneg(p, f) or ns(f'pp{k}') != pmonic(p, f): bad.append(('neg/monic', k))
    rep("fpadd, fpsub, fpmul, fpdivmod, fpquo, fprem, fpgcd, fpegcd (s f + t g = gcd), fppowmod, fpderiv, fpeval, fproots, fpneg, fpmonic over GF(2), GF(3), GF(5), GF(7): 8 random pairs", not bad, str(bad[:3]))
    rep("fpoly reduces coefficients (negative, large); trailing zeros vanish; degree; division by 0 gives (0, f); gcd of zeros",
        ns('pz1') == [2, 0, 2] and ns('pz2') == [] and int(E.dq(V('pz3')).r) == -1 and [nat(x) for x in E.lst(to_pair(V('pz4'))[0])] == [] and [nat(x) for x in E.lst(to_pair(V('pz4'))[1])] == [1, 2, 3]
        and ns('pz5') == [] and ns('pz6') == [4, 1])
    rep("fpscale c·f", all(ns(f'pn{k}') == [c * x % p for x in f] for k, (p, f, g) in enumerate(POLY) for c in [int([s_ for s_ in STM if s_[0] == f'pn{k}'][0][2].split(', ')[1])]))
    bad = [(k, p, f) for k, (p, f) in enumerate(IRR_CASES) if E.b(V(f'ir{k}')) != is_irred_ref(p, f)]
    rep(f"fpirreducible against trial division: {len(IRR_CASES)} polynomials over GF(2), GF(3), GF(5) (degrees 1 to 4, constants and zero)", not bad, str(bad[:3]))
    bad = []
    for k, (p, f) in enumerate(FAC):
        c, fs = to_pair(V(f'fa{k}')); got = (nat(c), [([nat(x) for x in E.lst(g)], nat(m)) for g, m in (to_pair(t) for t in E.lst(fs))])
        want = factor_ref(p, f)
        if got != want: bad.append((k, p, f, got, want))
    rep(f"fpfactor: {len(FAC)} polynomials over GF(2), GF(3), GF(5), GF(7) — repeated factors, p-th powers (x^6 + 1 = (x^2 + 1)^3 over GF(3)), irreducible and reducible, constants, zero — equal to trial division", not bad, str(bad[:2]))
    bad = []
    for k, (p, n) in enumerate(IP):
        if ns(f'ip{k}') != ref_irreducible_poly(p, n): bad.append(('irreduciblepoly', p, n, ns(f'ip{k}'), ref_irreducible_poly(p, n)))
        if ns(f'pp{k}x') != ref_primitive_poly(p, n): bad.append(('primitivepoly', p, n, ns(f'pp{k}x'), ref_primitive_poly(p, n)))
        if nat(V(f'ni{k}')) != len(irreds(p, n)) and n <= 3: bad.append(('count', p, n))
    rep("irreduciblepoly, primitivepoly (first in the order of the coefficient vector) and numirreducible (Gauss's formula = the brute-force count for n <= 3) for 11 pairs (p, n)", not bad, str(bad[:3]))
    cnt = {(2, 4): 3, (2, 5): 6, (3, 3): 8, (5, 2): 10, (7, 2): 21}
    rep("numirreducible: 3, 6, 8, 10, 21 irreducible polynomials of degrees 4, 5 over GF(2), 3 over GF(3), 2 over GF(5), GF(7)",
        all(nat(V(f'ni{IP.index(k)}')) == v for k, v in cnt.items()))
    rep("isprimitivepoly: x^4 + x + 1 yes; x^4 + x^3 + x^2 + x + 1 (x has order 5) no; x^2 + 1 (not irreducible) no; x^2 + x + 2 over GF(3) yes; the zero polynomial and x no",
        [E.b(V(f'ipp{i}')) for i in range(1, 7)] == [True, False, False, True, False, False])
    # ---- GF(p^n)
    bad = []
    for nm, p, n, m in FIELDS:
        F = FREF[nm]; a, b, c, e, poly = GFE[nm]
        mm = F.m
        if [nat(x) for x in E.lst(to_pair(V(f'F{nm}'))[1])] != mm: bad.append(('modulus', nm))
        g = lambda key: ns(key)
        if g(f'ga{nm}') != F.add(a, b) or g(f'gs{nm}') != F.sub(a, b) or g(f'gm{nm}') != F.mul(a, b) or g(f'gn{nm}') != pneg(p, a): bad.append(('add/sub/mul/neg', nm))
        inv = F.inv(c)
        if g(f'gi{nm}') != inv or F.mul(inv, c) != [1] or g(f'gd{nm}') != F.mul(a, inv): bad.append(('inv/div', nm))
        if g(f'gp{nm}') != F.pw(a, e): bad.append(('pow', nm))
        stmt = [s_ for s_ in STM if s_[0] == f'gq{nm}'][0][2]; eg = int(stmt.rsplit('-', 1)[1].strip(' )'))
        if g(f'gq{nm}') != F.pw(c, -eg): bad.append(('negative pow', nm))
        if nss(f'ge{nm}') != F.elements(): bad.append(('elements', nm))
        if nat(V(f'go{nm}')) != F.order(c) or nat(V(f'gz{nm}')) != 0: bad.append(('order', nm))
        if E.b(V(f'gI{nm}')) != (F.order(c) == p ** n - 1): bad.append(('isprimitive', nm))
        if g(f'gP{nm}') != gfprim_ref(F): bad.append(('primitive', nm))
        gp = gfprim_ref(F); lg = next(k for k in range(p ** n) if F.pw(gp, k) == c)
        if int(E.dq(V(f'gl{nm}')).r) != lg: bad.append(('log', nm))
        if g(f'gf{nm}') != F.pw(a, p): bad.append(('frobenius', nm))
        cj = F.conj(a); tsum = []
        for x in cj: tsum = F.add(tsum, x)
        nprod = [1]
        for x in cj: nprod = F.mul(nprod, x)
        if nat(V(f'gt{nm}')) != (tsum[0] if tsum else 0) or nat(V(f'gN{nm}')) != (nprod[0] if nprod else 0) or len(tsum) > 1 or len(nprod) > 1: bad.append(('trace/norm', nm))
        dist = []
        for x in cj:
            if x not in dist: dist.append(x)
        if nss(f'gC{nm}') != dist: bad.append(('conjugates', nm, nss(f'gC{nm}'), dist))
        mp = [nat(x) for x in E.lst(V(f'gM{nm}'))]
        # minimal polynomial: monic, degree = number of distinct conjugates, vanishes at a, irreducible over GF(p)
        val = []
        for k, cf in enumerate(mp): val = F.add(val, F.mul([cf % p] if cf else [], F.pw(a, k)))
        if not (mp and mp[-1] == 1 and len(mp) - 1 == len(dist) and val == [] and is_irred_ref(p, mp)): bad.append(('minpoly', nm, mp))
        roots = sorted(x for x in F.elements() if F.mul(x, x) == a)
        if sorted(nss(f'gr{nm}')) != sorted(roots): bad.append(('sqrt', nm))
        if E.b(V(f'gS{nm}')) != bool(roots): bad.append(('issquare', nm))
        rr = []
        for x in F.elements():
            acc = []
            for cf in reversed(poly): acc = F.add(cf, F.mul(x, acc))
            if not acc: rr.append(x)
        if nss(f'gR{nm}') != rr: bad.append(('roots', nm))
    rep("GF(p^n) for 8 fields (GF(8), GF(16), GF(9), GF(27), GF(25), GF(7); also GF(8) with the modulus x^3 + x + 1 and GF(9) with x^2 + 1, where x is not primitive): add, sub, mul, neg, inv, div, pow (also negative), elements, order, isprimitive, primitive, log, frobenius, trace, norm, conjugates, minpoly, sqrt, issquare, roots",
        not bad, str(bad[:3]))
    rep("gfchar, gfmodulus, gfdegree, gfsize, gfelement (reduces modulo p and the modulus), gfsubfields, 0^0 = 1, inverse and quotient by 0 are [], log of 0 is -1",
        nat(V('gc2')) == 2 and ns('gc3') == FREF['A'].m and nat(V('gc4')) == 4 and nat(V('gc5')) == 9 and ns('gc6') == FREF['B'].red([1, 1, 1, 1, 1, 1])
        and ns('gc7') == FREF['C'].red(P(3, [5, 7, 4])) and ns('gc8') == [1, 2, 3, 4, 6, 12] and ns('gc9') == [1] and ns('gcA') == [] and ns('gcB') == []
        and int(E.dq(V('gcC')).r) == -1 and [nat(x) for x in E.lst(to_pair(V('gc1'))[1])] == ref_primitive_poly(3, 1))
    # ---- number fields
    bad = []
    for k, (f, a) in enumerate(NF):
        M = mat_mult_by(f, a); f_ = trq(f); n = len(f_) - 1
        if mat(f'nm{k}') != M: bad.append(('matrix', k))
        cp = charpoly_q(M)
        if ql(f'nc{k}') != cp: bad.append(('charpoly', k, ql(f'nc{k}'), cp))
        resab = sylvester_res(f_, trq(pdivmodq(a, f_)[1])) / f_[-1] ** (len(trq(pdivmodq(a, f_)[1])) - 1) if trq(pdivmodq(a, f_)[1]) else Fr(0)
        if qq(f'nn{k}') != det_q(M) or qq(f'nn{k}') != resab: bad.append(('norm', k, qq(f'nn{k}'), det_q(M), resab))
        if qq(f'nt{k}') != sum(M[i][i] for i in range(n)): bad.append(('trace', k))
        mpl = ql(f'nq{k}')
        # minimal polynomial: monic, divides the characteristic polynomial, annihilates a, and the charpoly is a power of it
        def evalq(p_, a_):
            r = []
            for c in reversed(p_): r = trq([c] if not r and c else pdivmodq(padd_q(pmulq(r, a_), [c]), f_)[1])
            return r
        def padd_q(x, y):
            n_ = max(len(x), len(y)); return trq([(x[i] if i < len(x) else 0) + (y[i] if i < len(y) else 0) for i in range(n_)])
        acc = []
        for c in reversed(mpl): acc = pdivmodq(padd_q(pmulq(acc, a), [c]), f_)[1]
        pw_ = [Fr(1)]
        for _ in range(n // max(len(mpl) - 1, 1)): pw_ = pmulq(pw_, mpl)
        if not (mpl and mpl[-1] == 1 and not acc and n % (len(mpl) - 1) == 0 and trq(pw_) == cp): bad.append(('minpoly', k, mpl, cp))
        if nat(V(f'nd{k}')) != len(mpl) - 1: bad.append(('degree', k))
        if E.b(V(f'ni{k}x')) != all(c.denominator == 1 for c in mpl): bad.append(('integral', k))
        if qq(f'nx{k}') != (sylvester_res(f_, [i * c for i, c in enumerate(f_)][1:]) * (-1) ** (n * (n - 1) // 2) / f_[-1] if n > 1 else Fr(1)): bad.append(('disc', k, qq(f'nx{k}')))
    rep("nfmatrix, nfcharpoly, nfminpoly, nfdegree, nftrace, nfnorm (determinant = resultant formula), nfisintegral, nfdiscriminant in 9 number fields (quadratic, cubic, quartic; elements with denominators; a reducible modulus)", not bad, str(bad[:2]))
    # ---- algebraic numbers
    bad = []
    for k, (f, g) in enumerate(ALG):
        rf, rg = croots(f), croots(g)
        for nm, op in (('s', lambda x, y: x + y), ('d', lambda x, y: x - y), ('p', lambda x, y: x * y), ('q', lambda x, y: x / y)):
            if nm == 'q' and any(abs(y) < 1e-9 for y in rg): continue
            fac = qll(f'a{nm}{k}')
            combos = [op(x, y) for x in rf for y in rg]
            if not (fac and all(monic_irreducible_form(h) for h in fac) and same_roots(fac, combos)): bad.append((nm, k, fac))
    for k, f in enumerate(UN):
        rf = croots(f)
        for nm, op in (('n', lambda x: -x), ('i', lambda x: 1 / x), ('w', lambda x: x ** 2), ('x', lambda x: x ** 3)):
            fac = qll(f'a{nm}{k}')
            if not (fac and all(monic_irreducible_form(h) for h in fac) and same_roots(fac, [op(x) for x in rf])): bad.append((nm, k, fac))
        fac = qll(f'ar{k}'); combos = [cmath.sqrt(x) * s for x in rf for s in (1, -1)]
        if not (fac and all(monic_irreducible_form(h) for h in fac) and same_roots(fac, combos)): bad.append(('root', k, fac))
    rep("algsum, algdiff, algprod, algquot, algneg, alginv, algpow, algroot: the roots of the returned factors are exactly the combinations of the numerical roots of f and g (7 pairs, 5 single polynomials; every factor monic)", not bad, str(bad[:2]))
    known = [(qll('as0'), [[Fr(1), 0, Fr(-10), 0, Fr(1)]]), (qll('ap0'), [[Fr(-6), 0, Fr(1)]]), (qll('an0'), [[Fr(-2), 0, Fr(1)]]), (qll('ai0'), [[Fr(-1, 2), 0, Fr(1)]]),
             (qll('aw1'), [[Fr(-4), 0, 0, Fr(1)]]), (qll('ar0'), [[Fr(-2), 0, 0, 0, Fr(1)]]), (qll('as1'), [[Fr(0), Fr(1)], [Fr(-8), 0, Fr(1)]])]
    ok = all(sorted(map(trq, got), key=len) == sorted(map(trq, want), key=len) for got, want in known)
    rep("known minimal polynomials: sqrt 2 + sqrt 3: x^4 - 10 x^2 + 1;  sqrt 2 * sqrt 3: x^2 - 6;  -sqrt 2: x^2 - 2;  1/sqrt 2: x^2 - 1/2;  (cbrt 2)^2: x^3 - 4;  2^(1/4): x^4 - 2;  sqrt 2 + sqrt 2: x, x^2 - 8", ok)
    rep("algprod with a factor having the root 0 is [x]", qll('az1') == [[Fr(0), Fr(1)]])
    return rep.done()

sys.exit(0 if run_big(main) else 1)
