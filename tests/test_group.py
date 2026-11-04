"""test_group.py -- group theory (lib/group.imo) used from the HUMAN notation: every statement goes through doc 2, overload
resolution and the class checker, is evaluated in the language, decoded, and compared with an independent python computation
(permutations as tuples, closures by search, brute force over colourings / generator triples / bijections).
python3 tests/test_group.py"""
import os, sys, itertools
from math import gcd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()

SRC = r'''
s3 in List(List(\NN)) := symgroup(3)
s4 in List(List(\NN)) := symgroup(4)
a4 in List(List(\NN)) := altgroup(4)
d4 in List(List(\NN)) := dihedralgroup(4)
q8 in List(List(\NN)) := quaterniongroup
v4 in List(List(\NN)) := kleingroup
c6 in List(List(\NN)) := cyclicgroup(6)
c23 in List(List(\NN)) := directproduct(cyclicgroup(2), cyclicgroup(3))
c4c4 in List(List(\NN)) := semidirect(4, 4, 3)
c2q8 in List(List(\NN)) := directproduct(cyclicgroup(2), quaterniongroup)
h2 in List(List(\NN)) := generate([[1, 0, 2, 3]])
p1 in List(\NN) := pid(4)
p2 in List(\NN) := pid(0)
p3 in List(\NN) := pcompose([1, 2, 0], [1, 0, 2])
p4 in List(\NN) := pcompose([1, 0], [0, 2, 1])
p5 in List(\NN) := pinverse([2, 0, 3, 1])
p6 in List(\NN) := pinverse([])
p7 in \NN := papply([2, 0, 1], 0)
p8 in \NN := papply([2, 0, 1], 7)
p9 in List(\NN) := ppow([1, 2, 3, 4, 0], -2)
p10 in List(\NN) := ppow([1, 2, 3, 4, 0], 0)
p11 in List(\NN) := ppow([1, 0, 3, 4, 2], 7)
p12 in \NN := porder([1, 0, 3, 4, 2])
p13 in \NN := porder([])
p14 in List(List(\NN)) := pcycles([3, 2, 1, 0, 5, 6, 4])
p15 in List(List(\NN)) := pcycles(pid(3))
p16 in List(\NN) := fromcycles(6, [[4, 1, 3], [0, 5]])
p17 in List(\NN) := fromcycles(0, [[2, 0]])
p18 in List(\NN) := fromcycles(3, [[0, 1], [1, 2]])
p19 in \ZZ := psign([1, 0, 2])
p20 in \ZZ := psign([1, 2, 0])
p21 in \ZZ := psign([])
p22 in Bool := iseven([1, 2, 3, 0])
p23 in Bool := iseven([1, 2, 0, 4, 3, 6, 5])
p24 in List(\NN) := cycletype([1, 0, 3, 4, 2, 5])
p25 in List(\NN) := pconj([1, 2, 0, 3], [3, 1, 2, 0])
p26 in Bool := isperm([1, 1, 0])
p27 in Bool := isperm([])
p28 in Bool := isperm([2, 0, 1])
p29 in Bool := isperm([0, 3])
g1 in List(List(\NN)) := generate([[1, 2, 3, 0], [3, 2, 1, 0]])
g2 in List(List(\NN)) := generate([])
g3 in List(List(\NN)) := generate([[1, 0], [0, 2, 1]])
g4 in List(List(\NN)) := symgroup(0)
g5 in List(List(\NN)) := symgroup(1)
g6 in List(List(\NN)) := altgroup(2)
g7 in List(List(\NN)) := cyclicgroup(5)
g8 in List(List(\NN)) := cyclicgroup(0)
g9 in List(List(\NN)) := dihedralgroup(5)
g10 in List(List(\NN)) := dihedralgroup(1)
g11 in List(List(\NN)) := dihedralgroup(2)
g12 in List(List(\NN)) := dihedralgroup(0)
g13 in List(List(\NN)) := dihedralgroup(3)
g14 in List(List(\NN)) := altgroup(5)
r1 in List(List(\NN)) := regular([3, 1, 0, 2], x in \NN |-> y in \NN |-> (x + y) mod 4)
r2 in List(List(\NN)) := regular([0, 1, 2], x in \NN |-> y in \NN |-> (2 * x + y) mod 3)
r3 in List(List(\NN)) := regular([0, 1, 2], x in \NN |-> y in \NN |-> (x + y) mod 4)
r4 in List(List(\NN)) := regular([1, i, -1, -i], x in \Z |-> y in \Z |-> x * y)
r5 in List(List(\NN)) := regular([(1 in \D), (-1 in \D), j, -j, k, -k, (i in \D), (-i in \D)], x in \D |-> y in \D |-> x * y)
r6 in List(List(\NN)) := regular([[[1, 0], [0, 1]], [[0, -1], [1, 0]], [[-1, 0], [0, -1]], [[0, 1], [-1, 0]]], x in List(List(\Q)) |-> y in List(List(\Q)) |-> mmul(x, y))
r7 in List(List(\NN)) := regular(symgroup(3), x in List(\NN) |-> y in List(\NN) |-> pcompose(x, y))
r8 in List(List(\NN)) := regular([1, 1/2, 2, -1], x in \QQ |-> y in \QQ |-> x * y)
r9 in List(List(\NN)) := regular([], x in \NN |-> y in \NN |-> x)
o1 in \NN := grouporder(s4)
o2 in \NN := grouporder([[1, 0], [1, 0], [0, 1]])
o3 in \NN := grouporder([])
i1 in Bool := isgroup(s4)
i2 in Bool := isgroup([])
i3 in Bool := isgroup([[]])
i4 in Bool := isgroup([[1, 0]])
i5 in Bool := isgroup([[0, 0], [0, 1]])
i6 in Bool := isgroup([[0, 1, 2], [1, 2, 0]])
i7 in Bool := isgroup([[0, 1], [1, 0, 2]])
i8 in Bool := isgroup([[0, 1, 2, 3], [1, 2, 3, 0], [1, 0, 2, 3]])
u1 in Bool := issubgroup(v4, s4)
u2 in Bool := issubgroup(cyclicgroup(4), s4)
u3 in Bool := issubgroup([[1, 0, 2, 3]], s4)
u4 in Bool := issubgroup([], s4)
u5 in Bool := issubgroup(s4, s4)
u6 in Bool := issubgroup(a4, h2)
u7 in Bool := issubgroup([[0, 1]], [[0, 1, 2], [1, 2, 0]])
u8 in Bool := issubgroup([[0]], s3)
n1 in Bool := isnormal(v4, s4)
n2 in Bool := isnormal(cyclicgroup(4), s4)
n3 in Bool := isnormal(a4, s4)
n4 in Bool := isnormal(center(d4), d4)
n5 in Bool := isnormal(generate([[1, 0, 2]]), s3)
n6 in Bool := isnormal([[1, 0, 2]], s3)
k1 in List(List(List(\NN))) := leftcosets(generate([[1, 0, 2]]), s3)
k2 in List(List(List(\NN))) := rightcosets(generate([[1, 0, 2]]), s3)
k3 in List(List(List(\NN))) := leftcosets(v4, s4)
k4 in List(List(List(\NN))) := leftcosets(h2, a4)
k5 in List(List(List(\NN))) := rightcosets(generate([[0, 2, 1, 3], [0, 2, 3, 1]]), s4)
k6 in \NN := index(v4, s4)
k7 in \NN := index(a4, s4)
k8 in \NN := index([[1, 0, 2]], s3)
k9 in \NN := index([[0]], q8)
c1 in List(List(List(\NN))) := conjclasses(s4)
c2 in List(List(List(\NN))) := conjclasses(d4)
c3 in List(List(List(\NN))) := conjclasses(q8)
c4 in List(List(List(\NN))) := conjclasses([])
z1 in List(List(\NN)) := center(d4)
z2 in List(List(\NN)) := center(s3)
z3 in List(List(\NN)) := center(q8)
z4 in List(List(\NN)) := center(v4)
z5 in List(List(\NN)) := centralizer([1, 0, 2, 3], s4)
z6 in List(List(\NN)) := centralizer([1, 2, 0], s4)
z7 in List(List(\NN)) := centralizer([0, 1, 2, 3, 5, 4], s4)
z8 in List(List(\NN)) := normalizer(h2, s4)
z9 in List(List(\NN)) := normalizer(v4, s4)
z10 in List(List(\NN)) := normalizer(generate([[1, 2, 0, 3]]), s4)
d1 in List(List(\NN)) := commutatorsubgroup(s4)
d2 in List(List(\NN)) := commutatorsubgroup(d4)
d3 in List(List(\NN)) := commutatorsubgroup(q8)
d5 in List(List(\NN)) := commutatorsubgroup(a4)
d6 in List(List(\NN)) := commutatorsubgroup(v4)
d7 in List(List(\NN)) := commutatorsubgroup([[1, 0]])
v1 in Bool := issolvable(s4)
v2 in Bool := issolvable(g14)
v3 in Bool := issolvable([[]])
v4b in Bool := issolvable([[1, 0, 2]])
v5 in Bool := issolvable(semidirect(7, 3, 2))
b1 in Bool := isabelian(v4)
b2 in Bool := isabelian(s3)
b3 in Bool := isabelian(c6)
b4 in Bool := isabelian([[1, 0]])
y1 in Bool := iscyclic(c6)
y2 in Bool := iscyclic(c23)
y3 in Bool := iscyclic(v4)
y4 in Bool := iscyclic([[]])
y5 in Bool := iscyclic(q8)
e1 in List(Pair(\NN, \NN)) := elementorders(s4)
e2 in List(Pair(\NN, \NN)) := elementorders(q8)
e3 in List(Pair(\NN, \NN)) := elementorders([[]])
e4 in List(Pair(\NN, \NN)) := elementorders([[1, 0]])
e5 in List(Pair(\NN, \NN)) := elementorders(c2q8)
x1 in \NN := exponent(s4)
x2 in \NN := exponent(q8)
x3 in \NN := exponent([[]])
x4 in \NN := exponent([])
x5 in \NN := exponent(c23)
t1 in List(\NN) := orbit(generate([[1, 0, 2, 3, 4], [0, 1, 3, 4, 2]]), 3)
t2 in List(\NN) := orbit([[1, 2, 0, 3]], 3)
t3 in List(\NN) := orbit([], 2)
t4 in List(\NN) := orbit(s3, 5)
t5 in List(\NN) := orbit([[0, 2, 1, 3], [0, 1, 3, 2]], 1)
t6 in List(List(\NN)) := orbits([[1, 0, 2, 3, 4], [0, 1, 3, 4, 2]])
t7 in List(List(\NN)) := orbits([])
t8 in List(List(\NN)) := orbits([[0, 1, 2]])
t9 in List(List(\NN)) := orbits([[2, 3, 4, 0, 1, 5]])
w1 in List(List(\NN)) := stabilizer(s4, 0)
w2 in List(List(\NN)) := stabilizer(s3, 9)
w3 in List(List(\NN)) := stabilizer(d4, 1)
w4 in \NN := burnside(generate([[1, 0, 2, 3, 4], [0, 1, 3, 4, 2]]))
w5 in \NN := burnside(d4)
w6 in \NN := burnside([[]])
w7 in \NN := burnside([[0, 1, 2]])
w8 in \NN := burnside([[1, 0, 2]])
w9 in \NN := burnside(directproduct(c6, v4))
ct1 in List(List(\NN)) := cayleytable(s3)
ct2 in List(List(\NN)) := cayleytable(q8)
ct3 in List(List(\NN)) := cayleytable([[1, 0]])
ct4 in List(List(\NN)) := cayleytable([[0, 0]])
ct5 in List(List(\NN)) := cayleytable([[]])
dp1 in List(List(\NN)) := directproduct(cyclicgroup(2), cyclicgroup(3))
dp2 in List(List(\NN)) := directproduct([[]], v4)
dp3 in List(List(\NN)) := directproduct(s3, [[]])
dp4 in List(List(\NN)) := directproduct([[1, 0, 2]], [])
sy1 in List(List(\NN)) := sylow(s4, 2)
sy2 in List(List(\NN)) := sylow(s4, 3)
sy3 in List(List(\NN)) := sylow(s4, 5)
sy4 in List(List(\NN)) := sylow(s4, 4)
sy5 in List(List(\NN)) := sylow(s4, 1)
sy6 in List(List(\NN)) := sylow(semidirect(7, 3, 2), 3)
sy7 in List(List(\NN)) := sylow(q8, 2)
sy8 in List(List(\NN)) := sylow(s3, 1000000007)
sy9 in List(List(\NN)) := sylow([[1, 0]], 2)
sy10 in List(List(\NN)) := sylow(directproduct(s3, cyclicgroup(4)), 2)
sg1 in List(List(List(\NN))) := subgroups(s4)
sg2 in List(List(List(\NN))) := subgroups(q8)
sg3 in List(List(List(\NN))) := subgroups(directproduct(v4, cyclicgroup(2)))
sg4 in List(List(List(\NN))) := subgroups(s3)
sg5 in List(List(List(\NN))) := subgroups([[]])
sg6 in List(List(List(\NN))) := subgroups([[0, 1, 2], [1, 2, 0]])
sg7 in List(List(List(\NN))) := subgroups(c6)
si1 in Bool := sameinvariants(c4c4, c2q8)
si2 in Bool := sameinvariants(d4, q8)
si3 in Bool := sameinvariants(s3, c6)
si4 in Bool := sameinvariants(c6, c23)
si5 in Bool := sameinvariants([[]], [[1, 0]])
im1 in Bool := isomorphic(c4c4, c2q8)
im2 in Bool := isomorphic(c2q8, c4c4)
im3 in Bool := isomorphic(d4, semidirect(4, 2, 3))
im4 in Bool := isomorphic(q8, d4)
im5 in Bool := isomorphic(c6, c23)
im6 in Bool := isomorphic(dihedralgroup(6), directproduct(s3, cyclicgroup(2)))
im7 in Bool := isomorphic(s3, r7)
im8 in Bool := isomorphic(v4, cyclicgroup(4))
im9 in Bool := isomorphic([[]], [[0]])
im10 in Bool := isomorphic(a4, regular(a4, x in List(\NN) |-> y in List(\NN) |-> pcompose(x, y)))
im11 in Bool := isomorphic(q8, r5)
im12 in Bool := isomorphic(dihedralgroup(6), semidirect(3, 4, 2))
im13 in Bool := isomorphic([[1, 0]], [[0, 1], [1, 0]])
ab1 in List(\NN) := abelianinvariants(s4)
ab2 in List(\NN) := abelianinvariants(q8)
ab3 in List(\NN) := abelianinvariants(a4)
ab4 in List(\NN) := abelianinvariants(directproduct(cyclicgroup(4), cyclicgroup(6)))
ab5 in List(\NN) := abelianinvariants(v4)
ab6 in List(\NN) := abelianinvariants(cyclicgroup(12))
ab7 in List(\NN) := abelianinvariants([[]])
ab8 in List(\NN) := abelianinvariants(g14)
ab9 in List(\NN) := abelianinvariants(c4c4)
ab10 in List(\NN) := abelianinvariants(c2q8)
ab11 in List(\NN) := abelianinvariants(d4)
ab12 in List(\NN) := abelianinvariants([[1, 0]])
ab13 in List(\NN) := abelianinvariants(directproduct(directproduct(cyclicgroup(2), cyclicgroup(4)), cyclicgroup(6)))
cl1 in \NN := colorings(s4, 3)
cl2 in \NN := colorings(cyclicgroup(4), 2)
cl3 in \NN := colorings(d4, 3)
cl4 in \NN := colorings([[1, 0]], 2)
cl5 in \NN := colorings(cyclicgroup(3), 0)
cl6 in \NN := colorings(v4, 5)
nk1 in \NN := necklaces(6, 2)
nk2 in \NN := necklaces(0, 5)
nk3 in \NN := necklaces(1, 3)
nk4 in \NN := necklaces(4, 0)
nk5 in \NN := necklaces(5, 3)
br1 in \NN := bracelets(6, 2)
br2 in \NN := bracelets(2, 3)
br3 in \NN := bracelets(0, 2)
br4 in \NN := bracelets(5, 3)
br5 in \NN := bracelets(1, 4)
sd1 in List(List(\NN)) := semidirect(3, 2, 2)
sd2 in List(List(\NN)) := semidirect(5, 4, 2)
sd3 in List(List(\NN)) := semidirect(4, 3, 3)
sd4 in List(List(\NN)) := semidirect(6, 2, 2)
sd5 in List(List(\NN)) := semidirect(0, 2, 1)
sd6 in List(List(\NN)) := semidirect(1, 3, 0)
sd7 in List(List(\NN)) := semidirect(3, 2, 1)
'''

