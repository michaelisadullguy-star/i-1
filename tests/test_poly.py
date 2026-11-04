"""test_poly.py -- lib/poly.imo (polynomials in one indeterminate over ℚ[i]) used from the HUMAN notation: every statement goes through
doc 2, overload resolution and the class checker, is evaluated in the language, decoded, and compared with an independent python
reference (Fraction arithmetic, Sylvester determinants, explicit formulas, known roots and hand-checked factorisations).
python3 tests/test_poly.py"""
import os, sys, math, cmath, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()
Q = R.Q
def F(x): return x if isinstance(x, Q) else Q(Fr(x))
ZERO, ONE, I = Q(0), Q(1), Q(0, 1)

# ---------------------------------------------------------------- python reference: polynomials as lists of Q, lowest degree first
def trim(p):
    p = [F(c) for c in p]
    while p and p[-1].iszero(): p.pop()
    return p
def padd(p, q):
    n = max(len(p), len(q)); p, q = [F(c) for c in p], [F(c) for c in q]
    return trim([(p[k] if k < len(p) else ZERO) + (q[k] if k < len(q) else ZERO) for k in range(n)])
def pneg(p): return trim([-F(c) for c in p])
def psub(p, q): return padd(p, pneg(q))
def pscale(c, p): return trim([F(c) * F(x) for x in p])
def pmul(p, q):
    p, q = trim(p), trim(q)
    if not p or not q: return []
    out = [ZERO] * (len(p) + len(q) - 1)
    for a, x in enumerate(p):
        for b, y in enumerate(q): out[a + b] = out[a + b] + x * y
    return trim(out)
def ppow(p, n):
    r = [ONE]
    for _ in range(n): r = pmul(r, p)
    return r
def pdivmod(p, q):
    p, q = trim(p), trim(q)
    if not q: return [], p
    quo = [ZERO] * max(len(p) - len(q) + 1, 0); r = list(p); inv = q[-1].inv()
    while len(r) >= len(q):
        c = r[-1] * inv; k = len(r) - len(q); quo[k] = c
        for j, y in enumerate(q): r[k + j] = r[k + j] - c * y
        r = trim(r[:-1]) if r[-1].iszero() else trim(r)
    return trim(quo), r
def pev(p, z):
    acc = ZERO
    for c in reversed(trim(p)): acc = acc * F(z) + c
    return acc
def pder(p): return trim([F(k) * c for k, c in enumerate(trim(p))][1:])
def pmonic(p):
    p = trim(p); return pscale(p[-1].inv(), p) if p else []
def pgcd(p, q):
    p, q = trim(p), trim(q)
    while q: p, q = q, pdivmod(p, q)[1]
    return pmonic(p)
def pcompose(p, q):
    acc = []
    for c in reversed(trim(p)): acc = padd(pmul(acc, q), [c])
    return acc
def deg(p): return len(trim(p)) - 1
def fromroots(rs):
    r = [ONE]
    for z in rs: r = pmul(r, [-F(z), ONE])
    return r
def det(M):                                     # Gaussian elimination over Q(i)
    M = [[F(x) for x in row] for row in M]; n = len(M); d = ONE
    for c in range(n):
        piv = next((r for r in range(c, n) if not M[r][c].iszero()), None)
        if piv is None: return ZERO
        if piv != c: M[c], M[piv] = M[piv], M[c]; d = -d
        d = d * M[c][c]; inv = M[c][c].inv()
        for r in range(c + 1, n):
            f = M[r][c] * inv
            M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return d
def sylvester_res(p, q):
    p, q = trim(p), trim(q)
    if not p or not q: return ZERO
    m, n = deg(p), deg(q)
    if m == 0 and n == 0: return ONE
    if m == 0: return pow_q(p[0], n)
    if n == 0: return pow_q(q[0], m)
    rows = [[ZERO] * k + list(reversed(p)) + [ZERO] * (n - 1 - k) for k in range(n)]
    rows += [[ZERO] * k + list(reversed(q)) + [ZERO] * (m - 1 - k) for k in range(m)]
    return det(rows)
def pow_q(x, n):
    r = ONE
    for _ in range(n): r = r * x
    return r
