"""test_linalg.py -- exact linear algebra over Q[i] (lib/linalg.imo): vectors, matrices, echelon form, rank, the four subspaces, determinants
and adjugates, characteristic and minimal polynomials, eigenvalues and eigenvectors, LU, Gram-Schmidt, pseudo-inverse and least squares,
Smith normal form, matrix exponential, and the matrix operators (+ - * ^) of the human notation.
Every statement is a HUMAN-notation program (doc 2, overload resolution, class checker); results are decoded and compared with independent
Python computations in exact Gaussian-rational arithmetic (tests/refmath.py), or checked by the defining equations (A x = 0, P A = L U, the
four Penrose equations, ...) where the answer is not unique.            python3 tests/test_linalg.py"""
import os, sys, random, itertools, math
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()
Z, ONE = R.ZERO, R.ONE

# ------------------------------------------------------------------------------------------- python references (Gaussian rationals)
def mm(A, B): return [[sum((A[i][k] * B[k][j] for k in range(len(B))), Z) for j in range(len(B[0]))] for i in range(len(A))]
def madd(A, B): return [[a + b for a, b in zip(r, s)] for r, s in zip(A, B)]
def mscale(c, A): return [[c * a for a in r] for r in A]
def tr(A): return [list(r) for r in zip(*A)]
def ht(A): return [[a.conj() for a in r] for r in tr(A)]
def ident(n): return [[ONE if i == j else Z for j in range(n)] for i in range(n)]
def mvec(A, v): return [sum((a * x for a, x in zip(r, v)), Z) for r in A]
def meq(A, B): return len(A) == len(B) and all(len(r) == len(s) and all(a == b for a, b in zip(r, s)) for r, s in zip(A, B))
def rref(A):
    A = [list(r) for r in A]; m, n = len(A), len(A[0]) if A else 0; r = 0; piv = []
    for c in range(n):
        p = next((i for i in range(r, m) if not A[i][c].iszero()), None)
        if p is None: continue
        A[r], A[p] = A[p], A[r]
        iv = A[r][c].inv(); A[r] = [iv * a for a in A[r]]
        for i in range(m):
            if i != r and not A[i][c].iszero():
                f = A[i][c]; A[i] = [a - f * b for a, b in zip(A[i], A[r])]
        piv.append(c); r += 1
        if r == m: break
    return A, piv
def det(A):
    n = len(A)
    if n == 0: return ONE
    A = [list(r) for r in A]; d = ONE
    for c in range(n):
        p = next((i for i in range(c, n) if not A[i][c].iszero()), None)
        if p is None: return Z
        if p != c: A[c], A[p] = A[p], A[c]; d = -d
        d = d * A[c][c]; iv = A[c][c].inv()
        for i in range(c + 1, n):
            f = A[i][c] * iv; A[i] = [a - f * b for a, b in zip(A[i], A[c])]
    return d
def charpoly(A):
    n = len(A); M = ident(n); c = [ONE]
    # Faddeev-LeVerrier
    Mk = ident(n); coeffs = [ONE]
    for k in range(1, n + 1):
        AM = mm(A, Mk); ck = -(sum((AM[i][i] for i in range(n)), Z)) * R.Q(Fr(1, k))
        coeffs.append(ck); Mk = madd(AM, mscale(ck, ident(n)))
    return list(reversed(coeffs))        # lowest degree first
def peval(p, M):
    n = len(M); out = [[Z] * n for _ in range(n)]
    for c in reversed(p): out = madd(mm(out, M), mscale(c, ident(n)))
    return out
def randq(rng, gauss=False, den=3):
    return R.Q(Fr(rng.randint(-4, 4), rng.randint(1, den)), Fr(rng.randint(-3, 3), rng.randint(1, den)) if gauss else 0)
def rmat(rng, m, n, gauss=False, rank=None):
    A = [[randq(rng, gauss) for _ in range(n)] for _ in range(m)]
    if rank is not None and rank < min(m, n):                      # force a rank deficiency: make the last rows combinations of the first
        for i in range(rank, m):
            cs = [randq(rng, gauss) for _ in range(rank)]
            A[i] = [sum((c * A[k][j] for k, c in enumerate(cs)), Z) for j in range(n)]
    return A