# ---------------------------------------------------------------- independent python reference
def comp(p, q): return tuple(p[i] for i in q)                          # (p ∘ q)(i) = p(q(i))
def inv(p):
    r = [0] * len(p)
    for i, x in enumerate(p): r[x] = i
    return tuple(r)
def pad(p, n): return tuple(p) + tuple(range(len(p), n))
def ident(n): return tuple(range(n))
def deg(G): return max((len(g) for g in G), default=0)
def norm(G):
    n = deg(G); return sorted(set(pad(g, n) for g in G))
def closure(gens):
    n = deg(gens); gens = [pad(g, n) for g in gens]; S = {ident(n)}; todo = [ident(n)]
    while todo:
        x = todo.pop()
        for s in gens:
            y = comp(x, s)
            if y not in S: S.add(y); todo.append(y)
    return sorted(S)
def porder(p):
    e, q, k = ident(len(p)), tuple(p), 1
    while q != e: q = comp(q, p); k += 1
    return k
def cycles(p):
    seen, out = set(), []
    for i in range(len(p)):
        if i in seen: continue
        c, j = [], i
        while j not in seen: seen.add(j); c.append(j); j = p[j]
        out.append(c)
    return out
def sign(p): return (-1) ** sum(len(c) - 1 for c in cycles(p))
def ppow(p, k):
    k %= porder(p); r = ident(len(p))
    for _ in range(k): r = comp(r, p)
    return r
