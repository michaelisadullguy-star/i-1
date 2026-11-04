"""test_library.py -- the library added in parts 6–10 of the prelude (arith, list, real, linalg, set), used from the HUMAN notation:
every statement goes through doc 2, overload resolution and the class checker, then is evaluated and compared with python.
python3 tests/test_library.py"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()

SRC = r'''
a1 in \ZZ := 17 div 5
a2 in \ZZ := -17 div 5
a3 in \ZZ := -17 mod 5
a4 in \NN := gcd(84, 36)
a5 in \NN := lcm(4, 6)
a6 in \ZZ := floor(-7 / 2)
a7 in \ZZ := ceil(-7 / 2)
a8 in \ZZ := round(5 / 2)
a9 in \QQ := 2 ^ 10 + (1 / 2) ^ 3
a10 in \Q := (1 + i) ^ -2
a11 in \NN := factorial(10)
a12 in \NN := choose(30, 12)
a13 in \NN := isqrt(1000000)
a14 in \Z := gcd(4 + 2 * i, 3 + i)
a15 in \Z := rem(7 + 5 * i, 2 + i)
a16 in \QQ := abs(-3 / 4) + sgn(-5) + max(2, 7 / 3) + min(-1, 0)
a17 in \QQ := re((1 + 2 * i) / (3 - i)) + im((1 + 2 * i) / (3 - i))
a18 in \QQ := norm(3 + 4 * i)
a19 in \Q := canon(6 / 4)
b1 in Bool := (1 lt 2) implies (2 lt 3)
b2 in Bool := (1 lt 2) iff (3 lt 2)
b3 in Bool := xor(true, false)
l1 in List(\NN) := take(5, seq(k in \NN |-> k * k))
l2 in List(\NN) := filter(k in \NN |-> k mod 2 == 0, range(10))
l3 in \NN := foldr(x in \NN |-> y in \NN |-> x + y, 0, range(11))
l4 in List(\NN) := reverse(upto(3, 7))
l5 in List(\QQ) := sort(cons(3, cons(1 / 2, cons(-2, cons(1, nil)))))
l6 in \NN := nth(seq(k in \NN |-> 3 * k + 1), 20)
l7 in \QQ := sumof(cons(1 / 2, cons(1 / 3, cons(1 / 6, nil))))
l8 in Bool := elem(4, range(5)) and not elem(5, range(5))
l9 in List(\NN) := concat(cons(range(2), cons(upto(5, 6), nil)))
s1 in Bool := "abc" == "abc"
s2 in Bool := "abc" == "abd"
s3 in Char := chr(955)
s4 in Char := chr(1114112)
d1 in \Z := band(13, 6)
d2 in \Z := shl(3, 4)
d3 in \Z := shr(shl(3 + 2 * i, 5), 5)
d4 in \NN := ndigits(i)
r1 in \RR := sqrt(2)
r2 in \R := sqrt(-4)
r3 in \R := sqrt(3 + 4 * i)
r4 in \RR := log(2)
r5 in \RR := atan(1)
r6 in \RR := sinh(1 / 2) + cosh(1 / 2)
r7 in \RR := tan(1 / 2)
r8 in \RR := exp(sqrt(2))
r9 in \RR := deriv(x in \QQ |-> x * x * x, 2)
r10 in \RR := integral(x in \QQ |-> x * x, 0, 1)
m1 in \Q := det(cons(cons(2, cons(1, nil)), cons(cons(1, cons(3, nil)), nil)))
m2 in List(\Q) := solve(cons(cons(2, cons(1, nil)), cons(cons(1, cons(3, nil)), nil)), cons(3, cons(5, nil)))
m3 in \Q := det(cons(cons(0, cons(1, cons(2, nil))), cons(cons(1, cons(0, cons(3, nil))), cons(cons(4, cons(-3, cons(8, nil))), nil))))
m4 in List(List(\Q)) := mmul(identity(2), cons(cons(1, cons(i, nil)), cons(cons(0, cons(1, nil)), nil)))
m5 in List(List(\Q)) := inverse(cons(cons(1, cons(2, nil)), cons(cons(3, cons(4, nil)), nil)))
t1 in Bool := member(3, union(setof(range(2)), setof(cons(3, nil))))
t2 in Bool := member(1, setminus(setof(range(3)), setof(cons(1, nil))))
t3 in List(\Q) := members(compl(setof(cons(2, cons(4, nil)))), range(6))
'''

def main():
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'library.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("every statement of the library test program passes the class checker", not errs, str(errs[:2]) if errs else '')
    if errs: return rep.done()
    P.build(); E = Env(P)
    q = lambda n: E.dq(E.V(P.hum.spec_name(n)))
    L = lambda n: [E.dq(x) for x in E.lst(E.V(n))]
    Fq = lambda x: R.Q(Fr(x))
    rep("integer division and remainder (floor convention), gcd, lcm, floor, ceil, round",
        [q(f'a{k}') for k in range(1, 9)] == [Fq(3), Fq(-4), Fq(3), Fq(12), Fq(12), Fq(-4), Fq(-3), Fq(3)])
    rep("powers (natural and negative exponents), factorial, binomial, integer square root",
        q('a9') == Fq(Fr(8193, 8)) and q('a10') == (R.Q(1, 1) * R.Q(1, 1)).inv() and q('a11') == Fq(math.factorial(10))
        and q('a12') == Fq(math.comb(30, 12)) and q('a13') == Fq(1000))
    g = q('a14')
    rep("Gaussian gcd (normalised to Re > 0, Im ≥ 0) and Gaussian remainder with N(r) ≤ N(b)/2",
        g == R.Q(1, 1) and (lambda r: (r.r ** 2 + r.i ** 2) * 2 <= 5)(q('a15')))
    rep("abs, sgn, max, min, re, im, norm, canon", q('a16') == Fq(Fr(3, 4) - 1 + Fr(7, 3) - 1) and q('a17') == Fq(Fr(1, 10) + Fr(7, 10))
        and q('a18') == Fq(25) and E.pair_digits(E.V('a19')) == (to_digits((3, 0)), to_digits((2, 0))))
    rep("implies, iff, xor", E.b(E.V('b1')) and not E.b(E.V('b2')) and E.b(E.V('b3')))
    rep("lists and streams: take/seq, filter, foldr, reverse/upto, sort, nth, sumof, elem, concat",
        L('l1') == [Fq(k * k) for k in range(5)] and L('l2') == [Fq(k) for k in range(0, 10, 2)] and q('l3') == Fq(55)
        and L('l4') == [Fq(k) for k in (7, 6, 5, 4, 3)] and L('l5') == [Fq(-2), Fq(Fr(1, 2)), Fq(1), Fq(3)] and q('l6') == Fq(61)
        and q('l7') == Fq(1) and E.b(E.V('l8')) and L('l9') == [Fq(0), Fq(1), Fq(5), Fq(6)])
    rep("string equality, chr (a value outside Unicode gives U+FFFD)", E.b(E.V('s1')) and not E.b(E.V('s2')) and q('s3') == Fq(955) and q('s4') == Fq(0xFFFD))
    pad = lambda d, n: d + [0] * (n - len(d))
    A, B = to_digits((13, 0)), to_digits((6, 0)); n = max(len(A), len(B))
    rep("digit-wise and, shifts (z·bⁿ and back), number of digits",
        q('d1') == R.Q(*val([x & y for x, y in zip(pad(A, n), pad(B, n))])) and q('d2') == Fq(-12) and q('d3') == R.Q(3, 2) and q('d4') == Fq(2))
    def at(name, n): return E.dq(E.nth(E.V(name), n))
    ok = abs(float(at('r1', 30).r) - math.sqrt(2)) <= 2 ** -30 and at('r1', 30).r <= Fr(math.isqrt(2 * 4 ** 30), 2 ** 30)
    ok &= at('r2', 12) == R.Q(0, 2) and at('r3', 16) == R.Q(2, 1)
    rep("sqrt: element n of √2 is ⌊√(2·4ⁿ)⌋/2ⁿ (within 2⁻ⁿ); √−4 = 2i, √(3 + 4i) = 2 + i exactly once n is large enough", ok)
    ok = abs(float(at('r4', 20).r) - math.log(2)) < 1e-12 and abs(float(at('r5', 40).r) - math.pi / 4) < 1e-12
    ok &= abs(float(at('r6', 10).r) - math.exp(.5)) < 1e-12 and abs(float(at('r7', 12).r) - math.tan(.5)) < 1e-12
    ok &= abs(float(at('r8', 18).r) - math.exp(math.sqrt(2))) < 5 * 2 ** -18          # √2 is within 2⁻¹⁸ at element 18, and exp' < 5 there
    rep("log 2, atan 1 = π/4 (Euler's series), sinh + cosh = exp, tan, and exp of a lazy argument (exp √2) converge to the true values", ok)
    ok = at('r9', 6) == Fq(12 + Fr(1, 4 ** 6)) and abs(float(at('r10', 12).r) - 1 / 3) <= 1 / (12 * 13 ** 2) + 1e-15
    rep("derivative of x³ at 2 (central differences: exactly 12 + h²), integral of x² on [0, 1] (midpoint rule, error 1/(12 n²))", ok)
    ok = q('m1') == Fq(5) and L('m2') == [Fq(Fr(4, 5)), Fq(Fr(7, 5))] and q('m3') == Fq(-2)
    m4 = [[E.dq(x) for x in E.lst(r)] for r in E.lst(E.V('m4'))]
    m5 = [[E.dq(x) for x in E.lst(r)] for r in E.lst(E.V('m5'))]
    ok &= m4 == [[Fq(1), R.Q(0, 1)], [Fq(0), Fq(1)]] and m5 == [[Fq(-2), Fq(1)], [Fq(Fr(3, 2)), Fq(Fr(-1, 2))]]
    rep("linear algebra: det (with a pivot swap), solve, mmul with the identity, inverse", ok)
    rep("sets as characteristic functions: member, union, setminus, compl, setof, members",
        E.b(E.V('t1')) and not E.b(E.V('t2')) and L('t3') == [Fq(0), Fq(1), Fq(3), Fq(5)])
    return rep.done()

sys.exit(0 if run_big(main) else 1)