# ------------------------------------------------------------------------------------------- the human text of values
def hq(q):
    def f(x):
        t = f"{x.numerator}" + (f"/{x.denominator}" if x.denominator != 1 else "")
        return f"({t})" if x < 0 else t
    if q.i == 0: return f(q.r)
    if q.r == 0: return f"{f(q.i)}*i"
    return f"({f(q.r)} + {f(q.i)}*i)"
def hv(v): return "[" + ", ".join(hq(x) for x in v) + "]"
def hm(A): return "[" + ", ".join(hv(r) for r in A) + "]"

# ------------------------------------------------------------------------------------------- the program
rng = random.Random(20261026)
STM = []       # (name, class, expression)
VAL = {}       # name -> python data
def st(name, cls, expr): STM.append((name, cls, expr))
M, V, S = "List(List(\\Q))", "List(\\Q)", "\\Q"

A2 = [[R.Q(2), R.Q(1)], [R.Q(1), R.Q(3)]]
A3 = rmat(rng, 3, 3, True); A3b = rmat(rng, 3, 3)
B3 = rmat(rng, 3, 3, True)
Asing = [[R.Q(1), R.Q(2), R.Q(3)], [R.Q(2), R.Q(4), R.Q(6)], [R.Q(1), R.Q(0), R.Q(1)]]
Arect = rmat(rng, 3, 4, True); Arect2 = rmat(rng, 4, 2); Adef = rmat(rng, 4, 4, rank=2)
Arank = rmat(rng, 5, 3, True, rank=2)
u = [randq(rng, True) for _ in range(3)]; w = [randq(rng, True) for _ in range(3)]
u4 = [randq(rng, True) for _ in range(4)]

# vectors
st('v1', V, f"vsub({hv(u)}, {hv(w)})"); st('v2', V, f"vneg({hv(u)})"); st('v3', S, f"hdot({hv(u)}, {hv(w)})"); st('v4', S, f"vnorm2({hv(u)})")
st('v5', V, f"proj({hv(u)}, {hv(w)})"); st('v6', V, f"cross({hv(u)}, {hv(w)})"); st('v7', M, f"outer({hv(u)}, {hv(w)})")
st('v8', V, f"proj({hv(u)}, {hv([Z, Z, Z])})")
# arithmetic, operators
st('m1', M, f"msub({hm(A3)}, {hm(B3)})"); st('m2', M, f"mneg({hm(A3)})"); st('m3', M, f"mscale({hq(R.Q(Fr(1, 2), 1))}, {hm(A3)})")
st('m4', M, f"hadamard({hm(A3)}, {hm(B3)})"); st('m5', M, f"htranspose({hm(A3)})"); st('m6', M, f"kron({hm(A2)}, {hm(Arect2)})")
st('m7', M, f"blockdiag({hm(A2)}, {hm(A3)})"); st('m8', M, "zeros(2, 3)"); st('m9', S, f"trace({hm(A3)})"); st('ma', V, f"mdiag({hm(A3)})")
st('mb', M, f"diagm({hv(u)})"); st('mc', M, f"mpow({hm(A3b)}, 3)"); st('md', M, f"mpow({hm(A3b)}, 0)"); st('me', M, f"mpow({hm(A2)}, -2)")
st('o1', M, f"{hm(A3)} + {hm(B3)}"); st('o2', M, f"{hm(A3)} - {hm(B3)}"); st('o3', M, f"{hm(A3)} * {hm(B3)}"); st('o4', M, f"2 * {hm(A3)}")
st('o5', V, f"{hm(A3)} * {hv(u)}"); st('o6', M, f"-{hm(A3)}"); st('o7', M, f"{hm(A3b)} ^ 3"); st('o8', M, f"{hm(A2)} ^ -1")
st('o9', S, "1 + 2"); st('oa', S, "(1 + i) * (2 - i)")                     # the scalar operators still work
# predicates
PRED = [('p1', f"issymmetric({hm(A2)})", True), ('p2', f"issymmetric({hm(A3)})", False), ('p3', f"ishermitian({hm(madd(A3, ht(A3)))})", True),
        ('p4', f"ishermitian({hm(A3)})", False), ('p5', f"isunitary({hm([[R.Q(0), R.Q(1)], [R.Q(1), R.Q(0)]])})", True),
        ('p6', f"isunitary({hm(A2)})", False), ('p7', f"isdiagonal({hm(diag3 := [[R.Q(1), Z, Z], [Z, R.Q(2), Z], [Z, Z, R.Q(3)]])})", True),
        ('p8', f"isdiagonal({hm(A3)})", False), ('p9', f"isupper({hm([[R.Q(1), R.Q(2)], [Z, R.Q(3)]])})", True), ('pa', f"islower({hm([[R.Q(1), R.Q(2)], [Z, R.Q(3)]])})", False),
        ('pb', f"isinvertible({hm(A3b)})", not det(A3b).iszero()), ('pc', f"isinvertible({hm(Asing)})", False),
        ('pd', f"islower({hm([[R.Q(1), Z], [R.Q(2), R.Q(3)]])})", True)]
