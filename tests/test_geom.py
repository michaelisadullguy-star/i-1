"""test_geom.py -- lib/geom.imo (libsrc/geom.hum.imo): plane geometry with exact rational coordinates against Python implementations with fractions.
python3 tests/test_geom.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import random, sys
from fractions import Fraction as F
from langtest import *

R = random.Random(20261108)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('plane geometry')
add = S.add
PT = ('P', 'Q', 'Q'); LP = ('L', PT); LQ = ('L', 'Q')
def rp(lo=-6, hi=6): return (F(R.randint(2 * lo, 2 * hi), 2), F(R.randint(2 * lo, 2 * hi), 2))
def rpts(nmax=8): return [rp() for _ in range(R.randint(0, nmax))]
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def cross3(o, a, b): return cross(sub(a, o), sub(b, o))
def sgn(x): return (x > 0) - (x < 0)
def on_segment(p, a, b): return cross3(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
def hull(pts):
    s = sorted(set(pts))
    if len(s) <= 2: return s
    def chain(ps):
        st = []
        for p in ps:
            while len(st) >= 2 and cross3(st[-2], st[-1], p) <= 0: st.pop()
            st.append(p)
        return st
    return chain(s)[:-1] + chain(s[::-1])[:-1]
def shoelace(pts): return sum((cross(pts[k], pts[(k + 1) % len(pts)]) for k in range(len(pts))), F(0))
def inpoly(p, pts):
    es = list(zip(pts, pts[1:] + pts[:1]))
    if any(on_segment(p, a, b) for a, b in es): return 0
    c = 0
    for a, b in es:
        if (a[1] <= p[1] < b[1] and cross3(a, b, p) > 0) or (b[1] <= p[1] < a[1] and cross3(a, b, p) < 0): c += 1
    return 1 if c % 2 == 1 else -1

for t in range(n(40)):
    a, b, c, d = rp(), rp(), rp(), rp(); pts = rpts()
    L = lambda p: lit(p, PT)
    add(f'dist2 {a} {b}', f'dist2({L(a)}, {L(b)})', 'Q', (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    add(f'dotp {a} {b}', f'dotp({L(a)}, {L(b)})', 'Q', a[0] * b[0] + a[1] * b[1])
    add(f'crossp {a} {b}', f'crossp({L(a)}, {L(b)})', 'Q', cross(a, b))
    add(f'orient {a} {b} {c}', f'orient({L(a)}, {L(b)}, {L(c)})', 'Z', sgn(cross3(a, b, c)))
    add(f'triarea2 {a} {b} {c}', f'triarea2({L(a)}, {L(b)}, {L(c)})', 'Q', abs(cross3(a, b, c)))
    add(f'iscollinear {a} {b} {c}', f'iscollinear({L(a)}, {L(b)}, {L(c)})', 'B', cross3(a, b, c) == 0)
    add(f'midpoint {a} {b}', f'midpoint({L(a)}, {L(b)})', PT, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    add(f'vscale2 {a}', f'vscale2(3 / 2, {L(a)})', PT, (a[0] * F(3, 2), a[1] * F(3, 2)))
    add(f'onsegment {c} {a} {b}', f'onsegment({L(c)}, {L(a)}, {L(b)})', 'B', on_segment(c, a, b))
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    add(f'onsegment midpoint {a} {b}', f'onsegment({L(m)}, {L(a)}, {L(b)})', 'B', True)
    def seg(a, b, c, d):
        o1, o2, o3, o4 = sgn(cross3(a, b, c)), sgn(cross3(a, b, d)), sgn(cross3(c, d, a)), sgn(cross3(c, d, b))
        return (o1 * o2 < 0 and o3 * o4 < 0) or on_segment(c, a, b) or on_segment(d, a, b) or on_segment(a, c, d) or on_segment(b, c, d)
    add(f'segmentsintersect {a} {b} {c} {d}', f'segmentsintersect({L(a)}, {L(b)}, {L(c)}, {L(d)})', 'B', seg(a, b, c, d))
    den = cross(sub(b, a), sub(d, c))
    li = [] if den == 0 else [(a[0] + cross(sub(c, a), sub(d, c)) / den * (b[0] - a[0]), a[1] + cross(sub(c, a), sub(d, c)) / den * (b[1] - a[1]))]
    add(f'lineintersection {a} {b} {c} {d}', f'lineintersection({L(a)}, {L(b)}, {L(c)}, {L(d)})', LP, li)
    # the circumcentre is at the same distance from the three points
    cc = '' if cross3(a, b, c) == 0 else None
    if cross3(a, b, c) == 0: add(f'circumcenter of collinear {a} {b} {c}', f'circumcenter({L(a)}, {L(b)}, {L(c)})', LP, [])
    else: add(f'circumcenter equidistant {a} {b} {c}', f'forall((o in Pair(\\QQ, \\QQ) |-> (dist2(o, {L(a)}) == dist2(o, {L(b)})) and (dist2(o, {L(b)}) == dist2(o, {L(c)}))), circumcenter({L(a)}, {L(b)}, {L(c)}))', 'B', True)
    if pts:
        add(f'centroid {pts}', f'centroid({lit(pts, LP)})', PT, (sum((p[0] for p in pts), F(0)) / len(pts), sum((p[1] for p in pts), F(0)) / len(pts)))
        add(f'bbox {pts}', f'bbox({lit(pts, LP)})', ('P', PT, PT), ((min(p[0] for p in pts), min(p[1] for p in pts)), (max(p[0] for p in pts), max(p[1] for p in pts))))
    add(f'convexhull {pts}', f'convexhull({lit(pts, LP)})', LP, hull(pts))
    sa = shoelace(pts) if len(pts) >= 3 else F(0)
    add(f'signedarea2 {pts}', f'signedarea2({lit(pts, LP)})', 'Q', sa)
    add(f'polyarea2 {pts}', f'polyarea2({lit(pts, LP)})', 'Q', abs(sa))
    add(f'polyarea {pts}', f'polyarea({lit(pts, LP)})', 'Q', abs(sa) / 2)
    if len(pts) >= 2:
        add(f'polyperimeter2 {pts}', f'polyperimeter2({lit(pts, LP)})', LQ, [(p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for p, q in zip(pts, pts[1:] + pts[:1])])
        add(f'closestpair2 {pts}', f'closestpair2({lit(pts, LP)})', 'Q', min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for i, p in enumerate(pts) for q in pts[i + 1:]))
    h = hull(pts)
    if len(h) >= 3:
        q = rp()
        add(f'inpolygon {q} in the hull {h}', f'inpolygon({lit(q, PT)}, {lit(h, LP)})', 'Z', inpoly(q, h))
        add(f'isconvex of the hull {h}', f'isconvex({lit(h, LP)})', 'B', True)
        for v in h[:2]: add(f'inpolygon vertex {v} of {h}', f'inpolygon({lit(v, PT)}, {lit(h, LP)})', 'Z', 0)
    if len(pts) >= 3:
        def convex(ps):
            cs = [cross3(ps[k], ps[(k + 1) % len(ps)], ps[(k + 2) % len(ps)]) for k in range(len(ps))]
            return all(x >= 0 for x in cs) or all(x <= 0 for x in cs)
        add(f'isconvex {pts}', f'isconvex({lit(pts, LP)})', 'B', convex(pts))
        q = rp()
        add(f'inpolygon {q} in {pts}', f'inpolygon({lit(q, PT)}, {lit(pts, LP)})', 'Z', inpoly(q, pts))

# a few fixed cases
sq = [(F(0), F(0)), (F(4), F(0)), (F(4), F(4)), (F(0), F(4))]
for q, want in [((F(2), F(2)), 1), ((F(4), F(2)), 0), ((F(5), F(2)), -1), ((F(0), F(0)), 0), ((F(-1), F(-1)), -1)]:
    add(f'inpolygon {q} in the square', f'inpolygon({lit(q, PT)}, {lit(sq, LP)})', 'Z', want)
add('convexhull of the square with an interior point and a boundary point', f'convexhull({lit(sq + [(F(2), F(2)), (F(2), F(0))], LP)})', LP, hull(sq))
add('polyarea of the square', f'polyarea({lit(sq, LP)})', 'Q', F(16))

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