def is_group(G):
    G = norm(G)
    if not G: return False
    n = deg(G); S = set(G)
    if any(sorted(g) != list(range(n)) for g in G): return False
    return all(comp(a, b) in S for a in G for b in G)
def is_sub(H, G):
    n = max(deg(H), deg(G)); H = sorted(set(pad(h, n) for h in H)); G = sorted(set(pad(g, n) for g in G))
    return is_group(G) and bool(H) and set(H) <= set(G) and all(comp(a, b) in set(H) for a in H for b in H)
def lcosets(H, G): return sorted({tuple(sorted(comp(g, h) for h in H)) for g in G})
def rcosets(H, G): return sorted({tuple(sorted(comp(h, g) for h in H)) for g in G})
def conjclasses(G): return sorted({tuple(sorted({comp(comp(x, g), inv(x)) for x in G})) for g in G})
def center(G): return [z for z in G if all(comp(z, x) == comp(x, z) for x in G)]
def centralizer(x, G):
    n = max(len(x), deg(G)); x = pad(x, n); G = sorted(set(pad(g, n) for g in G))
    return [g for g in G if comp(g, x) == comp(x, g)]
def normalizer(H, G):
    n = max(deg(H), deg(G)); H = set(pad(h, n) for h in H); G = sorted(set(pad(g, n) for g in G))
    return [g for g in G if {comp(comp(g, h), inv(g)) for h in H} == H]
