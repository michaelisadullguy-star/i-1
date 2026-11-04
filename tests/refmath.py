"""refmath.py -- exact reference arithmetic (python) used by the tests: Gaussian rationals and the Cayley–Dickson tower."""
import random
from fractions import Fraction as Fr

# ------------------------------------------------------------------ exact Gaussian rationals in python
class Q:
    __slots__ = ('r', 'i')
    def __init__(s, r=0, i=0): s.r, s.i = Fr(r), Fr(i)
    def __add__(s, o): return Q(s.r + o.r, s.i + o.i)
    def __sub__(s, o): return Q(s.r - o.r, s.i - o.i)
    def __neg__(s): return Q(-s.r, -s.i)
    def __mul__(s, o): return Q(s.r*o.r - s.i*o.i, s.r*o.i + s.i*o.r)
    def conj(s): return Q(s.r, -s.i)
    def inv(s):
        n = s.r*s.r + s.i*s.i
        return Q(s.r/n, -s.i/n)
    def __eq__(s, o): return s.r == o.r and s.i == o.i
    def __hash__(s): return hash((s.r, s.i))
    def iszero(s): return s.r == 0 and s.i == 0
    def __repr__(s): return f"({s.r}+{s.i}i)"

ZERO, ONE, I = Q(0), Q(1), Q(0, 1)

# ---- python reference Cayley-Dickson tower over Q[i]:  leaf = Q ;  node = (a, b)
def depth(t): return 0 if isinstance(t, Q) else 1 + max(depth(t[0]), depth(t[1]))
def zero_like(t): return ZERO if isinstance(t, Q) else (zero_like(t[0]), zero_like(t[1]))
def lift(t): return t if isinstance(t, tuple) else (t, ZERO)
def tadd(x, y):
    if isinstance(x, Q) and isinstance(y, Q): return x + y
    x, y = lift(x), lift(y)
    return (tadd(x[0], y[0]), tadd(x[1], y[1]))
def tneg(x): return -x if isinstance(x, Q) else (tneg(x[0]), tneg(x[1]))
def tconj(x): return x.conj() if isinstance(x, Q) else (tconj(x[0]), tneg(x[1]))
def tmul(x, y):
    if isinstance(x, Q) and isinstance(y, Q): return x * y
    (a, b), (c, d) = lift(x), lift(y)
    return (tadd(tmul(a, c), tneg(tmul(tconj(d), b))), tadd(tmul(d, a), tmul(b, tconj(c))))
def tflat(x, d):
    """coefficient vector of x padded to depth d (inclusion a -> (a,0))"""
    if d == 0:
        assert isinstance(x, Q); return [x]
    a, b = lift(x)
    return tflat(a, d - 1) + tflat(b, d - 1)
def tiszero(x): return all(c.iszero() for c in tflat(x, depth(x)))
def teq(x, y):
    d = max(depth(x), depth(y)); return tflat(x, d) == tflat(y, d)
def randQ(rnd, den=4):
    return Q(Fr(rnd.randint(-5, 5), rnd.randint(1, den)), Fr(rnd.randint(-5, 5), rnd.randint(1, den)))
def randT(rnd, d):
    if d == 0 or rnd.random() < 0.25: return randQ(rnd)
    return (randT(rnd, d - 1), randT(rnd, d - 1))