for n, e, _ in PRED: st(n, "Bool", e)
# echelon form, rank, subspaces
for k, A in enumerate([A3, Asing, Arect, Adef, Arank, A2]):
    st(f'r{k}', M, f"rref({hm(A)})"); st(f'k{k}', "\\NN", f"rank({hm(A)})"); st(f'n{k}', M, f"nullspace({hm(A)})")
    st(f'c{k}', M, f"colspace({hm(A)})"); st(f'w{k}', M, f"rowspace({hm(A)})")
# determinants, adjugate, characteristic and minimal polynomial
for k, A in enumerate([A2, A3, A3b, Asing]):
    st(f'd{k}', S, f"det({hm(A)})"); st(f'j{k}', M, f"adjugate({hm(A)})"); st(f'q{k}', V, f"charpoly({hm(A)})"); st(f'h{k}', V, f"minpoly({hm(A)})")
st('mn', S, f"minor({hm(A3)}, 1, 2)"); st('cf', S, f"cofactor({hm(A3)}, 1, 2)"); st('cf2', S, f"cofactor({hm(A3)}, 0, 0)")
# eigenvalues: exact ones, with multiplicity
EIG = [[R.Q(2), R.Q(0), R.Q(0)], [R.Q(0), R.Q(2), R.Q(1)], [R.Q(0), R.Q(0), R.Q(3)]]
ROT = [[R.Q(0), R.Q(-1)], [R.Q(1), R.Q(0)]]
SYM = [[R.Q(2), R.Q(1)], [R.Q(1), R.Q(2)]]
NOEIG = [[R.Q(0), R.Q(2)], [R.Q(1), R.Q(0)]]
st('e1', "List(Pair(\\Q, \\NN))", f"eigenvals({hm(EIG)})"); st('e2', "List(Pair(\\Q, \\NN))", f"eigenvals({hm(ROT)})")
st('e3', "List(Pair(\\Q, \\NN))", f"eigenvals({hm(SYM)})"); st('e4', "List(Pair(\\Q, \\NN))", f"eigenvals({hm(NOEIG)})")
st('e5', M, f"eigvecs({hm(EIG)}, 2)"); st('e6', M, f"eigvecs({hm(ROT)}, i)"); st('e7', M, f"eigvecs({hm(SYM)}, 3)"); st('e8', M, f"eigvecs({hm(SYM)}, 5)")
st('e9', "List(\\R)", f"eigvals({hm(NOEIG)})"); st('ea', "List(\\R)", f"eigvals({hm(SYM)})")
# systems
bb = [randq(rng, True) for _ in range(3)]; b2 = [randq(rng) for _ in range(2)]
st('s1', "Pair(Bool, Pair(List(\\Q), List(List(\\Q))))", f"linsolve({hm(A3b)}, {hv(bb)})")
st('s2', "Pair(Bool, Pair(List(\\Q), List(List(\\Q))))", f"linsolve({hm(Asing)}, {hv([R.Q(1), R.Q(2), R.Q(1)])})")
st('s3', "Pair(Bool, Pair(List(\\Q), List(List(\\Q))))", f"linsolve({hm(Asing)}, {hv([R.Q(1), R.Q(3), R.Q(1)])})")
st('s4', "Pair(Bool, Pair(List(\\Q), List(List(\\Q))))", f"linsolve({hm(Arect)}, {hv(bb)})")
st('s5', V, f"solve({hm(A3b)}, {hv(bb)})")
# LU
for k, A in enumerate([A3b, [[R.Q(0), R.Q(1), R.Q(2)], [R.Q(1), R.Q(0), R.Q(3)], [R.Q(4), R.Q(-3), R.Q(8)]], [[R.Q(0), R.Q(0), R.Q(1)], [R.Q(0), R.Q(1), R.Q(1)], [R.Q(1), R.Q(1), R.Q(1)]], Asing, [[R.Q(2), R.Q(1)], [R.Q(4), R.Q(3)]]]):
    st(f'l{k}', f"Pair({M}, Pair({M}, {M}))", f"lu({hm(A)})")