def disc_ref(p):
    p = trim(p); n = deg(p)
    if n < 1: return ZERO
    if n == 1: return ONE
    return F((-1) ** (n * (n - 1) // 2)) * sylvester_res(p, pder(p)) * p[-1].inv()
def realfr(p): return [c.r for c in trim(p)]
def prim_pos(p):                                 # p·(positive rational) with coprime integer coefficients
    p = realfr(p)
    if not p: return []
    L = 1
    for c in p: L = L * c.denominator // math.gcd(L, c.denominator)
    z = [int(c * L) for c in p]; g = 0
    for c in z: g = math.gcd(g, c)
    return [Q(c // g) for c in z]
def sturm_ref(p):
    p = trim(p)
    if not p: return []
    seq = [prim_pos(p)]
    if deg(p) >= 1:
        seq.append(prim_pos(pder(p)))
        while True:
            r = pneg(pdivmod(seq[-2], seq[-1])[1])
            if not r: break
            seq.append(prim_pos(r))
    return seq
def sqfree_ref(p): return pmonic(pdivmod(p, pgcd(p, pder(p)))[0]) if trim(p) else []
def sgnq(x): return (x > 0) - (x < 0)
def isolate_ok(p, ivs, roots):                   # roots: sorted exact-or-float list of the distinct real roots
    if len(ivs) != len(roots): return False
    for (a, b), r in zip(ivs, roots):
        if a == b:
            if pev(p, a) != ZERO or abs(float(a) - float(r)) > 1e-12: return False
        elif not (a < b and float(a) < float(r) < float(b) and pev(p, b) != ZERO): return False
    return all(ivs[k][1] < ivs[k + 1][0] or (ivs[k][1] == ivs[k + 1][0] < ivs[k + 1][1]) for k in range(len(ivs) - 1))
def hum(p):                                      # a python polynomial as a human list literal
    def one(c):
        c = F(c)
        if c.i == 0: return f"({c.r} in \\Q)" if cplx else (str(c.r) if c.r.denominator == 1 else f"({c.r} in \\QQ)")
        return f"(({c.r}) + ({c.i}) * i in \\Q)"
    cplx = any(F(c).i != 0 for c in p)
    return '[' + ', '.join(one(c) for c in p) + ']'

# ---------------------------------------------------------------- the test program
X1 = [Q(1), Q(2, -1), Q(0), Q(Fr(1, 2), 3)]                   # 1 + (2 − i)x + (1/2 + 3i)x³
X2 = [Q(-3, 1), Q(0, 1), Q(1)]                                # (−3 + i) + i x + x²
P3 = [-6, 11, -6, 1]                                          # (x − 1)(x − 2)(x − 3)
P5 = [Fr(1, 2), Fr(-3, 4), 0, 2, Fr(5, 3), 1]
D1 = [1, 2, 3, 4, 5, 6]; D2 = [Fr(1, 2), -1, 3]
C1 = [Q(1, 2), Q(-1), Q(0, 3), Q(2, -1), Q(1)]; C2 = [Q(0, 1), Q(2), Q(1, 1)]
G1 = pmul(pmul([-1, 1], [-1, 1]), [2, 0, 1]); G2 = pmul([-1, 1], [-3, 0, 0, 1])       # gcd x − 1
SQ = pmul(pmul(ppow([1, 1], 3), ppow([-2, 0, 1], 2)), [0, 5])                         # 5x(x + 1)³(x² − 2)²
CSQ = pmul(ppow([Q(0, -1), Q(1)], 2), [Q(1), Q(1, 1)])                                 # (x − i)²(1 + (1 + i)x)
ST = pmul(pmul([-2, 0, 1], [1, 0, 1]), [Fr(-1, 3), 1])                                 # (x² − 2)(x² + 1)(x − 1/3)
MR = pmul(ppow([-1, 1], 2), pmul([0, 1], [-2, 0, 1]))                                  # x(x − 1)²(x² − 2)
W = pmul(pmul([-2, 0, 1], [-3, 0, 0, 1]), [Fr(1, 2), 1])                               # (x² − 2)(x³ − 3)(x + 1/2)
QR11_ROOTS = [Q(Fr(1, 3), Fr(2, 3)), Q(Fr(1, 2), Fr(-3, 2)), Q(Fr(2, 5), Fr(-1, 5))]               # (1 + 2i)/3, (2 − i)/(1 + i), 1/(2 + i)
QR11 = pmul(fromroots(QR11_ROOTS), [2, 0, 1])
FAC = [
    ([-1, 0, 0, 0, 1], (1, [([1, 1], 1), ([-1, 1], 1), ([1, 0, 1], 1)])),
    ([4, 0, 0, 0, 1], (1, [([2, -2, 1], 1), ([2, 2, 1], 1)])),
    ([1, 0, 1, 0, 1], (1, [([1, -1, 1], 1), ([1, 1, 1], 1)])),
    ([-2, 0, 0, 0, 0, 0, 2], (2, [([1, 1], 1), ([-1, 1], 1), ([1, -1, 1], 1), ([1, 1, 1], 1)])),
    (pmul([3, 2, 0, 1], [5, -1, 0, 1]), (1, [([1, 1], 1), ([3, -1, 1], 1), ([5, -1, 0, 1], 1)])),
    (pscale(Fr(-3, 2), pmul(ppow([1, 2], 2), pmul([-2, 0, 1], [1, 0, 1]))), (Fr(-3, 2), [([1, 2], 2), ([-2, 0, 1], 1), ([1, 0, 1], 1)])),
    ([1, 0, -10, 0, 1], (1, [([1, 0, -10, 0, 1], 1)])),
    ([1, 1, 0, 0, 0, 0, 1], (1, [([1, 1, 0, 0, 0, 0, 1], 1)])),
    (pmul([3, 0, 1], [5, -1, 0, 0, 1]), (1, [([3, 0, 1], 1), ([5, -1, 0, 0, 1], 1)])),
    ([Fr(3, 2), 3], (Fr(3, 2), [([1, 2], 1)])),
    (pmul([1, 0, 3], [-2, 0, 0, 5]), (1, [([1, 0, 3], 1), ([-2, 0, 0, 5], 1)])),
    (pmul(pmul([1, 0, 1], [2, 0, 1]), [3, 0, 1]), (1, [([1, 0, 1], 1), ([2, 0, 1], 1), ([3, 0, 1], 1)])),
    ([1, 0, 0, 0, 1], (1, [([1, 0, 0, 0, 1], 1)])),
    ([0, 0, 0, 7], (7, [([0, 1], 3)])),
    ([-5], (-5, [])), ([], (0, [])),
]
SRC = rf'''
r1 in Poly := poly([1, 2, 0, 0])
r2 in Poly := poly([(1/2 in \Q), (2/4 in \Q), 0, i - i])
r3 in \ZZ := deg([])
r4 in \ZZ := deg([0, 0, 0])
r5 in \ZZ := deg({hum(X1)})
r6 in \Q := lc({hum(X1 + [0, 0])})
r7 in \Q := lc([])
r8 in \Q := coeff({hum(X1)}, 3)
r9 in \Q := coeff({hum(X1)}, 7)
r10 in Poly := polyx
r11 in Poly := monomial(3/2 + i, 3)
r12 in Poly := monomial(0, 4)
r13 in List(\ZZ) := poly([-4, 2, 0])
r14 in Bool := polyeq([1, 2, 0], [(2/2 in \QQ), 2])
r15 in Bool := polyeq([1, 2], [1, 2, 1])
r16 in Bool := polyeq([], [0, 0])
a1 in Poly := polyadd({hum(X1)}, {hum(X2)})
a2 in Poly := polysub({hum(X1)}, {hum(X1)})
a3 in Poly := polyneg({hum(X2)})
a4 in Poly := polyscale(2 - i, {hum(X1)})
a5 in Poly := polyscale(0, {hum(X1)})
a6 in Poly := polymul({hum(X1)}, {hum(X2)})
a7 in Poly := polymul({hum(X1)}, [])
a8 in Poly := polypow({hum(X2)}, 3)
a9 in Poly := polypow({hum(X2)}, 0)
a10 in List(\ZZ) := polypow([1, -1], 7)
a11 in List(\ZZ) := polysub([1, 2, 3], [1, 2, 3, 4])
d1 in Pair(Poly, Poly) := polydivmod({hum(D1)}, {hum(D2)})
d2 in Pair(Poly, Poly) := polydivmod({hum(C1)}, {hum(C2)})
d3 in Pair(Poly, Poly) := polydivmod([1, 2], [0, 0, 1])
d4 in Pair(Poly, Poly) := polydivmod({hum(X1)}, [])
d5 in Pair(Poly, Poly) := polydivmod({hum(X1)}, [2 * i])
d6 in Pair(Poly, Poly) := polydivmod([], [1, 1])
d7 in Poly := polyquo([-1, 0, 0, 0, 1], [-1, 1])
d8 in Poly := polyrem([5, 0, 0, 0, 1], [-1, 1])
d9 in Poly := polyrem({hum(X1)}, [])
d10 in Poly := polypowmod([0, 1], 10, [1, 0, 1])
d11 in Poly := polypowmod({hum(X2)}, 5, {hum(D2)})
d12 in Poly := polypowmod([1, 1], 3, [])
e1 in \Q := polyeval({hum(X1)}, 1 - 2 * i)
e2 in \QQ := polyeval({hum(P5)}, -2/3)
e3 in \Q := polyeval([], 5)
e4 in \ZZ := polyeval([-6, 11, -6, 1], 4)
e5 in List(\Q) := polyevalmany({hum(X2)}, [0, 1, i, (1/2 in \Q)])
e6 in \RR := polyevalR([-2, 0, 1], sqrt(2))
e7 in \R := polyevalR([1, 0, 1], sqrt(-1))
e8 in \RR := polyevalR([1, 2, 3], 1 / 3)
c1 in Poly := polycompose({hum(X1)}, {hum(X2)})
c2 in Poly := polycompose([1, 0, 1], [1, 1])
c3 in Poly := polycompose([5], {hum(X2)})
c4 in Poly := polyshift({hum(X1)}, 1 + i)
c5 in Poly := polyderiv({hum(X1)})
c6 in Poly := polyderiv([7])
c7 in Poly := polyinteg({hum(P5)})
c8 in Poly := polyinteg([])
c9 in Poly := polyconj({hum(X1)})
c10 in Poly := polymonic({hum(X1)})
c11 in Poly := polymonic([])
g1 in Poly := polygcd({hum(G1)}, {hum(G2)})
g2 in Poly := polygcd([], [])
g3 in Poly := polygcd([], [0, 2])
g4 in Poly := polygcd([1, 0, 1], [i, 1])
g5 in Poly := polygcd({hum(C1)}, {hum(C2)})
g6 in Pair(Poly, Pair(Poly, Poly)) := polyegcd({hum(G1)}, {hum(G2)})
g7 in Pair(Poly, Pair(Poly, Poly)) := polyegcd({hum(X1)}, {hum(X2)})
g8 in Pair(Poly, Pair(Poly, Poly)) := polyegcd([], [0, 3])
g9 in Pair(Poly, Pair(Poly, Poly)) := polyegcd([], [])
g10 in Poly := polylcm({hum(G1)}, {hum(G2)})
g11 in Poly := polylcm([], [1, 1])
g12 in \QQ := polycontent([(2/3 in \QQ), (4/9 in \QQ), -6])
g13 in List(\ZZ) := polyprimitive([(2/3 in \QQ), (4/9 in \QQ), -6])
g14 in \QQ := polycontent([])
g15 in List(\ZZ) := polyprimitive([])
g16 in List(\ZZ) := polyprimitive([0, (-1/2 in \QQ)])
g17 in Poly := polygcd([(1/2 in \QQ), 1], [-1, 0, 4])
s1 in Poly := sqfree({hum(SQ)})
s2 in List(Pair(Poly, \NN)) := sqfreefactor({hum(SQ)})
s3 in Poly := sqfree({hum(CSQ)})
s4 in List(Pair(Poly, \NN)) := sqfreefactor({hum(CSQ)})
s5 in List(Pair(Poly, \NN)) := sqfreefactor([3])
s6 in Poly := sqfree([])
s7 in List(Pair(Poly, \NN)) := sqfreefactor([1, 1])
t1 in \Q := resultant({hum(X1)}, {hum(X2)})
t2 in \Q := resultant({hum(P5)}, {hum(D2)})
t3 in \Q := resultant([-2, 0, 1], [-3, 0, 1])
t4 in \Q := resultant([2], [1, 1, 1])
t5 in \Q := resultant([], [1, 1])
t6 in \Q := resultant({hum(G1)}, {hum(G2)})
t7 in \Q := disc([1, 1, 1])
t8 in \Q := disc([5, 2, 0, 1])
t9 in \Q := disc({hum(P5)})
t10 in \Q := disc({hum(X1)})
t11 in \Q := disc([3, 2])
t12 in \Q := disc([4])
t13 in \Q := disc([1, 2, 1])
u1 in List(Poly) := sturm({hum(ST)})
u2 in List(Poly) := sturm({hum(MR)})
u3 in List(Poly) := sturm([])
u4 in \NN := nrealroots({hum(ST)})
u5 in \NN := nrealroots({hum(MR)})
u6 in \NN := nrealroots([1, 0, 1])
u7 in \NN := nrealroots([])
u8 in \NN := nrealroots([7])
u9 in \NN := countroots({hum(MR)}, -2, 2)
u10 in \NN := countroots({hum(MR)}, 0, 1)
u11 in \NN := countroots({hum(MR)}, -1, 0)
u12 in \NN := countroots({hum(MR)}, 1, 1)
u13 in \NN := countroots({hum(MR)}, 2, -2)
u14 in \NN := countroots({hum(ST)}, (1/3 in \QQ), (1/2 in \QQ))
u15 in \NN := countroots({hum(ST)}, 0, (1/3 in \QQ))
u16 in \NN := countroots({hum(W)}, 1, 2)
i1 in List(Pair(\QQ, \QQ)) := isolate({hum(MR)})
i2 in List(Pair(\QQ, \QQ)) := isolate({hum(W)})
i3 in List(Pair(\QQ, \QQ)) := isolate([1, 0, 1])
i4 in List(Pair(\QQ, \QQ)) := isolate([])
i5 in List(Pair(\QQ, \QQ)) := isolate([(-1/3 in \QQ), 1])
i6 in Pair(\QQ, \QQ) := refine([-2, 0, 1], 0, 2, 12)
i7 in Pair(\QQ, \QQ) := refine({hum(W)}, (23/16 in \QQ), (3/2 in \QQ), 9)
i10 in Pair(\QQ, \QQ) := refine({hum(W)}, 1, (3/2 in \QQ), 9)
i11 in Pair(\QQ, \QQ) := refine({hum(W)}, 2, 1, 9)
i8 in Pair(\QQ, \QQ) := refine([-1, 2], 0, 1, 5)
i9 in Pair(\QQ, \QQ) := refine([-1, 3], 0, (1/2 in \QQ), 5)
i12 in Pair(\QQ, \QQ) := refine([-1, 3], 0, (1/3 in \QQ), 5)
v1 in \ZZ := signat([-3, 0, 1], [-2, 0, 1], 0, 2)
v2 in \ZZ := signat([-2, 0, 1], [-2, 0, 0, 0, 1], 0, 2)
v3 in \ZZ := signat([-2, 0, 1], [-4, 0, 0, 0, 1], 0, 2)
v4 in \ZZ := signat([-3, 0, 0, 1], {hum(W)}, 1, (23/16 in \QQ))
v5 in \ZZ := signat([-3, 0, 0, 1], {hum(W)}, (23/16 in \QQ), 2)
v6 in \ZZ := signat([1, 1], {hum(W)}, -1, 0)
v7 in \ZZ := signat([(-1/2 in \QQ), 1], [-1, 2], 0, 1)
v8 in \ZZ := signat([5], [-2, 0, 1], -2, 0)
v9 in \ZZ := signat([-2, 0, 1], [-2, 0, 1], -2, 0)
v10 in \ZZ := signat([1, 1], [-2, 0, 1], -2, 2)
v11 in \ZZ := signat([], [-2, 0, 1], 0, 2)
v12 in \ZZ := signat([1, 1], [-2, 0, 1], 1, 1)
v13 in \ZZ := signat([1, 1], [-1, 0, 1], 1, 1)
v14 in \ZZ := signat([-1, 1], [-1, 0, 1], -1, -1)
q1 in List(\Q) := ratroots([-6, 11, -6, 1])
q2 in List(\Q) := ratroots([1, 0, 1])
q3 in List(\Q) := ratroots({hum(pmul(pmul([1, 0, 1], [2, 1, 1]), [3, 2]))})
q4 in List(\Q) := ratroots({hum(pmul(fromroots([Q(1, 1), Q(Fr(-1, 2), 2), Q(3)]), [1, 0, 1]))})
q5 in List(\Q) := ratroots([])
q6 in List(\Q) := ratroots([5])
q7 in List(\Q) := ratroots([-2, 0, 1])
q8 in List(\Q) := ratroots({hum(pmul(ppow([-1, 3], 2), [0, 0, 2]))})
q9 in List(\Q) := ratroots({hum(pmul([Q(0, 2), Q(1)], [Q(-1), Q(0), Q(1)]))})
q10 in List(\Q) := ratroots({hum(pmul([2, 1, 3, 1, 1], [-5, 1]))})
q11 in List(\Q) := ratroots({hum(QR11)})
q12 in List(\Q) := ratroots({hum(pmul(ppow([Q(0, -1), Q(1)], 2), [1, 1]))})
q13 in List(\Q) := ratroots({hum(pmul([5, 4, 4], [-2, 0, 0, 1]))})
q14 in List(\Q) := ratroots({hum(pmul([0, 0, Q(2, 1)], [Q(0, -3), Q(1)]))})
o1 in \RR := root([-2, 0, 0, 1], 1)
o2 in \RR := root({hum(W)}, 3)
o3 in \RR := root({hum(MR)}, 2)
o4 in \RR := root([-2, 0, 1], 3)
o5 in \RR := root([-2, 0, 1], 0)
o6 in List(\RR) := realroots({hum(MR)})
o7 in List(\RR) := realroots([1, 0, 1])
o8 in List(\R) := croots([1, 0, 1])
o9 in List(\R) := croots({hum(pmul(ppow([-1, 1], 2), [Q(0, -1), Q(1)]))})
o10 in List(\R) := croots([-2, 0, 0, 1])
o11 in List(\R) := croots([])
f0 in \NN := 0
p1 in Poly := interpolate([0, 1, 2], [1, 3, 7])
p2 in Poly := interpolate([(1/2 in \Q), i, -1, 2], [(3 in \Q), 1 + i, 0, -2])
p3 in Poly := interpolate([], [])
p4 in Poly := interpolate([1, 1, 2], [5, 6, 7])
p5 in Poly := polyfromroots([1, 2, i])
p6 in Poly := polyfromroots([])
{chr(10).join(f"k{n} in Pair(\\QQ, List(Pair(Poly, \\NN))) := polyfactor({hum(p)})" for n, (p, _) in enumerate(FAC))}
k90 in Bool := isirreducible([1, 1, 1, 1, 1])
k91 in Bool := isirreducible([1, 0, 1, 0, 1])
k92 in Bool := isirreducible([3])
k93 in Bool := isirreducible([2, 4])
k94 in Bool := isirreducible([0, 0, 1])
k95 in Bool := isirreducible([7, 0, 0, 0, 0, -3, 1])
{chr(10).join(f"y{n} in List(\\ZZ) := cyclotomic({n})" for n in (0, 1, 2, 6, 8, 12, 15, 30))}
{chr(10).join(f"n{n} in List(\\ZZ) := chebyshevT({n})" for n in (0, 1, 5))}
{chr(10).join(f"m{n} in List(\\ZZ) := chebyshevU({n})" for n in (0, 1, 4))}
{chr(10).join(f"l{n} in List(\\QQ) := legendreP({n})" for n in (0, 1, 4))}
{chr(10).join(f"h{n} in List(\\ZZ) := hermiteH({n})" for n in (0, 1, 4))}
{chr(10).join(f"w{n} in List(\\QQ) := laguerreL({n})" for n in (0, 1, 3))}
b1 in List(List(\Q)) := companion([6, -5, 1])
b2 in List(List(\Q)) := companion({hum(X1)})
b3 in List(List(\Q)) := companion([5])
x1 in String := polystr([1, -2, 1])
x2 in String := polystr([3, 1 + i])
x3 in String := polystr([])
x4 in String := polystr([(1/2 in \Q), 0, (-3/4 in \Q)])
x5 in String := polystr([0, -1, 0, 1])
x6 in String := polystr([-i, 0, 2 * i])
x7 in String := polystr([-1])
'''
FAC_N = len(FAC)

def main():
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'poly.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("every statement of the polynomial test program passes the class checker", not errs, str(errs[:2]) if errs else '')
    if errs: return rep.done()
    P.build(); E = Env(P)
    V = lambda n: E.V(P.hum.spec_name(n))
    q = lambda n: E.dq(V(n))
    pl = lambda v: [E.dq(x) for x in E.lst(v)]                 # a polynomial value -> list of Q (exact)
    L = lambda n: pl(V(n))
    b = lambda n: E.b(V(n))
    pair = lambda v: to_pair(v)
    def canon(v):                                              # every coefficient in canonical form, no trailing zero
        out = []
        for x in E.lst(v):
            p_, d_ = to_pair(x); P_, D_ = val(to_list(p_)), val(to_list(d_))
            g = math.gcd(math.gcd(P_[0], P_[1]), D_[0])
            if D_[1] != 0 or D_[0] <= 0 or g != 1: return False
            if to_list(p_)[-1:] == [0] or to_list(d_)[-1:] == [0]: return False
            out.append(P_)
        return not out or out[-1] != (0, 0)
    def at(v, n): return E.dq(E.nth(v, n))
    def tx(n): return ''.join(chr(int(E.dq(c).r)) for c in E.lst(V(n)))

    # ---- representation and access
    rep("poly: canonical form (trailing zeros removed, 2/4 → 1/2, i − i → nothing), every coefficient in canonical digit form",
        L('r1') == [F(1), F(2)] and L('r2') == [F(Fr(1, 2)), F(Fr(1, 2))] and canon(V('r2')) and canon(V('r13')) and L('r13') == [F(-4), F(2)])
    rep("deg: −1 for the zero polynomial (also with trailing zeros), 3 for a complex cubic",
        q('r3') == F(-1) and q('r4') == F(-1) and q('r5') == F(3))
    rep("lc, coeff (beyond the degree: 0), polyx, monomial (0·xⁿ is the zero polynomial)",
        q('r6') == X1[3] and q('r7') == ZERO and q('r8') == X1[3] and q('r9') == ZERO and L('r10') == [ZERO, ONE]
        and L('r11') == [ZERO] * 3 + [Q(Fr(3, 2), 1)] and L('r12') == [])
    rep("polyeq: equal as values (trailing zeros, non-canonical coefficients), unequal, zero", b('r14') and not b('r15') and b('r16'))

    # ---- ring operations
    ok = L('a1') == padd(X1, X2) and L('a2') == [] and L('a3') == pneg(X2) and L('a4') == pscale(Q(2, -1), X1) and L('a5') == []
    ok &= L('a6') == pmul(X1, X2) and L('a7') == [] and L('a8') == ppow(X2, 3) and L('a9') == [ONE]
    ok &= L('a10') == [F(math.comb(7, k) * (-1) ** k) for k in range(8)] and L('a11') == [ZERO, ZERO, ZERO, F(-4)]
    ok &= all(canon(V(n)) for n in ('a1', 'a4', 'a6', 'a8'))
    rep("polyadd, polysub, polyneg, polyscale, polymul, polypow over ℚ(i) (exact, canonical, cancellation to 0, p⁰ = 1, binomial (1 − x)⁷)", ok)

    # ---- division
    def dm(n):
        a, c = pair(V(n)); return pl(a), pl(c)
    ok = True
    for n, (p, d) in (('d1', (D1, D2)), ('d2', (C1, C2)), ('d3', ([1, 2], [0, 0, 1])), ('d5', (X1, [Q(0, 2)])), ('d6', ([], [1, 1]))):
        qq, rr = dm(n); ok &= (qq, rr) == pdivmod(p, d) and padd(pmul(qq, d), rr) == trim(p) and deg(rr) < deg(d)
    ok &= dm('d4') == ([], trim(X1)) and L('d9') == trim(X1)
    ok &= L('d7') == [ONE] * 4 and L('d8') == [F(6)]
    rep("polydivmod: p = q·quo + rem with deg rem < deg q (real, complex, constant divisor, divisor of higher degree, 0 / q); "
        "polydivmod(p, 0) = (0, p); polyquo, polyrem", ok)
    ok = L('d10') == [F(-1)] and L('d11') == pdivmod(ppow(X2, 5), D2)[1] and L('d12') == ppow([1, 1], 3)
    rep("polypowmod: x¹⁰ mod (x² + 1) = −1, a complex base modulo a real quadratic, modulus 0", ok)

    # ---- evaluation, composition, calculus
    ok = q('e1') == pev(X1, Q(1, -2)) and q('e2') == pev(P5, Fr(-2, 3)) and q('e3') == ZERO and q('e4') == F(6)
    ok &= L('e5') == [pev(X2, z) for z in (ZERO, ONE, I, F(Fr(1, 2)))]
    rep("polyeval (Horner) at complex and rational points, of the zero polynomial; polyevalmany", ok)
    e6, e7, e8 = V('e6'), V('e7'), V('e8')
    ok = all(abs(at(e6, n).r) <= Fr(6, 2 ** n) for n in (4, 10, 16)) and at(e7, 6) == ZERO
    ok &= all(abs(at(e8, n).r - Fr(2)) <= Fr(5, 2 ** n) for n in (3, 9))
    rep("polyevalR: x² − 2 at √2 tends to 0, x² + 1 at √−1 = i is 0, a polynomial at a lazy constant", ok)
    ok = L('c1') == pcompose(X1, X2) and L('c2') == [F(2), F(2), ONE] and L('c3') == [F(5)] and L('c4') == pcompose(X1, [Q(1, 1), ONE])
    ok &= L('c5') == pder(X1) and L('c6') == [] and L('c8') == []
    c7 = L('c7'); ok &= pder(c7) == trim(P5) and c7[0] == ZERO
    ok &= L('c9') == [x.conj() for x in X1] and L('c10') == pmonic(X1) and L('c11') == []
    rep("polycompose, polyshift p(x + a), polyderiv, polyinteg (constant term 0, derivative gives p back), polyconj, polymonic", ok)

    # ---- gcd family, content
    ok = L('g1') == [F(-1), ONE] == pgcd(G1, G2) and L('g2') == [] and L('g3') == [ZERO, ONE] and L('g4') == [I, ONE]
    ok &= L('g5') == pgcd(C1, C2) and L('g17') == [F(Fr(1, 2)), ONE]
    for n, (p, qq) in (('g6', (G1, G2)), ('g7', (X1, X2)), ('g8', ([], [0, 3])), ('g9', ([], []))):
        g, st = pair(V(n)); s, t = pair(st); g, s, t = pl(g), pl(s), pl(t)
        ok &= g == pgcd(p, qq) and padd(pmul(s, p), pmul(t, qq)) == g
    ok &= L('g10') == pmonic(pdivmod(pmul(G1, G2), pgcd(G1, G2))[0]) and L('g11') == []
    ok &= q('g12') == F(Fr(2, 9)) and L('g13') == [F(-3), F(-2), F(27)] and q('g14') == ZERO and L('g15') == [] and L('g16') == [ZERO, ONE]
    rep("polygcd (monic; gcd(0, 0) = 0; complex), polyegcd (s·p + t·q = g), polylcm, polycontent and polyprimitive (positive content, "
        "coprime integer coefficients, positive leading coefficient)", ok)

    # ---- square-free decomposition
    def sff(n): return [(pl(f), int(E.dq(k).r)) for f, k in (pair(x) for x in E.lst(V(n)))]
    ok = L('s1') == sqfree_ref(SQ) == pmonic(pmul(pmul([0, 1], [1, 1]), [-2, 0, 1]))
    s2 = sff('s2'); ok &= s2 == [(pmul([0, 1], []) or [ZERO, ONE], 1), ([F(-2), ZERO, ONE], 2), ([ONE, ONE], 3)]
    rebuilt = [F(5)]
    for f, k in s2: rebuilt = pmul(rebuilt, ppow(f, k))
    ok &= rebuilt == trim(SQ)
    ok &= L('s3') == sqfree_ref(CSQ) and sff('s4') == [(pmonic([Q(1), Q(1, 1)]), 1), ([Q(0, -1), ONE], 2)]
    ok &= sff('s5') == [] and L('s6') == [] and sff('s7') == [([ONE, ONE], 1)]
    rep("sqfree and sqfreefactor (Yun): 5x(x + 1)³(x² − 2)², a complex (x − i)²(1 + (1 + i)x); factors monic, multiplicities, product rebuilds p", ok)

    # ---- resultant and discriminant
    ok = q('t1') == sylvester_res(X1, X2) and q('t2') == sylvester_res(P5, D2) and q('t3') == F(1) and q('t4') == F(4)
    ok &= q('t5') == ZERO and q('t6') == ZERO
    ok &= q('t7') == F(-3) and q('t8') == F(-4 * 8 - 27 * 25) and q('t9') == disc_ref(P5) and q('t10') == disc_ref(X1)
    ok &= q('t11') == ONE and q('t12') == ZERO and q('t13') == ZERO
    rep("resultant = Sylvester determinant (complex, rational, common root → 0, constants), discriminant: b² − 4c, −4p³ − 27q², "
        "degree 5 and complex against (−1)^(n(n−1)/2)·Res(p, p′)/lc", ok)

    # ---- Sturm sequences and root counting
    ok = [pl(x) for x in E.lst(V('u1'))] == sturm_ref(ST) and [pl(x) for x in E.lst(V('u2'))] == sturm_ref(MR) and E.lst(V('u3')) == []
    rep("sturm: p, p′, −rem, … each a primitive integer polynomial times a positive factor (square-free and with multiple roots)", ok)
    def var(seq, x):
        s = [sgnq(pev(f, x).r) for f in seq]; s = [v for v in s if v]
        return sum(1 for a, c in zip(s, s[1:]) if a != c)
    st = sturm_ref(ST)
    brute = sum(1 for k in range(-400, 400) if sgnq(pev(ST, Fr(k, 100)).r) != sgnq(pev(ST, Fr(k + 1, 100)).r))
    ok = var(st, -100) - var(st, 100) == 3 == brute
    ok &= q('u4') == F(3) and q('u5') == F(4) and q('u6') == ZERO and q('u7') == ZERO and q('u8') == ZERO
    ok &= [q(f'u{k}') for k in range(9, 17)] == [F(x) for x in (4, 1, 1, 0, 0, 0, 1, 2)]
    rep("nrealroots, countroots on (a, b] (distinct roots; a root at b counts, at a does not; a ≥ b gives 0), "
        "against brute-force sign changes and the python Sturm count", ok)

    # ---- isolation, refinement, signs at roots
    def ivs(n): return [tuple(E.dq(c).r for c in pair(x)) for x in E.lst(V(n))]
    r2, r3 = math.sqrt(2), 3 ** (1 / 3)
    ok = isolate_ok(MR, ivs('i1'), [-r2, 0, 1, r2]) and isolate_ok(W, ivs('i2'), [-r2, -0.5, r2, r3])
    ok &= ivs('i3') == [] and ivs('i4') == [] and isolate_ok([Fr(-1, 3), 1], ivs('i5'), [1 / 3])
    rep("isolate: sorted disjoint intervals, one distinct root in each (multiple and rational roots, a root at a bisection point as (r, r)); "
        "none for x² + 1 and for 0", ok)
    (a6, b6), (a7, b7), (a8, b8), (a9, b9) = [tuple(E.dq(c).r for c in pair(V(n))) for n in ('i6', 'i7', 'i8', 'i9')]
    ok = b6 - a6 <= Fr(1, 2 ** 12) and a6 * a6 < 2 < b6 * b6 and 0 < b7 - a7 <= Fr(1, 2 ** 9) and a7 < r3 < b7 and a7 ** 3 < 3 < b7 ** 3
    ok &= a8 == b8 == Fr(1, 2) and a9 < Fr(1, 3) < b9 and b9 - a9 <= Fr(1, 32)
    ok &= [tuple(E.dq(c).r for c in pair(V(n))) for n in ('i10', 'i11', 'i12')] == [(1, Fr(3, 2)), (2, 1), (Fr(1, 3), Fr(1, 3))]
    rep("refine: width ≤ 2⁻ⁿ around √2 and ∛3 (a degree-6 polynomial), a root hit exactly gives (r, r), a non-dyadic root; a non-isolating interval is returned unchanged", ok)
    ok = [q(f'v{k}') for k in range(1, 15)] == [F(x) for x in (-1, -1, 0, -1, 0, 1, 0, 1, 0, 0, 0, 0, 1, -1)]
    rep("signat: sign of q at an algebraic root (negative, zero by a common factor, at √2 and at ∛3 of a degree-6 polynomial, rational roots, not one root in (a, b] → 0; a degenerate (r, r): q(r) if p(r) = 0, else 0)", ok)

    # ---- rational roots
    ok = L('q1') == [F(1), F(2), F(3)] and L('q2') == [-I, I] and L('q3') == [F(Fr(-3, 2)), -I, I]
    ok &= L('q4') == sorted([Q(1, 1), Q(Fr(-1, 2), 2), Q(3), I, -I], key=lambda z: (z.r, z.i))
    ok &= L('q5') == [] and L('q6') == [] and L('q7') == [] and L('q8') == [ZERO, F(Fr(1, 3))] and L('q9') == [F(-1), Q(0, -2), F(1)]
    ok &= L('q10') == [-I, I, F(5)]
    ok &= L('q11') == sorted(QR11_ROOTS, key=lambda z: (z.r, z.i)) and L('q12') == [F(-1), I]
    ok &= L('q13') == [Q(Fr(-1, 2), -1), Q(Fr(-1, 2), 1)] and L('q14') == [ZERO, Q(0, 3)]
    rep("ratroots: all distinct roots in ℚ(i) sorted by (Re, Im) — rational, Gaussian (complex coefficients; Gaussian denominators 3, 1 + i, 2 + i), "
        "multiple, non-real roots of a real polynomial with lc 4, a zero root of a complex polynomial, none", ok)

    # ---- real roots as lazy reals, complex roots
    def close(v, r, ns): return all(abs(float(at(v, n).r) - r) <= 2.0 ** -n + 1e-12 for n in ns)
    ok = close(V('o1'), 2 ** (1 / 3), (0, 5, 16)) and close(V('o2'), r2, (3, 12)) and close(V('o3'), 0, (4,)) and at(V('o3'), 9) == ZERO
    ok &= at(V('o4'), 3) == ZERO and at(V('o5'), 3) == ZERO
    o6 = E.lst(V('o6')); ok &= len(o6) == 4 and all(close(v, r, (2, 10)) for v, r in zip(o6, (-r2, 0, 1, r2))) and E.lst(V('o7')) == []
    rep("root(p, k): element n within 2⁻ⁿ of the k-th real root (∛2, √2 of a degree-6 polynomial, a rational root exactly); "
        "0 for k out of range; realroots", ok)
    def croots_ok(n, roots, ns):
        vs = E.lst(V(n))
        if len(vs) != len(roots): return False
        for k in ns:
            got = [complex(float(at(v, k).r), float(at(v, k).i)) for v in vs]; want = list(roots)
            for z in got:
                j = min(range(len(want)), key=lambda j: abs(want[j] - z))
                if abs(want[j] - z) > 2.0 ** -k: return False
                want.pop(j)
        return True
    cb = [2 ** (1 / 3) * cmath.exp(2j * math.pi * k / 3) for k in range(3)]
    ok = croots_ok('o8', [1j, -1j], (0, 6, 12)) and croots_ok('o9', [1, 1, 1j], (4, 10)) and croots_ok('o10', cb, (3, 10))
    ok &= E.lst(V('o11')) == []
    rep("croots: all complex roots with multiplicity (Durand–Kerner), element n within 2⁻ⁿ: ±i, a double root and i, the three cube roots of 2", ok)

    # ---- interpolation, products of linear factors
    ok = L('p1') == [ONE, ONE, ONE] and L('p3') == [] and L('p4') == [F(3), F(2)]
    p2 = L('p2'); ok &= deg(p2) <= 3 and [pev(p2, x) for x in (F(Fr(1, 2)), I, F(-1), F(2))] == [F(3), Q(1, 1), ZERO, F(-2)]
    ok &= L('p5') == fromroots([1, 2, I]) and L('p6') == [ONE]
    rep("interpolate (through the points, complex nodes, a repeated node ignored, no points → 0), polyfromroots", ok)

    # ---- factorisation over ℚ
    ok = True; bad = []
    for n, (p, (c, fs)) in enumerate(FAC):
        cc, lst = pair(V(f'k{n}'))
        got = (E.dq(cc), [(pl(f), int(E.dq(k).r)) for f, k in (pair(x) for x in E.lst(lst))])
        want = (F(c), [(trim(f), k) for f, k in fs])
        same = got[0] == want[0] and sorted(map(repr, got[1])) == sorted(map(repr, want[1]))
        prod = trim([got[0]])
        for f, k in got[1]: prod = pmul(prod, ppow(f, k))
        if not (same and prod == trim(p)): ok = False; bad.append(n)
    rep("polyfactor: complete factorisations over ℚ (x⁴ − 1, x⁴ + 4, x⁴ + x² + 1, 2x⁶ − 2, a product of two cubics, multiplicities and a "
        "rational content, irreducible quartic and sextic, x³, non-monic factors (3x² + 1)(5x³ − 2), (x² + 1)(x² + 2)(x² + 3), x⁴ + 1 "
        "(reducible modulo every prime), constants, 0); the product rebuilds p", ok, str(bad) if bad else '')
    ok = b('k90') and not b('k91') and not b('k92') and b('k93') and not b('k94') and b('k95')
    rep("isirreducible: Φ₅ yes, x⁴ + x² + 1 no, constants no, linear yes, x² no, x⁶ − 3x⁵ + 7 yes", ok)

    # ---- special polynomials
    def cyc(n):
        if n == 0: return [ONE]
        p = [F(-1)] + [ZERO] * (n - 1) + [ONE]
        for d in range(1, n):
            if n % d == 0: p = pdivmod(p, cyc(d))[0]
        return p
    ok = all(L(f'y{n}') == cyc(n) for n in (0, 1, 2, 6, 8, 12, 15, 30))
    rep("cyclotomic Φₙ (n = 0, 1, 2, 6, 8, 12, 15, 30) against (xⁿ − 1)/Π_{d|n, d<n} Φ_d", ok)
    def mono(cs): return trim([F(c) for c in cs])
    def T(n):                                      # Tₙ = Σ C(n, 2k) (x² − 1)ᵏ xⁿ⁻²ᵏ
        acc = []
        for k in range(n // 2 + 1): acc = padd(acc, pscale(math.comb(n, 2 * k), pmul(ppow([-1, 0, 1], k), ppow([0, 1], n - 2 * k))))
        return acc
    def U(n): return mono([sum((-1) ** k * math.comb(n - k, k) * 2 ** (n - 2 * k) for k in range(n // 2 + 1) if n - 2 * k == j) for j in range(n + 1)])
    def Pl(n): return mono([Fr(sum((-1) ** k * math.comb(n, k) * math.comb(2 * n - 2 * k, n) for k in range(n // 2 + 1) if n - 2 * k == j), 2 ** n) for j in range(n + 1)])
    def He(n): return mono([sum((-1) ** m * Fr(math.factorial(n), math.factorial(m) * math.factorial(n - 2 * m)) * 2 ** (n - 2 * m) for m in range(n // 2 + 1) if n - 2 * m == j) for j in range(n + 1)])
    def La(n): return mono([Fr(math.comb(n, k) * (-1) ** k, math.factorial(k)) for k in range(n + 1)])
    ok = all(L(f'n{n}') == T(n) for n in (0, 1, 5)) and all(L(f'm{n}') == U(n) for n in (0, 1, 4))
    ok &= all(L(f'l{n}') == Pl(n) for n in (0, 1, 4)) and all(L(f'h{n}') == He(n) for n in (0, 1, 4)) and all(L(f'w{n}') == La(n) for n in (0, 1, 3))
    rep("chebyshevT, chebyshevU, legendreP, hermiteH (physicists'), laguerreL against their explicit sums", ok)

    # ---- companion matrix
    def charpoly(M):                                  # det(xI − M) by Faddeev–LeVerrier
        n = len(M); Mk = [[ZERO] * n for _ in range(n)]; c = [ZERO] * n + [ONE]; Id = [[ONE if r == s else ZERO for s in range(n)] for r in range(n)]
        for k in range(1, n + 1):
            A = [[sum((M[r][t] * (Mk[t][s] + (c[n - k + 1] * Id[t][s])) for t in range(n)), ZERO) for s in range(n)] for r in range(n)]
            Mk = A; c[n - k] = F(Fr(-1, k)) * sum((A[r][r] for r in range(n)), ZERO)
        return trim(c)
    def mat(n): return [[E.dq(x) for x in E.lst(r)] for r in E.lst(V(n))]
    ok = mat('b1') == [[ZERO, F(-6)], [ONE, F(5)]] and charpoly(mat('b1')) == [F(6), F(-5), ONE]
    ok &= charpoly(mat('b2')) == pmonic(X1) and mat('b3') == []
    rep("companion: the characteristic polynomial of the companion matrix is the monic p (real, complex); [] for a constant", ok)

    # ---- text
    ok = [tx(f'x{k}') for k in range(1, 8)] == ["x^2 - 2*x + 1", "(1 + i)*x + 3", "0", "-3/4*x^2 + 1/2", "x^3 - x", "(2*i)*x^2 + (-i)", "-1"]
    rep("polystr: human notation, highest degree first, coefficients ±1 omitted, non-real coefficients parenthesised", ok,
        '' if ok else str([tx(f'x{k}') for k in range(1, 8)]))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
