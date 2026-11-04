"""test_galois.py -- Galois theory (lib/galois.imo) used from the HUMAN notation: every statement goes through doc 2, overload resolution and the
class checker, is evaluated in the language, decoded, and compared with an independent python computation: textbook Galois groups of
quadratics, cubics and quartics (names, orders, cycle types of the elements, the subgroup lattice by brute force), the factorisation
patterns modulo primes (a theorem of Dedekind and Chebotarev: every pattern of a good prime is the cycle type of an element of the group),
the unit groups (Z/n)^x, the factorisation of cyclotomic polynomials modulo p, Eisenstein's criterion.
python3 tests/test_galois.py"""
import os, sys, itertools, math, cmath
from math import gcd
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()

def ph(f): return "[" + ", ".join((f"({c})" if c < 0 else str(c)) for c in f) + "]"
def phq(f):
    def one(c):
        c = Fr(c); t = str(c.numerator) + (f"/{c.denominator}" if c.denominator != 1 else "")
        return f"({t} in \\QQ)" if c.denominator != 1 else (f"({t})" if c < 0 else t)
    return "[" + ", ".join(one(c) for c in f) + "]"
def pmul(f, g):
    r = [0] * (len(f) + len(g) - 1)
    for i, a in enumerate(f):
        for j, b in enumerate(g): r[i + j] += a * b
    return r

# ------------------------------------------------------------------------------------------------ the polynomials (lowest degree first)
# (name, polynomial, expected group name, expected order, expected number of points)
KNOWN = [
    ("x^2 - 2", [-2, 0, 1], "C2", 2), ("x^2 + 1", [1, 0, 1], "C2", 2), ("x^2 - 4", [-4, 0, 1], "1", 1), ("x - 1", [-1, 1], "1", 1), ("x^2", [0, 0, 1], "1", 1),
    ("x^3 - 2", [-2, 0, 0, 1], "S3", 6), ("x^3 - 3x + 1", [1, -3, 0, 1], "C3", 3), ("x^3 + x + 1", [1, 1, 0, 1], "S3", 6), ("x^3 - x", [0, -1, 0, 1], "1", 1),
    ("(x^2 - 2)(x - 1)", pmul([-2, 0, 1], [-1, 1]), "C2", 2), ("(x^3 - 2)(x + 3)", pmul([-2, 0, 0, 1], [3, 1]), "S3", 6), ("2x^3 - 6x + 2", [2, -6, 0, 2], "C3", 3),
    ("x^4 - 2", [-2, 0, 0, 0, 1], "D4", 8), ("x^4 + 1", [1, 0, 0, 0, 1], "V4", 4), ("x^4 - 4x^2 + 2", [2, 0, -4, 0, 1], "C4", 4), ("x^4 + x^3 + x^2 + x + 1", [1, 1, 1, 1, 1], "C4", 4),
    ("x^4 - x - 1", [-1, -1, 0, 0, 1], "S4", 24), ("x^4 + 8x + 12", [12, 8, 0, 0, 1], "A4", 12), ("x^4 + 5x^2 + 5", [5, 0, 5, 0, 1], "C4", 4), ("x^4 - 10x^2 + 1", [1, 0, -10, 0, 1], "V4", 4),
    ("x^4 + 3", [3, 0, 0, 0, 1], "D4", 8), ("x^4 - 3", [-3, 0, 0, 0, 1], "D4", 8), ("(x^2 - 2)(x^2 - 3)", pmul([-2, 0, 1], [-3, 0, 1]), "V4", 4),
    ("(x^2 - 2)(x^2 - 8)", pmul([-2, 0, 1], [-8, 0, 1]), "C2", 2), ("(x^2 - 2)(x^2 - 6)", pmul([-2, 0, 1], [-6, 0, 1]), "V4", 4), ("x^4 + 4", [4, 0, 0, 0, 1], "C2", 2),
    ("2x^4 - 4", [-4, 0, 0, 0, 2], "D4", 8), ("(x^2 + 1)(x + 2)(x - 3)", pmul(pmul([1, 0, 1], [2, 1]), [-3, 1]), "C2", 2), ("x^4 - 2x^2 - 1", [-1, 0, -2, 0, 1], "D4", 8),
    ("x^4 - 6x^2 + 1 = (x^2 - 2x - 1)(x^2 + 2x - 1)", [1, 0, -6, 0, 1], "C2", 2), ("(x^2 - 3)^2 (squares ignored)", pmul([-3, 0, 1], [-3, 0, 1]), "C2", 2),
    ("5", [5], "1", 1),
]
UNSUPPORTED = [("x^5 - 2", [-2, 0, 0, 0, 0, 1]), ("x^5 - x - 1", [-1, -1, 0, 0, 0, 1])]
CENSUS_BOUND = 30