LUS = [A3b, [[R.Q(0), R.Q(1), R.Q(2)], [R.Q(1), R.Q(0), R.Q(3)], [R.Q(4), R.Q(-3), R.Q(8)]], [[R.Q(0), R.Q(0), R.Q(1)], [R.Q(0), R.Q(1), R.Q(1)], [R.Q(1), R.Q(1), R.Q(1)]], Asing, [[R.Q(2), R.Q(1)], [R.Q(4), R.Q(3)]]]
# Gram-Schmidt, pseudo-inverse, least squares, Smith, exponential
GSV = [u, w, [randq(rng, True) for _ in range(3)], [u[i] + w[i] for i in range(3)]]
st('g1', M, f"gramschmidt({hm(GSV)})")
for k, A in enumerate([Arect, Arect2, Adef, Asing, A3b, Arank]): st(f'i{k}', M, f"pinv({hm(A)})")
bl = [randq(rng) for _ in range(4)]
st('t1', V, f"lstsq({hm(Arect2)}, {hv(bl)})")
SM = [[[R.Q(2), R.Q(4), R.Q(4)], [R.Q(-6), R.Q(6), R.Q(12)], [R.Q(10), R.Q(-4), R.Q(-16)]], [[R.Q(2), R.Q(0)], [R.Q(0), R.Q(3)]], [[R.Q(1), R.Q(2), R.Q(3)], [R.Q(4), R.Q(5), R.Q(6)], [R.Q(7), R.Q(8), R.Q(9)]],
      [[R.Q(0), R.Q(0)], [R.Q(0), R.Q(0)]], [[R.Q(6), R.Q(4), R.Q(2)], [R.Q(2), R.Q(4), R.Q(6)]]]
for k, A in enumerate(SM): st(f'z{k}', "List(\\NN)", f"smith({hm(A)})")
EXPM = [[R.Q(0), R.Q(1)], [R.Q(-1), R.Q(0)]]
st('x1', "Stream(List(List(\\Q)))", f"matexp({hm(EXPM)})")

def smith_ref(A):
    """invariant factors by integer row/column reduction (independent of the gcd-of-minors method used in the language)"""
    A = [[int(a.r) for a in r] for r in A]; m, n = len(A), len(A[0]); out = []
    t = 0
    while t < min(m, n):
        nz = [(abs(A[i][j]), i, j) for i in range(t, m) for j in range(t, n) if A[i][j] != 0]
        if not nz: break
        _, i, j = min(nz)
        A[t], A[i] = A[i], A[t]
        for r in A: r[t], r[j] = r[j], r[t]
        done = True
        for i in range(t + 1, m):
            q = A[i][t] // A[t][t]
            A[i] = [a - q * b for a, b in zip(A[i], A[t])]
            if A[i][t] != 0: done = False
        for j in range(t + 1, n):
            q = A[t][j] // A[t][t]
            for r in A: r[j] -= q * r[t]
            if A[t][j] != 0: done = False
        if not done: continue
        bad = next(((i, j) for i in range(t + 1, m) for j in range(t + 1, n) if A[i][j] % A[t][t] != 0), None)
        if bad:
            A[t] = [a + b for a, b in zip(A[t], A[bad[0]])]; continue
        out.append(abs(A[t][t])); t += 1
    return out