def derived(G): return closure([comp(comp(a, b), comp(inv(a), inv(b))) for a in G for b in G])
def solvable(G):
    while len(G) > 1:
        D = derived(G)
        if len(D) == len(G): return False
        G = D
    return True
def abelian(G): return all(comp(a, b) == comp(b, a) for a in G for b in G)
def eorders(G):
    from collections import Counter
    c = Counter(porder(g) for g in G); return sorted(c.items())
def exponent(G):
    from math import lcm
    r = 1
    for g in G: r = lcm(r, porder(g))
    return r
def orbits(G, n):
    par = list(range(n))
    def f(x):
        while par[x] != x: x = par[x]
        return x
    for g in G:
        for i in range(n): par[f(i)] = f(g[i])
    groups = {}
    for i in range(n): groups.setdefault(f(i), []).append(i)
    return sorted(sorted(v) for v in groups.values())
def cayley(G):
    idx = {g: k for k, g in enumerate(G)}; return [[idx[comp(a, b)] for b in G] for a in G]
def dprod(G, H):
    n = deg(G); return sorted(tuple(g) + tuple(x + n for x in h) for g in G for h in H)
def subgroups_brute(G):
    found = set()
    for a in G:
        for b in G:
            for c in G: found.add(tuple(closure([a, b, c])))
    return sorted((list(s) for s in found), key=lambda s: (len(s), s))
def ppart(n, p):
    r = 1
    while n % p == 0: n //= p; r *= p
    return r
def isomorphic_brute(G, H):
    """bijections fixing the identity (small orders only)"""
    if len(G) != len(H): return False
    eG, eH = ident(deg(G)), ident(deg(H)); Gs = [g for g in G if g != eG]; Hs = [h for h in H if h != eH]
    for perm in itertools.permutations(Hs):
        f = dict(zip(Gs, perm)); f[eG] = eH
        if all(f[comp(a, b)] == comp(f[a], f[b]) for a in G for b in G): return True
    return False
def iso_search(G, H):
    """an independent search: images of a generating pair/triple, homomorphism checked on all products"""
    if len(G) != len(H) or eorders(G) != eorders(H): return False
    gens = []
    while len(closure(gens or [ident(deg(G))])) < len(G):
        K = set(closure(gens or [ident(deg(G))])); gens.append(next(g for g in G if g not in K))
    def words(gs):
        e = ident(deg(G)); W = {e: ()}; todo = [e]
        while todo:
            x = todo.pop(0)
            for i, s in enumerate(gs):
                y = comp(x, s)
                if y not in W: W[y] = W[x] + (i,); todo.append(y)
        return W
    W = words(gens)
    for imgs in itertools.product(*[[h for h in H if porder(h) == porder(g)] for g in gens]):
        f = {}
        for x, w in W.items():
            y = ident(deg(H))
            for i in w: y = comp(y, imgs[i])
            f[x] = y
        if len(set(f.values())) == len(G) and all(f[comp(a, b)] == comp(f[a], f[b]) for a in G for b in G): return True
    return False
def abelian_invariants(G):
    """invariant factors of G/G' from the counts of x with x^(p^j) ∈ G' (an independent route: no Smith form)"""
    D = set(derived(G)); m = len(G) // len(D)
    def pw(x, k):
        r = ident(len(x))
        for _ in range(k): r = comp(r, x)
        return r
    elem = {}                                       # prime -> partition (exponents)
    for p in range(2, m + 1):
        if m % p or any(p % q == 0 for q in range(2, p)): continue
        s, j, parts = [0], 1, []
        while True:
            cnt = sum(1 for x in G if pw(x, p ** j) in D) // len(D)
            e = 0
            while p ** (e + 1) <= cnt: e += 1
            s.append(e)
            if p ** e >= ppart(m, p): break
            j += 1
        conj = [s[i] - s[i - 1] for i in range(1, len(s))]          # number of parts >= i
        lam = [sum(1 for c in conj if c >= r) for r in range(1, (conj[0] if conj else 0) + 1)]
        elem[p] = sorted(lam, reverse=True)
    k = max((len(v) for v in elem.values()), default=0); inv_ = []
    for r in range(k):
        d = 1
        for p, v in elem.items():
            if r < len(v): d *= p ** v[r]
        inv_.append(d)
    return sorted(inv_)
def colorings_brute(G, k):
    n = deg(G); cols = list(itertools.product(range(k), repeat=n)); seen, orbs = set(), 0
    for c in cols:
        if c in seen: continue
        orbs += 1
        for g in G: seen.add(tuple(c[g[i]] for i in range(n)))
    return orbs
def rot(n): return [tuple((i + r) % n for i in range(n)) for r in range(n)]
def refl(n): return [tuple((r - i) % n for i in range(n)) for r in range(n)]
def semidirect(m, n, a):
    if m < 1 or n < 1 or gcd(a, m) != 1 or pow(a, n, m) != 1 % m: return []
    els = [(b, j) for j in range(n) for b in range(m)]; pos = {e: e[0] + m * e[1] for e in els}
    mul = lambda x, y: ((x[0] + pow(a, x[1], m) * y[0]) % m, (x[1] + y[1]) % n)
    return sorted(tuple(pos[mul(g, x)] for x in els) for g in els)
def regular(els, op, eq=lambda a, b: a == b):
    d = []
    for x in els:
        if not any(eq(x, y) for y in d): d.append(x)
    def pos(z):
        for k, y in enumerate(d):
            if eq(z, y): return k
        return None
    L = [tuple(pos(op(g, x)) for x in d) for g in d]
    if any(None in l or sorted(l) != list(range(len(d))) for l in L) or len(set(L)) != len(d): return []
    if any(op(op(a, b), c) != op(a, op(b, c)) for a in d for b in d for c in d): return []
    return sorted(L)