STM = []
def st(name, cls, expr): STM.append((name, cls, expr))
NN, LN = "\\NN", "List(\\NN)"
for k, (nm, f, g, o) in enumerate(KNOWN):
    st(f'gg{k}', f"List({LN})", f"galoisgroup({phq(f)})"); st(f'gn{k}', "String", f"galoisname({phq(f)})"); st(f'go{k}', NN, f"galoisorder({phq(f)})")
    st(f'gc{k}', f"List({LN})", f"frobeniuscensus({ph(f)}, {CENSUS_BOUND})")
    if o <= 12: st(f'gi{k}', LN, f"intermediatefielddegrees({phq(f)})")
    st(f'gd{k}', "Bool", f"isdiscsquare({phq(f)})")
for k, (nm, f) in enumerate(UNSUPPORTED): st(f'gu{k}', f"List({LN})", f"galoisgroup({phq(f)})"); st(f'gv{k}', "String", f"galoisname({phq(f)})"); st(f'gw{k}', NN, f"galoisorder({phq(f)})")
UN = [1, 2, 3, 4, 5, 7, 8, 9, 12, 15, 16, 20]
for n in UN: st(f'ug{n}', f"List({LN})", f"unitgroup({n})"); st(f'gz{n}', f"List({LN})", f"galoiscyclotomic({n})")
CYC = [(2, 3), (2, 5), (2, 7), (3, 4), (3, 5), (3, 8), (5, 8), (7, 4), (5, 12), (2, 9), (11, 7)]
for k, (p, n) in enumerate(CYC): st(f'cy{k}', f"List({LN})", f"cyclotomicfactors({p}, {n})")
GFG = [(2, 2), (2, 3), (3, 2), (2, 4)]
for k, (p, n) in enumerate(GFG): st(f'F{k}', f"Pair({NN}, {LN})", f"gf({p}, {n})"); st(f'ga{k}', f"List({LN})", f"gfgalois(F{k})"); st(f'ge{k}', f"List({LN})", f"gfelements(F{k})")
FP = [([-2, 0, 1], 3), ([-2, 0, 1], 7), ([-2, 0, 1], 2), ([-2, 0, 0, 1], 5), ([-2, 0, 0, 1], 7), ([-2, 0, 0, 1], 13), ([1, 1, 1, 1, 1], 11), ([1, 1, 1, 1, 1], 5), ([-1, -1, 0, 0, 1], 11), ([-1, -1, 0, 0, 1], 283),
      ([-2, 0, 0, 0, 1], 7), ([-2, 0, 0, 0, 1], 17)]