def main():
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    src = "\n".join(f"{n} in {c} := {e}" for n, c, e in STM)
    P.add_text(src, 'linalg.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep(f"the test program ({len(STM)} statements) passes the class checker — the matrix operators + - * ^ resolve without ambiguity", not errs, str(errs[:2]))
    if errs: return rep.done()
    P.build(); E = Env(P)
    g = lambda n: E.V(P.hum.spec_name(n))
    q = lambda n: E.dq(g(n))
    vec = lambda n: [E.dq(x) for x in E.lst(g(n))]
    mat = lambda n: [[E.dq(x) for x in E.lst(r)] for r in E.lst(g(n))]
    meqq = meq
    # ---- vectors
    ip = lambda a, b: sum((x.conj() * y for x, y in zip(a, b)), Z)
    rep("vsub, vneg, outer, hdot, vnorm2", vec('v1') == [a - b for a, b in zip(u, w)] and vec('v2') == [-a for a in u] and q('v3') == ip(u, w) and q('v4') == ip(u, u)
        and meq(mat('v7'), [[a * b for b in w] for a in u]))
    rep("proj(u, v) = (<v, u>/<v, v>) v  (0 for v = 0);  cross product of two 3-vectors",
        vec('v5') == [ip(w, u) * ip(w, w).inv() * x for x in w] and vec('v8') == [Z, Z, Z] and
        vec('v6') == [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]])
    # ---- arithmetic
    half = R.Q(Fr(1, 2), 1)
    ok = (meq(mat('m1'), madd(A3, mscale(R.Q(-1), B3))) and meq(mat('m2'), mscale(R.Q(-1), A3)) and meq(mat('m3'), mscale(half, A3))
          and meq(mat('m4'), [[a * b for a, b in zip(r, s)] for r, s in zip(A3, B3)]) and meq(mat('m5'), ht(A3)))
    rep("msub, mneg, mscale, hadamard, htranspose", ok)
    K = [[a * b for a in r for b in s] for r in A2 for s in Arect2]
    BD = [r + [Z] * 3 for r in A2] if False else None
    bd = [list(r) + [Z] * 3 for r in A2] + [[Z] * 2 + list(r) for r in A3]
    rep("kron, blockdiag, zeros, trace, mdiag, diagm",
        meq(mat('m6'), K) and meq(mat('m7'), bd) and meq(mat('m8'), [[Z] * 3, [Z] * 3]) and q('m9') == sum((A3[i][i] for i in range(3)), Z)
        and vec('ma') == [A3[i][i] for i in range(3)] and meq(mat('mb'), [[u[i] if i == j else Z for j in range(3)] for i in range(3)]))
    A2inv = [[R.Q(Fr(3, 5)), R.Q(Fr(-1, 5))], [R.Q(Fr(-1, 5)), R.Q(Fr(2, 5))]]
    rep("mpow: A^3, A^0 = I, A^-2 (a power of the inverse)", meq(mat('mc'), mm(A3b, mm(A3b, A3b))) and meq(mat('md'), ident(3)) and meq(mat('me'), mm(A2inv, A2inv)))
    rep("the operators of the human notation on matrices:  A + B,  A - B,  A * B,  2 * A,  A * v,  -A,  A ^ 3,  A ^ -1  (and scalars as before)",
        meq(mat('o1'), madd(A3, B3)) and meq(mat('o2'), madd(A3, mscale(R.Q(-1), B3))) and meq(mat('o3'), mm(A3, B3)) and meq(mat('o4'), mscale(R.Q(2), A3))
        and vec('o5') == mvec(A3, u) and meq(mat('o6'), mscale(R.Q(-1), A3)) and meq(mat('o7'), mm(A3b, mm(A3b, A3b))) and meq(mat('o8'), A2inv)
        and q('o9') == R.Q(3) and q('oa') == R.Q(3, 1))
    rep("issymmetric, ishermitian, isunitary, isdiagonal, isupper, islower, isinvertible",
        all(E.b(g(n)) == want for n, _, want in PRED), str([n for n, _, want in PRED if E.b(g(n)) != want]))
    # ---- echelon form and subspaces
    bad = []
    for k, A in enumerate([A3, Asing, Arect, Adef, Arank, A2]):
        Rr, piv = rref(A)
        r_ = len(piv)
        if not meq(mat(f'r{k}'), Rr): bad.append(('rref', k))
        if int(q(f'k{k}').r) != r_: bad.append(('rank', k))
        N = mat(f'n{k}')
        if len(N) != len(A[0]) - r_ or any(not all(x.iszero() for x in mvec(A, nv)) for nv in N) or rref(N)[1].__len__() != len(N): bad.append(('nullspace', k))
        C = mat(f'c{k}'); Wr = mat(f'w{k}')
        if len(C) != r_ or rref(tr(A) if False else C)[1].__len__() != r_: bad.append(('colspace size', k))
        if C != [[A[i][p] for i in range(len(A))] for p in piv]: bad.append(('colspace', k))
        if not meq(Wr, Rr[:r_]): bad.append(('rowspace', k))
    rep("rref (= the reduced echelon form), rank, nullspace (A x = 0, independent, dimension n - rank), colspace (the pivot columns), rowspace — 6 matrices incl. singular, rectangular, rank-deficient",
        not bad, str(bad[:4]))
    # ---- determinants, adjugate, polynomials
    bad = []
    for k, A in enumerate([A2, A3, A3b, Asing]):
        n = len(A)
        if q(f'd{k}') != det(A): bad.append(('det', k))
        adj = mat(f'j{k}')
        if not meq(mm(A, adj), mscale(det(A), ident(n))): bad.append(('adjugate', k))
        cp = vec(f'q{k}')
        if cp != charpoly(A) or not meq(peval(cp, A), [[Z] * n for _ in range(n)]): bad.append(('charpoly', k))
        mp_ = vec(f'h{k}')
        if mp_[-1] != ONE or not meq(peval(mp_, A), [[Z] * n for _ in range(n)]): bad.append(('minpoly annihilates', k))
        # minimal: no monic polynomial of smaller degree annihilates A -> the powers I..A^(d-1) are independent
        d = len(mp_) - 1
        pw = [ident(n)]
        for _ in range(d - 1): pw.append(mm(pw[-1], A))
        flat = [[x for r in P_ for x in r] for P_ in pw]
        if rref(flat)[1].__len__() != d: bad.append(('minpoly minimal', k))
    rep("det, adjugate (A adj(A) = det(A) I), charpoly (= Faddeev-LeVerrier, annihilates A), minpoly (monic, annihilates A, of least degree) — 4 matrices", not bad, str(bad[:4]))
    rep("minor, cofactor (sign (-1)^(i+j))", q('mn') == det([[A3[r][c] for c in range(3) if c != 2] for r in range(3) if r != 1])
        and q('cf') == -det([[A3[r][c] for c in range(3) if c != 2] for r in range(3) if r != 1]) and q('cf2') == det([[A3[r][c] for c in range(1, 3)] for r in range(1, 3)]))
    # ---- eigenvalues and eigenvectors
    def pairs(n): return [(E.dq(a), int(E.dq(b).r)) for a, b in (to_pair(p) for p in E.lst(g(n)))]
    rep("eigenvals: diag-like [2,2,3] -> (2, 2), (3, 1);  rotation by 90 deg -> -i, i;  [[2,1],[1,2]] -> 1, 3;  [[0,2],[1,0]] (eigenvalues +-sqrt 2) has none in Q(i)",
        pairs('e1') == [(R.Q(2), 2), (R.Q(3), 1)] and pairs('e2') == [(R.Q(0, -1), 1), (R.Q(0, 1), 1)] and pairs('e3') == [(R.Q(1), 1), (R.Q(3), 1)] and pairs('e4') == [])
    def eigcheck(n, A, lam, dim):
        V_ = mat(n)
        return len(V_) == dim and all(meq([[a] for a in mvec(A, x)], [[lam * c] for c in x]) for x in V_) and (rref(V_)[1].__len__() == dim if V_ else True)
    rep("eigvecs: A x = lambda x, independent, of the right dimension (geometric multiplicity 2 for lambda = 2 of [2,2,3] ...)",
        eigcheck('e5', EIG, R.Q(2), 2) and eigcheck('e6', ROT, R.Q(0, 1), 1) and eigcheck('e7', SYM, R.Q(3), 1) and mat('e8') == [])
    def lazy(n, k): return [complex(float((z := E.dq(E.nth(x, k))).r), float(z.i)) for x in E.lst(g(n))]
    ev = lazy('e9', 20); ev2 = lazy('ea', 20)
    rep("eigvals (numerical, lazy, element n within 2^-n): +-sqrt 2 for [[0,2],[1,0]], 1 and 3 for [[2,1],[1,2]]",
        sorted(abs(x.real) for x in ev) and all(abs(abs(x) - math.sqrt(2)) < 1e-5 for x in ev) and len(ev) == 2 and abs(sum(ev)) < 1e-5
        and sorted(round(x.real, 4) for x in ev2) == [1.0, 3.0])
    # ---- linear systems
    def unpack(n):
        okf, rest = to_pair(g(n)); xp, nb = to_pair(rest)
        return E.b(okf), [E.dq(x) for x in E.lst(xp)], [[E.dq(x) for x in E.lst(r)] for r in E.lst(nb)]
    ok1, x1, n1 = unpack('s1'); ok2, x2, n2 = unpack('s2'); ok3, x3, n3 = unpack('s3'); ok4, x4, n4 = unpack('s4')
    rep("linsolve: a unique solution (A x = b, no kernel); a consistent singular system (particular solution + kernel basis); an inconsistent one; an under-determined rectangular one",
        ok1 and mvec(A3b, x1) == bb and not n1 and ok2 and mvec(Asing, x2) == [R.Q(1), R.Q(2), R.Q(1)] and len(n2) == 1
        and not ok3 and ok4 and mvec(Arect, x4) == bb and len(n4) == 1 and vec('s5') == x1 if not det(A3b).iszero() else True)
    # ---- LU
    bad = []
    for k, A in enumerate(LUS):
        Pm, rest = to_pair(g(f'l{k}')); Lm, Um = to_pair(rest)
        Pm, Lm, Um = [[[E.dq(x) for x in E.lst(r)] for r in E.lst(X)] for X in (Pm, Lm, Um)]
        n = len(A)
        isperm = all(sorted(map(str, r)) == sorted(map(str, ([Z] * (n - 1) + [ONE]))) for r in Pm) and all(sum((r[j] for r in Pm), Z) == ONE for j in range(n))
        lower1 = all(Lm[i][i] == ONE and all(Lm[i][j].iszero() for j in range(i + 1, n)) for i in range(n))
        upper = all(Um[i][j].iszero() for i in range(n) for j in range(i))
        if not (isperm and lower1 and upper and meq(mm(Pm, A), mm(Lm, Um))): bad.append((k, isperm, lower1, upper))
    rep("lu: P A = L U with P a permutation matrix, L unit lower triangular, U upper triangular — including a zero leading pivot, a singular matrix and a matrix with a zero first column", not bad, str(bad))
    # ---- Gram-Schmidt
    GS = mat('g1')
    ortho = all(ip(a, b).iszero() for i, a in enumerate(GS) for b in GS[:i]) and all(not ip(a, a).iszero() for a in GS)
    rep("gramschmidt: orthogonal vectors, no zero vector, the same span (the dependent fourth vector is dropped)",
        ortho and len(GS) == 3 and rref(GSV)[1].__len__() == 3 and rref(GS)[1].__len__() == 3 and rref([list(a) for a in GSV] + [list(a) for a in GS])[1].__len__() == 3)
    # ---- pseudo-inverse and least squares: the four Penrose equations
    bad = []
    for k, A in enumerate([Arect, Arect2, Adef, Asing, A3b, Arank]):
        Pi = mat(f'i{k}')
        AP, PA = mm(A, Pi), mm(Pi, A)
        if not (meq(mm(AP, A), A) and meq(mm(PA, Pi), Pi) and meq(ht(AP), AP) and meq(ht(PA), PA)): bad.append(k)
    rep("pinv: the four Penrose equations A A+ A = A, A+ A A+ = A+, (A A+)^H = A A+, (A+ A)^H = A+ A — wide, tall, rank-deficient, singular, invertible", not bad, str(bad))
    x = vec('t1'); res = [bl[i] - c for i, c in enumerate(mvec(Arect2, x))]
    rep("lstsq: the residual b - A x is orthogonal to the columns of A (normal equations A^H (b - A x) = 0)", all(c.iszero() for c in mvec(ht(Arect2), res)))
    rep("smith: the invariant factors of integer matrices agree with an independent row/column reduction",
        all([int(E.dq(x).r) for x in E.lst(g(f'z{k}'))] == smith_ref(A) for k, A in enumerate(SM)), str([[int(E.dq(x).r) for x in E.lst(g(f'z{k}'))] for k in range(len(SM))]))
    # ---- matrix exponential
    S_ = ident(2); T = ident(2); parts = []
    for n in range(0, 7):
        parts.append([r[:] for r in S_] if n == 0 else None)
    Sn = [[Z, Z], [Z, Z]]; T = ident(2); ref = []
    for n in range(7):
        Sn = madd(Sn, T); ref.append([r[:] for r in Sn]); T = mscale(R.Q(Fr(1, n + 1)), mm(T, EXPM))
    got = [[[E.dq(x) for x in E.lst(r)] for r in E.lst(E.nth(g('x1'), n))] for n in range(7)]
    rep("matexp: element n of e^A is the exact partial sum A^0/0! + ... + A^n/n! (A = rotation generator)", all(meq(a, b) for a, b in zip(got, ref)))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