def qmul(x, y):
    a1, b1, c1, d1 = x; a2, b2, c2, d2 = y
    return (a1*a2 - b1*b2 - c1*c2 - d1*d2, a1*b2 + b1*a2 + c1*d2 - d1*c2, a1*c2 - b1*d2 + c1*a2 + d1*b2, a1*d2 + b1*c2 - c1*b2 + d1*a2)
def mmul(A, B): return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(2)) for j in range(2)) for i in range(2))

def main():
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'group.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("every statement of the group test program passes the class checker", not errs, str(errs[:2]) if errs else '')
    if errs: return rep.done()
    P.build(); E = Env(P)
    def deco(v, c):
        if c[0] == 'K' and c[1] == '𝔏': return [deco(x, c[2][0]) for x in E.lst(v)]
        if c[0] == 'K' and c[1] == '𝔹': return E.b(v)
        if c[0] == 'K' and c[1] == '𝔓':
            a, b = to_pair(v); return (deco(a, c[2][0]), deco(b, c[2][1]))
        q = E.dq(v); assert q.i == 0 and q.r.denominator == 1, q
        return int(q.r)
    cache = {}
    def V(n):
        if n not in cache:
            sn = P.hum.spec_name(n); cache[n] = deco(E.V(sn), P.checker.norm(P.checker.sigs[sn][0]))
        return cache[n]
    T = lambda G: sorted(tuple(g) for g in G)                         # a decoded group as sorted tuples
    def chk(label, name, want):
        got = V(name); ok = got == want
        rep(f"{label}", ok, '' if ok else f"got {got!r}, want {want!r}")

    S3, S4 = sorted(itertools.permutations(range(3))), sorted(itertools.permutations(range(4)))
    A4 = [p for p in S4 if sign(p) == 1]
    D4 = closure([(1, 2, 3, 0), (3, 2, 1, 0)])
    V4 = [(0, 1, 2, 3), (1, 0, 3, 2), (2, 3, 0, 1), (3, 2, 1, 0)]
    units = [(1, 0, 0, 0), (-1, 0, 0, 0), (0, 1, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, -1, 0), (0, 0, 0, 1), (0, 0, 0, -1)]
    Q8 = regular(units, qmul)
    C6 = rot(6); C23 = dprod(rot(2), rot(3))
    C4C4 = semidirect(4, 4, 3); C2Q8 = dprod(rot(2), Q8)
    H2 = closure([(1, 0, 2, 3)])
    lst = lambda G: [list(g) for g in G]

    # ---- groups used below
    chk("symgroup(3), symgroup(4): all permutations, sorted", 's3', lst(S3)); chk("symgroup(4)", 's4', lst(S4))
    chk("altgroup(4): the 12 even permutations", 'a4', lst(A4))
    chk("dihedralgroup(4): the 8 symmetries of the square", 'd4', lst(D4))
    chk("quaterniongroup: Q₈ from the Cayley–Dickson units 1, −1, i, −i, j, −j, k, −k (regular representation)", 'q8', lst(Q8))
    chk("kleingroup", 'v4', lst(V4))
    chk("cyclicgroup(6)", 'c6', lst(sorted(C6)))
    chk("semidirect(4, 4, 3) = C₄ ⋊ C₄ on 16 points", 'c4c4', lst(C4C4))
    chk("directproduct(C₂, Q₈) on 2 + 8 points", 'c2q8', lst(C2Q8))
    # ---- permutations
    chk("pid(4)", 'p1', [0, 1, 2, 3]); chk("pid(0) = []", 'p2', [])
    chk("pcompose: (p ∘ q)(i) = p(q(i))", 'p3', list(comp((1, 2, 0), (1, 0, 2))))
    chk("pcompose of different lengths pads with fixed points", 'p4', list(comp((1, 0, 2), (0, 2, 1))))
    chk("pinverse", 'p5', list(inv((2, 0, 3, 1)))); chk("pinverse([]) = []", 'p6', [])
    chk("papply", 'p7', 2); chk("papply beyond the list: a fixed point", 'p8', 7)
    chk("ppow with a negative exponent", 'p9', list(ppow((1, 2, 3, 4, 0), -2)))
    chk("ppow(p, 0) is the identity", 'p10', [0, 1, 2, 3, 4])
    chk("ppow(p, 7) for p of order 6", 'p11', list(ppow((1, 0, 3, 4, 2), 7)))
    chk("porder: lcm of the cycle lengths", 'p12', porder((1, 0, 3, 4, 2))); chk("porder([]) = 1", 'p13', 1)
    chk("pcycles: cycles ≥ 2 from their least point, sorted", 'p14', [c for c in cycles((3, 2, 1, 0, 5, 6, 4)) if len(c) > 1])
    chk("pcycles(identity) = []", 'p15', [])
    def fromcyc(n, cs):
        m = max([n] + [x + 1 for c in cs for x in c]); r = ident(m)
        for c in reversed(cs):
            p = list(range(m))
            for a, b in zip(c, c[1:] + c[:1]): p[a] = b
            r = comp(tuple(p), r)
        return list(r)
    chk("fromcycles(6, [[4, 1, 3], [0, 5]])", 'p16', fromcyc(6, [[4, 1, 3], [0, 5]]))
    chk("fromcycles: the degree grows to the largest point", 'p17', [2, 1, 0])
    chk("fromcycles with overlapping cycles: c₁ ∘ c₂", 'p18', fromcyc(3, [[0, 1], [1, 2]]))
    chk("psign of a transposition", 'p19', -1); chk("psign of a 3-cycle", 'p20', 1); chk("psign([]) = 1", 'p21', 1)
    chk("iseven of a 4-cycle", 'p22', False); chk("iseven of (0 1 2)(3 4)(5 6)", 'p23', sign((1, 2, 0, 4, 3, 6, 5)) == 1)
    chk("cycletype: all cycle lengths, decreasing", 'p24', sorted((len(c) for c in cycles((1, 0, 3, 4, 2, 5))), reverse=True))
    q = (3, 1, 2, 0); chk("pconj(p, q) = q p q⁻¹", 'p25', list(comp(comp(q, (1, 2, 0, 3)), inv(q))))
    chk("isperm([1, 1, 0]) is false", 'p26', False); chk("isperm([]) is true", 'p27', True)
    chk("isperm([2, 0, 1])", 'p28', True); chk("isperm([0, 3]) is false", 'p29', False)
    # ---- constructors and generation
    chk("generate: the closure of two generators, sorted", 'g1', lst(closure([(1, 2, 3, 0), (3, 2, 1, 0)])))
    chk("generate([]) is the trivial group [[]]", 'g2', [[]])
    chk("generate pads generators of different lengths", 'g3', lst(S3))
    chk("symgroup(0) = [[]]", 'g4', [[]]); chk("symgroup(1) = [[0]]", 'g5', [[0]])
    chk("altgroup(2) is trivial", 'g6', [[0, 1]])
    chk("cyclicgroup(5)", 'g7', lst(sorted(rot(5)))); chk("cyclicgroup(0) = [[]]", 'g8', [[]])
    chk("dihedralgroup(5): order 10 on 5 points", 'g9', lst(sorted(set(rot(5) + refl(5)))))
    chk("dihedralgroup(1) = C₂ on 2 points", 'g10', [[0, 1], [1, 0]])
    chk("dihedralgroup(2) = V₄", 'g11', lst(V4)); chk("dihedralgroup(0) = [[]]", 'g12', [[]])
    chk("dihedralgroup(3) = S₃", 'g13', lst(S3))
    A5 = sorted(p for p in itertools.permutations(range(5)) if sign(p) == 1)
    chk("altgroup(5): 60 elements", 'g14', lst(A5))
    # ---- Cayley's theorem
    chk("regular: ℤ/4 listed as 3, 1, 0, 2", 'r1', lst(regular([3, 1, 0, 2], lambda x, y: (x + y) % 4)))
    chk("regular: a non-associative operation gives []", 'r2', [])
    chk("regular: a product outside the list gives []", 'r3', [])
    chk("regular on ℤ[i]: the units {1, i, −1, −i} under ·", 'r4', lst(regular([1, 1j, -1, -1j], lambda x, y: x * y)))
    order8 = [units[0], units[1], units[4], units[5], units[6], units[7], units[2], units[3]]
    chk("regular on the Cayley–Dickson tower: 1, −1, j, −j, k, −k, i, −i under ⊠𝔻", 'r5', lst(regular(order8, qmul)))
    I2 = ((1, 0), (0, 1)); R = ((0, -1), (1, 0))
    mats = [I2, R, mmul(R, R), mmul(R, mmul(R, R))]
    chk("regular on matrices: rotations by quarter turns under mmul", 'r6', lst(regular(mats, mmul)))
    chk("regular on permutations under pcompose", 'r7', lst(regular(S3, comp)))
    from fractions import Fraction as F
    chk("regular: {1, 1/2, 2, −1} is not closed under ·", 'r8', [])
    chk("regular([]) = []", 'r9', [])
    # ---- predicates on groups
    chk("grouporder(S₄) = 24", 'o1', 24); chk("grouporder counts distinct elements", 'o2', 2); chk("grouporder([]) = 0", 'o3', 0)
    for n_, G_ in [('i1', S4), ('i2', []), ('i3', [()]), ('i4', [(1, 0)]), ('i5', [(0, 0), (0, 1)]), ('i6', [(0, 1, 2), (1, 2, 0)]),
                   ('i7', [(0, 1), (1, 0, 2)]), ('i8', [(0, 1, 2, 3), (1, 2, 3, 0), (1, 0, 2, 3)])]:
        chk(f"isgroup ({n_})", n_, is_group(G_))
    for n_, H_, G_ in [('u1', V4, S4), ('u2', closure([(1, 2, 3, 0)]), S4), ('u3', [(1, 0, 2, 3)], S4), ('u4', [], S4), ('u5', S4, S4),
                       ('u6', A4, H2), ('u7', [(0, 1)], [(0, 1, 2), (1, 2, 0)]), ('u8', [(0,)], S3)]:
        chk(f"issubgroup ({n_})", n_, is_sub(H_, G_))
    def is_normal(H, G): return is_sub(H, G) and len(normalizer(H, G)) == len(norm(G))
    for n_, H_, G_ in [('n1', V4, S4), ('n2', closure([(1, 2, 3, 0)]), S4), ('n3', A4, S4), ('n4', center(D4), D4),
                       ('n5', closure([(1, 0, 2)]), S3), ('n6', [(1, 0, 2)], S3)]:
        chk(f"isnormal ({n_})", n_, is_normal(H_, G_))
    H = closure([(1, 0, 2)])
    chk("leftcosets of ⟨(0 1)⟩ in S₃", 'k1', [lst(c) for c in lcosets(H, S3)])
    chk("rightcosets of ⟨(0 1)⟩ in S₃ (different from the left ones)", 'k2', [lst(c) for c in rcosets(H, S3)])
    chk("leftcosets of V₄ in S₄: 6 cosets", 'k3', [lst(c) for c in lcosets(V4, S4)])
    chk("leftcosets of a non-subgroup: []", 'k4', [])
    K = closure([(0, 2, 1, 3), (0, 2, 3, 1)])
    chk("rightcosets of S₃ (fixing 0) in S₄", 'k5', [lst(c) for c in rcosets(K, S4)])
    chk("index(V₄, S₄) = 6", 'k6', 6); chk("index(A₄, S₄) = 2", 'k7', 2); chk("index of a non-subgroup is 0", 'k8', 0)
    chk("index of the trivial subgroup = |Q₈|, padded degrees", 'k9', 8)
    chk("conjclasses(S₄): 5 classes", 'c1', [lst(c) for c in conjclasses(S4)])
    chk("conjclasses(D₄)", 'c2', [lst(c) for c in conjclasses(D4)])
    chk("conjclasses(Q₈)", 'c3', [lst(c) for c in conjclasses(Q8)]); chk("conjclasses([]) = []", 'c4', [])
    chk("center(D₄)", 'z1', lst(center(D4))); chk("center(S₃) is trivial", 'z2', [[0, 1, 2]])
    chk("center(Q₈) = {±1}", 'z3', lst(center(Q8))); chk("center(V₄) = V₄", 'z4', lst(V4))
    chk("centralizer of (0 1) in S₄", 'z5', lst(centralizer((1, 0, 2, 3), S4)))
    chk("centralizer of a shorter permutation (padded)", 'z6', lst(centralizer((1, 2, 0), S4)))
    chk("centralizer of a longer permutation (G padded)", 'z7', lst(centralizer((0, 1, 2, 3, 5, 4), S4)))
    chk("normalizer of ⟨(0 1)⟩ in S₄", 'z8', lst(normalizer(H2, S4)))
    chk("normalizer of V₄ in S₄ is S₄", 'z9', lst(S4))
    chk("normalizer of ⟨(0 1 2)⟩ in S₄", 'z10', lst(normalizer(closure([(1, 2, 0, 3)]), S4)))
    chk("commutatorsubgroup(S₄) = A₄", 'd1', lst(A4)); chk("commutatorsubgroup(D₄)", 'd2', lst(derived(D4)))
    chk("commutatorsubgroup(Q₈) = {±1}", 'd3', lst(derived(Q8))); chk("commutatorsubgroup(A₄) = V₄", 'd5', lst(V4))
    chk("commutatorsubgroup(V₄) is trivial", 'd6', [[0, 1, 2, 3]]); chk("commutatorsubgroup of a non-group: []", 'd7', [])
    chk("issolvable(S₄)", 'v1', True); chk("issolvable(A₅) is false (A₅ is perfect)", 'v2', solvable(A5))
    chk("issolvable of the trivial group", 'v3', True); chk("issolvable of a non-group: false", 'v4b', False)
    chk("issolvable(C₇ ⋊ C₃)", 'v5', solvable(semidirect(7, 3, 2)))
    chk("isabelian(V₄)", 'b1', True); chk("isabelian(S₃) is false", 'b2', False); chk("isabelian(C₆)", 'b3', True)
    chk("isabelian of a non-group: false", 'b4', False)
    chk("iscyclic(C₆)", 'y1', True); chk("iscyclic(C₂ × C₃)", 'y2', True); chk("iscyclic(V₄) is false", 'y3', False)
    chk("iscyclic of the trivial group", 'y4', True); chk("iscyclic(Q₈) is false", 'y5', False)
    chk("elementorders(S₄)", 'e1', eorders(S4)); chk("elementorders(Q₈)", 'e2', eorders(Q8))
    chk("elementorders of the trivial group", 'e3', [(1, 1)]); chk("elementorders of a non-group: []", 'e4', [])
    chk("elementorders(C₂ × Q₈)", 'e5', eorders(C2Q8))
    chk("exponent(S₄) = 12", 'x1', exponent(S4)); chk("exponent(Q₈) = 4", 'x2', 4); chk("exponent of the trivial group", 'x3', 1)
    chk("exponent of a non-group: 0", 'x4', 0); chk("exponent(C₂ × C₃) = 6", 'x5', 6)
    # ---- actions
    G5 = closure([(1, 0, 2, 3, 4), (0, 1, 3, 4, 2)])
    chk("orbit of a point under a group", 't1', [2, 3, 4]); chk("orbit of a fixed point", 't2', [3])
    chk("orbit under no generators", 't3', [2]); chk("orbit of a point beyond the degree", 't4', [5])
    chk("orbit under generators (not a group)", 't5', next(o for o in orbits(closure([(0, 2, 1, 3), (0, 1, 3, 2)]), 4) if 1 in o))
    chk("orbits under generators", 't6', orbits(G5, 5)); chk("orbits([]) = []", 't7', [])
    chk("orbits of the identity: singletons", 't8', [[0], [1], [2]])
    chk("orbits of a single permutation (its cycles)", 't9', orbits([(2, 3, 4, 0, 1, 5)], 6))
    chk("stabilizer of 0 in S₄ (≅ S₃)", 'w1', lst([g for g in S4 if g[0] == 0]))
    chk("stabilizer of a point beyond the degree: the whole group", 'w2', lst(S3))
    chk("stabilizer of a vertex in D₄", 'w3', lst([g for g in D4 if g[1] == 1]))
    chk("burnside = number of orbits", 'w4', len(orbits(G5, 5))); chk("burnside(D₄) = 1", 'w5', 1)
    chk("burnside of the trivial group on 0 points", 'w6', 0); chk("burnside of the identity on 3 points", 'w7', 3)
    chk("burnside of a non-group: 0", 'w8', 0)
    C6V4 = dprod(sorted(C6), V4); chk("burnside(C₆ × V₄) on 10 points", 'w9', len(orbits(C6V4, 10)))
    chk("cayleytable(S₃)", 'ct1', cayley(S3)); chk("cayleytable(Q₈)", 'ct2', cayley(Q8))
    chk("cayleytable of a non-group (no identity): []", 'ct3', []); chk("cayleytable of a non-permutation: []", 'ct4', [])
    chk("cayleytable of the trivial group", 'ct5', [[0]])
    chk("directproduct(C₂, C₃) on 5 points", 'dp1', lst(dprod(rot(2), sorted(rot(3)))))
    chk("directproduct with the trivial group on 0 points", 'dp2', lst(V4))
    chk("directproduct(S₃, trivial)", 'dp3', lst(S3)); chk("directproduct with [] is []", 'dp4', [])
    # ---- Sylow
    def is_sylow(Pn, G, p): Pg = T(V(Pn)); return is_sub(Pg, G) and len(Pg) == ppart(len(G), p)
    rep("sylow(S₄, 2): a subgroup of order 8", is_sylow('sy1', S4, 2), str(V('sy1')))
    rep("sylow(S₄, 3): a subgroup of order 3", is_sylow('sy2', S4, 3), str(V('sy2')))
    chk("sylow(S₄, 5): 5 ∤ 24, the trivial subgroup", 'sy3', [[0, 1, 2, 3]])
    chk("sylow(S₄, 4): 4 is not a prime, trivial", 'sy4', [[0, 1, 2, 3]]); chk("sylow(S₄, 1): trivial", 'sy5', [[0, 1, 2, 3]])
    rep("sylow(C₇ ⋊ C₃, 3): order 3", is_sylow('sy6', semidirect(7, 3, 2), 3))
    chk("sylow(Q₈, 2) = Q₈", 'sy7', lst(Q8)); chk("sylow with a huge prime: trivial", 'sy8', [[0, 1, 2]])
    chk("sylow of a non-group: []", 'sy9', [])
    S3C4 = dprod(S3, sorted(rot(4))); rep("sylow(S₃ × C₄, 2): order 8", is_sylow('sy10', S3C4, 2))
    # ---- all subgroups (python: closures of all generator triples)
    for n_, G_, lab in [('sg1', S4, "S₄: 30 subgroups"), ('sg2', Q8, "Q₈: 6 subgroups"), ('sg3', dprod(V4, rot(2)), "C₂³: 16 subgroups"),
                        ('sg4', S3, "S₃: 6 subgroups"), ('sg7', sorted(C6), "C₆: 4 subgroups")]:
        want = [lst(s) for s in subgroups_brute(G_)]
        chk(f"subgroups({lab})", n_, want)
    chk("subgroups of the trivial group", 'sg5', [[[]]]); chk("subgroups of a non-group: []", 'sg6', [])
    # ---- invariants and isomorphism
    def sameinv(G, H):
        return (is_group(G) and is_group(H) and len(G) == len(H) and eorders(G) == eorders(H) and len(center(G)) == len(center(H))
                and abelian(G) == abelian(H) and solvable(G) == solvable(H)
                and any(porder(g) == len(G) for g in G) == any(porder(h) == len(H) for h in H))
    chk("sameinvariants(C₄ ⋊ C₄, C₂ × Q₈): the invariants agree", 'si1', sameinv(C4C4, C2Q8))
    chk("sameinvariants(D₄, Q₈) is false (element orders differ)", 'si2', sameinv(D4, Q8))
    chk("sameinvariants(S₃, C₆) is false", 'si3', sameinv(S3, sorted(C6)))
    chk("sameinvariants(C₆, C₂ × C₃)", 'si4', True); chk("sameinvariants with a non-group: false", 'si5', False)
    rep("C₄ ⋊ C₄ and C₂ × Q₈ really differ: their abelianizations are C₂ × C₄ and C₂³ (python)",
        abelian_invariants(C4C4) == [2, 4] and abelian_invariants(C2Q8) == [2, 2, 2])
    chk("isomorphic(C₄ ⋊ C₄, C₂ × Q₈) is false although the invariants agree", 'im1', False)
    chk("isomorphic(C₂ × Q₈, C₄ ⋊ C₄) is false", 'im2', False)
    chk("isomorphic(D₄, C₄ ⋊ C₂)", 'im3', isomorphic_brute(D4, semidirect(4, 2, 3)))
    chk("isomorphic(Q₈, D₄) is false", 'im4', isomorphic_brute(Q8, D4))
    chk("isomorphic(C₆, C₂ × C₃)", 'im5', isomorphic_brute(sorted(C6), C23))
    D6 = sorted(set(rot(6) + refl(6)))
    chk("isomorphic(D₆, S₃ × C₂) (search in python)", 'im6', iso_search(D6, dprod(S3, rot(2))))
    chk("isomorphic(S₃, its regular representation)", 'im7', isomorphic_brute(S3, regular(S3, comp)))
    chk("isomorphic(V₄, C₄) is false", 'im8', False); chk("isomorphic of trivial groups of different degrees", 'im9', True)
    chk("isomorphic(A₄, its regular representation on 12 points)", 'im10', iso_search(A4, regular(A4, comp)))
    chk("isomorphic(Q₈, Q₈ from another order of the units)", 'im11', isomorphic_brute(Q8, regular(order8, qmul)))
    chk("isomorphic(D₆, C₃ ⋊ C₄) is false (the dicyclic group)", 'im12', iso_search(D6, semidirect(3, 4, 2)))
    chk("isomorphic with a non-group: false", 'im13', False)
    for n_, G_, lab in [('ab1', S4, "S₄"), ('ab2', Q8, "Q₈"), ('ab3', A4, "A₄"), ('ab4', dprod(sorted(rot(4)), sorted(rot(6))), "C₄ × C₆"),
                        ('ab5', V4, "V₄"), ('ab6', sorted(rot(12)), "C₁₂"), ('ab8', A5, "A₅ (perfect)"), ('ab9', C4C4, "C₄ ⋊ C₄"),
                        ('ab10', C2Q8, "C₂ × Q₈"), ('ab11', D4, "D₄"), ('ab13', dprod(dprod(rot(2), sorted(rot(4))), sorted(rot(6))), "C₂ × C₄ × C₆")]:
        chk(f"abelianinvariants({lab})", n_, abelian_invariants(G_))
    chk("abelianinvariants of the trivial group: []", 'ab7', []); chk("abelianinvariants of a non-group: []", 'ab12', [])
    # ---- colourings (python: brute force over all colourings)
    chk("colorings(S₄, 3) = 15", 'cl1', colorings_brute(S4, 3)); chk("colorings(C₄, 2)", 'cl2', colorings_brute(sorted(rot(4)), 2))
    chk("colorings(D₄, 3)", 'cl3', colorings_brute(D4, 3)); chk("colorings of a non-group: 0", 'cl4', 0)
    chk("colorings with 0 colours", 'cl5', 0); chk("colorings(V₄, 5)", 'cl6', colorings_brute(V4, 5))
    chk("necklaces(6, 2) = 14", 'nk1', colorings_brute(rot(6), 2)); chk("necklaces(0, 5) = 1 (the empty necklace)", 'nk2', 1)
    chk("necklaces(1, 3) = 3", 'nk3', 3); chk("necklaces(4, 0) = 0", 'nk4', 0); chk("necklaces(5, 3)", 'nk5', colorings_brute(rot(5), 3))
    chk("bracelets(6, 2) = 13", 'br1', colorings_brute(rot(6) + refl(6), 2)); chk("bracelets(2, 3) = 6", 'br2', colorings_brute(rot(2) + refl(2), 3))
    chk("bracelets(0, 2) = 1", 'br3', 1); chk("bracelets(5, 3)", 'br4', colorings_brute(rot(5) + refl(5), 3)); chk("bracelets(1, 4) = 4", 'br5', 4)
    # ---- semidirect products
    for n_, args in [('sd1', (3, 2, 2)), ('sd2', (5, 4, 2)), ('sd3', (4, 3, 3)), ('sd4', (6, 2, 2)), ('sd5', (0, 2, 1)), ('sd6', (1, 3, 0)), ('sd7', (3, 2, 1))]:
        chk(f"semidirect{args}", n_, lst(semidirect(*args)))
    rep("semidirect(3, 2, 2) ≅ S₃ (python brute force)", isomorphic_brute(T(V('sd1')), S3))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