for k, (f, p) in enumerate(FP): st(f'fp{k}', LN, f"frobeniuspattern({ph(f)}, {p})"); st(f'fg{k}', "Bool", f"isgoodprime({ph(f)}, {p})")
EIS = [[-3, 0, 1], [2, 0, 0, 0, 1], [-2, 0, 0, 1], [1, 0, 1], [5, 10, 0, 0, 0, 1], [-4, 0, 1], [6, 3, 0, 3], [5], [0, 0, 1], [3, -9, 6], [9, 3, 1], [-12, 6, 0, 1], [14, 7, 21, 3]]
for k, f in enumerate(EIS): st(f'ei{k}', NN, f"eisensteinprime({ph(f)})"); st(f'ej{k}', "Bool", f"iseisenstein({ph(f)})")
QUARTICS = [[-2, 0, 0, 0, 1], [1, 0, 0, 0, 1], [-1, -1, 0, 0, 1], [12, 8, 0, 0, 1], [2, 0, -4, 0, 1], [3, 5, -1, 2, 1]]
for k, f in enumerate(QUARTICS): st(f'rc{k}', "List(\\Q)", f"resolventcubic({phq(f)})")
st('rc9', "List(\\Q)", "resolventcubic([1, 2, 3])")

# ------------------------------------------------------------------------------------------------ python references
def cycle_type(p):
    seen, out = set(), []
    for i in range(len(p)):
        if i in seen: continue
        j, l = i, 0
        while j not in seen: seen.add(j); j = p[j]; l += 1
        out.append(l)
    return tuple(sorted(out))
def compose(p, q): return tuple(p[i] for i in q)
def is_group(G):
    S = set(map(tuple, G)); n = len(G[0]) if G else 0
    return tuple(range(n)) in S and all(compose(a, b) in S for a in S for b in S) and all(sorted(a) == list(range(n)) for a in S)
def closure(gens, n):
    S = {tuple(range(n))}; frontier = [tuple(range(n))]
    while frontier:
        new = []
        for a in frontier:
            for g in gens:
                b = compose(g, a)
                if b not in S: S.add(b); new.append(b)
        frontier = new
    return frozenset(S)
def subgroups_ref(G):
    G = [tuple(g) for g in G]; n = len(G[0]); subs = {frozenset([tuple(range(n))])}
    for k in (1, 2, 3):
        for gens in itertools.combinations(G, k):
            subs.add(closure(gens, n))
        if len(subs) > 0 and k == 2 and len(G) <= 24: pass
    return subs
def type_counts(G):
    c = {}
    for g in G:
        t = cycle_type(g); c[t] = c.get(t, 0) + 1
    return c
EXPECT_TYPES = {
    "S4": {(1, 1, 1, 1): 1, (1, 1, 2): 6, (2, 2): 3, (1, 3): 8, (4,): 6},
    "A4": {(1, 1, 1, 1): 1, (2, 2): 3, (1, 3): 8},
    "V4": {(1, 1, 1, 1): 1, (2, 2): 3},
    "D4": {(1, 1, 1, 1): 1, (2, 2): 3, (1, 1, 2): 2, (4,): 2},
    "C4": {(1, 1, 1, 1): 1, (2, 2): 1, (4,): 2},
    "S3": {(1, 1, 1): 1, (1, 2): 3, (3,): 2},
    "C3": {(1, 1, 1): 1, (3,): 2},
}
def croots(f):
    f = [complex(Fr(c)) for c in f]; n = len(f) - 1
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
def euler_phi(n): return sum(1 for a in range(1, n + 1) if gcd(a, n) == 1)
def unit_orders(n):
    c = {}
    for a in range(n):
        if gcd(a, n) != 1: continue
        k, x = 1, a % n
        while x % n != 1 % n: x = x * a % n; k += 1
        c[k] = c.get(k, 0) + 1
    return c
# polynomials over GF(p) by trial division (as in test_field)
def tr(f):
    f = list(f)
    while f and f[-1] == 0: f.pop()
    return f
def pdivmod_p(p, f, g):
    f = tr([c % p for c in f]); g = tr([c % p for c in g]); q = [0] * max(len(f) - len(g) + 1, 0); inv = pow(g[-1], -1, p)
    while len(f) >= len(g) and f:
        c = f[-1] * inv % p; k = len(f) - len(g); q[k] = c
        for j, y in enumerate(g): f[k + j] = (f[k + j] - c * y) % p
        f = tr(f)
    return tr(q), f
