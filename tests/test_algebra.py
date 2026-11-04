"""test_algebra.py -- Q[i], lazy R[i], the Cayley–Dickson tower and function spaces of the prelude.   python3 tests/test_algebra.py"""
import os, sys, time, random, itertools
from fractions import Fraction as Fr
from math import lcm
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from harness import *                                 # the core under test: --core pymo (default) or --core haskimo
from base_b import gadd, gmul
from refmath import Q, ZERO, ONE, I

# two functions of the tower-valued function space, written in the language (the host cannot pass its own functions to another core)
EXTRA = """qf ∶ ℚ[i] → 𝔗 ℚ[i]
qf ξ ≔ (❁ (❀ (ϝ ξ)) (❀ (ϛ ξ)))
qg ∶ ℚ[i] → 𝔗 ℚ[i]
qg ξ ≔ (❁ (❀ 11) (❀ 1))
"""

RESULTS = []
def report(label, ok, extra=''):
    RESULTS.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}"); sys.stdout.flush()

def main():
    t0 = time.time()
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_file(os.path.join(ROOT, 'examples', 'target.spec.imo')); P.add_file(os.path.join(ROOT, 'examples', 'spaces.spec.imo'))
    P.add_text(EXTRA, 'extra.imo', notation='spec')
    errs = P.check(collect=True)
    if errs: raise SystemExit(f"class errors: {errs[:2]}")
    P.build(); E = Env(P)
    V, call = E.V, E.call
    zint = E.z
    def qval(q):
        D = lcm(q.r.denominator, q.i.denominator)
        return call('⊗', zint((int(q.r * D), int(q.i * D))), zint((D, 0)))
    def qdec(v):
        p, d = to_pair(v); P_, D_ = val(to_list(p)), val(to_list(d)); assert D_ != (0, 0)
        return Q(P_[0], P_[1]) * Q(D_[0], D_[1]).inv()
    tval = lambda t: call('❀', qval(t)) if isinstance(t, Q) else call('❁', tval(t[0]), tval(t[1]))
    def tdec(v):
        if to_bool(call('◀', v)):
            a, b = to_pair(call('▶', v)); return (tdec(a), tdec(b))
        return qdec(call('▶', v))
    rnd = random.Random(11)
    AQ = V('𝔸ℚ[i]')

    # exhaustive: the adder, in the language (all digit strings up to length 4) and in its python twin (all pairs with total length <= 12)
    import itertools, base_b
    ok = True
    strings = [list(t) for L in range(0, 5) for t in itertools.product([0, 1], repeat=L)]
    for a in strings:
        for b in strings:
            ok &= val(to_list(call('⊞ᶻ', E.raw(a), E.raw(b)))) == gadd(val(a), val(b))
    report(f"ℤ[i] adder in the language is exact on ALL {len(strings)**2} pairs of digit strings of length ≤ 4", ok)
    bad = n_ = 0
    for la in range(0, 9):
        for a in itertools.product([0, 1], repeat=la):
            for lb in range(0, 9):
                if la + lb > 12: continue
                for b in itertools.product([0, 1], repeat=lb):
                    n_ += 1; bad += val(base_b.add_digits(list(a), list(b))) != gadd(val(list(a)), val(list(b)))
    report(f"the adder's python twin (15 carry numerals, 10-entry tail+110 table) is exact on all {n_} pairs of total length ≤ 12", bad == 0)

    # Z[i] and Q[i]
    ok = True
    for _ in range(30):
        a = (rnd.randint(-30, 30), rnd.randint(-30, 30)); b = (rnd.randint(-30, 30), rnd.randint(-30, 30))
        ok &= val(to_list(call('⊞ᶻ', zint(a), zint(b)))) == gadd(a, b) and val(to_list(call('⊠ᶻ', zint(a), zint(b)))) == gmul(a, b) \
              and val(to_list(call('∗ᶻ', zint(a)))) == (a[0], -a[1])
    report("ℤ[i] in base i-1: add, multiply, conjugate agree with Gaussian integers", ok)
    ok = True
    for _ in range(20):
        x, y = R.randQ(rnd), R.randQ(rnd)
        while y.iszero(): y = R.randQ(rnd)
        X, Y = qval(x), qval(y)
        ok &= qdec(call('⊞', X, Y)) == x + y and qdec(call('⊠', X, Y)) == x * y and qdec(call('⊖', X)) == -x \
              and qdec(call('∗', X)) == x.conj() and qdec(call('÷', X, Y)) == x * y.inv() and qdec(call('⊟', X, Y)) == x - y
    report("ℚ[i]: + · − conj ÷ against exact Gaussian rationals", ok)

    # tower
    ok, n = True, 0
    for _ in range(12):
        x, y = R.randT(rnd, 2), R.randT(rnd, 2); X, Y = tval(x), tval(y)
        ok &= tdec(call('∔', AQ, X, Y)) == R.tadd(x, y) and tdec(call('⊠ᵀ', AQ, X, Y)) == R.tmul(x, y) \
              and tdec(call('⊖ᵀ', AQ, X)) == R.tneg(x) and tdec(call('∗ᵀ', AQ, X)) == R.tconj(x)
        n += 1
    report(f"Cayley–Dickson tower over ℚ[i] equals the python reference as ragged trees (shapes included), {n} random depth ≤ 2 pairs", ok)
    x = R.randT(rnd, 2)
    while R.depth(x) < 2: x = R.randT(rnd, 2)
    X = tval(x)
    z = tdec(call('∔', AQ, X, call('⊖ᵀ', AQ, X))); zz = tdec(call('⊠ᵀ', AQ, X, tval(R.zero_like(x))))
    report("dimension never reduces: x + (-x) and x·0 are zeros of the same depth; 1 + 0₂ has depth 2",
           R.depth(z) == 2 and R.tiszero(z) and R.depth(zz) == 2 and R.tiszero(zz) and R.depth(tdec(call('∔', AQ, tval(Q(1)), tval(R.zero_like(x))))) == 2)
    J, K = V('𝕛'), V('𝕜')
    ij = call('⊠𝔻', call('↑', qval(I)), J); ji = call('⊠𝔻', J, call('↑', qval(I)))
    report("quaternions (depth 1): j² = −1, ij = k = −ji, k² = −1",
           R.teq(tdec(call('⊠𝔻', J, J)), Q(-1)) and R.teq(tdec(ij), tdec(K)) and R.teq(tdec(ji), R.tneg(tdec(K))) and R.teq(tdec(call('⊠𝔻', K, K)), Q(-1)))

    def e(d, n_):
        if d == 0: return [ONE, I][n_]
        h = 2 ** d
        return (e(d - 1, n_), R.zero_like(e(d - 1, 0))) if n_ < h else (R.zero_like(e(d - 1, 0)), e(d - 1, n_ - h))
    def scale(t, c): return t * c if isinstance(t, Q) else (scale(t[0], c), scale(t[1], c))
    def lin(d, terms):
        s = None
        for c, n_ in terms:
            t = scale(e(d, n_), Q(c)); s = t if s is None else R.tadd(s, t)
        return s
    ea, eb, ec = e(2, 1), e(2, 2), e(2, 4)
    lhs = tdec(call('⊠𝔻', call('⊠𝔻', tval(ea), tval(eb)), tval(ec))); rhs = tdec(call('⊠𝔻', tval(ea), call('⊠𝔻', tval(eb), tval(ec))))
    x2, y2 = lin(2, [(1, 1), (2, 3), (-1, 5)]), lin(2, [(3, 0), (1, 6)])
    X2, Y2 = tval(x2), tval(y2)
    alt = R.teq(tdec(call('⊠𝔻', call('⊠𝔻', X2, X2), Y2)), tdec(call('⊠𝔻', X2, call('⊠𝔻', X2, Y2))))
    report("octonions (depth 2): non-associative ((e1 e2) e4 ≠ e1 (e2 e4)) but alternative ((xx)y = x(xy))", (not R.teq(lhs, rhs)) and alt)
    def find_zd(d):
        dim = 2 ** (d + 1)
        els = [lin(d, [(1, a), (sg, b)]) for a, b in itertools.combinations(range(dim), 2) for sg in (1, -1)]
        return [(x_, y_) for x_ in els for y_ in els if R.tiszero(R.tmul(x_, y_))]
    zd2, zd3 = find_zd(2), find_zd(3)
    report("exhaustive search over all (e_a ± e_b)(e_c ± e_d): octonions have no zero divisor, sedenions have some", len(zd2) == 0 and len(zd3) > 0, f"(depth 3: {len(zd3)} ordered pairs)")
    x3, y3 = lin(3, [(1, 1), (1, 10)]), lin(3, [(1, 4), (-1, 15)])
    pr = tdec(call('⊠𝔻', tval(x3), tval(y3)))
    nx = tdec(call('⊠𝔻', tval(x3), call('∗𝔻', tval(x3))))
    report("sedenions (depth 3): (e1 + e10)(e4 − e15) = 0 with both factors ≠ 0, evaluated in the language",
           R.tiszero(pr) and R.depth(pr) == 3 and not R.tiszero(nx), f"|x|² = {R.tflat(nx, R.depth(nx))[0]}")

    # lazy ℝ[i]: tower over streams
    AR = V('𝔸ℝ[i]'); zs, ps, es = V('𝕫'), V('π'), V('𝕖')
    x = call('❁', call('❀', zs), call('❀', ps)); y = call('❁', call('❀', es), call('❀', zs))
    pr = call('⊠ᵀ', AR, x, y)
    def at(v, N):
        if to_bool(call('◀', v)):
            a, b = to_pair(call('▶', v)); return (at(a, N), at(b, N))
        return qdec(stream_nth(call('▶', v), N))
    def pN(N):
        s = t = Fr(2)
        for k in range(1, N + 1): t = t * k / (2 * k + 1); s += t
        return s
    def eN(N):
        s = t = Fr(1)
        for k in range(1, N + 1): t = t / k; s += t
        return s
    ok = all(at(pr, N) == R.tmul((Q(pN(N), eN(N)), Q(pN(N))), (Q(eN(N)), Q(pN(N), eN(N)))) for N in range(0, 4))
    report("Cayley–Dickson over the lazy ℝ[i]: the quaternion (z, π)·(e, z) is computed streamwise and matches exact partial sums", ok)

    # function spaces
    AF = call('𝔉', AQ); fz, fs = V('ϝ'), V('ϛ')
    ip = call('⟨⟩', AQ, fz, fs); nn = call('⟨⟩', AQ, fz, fz)
    ok = all(qdec(stream_nth(ip, N)) == Q(Fr(N, N + 1)) for N in range(0, 7))
    report("ℓ² over ℚ[i]: ⟨ϝ, ϛ⟩_N = Σ 1/((n+1)(n+2)) = N/(N+1)", ok)
    report("‖ϝ‖²_N = Σ_{n<N} 1/(n+1)²  (partial sums of ζ(2))", all(qdec(stream_nth(nn, N)) == Q(sum(Fr(1, (n_ + 1) ** 2) for n_ in range(N))) for N in range(0, 7)))
    d2, d3 = call('δ', AQ, qval(Q(2))), call('δ', AQ, qval(Q(3)))
    ok = all(qdec(stream_nth(call('⟨⟩', AQ, d2, d3), N)) == Q(0) and qdec(stream_nth(call('⟨⟩', AQ, d2, d2), N)) == (Q(1) if N >= 3 else Q(0)) for N in range(0, 6))
    report("the standard basis vectors δ_2, δ_3 are orthonormal in the function space", ok)
    xv = qval(Q(3))
    ok = qdec(call(call(call('Ⓐ', AF), fz, fs), xv)) == qdec(call(fz, xv)) + qdec(call(fs, xv)) and qdec(call(call(call('Ⓜ', AF), fz, fs), xv)) == qdec(call(fz, xv)) * qdec(call(fs, xv))
    report("𝔉(ℚ[i]): pointwise + and × agree with the values of ϝ and ϛ", ok)
    AT = call('𝕋', AQ)
    qf, qg = V('qf'), V('qg')
    ipq = call('⟨⟩', AT, qf, qg); acc, ok = None, True
    for N in range(0, 5):
        if N > 0:
            term = R.tmul(R.tconj((Q(Fr(1, N)), Q(Fr(1, N + 1)))), (I, ONE)); acc = term if acc is None else R.tadd(acc, term)
        ok &= R.teq(tdec(stream_nth(ipq, N)), acc if acc is not None else ZERO)
    report("function space of quaternion-valued sequences (base = the Cayley–Dickson tower): ⟨f, g⟩_N matches the python reference", ok)
    P2 = call('⊠ᵀ', AF, call('❁', call('❀', fz), call('❀', fs)), call('❁', call('❀', fs), call('❀', fz)))
    ok = True
    for n_ in range(0, 4):
        a_, b_ = to_pair(call('▶', P2)); xv = qval(Q(n_))
        want = R.tmul((Q(Fr(1, n_ + 1)), Q(Fr(1, n_ + 2))), (Q(Fr(1, n_ + 2)), Q(Fr(1, n_ + 1))))
        ok &= qdec(call(call('▶', a_), xv)) == want[0] and qdec(call(call('▶', b_), xv)) == want[1]
    report("Cayley–Dickson over a function space (ℚ[i]^ℕ ⊕ ℚ[i]^ℕ j): ((ϝ,ϛ)·(ϛ,ϝ))(n) = CD product of the values", ok)
    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed  ({time.time()-t0:.1f}s)")
run_big(main)