def monics(p, d):
    for t in itertools.product(range(p), repeat=d): yield list(t) + [1]
def irreducible_p(p, f):
    n = len(f) - 1
    for d in range(1, n // 2 + 1):
        for g in monics(p, d):
            if not pdivmod_p(p, f, g)[1]: return False
    return n >= 1
def pattern_ref(p, f):
    f = tr([c % p for c in f]); out = []
    f = [c * pow(f[-1], -1, p) % p for c in f]
    for d in range(1, len(f)):
        for g in monics(p, d):
            if len(g) > len(f): break
            if not irreducible_p(p, g): continue
            while len(f) >= len(g) and len(f) > 1 and not pdivmod_p(p, f, g)[1]:
                f = pdivmod_p(p, f, g)[0]; out.append(d)
        if len(f) == 1: break
    return sorted(out)
def disc_ref(f):
    n = len(f) - 1
    if n < 1: return 0
    rs = croots(f); lead = Fr(f[-1])
    d = 1
    for i in range(n):
        for j in range(i): d *= (rs[i] - rs[j]) ** 2
    return d * float(lead) ** (2 * n - 2)
def cyclotomic_ref(n):
    f = [-1] + [0] * (n - 1) + [1]
    for d in range(1, n):
        if n % d == 0:
            g = cyclotomic_ref(d)
            q = []; r = list(f)
            while len(r) >= len(g):
                c = r[-1] // g[-1]; k = len(r) - len(g); q.append((k, c))
                for j, y in enumerate(g): r[k + j] -= c * y
                while r and r[-1] == 0: r.pop()
            f = [0] * (max(k for k, _ in q) + 1) if q else [1]
            for k, c in q: f[k] = c
    return f
def eisenstein_ref(f):
    if len(f) < 2: return 0
    for p in range(2, 200):
        if all(p % q for q in range(2, p)) and f[-1] % p and all(c % p == 0 for c in f[:-1]) and f[0] % (p * p): return p
    return 0

def main():
    SRC = "\n".join(f"{n} in {c} := {e}" for n, c, e in STM)
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'galois.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("the test program passes the class checker", not errs, str(errs[:2]))
    if errs: return rep.done()
    P.build(); E = Env(P)
    V = lambda n: E.V(P.hum.spec_name(n))
    nat = lambda v: int(E.dq(v).r)
    ns = lambda n: [nat(c) for c in E.lst(V(n))]
    nss = lambda n: [[nat(c) for c in E.lst(l)] for l in E.lst(V(n))]
    def tx(n): return ''.join(chr(int(E.dq(c).r)) for c in E.lst(V(n)))
    # ---- Galois groups of the known polynomials
    bad = []
    for k, (nm, f, name, order) in enumerate(KNOWN):
        G = nss(f'gg{k}')
        if tx(f'gn{k}') != name or nat(V(f'go{k}')) != order or len(G) != order or not is_group(G):
            bad.append((nm, tx(f'gn{k}'), nat(V(f'go{k}')), len(G)))
            continue
        strip = lambda c: {tuple(x for x in t if x > 1): n for t, n in c.items()}      # fixed points (the rational roots) do not matter
        if name in EXPECT_TYPES:
            ok_t = strip(type_counts(G)) == strip(EXPECT_TYPES[name])
            if name == "V4": ok_t = ok_t or strip(type_counts(G)) == {(): 1, (2,): 2, (2, 2): 1}      # V4 acting on two pairs of roots
            if not ok_t: bad.append((nm, 'types', type_counts(G)))
    rep(f"galoisgroup / galoisname / galoisorder: {len(KNOWN)} polynomials (quadratics, cubics, quartics, reducible products, constants, squares) — name, order, a permutation group with the cycle types of S4, A4, V4, D4, C4, S3, C3", not bad, str(bad[:3]))
    rep("galoisgroup of x^5 - 2 and x^5 - x - 1 (degree 5): [] / the empty name / order 0 — outside the cases handled",
        all(nss(f'gu{k}') == [] and tx(f'gv{k}') == "" and nat(V(f'gw{k}')) == 0 for k in range(len(UNSUPPORTED))))
    # ---- the Frobenius census is contained in the cycle types of the group (Dedekind), and the group types are met (Chebotarev), checked on the unions
    bad, miss = [], []
    for k, (nm, f, name, order) in enumerate(KNOWN):
        G = nss(f'gg{k}')
        types = set()
        for g in G:
            # Frobenius cycle types act on ALL the roots of the squarefree part: the roots of the linear factors are fixed points
            types.add(tuple(sorted(cycle_type(g))))
        cen = [tuple(c) for c in nss(f'gc{k}')]
        for c in cen:
            if c not in types: bad.append((nm, c, sorted(types)))
        if set(types) - set(cen): miss.append((nm, sorted(set(types) - set(cen))))
    rep(f"frobeniuscensus up to {CENSUS_BOUND}: every cycle type met by a Frobenius element at a good prime is the cycle type of an element of the computed Galois group (Dedekind) — a refutation test for the group", not bad, str(bad[:3]))
    print(f"      (types of the group not yet met up to {CENSUS_BOUND}, by Chebotarev only a matter of more primes: {len(miss)} of {len(KNOWN)} polynomials)")
    # ---- the lattice of intermediate fields
    bad = []
    for k, (nm, f, name, order) in enumerate(KNOWN):
        if order > 12: continue
        G = nss(f'gg{k}'); subs = subgroups_ref(G)
        want = sorted(order // len(H) for H in subs)
        if ns(f'gi{k}') != want: bad.append((nm, ns(f'gi{k}'), want))
    rep("intermediatefielddegrees: [G : H] for all subgroups H of the Galois group (the subgroups found independently by closing the subsets of at most three elements)", not bad, str(bad[:3]))
    # ---- discriminant square
    bad = []
    for k, (nm, f, name, order) in enumerate(KNOWN):
        d = disc_ref(f); d = d.real if isinstance(d, complex) else d
        sq = d > 1e-6 and abs(math.sqrt(d) - round(math.sqrt(d))) < 1e-6
        if len(f) > 2 and abs(d) > 1e-6 and E.b(V(f'gd{k}')) != bool(sq): bad.append((nm, d))
    rep("isdiscsquare against the discriminant computed from the numerical roots (a perfect square or not)", not bad, str(bad[:3]))
    # ---- unit groups
    bad = []
    for n in UN:
        for key in (f'ug{n}', f'gz{n}'):
            G = nss(key); co = {}
            for g in G:
                t = cycle_type(g)
                co[t[0] if t else 1] = co.get(t[0] if t else 1, 0) + 1
            if len(G) != euler_phi(n) or not is_group(G) or co != unit_orders(n): bad.append((key, len(G), co, unit_orders(n)))
    rep(f"unitgroup / galoiscyclotomic for n in {UN}: the regular permutation group of (Z/n)^x — order phi(n), a group, the same element orders", not bad, str(bad[:2]))
    # ---- cyclotomic polynomials modulo p
    bad = []
    for k, (p, n) in enumerate(CYC):
        fs = nss(f'cy{k}'); order = next(m for m in range(1, 100) if pow(p, m, n) == 1 % n)
        prod = [1]
        for g in fs:
            r = [0] * (len(prod) + len(g) - 1)
            for i, a in enumerate(prod):
                for j, b in enumerate(g): r[i + j] = (r[i + j] + a * b) % p
            prod = tr(r)
        phi = tr([c % p for c in cyclotomic_ref(n)])
        if not (all(len(g) - 1 == order for g in fs) and len(fs) * order == euler_phi(n) and prod == phi): bad.append((p, n, fs))
    rep("cyclotomicfactors(p, n): phi(n)/ord_n(p) irreducible factors of degree ord_n(p) whose product is Phi_n mod p (11 pairs)", not bad, str(bad[:2]))
    # ---- finite field Galois groups
    bad = []
    for k, (p, n) in enumerate(GFG):
        G = nss(f'ga{k}'); els = [[nat(c) for c in E.lst(e)] for e in E.lst(V(f'ge{k}'))]
        frob = tuple(els.index(tr([c for c in pow_el(p, [nat(c) for c in E.lst(to_pair(V(f'F{k}'))[1])], e)])) for e in els)
        want = closure([frob], len(els))
        if not (len(G) == n and is_group(G) and frozenset(map(tuple, G)) == want): bad.append((p, n, len(G)))
    rep("gfgalois: the cyclic group of order n generated by the Frobenius x -> x^p on the elements of GF(p^n) (4 fields)", not bad, str(bad))
    # ---- Frobenius patterns, good primes
    bad = []
    for k, (f, p) in enumerate(FP):
        disc = disc_ref(f); good = (f[-1] % p != 0) and abs(round(abs(disc)) % p) > 0
        if E.b(V(f'fg{k}')) != bool(good and p > 1): bad.append(('good', f, p))
        if ns(f'fp{k}') != pattern_ref(p, f): bad.append(('pattern', f, p, ns(f'fp{k}'), pattern_ref(p, f)))
    rep("frobeniuspattern (degrees of the factors modulo p, trial division) and isgoodprime (p divides neither the leading coefficient nor the discriminant) for 12 cases", not bad, str(bad[:3]))
    # ---- Eisenstein
    bad = [(f, nat(V(f'ei{k}')), eisenstein_ref(f)) for k, f in enumerate(EIS) if nat(V(f'ei{k}')) != eisenstein_ref(f) or E.b(V(f'ej{k}')) != bool(eisenstein_ref(f))]
    rep("eisensteinprime / iseisenstein against a direct test of the criterion (13 polynomials)", not bad, str(bad[:3]))
    # ---- resolvent cubic: its roots are alpha1 alpha2 + alpha3 alpha4, ...
    bad = []
    for k, f in enumerate(QUARTICS):
        R = [Fr(c) for c in [E.dq(c).r for c in E.lst(V(f'rc{k}'))]]
        rs = croots(f); n4 = len(rs)
        vals = [rs[0] * rs[1] + rs[2] * rs[3], rs[0] * rs[2] + rs[1] * rs[3], rs[0] * rs[3] + rs[1] * rs[2]]
        def ev(x):
            r = 0
            for c in reversed(R): r = r * x + complex(c)
            return r
        if len(R) != 4 or R[-1] != 1 or any(abs(ev(v)) > 1e-6 * (1 + abs(v) ** 3) for v in vals): bad.append((f, R))
    rep("resolventcubic: monic cubic whose roots are alpha1 alpha2 + alpha3 alpha4, alpha1 alpha3 + alpha2 alpha4, alpha1 alpha4 + alpha2 alpha3 (6 quartics, one with a leading coefficient)", not bad and E.lst(V('rc9')) == [], str(bad[:2]))
    return rep.done()

def pow_el(p, m, e):
    """e^p reduced modulo (p, m) with the reference polynomial arithmetic"""
    def red(a):
        a = tr([c % p for c in a])
        while len(a) >= len(m):
            c = a[-1]; k = len(a) - len(m)
            a = tr([(x - c * (m[j - k] if 0 <= j - k < len(m) else 0)) % p for j, x in enumerate(a)])
        return a
    r = [1]
    for _ in range(p):
        prod = [0] * (len(r) + len(e) - 1) if r and e else []
        for i, a in enumerate(r):
            for j, b in enumerate(e): prod[i + j] = (prod[i + j] + a * b) % p
        r = red(prod) if prod else []
    return r

sys.exit(0 if run_big(main) else 1)
