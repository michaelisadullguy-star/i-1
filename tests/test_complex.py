"""test_complex.py -- functions of a complex variable (lib/complex.imo): every function is evaluated in the language at several points
(real, negative, complex, near branch cuts) and element N of the stream is compared with an independent reference computed in Python
(math, cmath, or a series written here with plenty of terms).  The modulus of convergence is part of the contract: element N is within
2^-N of the value, so |element N - reference| <= 2^-N (plus the reference's own rounding, 1e-12).
Statements go through the human notation, doc 2 (overloads: a real argument picks the real function), the class checker, and the evaluator.
python3 tests/test_complex.py"""
import os, sys, math, cmath, time
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()
I = 1j

# ---------------------------------------------------------------------------------------------------------- references
def gamma_c(z):
    """Lanczos approximation (g = 7, n = 9): accurate to ~1e-14"""
    g = 7
    p = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059,
         12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
    z = complex(z)
    if z.real < 0.5: return cmath.pi / (cmath.sin(cmath.pi * z) * gamma_c(1 - z))
    z -= 1
    x = p[0]
    for i in range(1, g + 2): x += p[i] / (z + i)
    t = z + g + 0.5
    return cmath.sqrt(2 * cmath.pi) * t ** (z + 0.5) * cmath.exp(-t) * x

def digamma_r(x):
    r = 0.0
    while x < 20: r -= 1 / x; x += 1
    f = 1 / (x * x)
    return r + math.log(x) - 0.5 / x - f * (1 / 12 - f * (1 / 120 - f * (1 / 252 - f * (1 / 240 - f / 132))))

def zeta_r(s):
    if s == 1: return 0.0
    if s < 0 and float(s) != int(s) or s < 0:
        return 2 ** s * math.pi ** (s - 1) * math.sin(math.pi * s / 2) * math.gamma(1 - s) * zeta_r(1 - s)
    N = 60
    t = sum(k ** -s for k in range(1, N))
    t += N ** (1 - s) / (s - 1) + 0.5 * N ** -s
    B = [1 / 6, -1 / 30, 1 / 42, -1 / 30, 5 / 66, -691 / 2730, 7 / 6]
    term = s * N ** (-s - 1)
    fact = 2.0
    for j, b in enumerate(B, 1):
        t += b / math.factorial(2 * j) * (math.prod(s + i for i in range(2 * j - 1)) * N ** (-s - 2 * j + 1))
    return t

def erf_c(z):
    z = complex(z); t = z; s = z; k = 0
    while abs(t) > 1e-18 or k < 5:
        k += 1; t *= -z * z / k; s += t / (2 * k + 1)
        if k > 400: break
    return 2 / math.sqrt(math.pi) * s

def polylog_r(s, z):
    if s <= 0:
        # Li_{-t}(z) from repeated z d/dz of z/(1-z)
        f = lambda w: w / (1 - w)
        import itertools
        # use the Eulerian-number closed form via series sum_k k^t z^k (|z|<1)
        return sum((k ** -s) * z ** k for k in range(1, 4000))
    return sum(z ** k / k ** s for k in range(1, 4000))

def lambertw_r(x):
    w = math.log(1 + x) if x > -0.3 else -0.9
    for _ in range(80):
        e = math.exp(w); f = w * e - x
        w -= f / (e * (w + 1) - (w + 2) * f / (2 * w + 2))
    return w

def bessel_j(n, x):
    s = 0.0
    for k in range(0, 80):
        s += (-1) ** k / (math.factorial(k) * math.factorial(k + abs(n))) * (x / 2) ** (2 * k + abs(n))
    return s * (-1) ** n if n < 0 else s

def agm_r(a, b):
    for _ in range(40): a, b = (a + b) / 2, math.sqrt(a * b)
    return a

def ellipk_r(m): return math.pi / (2 * agm_r(1, math.sqrt(1 - m)))
def ellipe_r(m):
    # E(m) = K(m) (1 - sum_{n>=0} 2^(n-1) c_n^2),  c_0^2 = m,  c_{n+1} = (a_n - b_n)/2   (Gauss; valid for every m < 1)
    a, b = 1.0, math.sqrt(1 - m); s = m / 2; n = 0
    for _ in range(30):
        a, b, c = (a + b) / 2, math.sqrt(a * b), (a - b) / 2
        n += 1; s += 2 ** (n - 1) * c * c
    return ellipk_r(m) * (1 - s)

def Ei_r(x):
    return 0.5772156649015329 + math.log(abs(x)) + sum(x ** k / (k * math.factorial(k)) for k in range(1, 120))
def li_r(x): return Ei_r(math.log(x))
def Si_r(x): return sum((-1) ** k * x ** (2 * k + 1) / ((2 * k + 1) * math.factorial(2 * k + 1)) for k in range(0, 60))
def Ci_c(z):
    z = complex(z)
    return 0.5772156649015329 + cmath.log(z) + sum((-1) ** k * z ** (2 * k) / (2 * k * math.factorial(2 * k)) for k in range(1, 60))

def sinc_c(z): return 1.0 if z == 0 else cmath.sin(z) / z
def cbrt_c(z):
    z = complex(z)
    if z.imag == 0: return math.copysign(abs(z.real) ** (1 / 3), z.real)
    return z ** (1 / 3)
def pow_c(z, w):
    z, w = complex(z), complex(w)
    if w == int(w.real) and w.imag == 0: return z ** int(w.real) if z != 0 or w.real >= 0 else 0
    if z == 0: return 0
    return cmath.exp(w * cmath.log(z))
def acoth_c(z): return cmath.atanh(1 / z) if z != 0 else 1j * math.pi / 2

# (human expression, reference value, N)   N: the element compared (error <= 2^-N)
Q = lambda s: s     # readability
CASES = []
def add(expr, ref, n=16): CASES.append((expr, complex(ref), n))

for z, t in [(Fr(3), '3'), (Fr(1, 2), '1/2'), (Fr(-5, 2), '-5/2'), (Fr(1, 2) + 2 * Fr(3, 4) * 0, '1/2')]:
    pass
# constants
add('Pi', math.pi, 24); add('E', math.e, 24); add('EulerGamma', 0.5772156649015329, 24); add('Catalan', 0.915965594177219, 24)
# logarithms, powers, roots
for z in ['1/2 + 3*i/4', '-3', '5', '-1/2 - i', '2*i']:
    zz = eval(z.replace('i', 'j').replace('/', '/').replace('^', '**'), {'j': 1j}) if False else None
def cz(text):
    """a human complex literal such as  '1/2 + 3*i/4'  as a Python complex"""
    t = text.replace('i', 'J_')
    return eval(t.replace('J_', '1j'), {'__builtins__': {}})
PTS = ['1/2 + 3*i/4', '-3', '5', '-1/2 - i', '2*i', '1/3 - 2*i/3', '7/2']
for p in PTS:
    z = cz(p)
    add(f'Log({p})', cmath.log(z)); add(f'log1p({p})', cmath.log(1 + z) if z != -1 else 0)
    add(f'expm1({p})', cmath.exp(z) - 1); add(f'arg({p})', cmath.phase(z)); add(f'csgn({p})', z / abs(z))
    add(f'cbrt({p})', cbrt_c(z)); add(f'nthroot({p}, 3)', z ** (1 / 3)); add(f'nthroot({p}, -2)', z ** (-1 / 2))
    add(f'cis({p})' if p in ('5', '7/2', '-3') else f'cos({p})', cmath.exp(1j * z) if p in ('5', '7/2', '-3') else cmath.cos(z))
for a, b in [('2', '3'), ('1/2', '1/3'), ('-1/2', '5')]:
    add(f'pow({a}, {b})', pow_c(cz(a), cz(b))); add(f'pow({a} + i, {b})', pow_c(cz(a) + 1j, cz(b)))
add('pow(1/2 + i, 1/2 - i)', pow_c(0.5 + 1j, 0.5 - 1j)); add('pow(0, 2)', 0); add('pow(0, 0)', 1); add('pow(0, 1/2)', 0); add('pow(-8, 1/3)', pow_c(-8, 1 / 3))
add('logb(2, 8)', 3); add('logb(1/2, 1/8)', 3); add('logb(3, 5)', math.log(5) / math.log(3))
add('hypot(3, 4)', 5); add('hypot(1/2, -1/3)', math.hypot(0.5, 1 / 3))
add('atan2(1, 1)', math.pi / 4); add('atan2(-1, -1)', -3 * math.pi / 4); add('atan2(0, -1)', math.pi); add('atan2(3, -4)', math.atan2(3, -4)); add('atan2(0, 0)', 0)
add('polar(2, 1/2)', 2 * cmath.exp(0.5j)); add('cis(1)', cmath.exp(1j)); add('cis(-7/2)', cmath.exp(-3.5j))
# trigonometric / hyperbolic family
for p in ['1/2', '-3/2', '2', '1/2 + 3*i/4', '-1 + i', '3*i/2', '1/4 - 2*i']:
    z = cz(p)
    add(f'cot({p})', 1 / cmath.tan(z)); add(f'sec({p})', 1 / cmath.cos(z)); add(f'csc({p})', 1 / cmath.sin(z))
    add(f'coth({p})', 1 / cmath.tanh(z)); add(f'sech({p})', 1 / cmath.cosh(z)); add(f'csch({p})', 1 / cmath.sinh(z))
    add(f'sinc({p})', sinc_c(z)); add(f'tan({p})', cmath.tan(z)); add(f'sinh({p})', cmath.sinh(z)); add(f'cosh({p})', cmath.cosh(z)); add(f'tanh({p})', cmath.tanh(z))
for p in ['1/2', '-1/2', '2', '-3', '1/2 + 3*i/4', '-1 + i', '3*i/2', '1/4 - 2*i', '3 + 2*i', '-2 - i/2']:
    z = cz(p)
    add(f'asin({p})', cmath.asin(z)); add(f'acos({p})', cmath.acos(z)); add(f'atan({p})' if False else f'asinh({p})', cmath.asinh(z))
    add(f'acosh({p})', cmath.acosh(z)); add(f'atanh({p})', cmath.atanh(z) if z not in (1, -1) else 0)
    add(f'acot({p})', cmath.atan(1 / z) if z != 0 else math.pi / 2); add(f'asec({p})', cmath.acos(1 / z)); add(f'acsc({p})', cmath.asin(1 / z))
    add(f'acoth({p})', acoth_c(z)); add(f'asech({p})', cmath.acosh(1 / z)); add(f'acsch({p})', cmath.asinh(1 / z))
for p in ['2', '-1/2', '1/4']:
    z = cz(p)
# special functions
for p in ['3', '1/2', '-5/2', '7/3', '1/2 + i', '3 - 2*i/3']:
    z = cz(p); add(f'gamma({p})', gamma_c(z), 14)
for x in ['1/2', '3', '9/2', '10', '-1/2']:
    if cz(x) > 0: add(f'lgamma({x})', math.lgamma(float(cz(x).real)), 14)
    add(f'digamma({x})', digamma_r(float(cz(x).real)) if cz(x).real > 0 else digamma_r(1 - float(cz(x).real)) - math.pi / math.tan(math.pi * float(cz(x).real)), 14)
add('lgamma(-1/2)', math.lgamma(-0.5), 14)
for a, b in [('1/2', '1/2'), ('3', '4'), ('5/2', '1/3')]:
    add(f'beta({a}, {b})', math.gamma(float(cz(a).real)) * math.gamma(float(cz(b).real)) / math.gamma(float(cz(a).real) + float(cz(b).real)), 14)
for x in ['1/2', '-3/2', '1', '2', '1/2 + i', '3*i/4']:
    z = cz(x); add(f'erf({x})', erf_c(z), 14); add(f'erfc({x})', 1 - erf_c(z), 14)
for s in ['2', '3', '4', '1/2 + 0', '5/2', '3/2', '-1', '-2', '0']:
    v = zeta_r(float(cz(s).real)) if s != '0' else -0.5
    add(f'zeta({s})', v, 14)
add('zeta(3/2)', 2.612375348685488, 14); add('zeta(2)', math.pi ** 2 / 6, 14); add('zeta(4)', math.pi ** 4 / 90, 14); add('zeta(-1)', -1 / 12, 14); add('zeta(0)', -0.5, 14)
for s, z in [(2, '1/2'), (3, '-1/2'), (1, '1/3'), (2, '1/4 + i/4'), (0, '1/2'), (-1, '1/3'), (-2, '-1/2')]:
    add(f'polylog({s}, {z})', polylog_r(s, cz(z)) if s != 1 else -cmath.log(1 - cz(z)), 14)
for x in ['0', '1', '-1/4', '5', '1/2']:
    xv = float(cz(x).real)
    if xv >= -1 / math.e: add(f'lambertw({x})', lambertw_r(xv), 14)
for n, x in [(0, '1'), (1, '3'), (2, '1/2'), (-1, '2'), (3, '5'), (0, '-3/2'), (1, '1/2 + i')]:
    xv = cz(x)
    add(f'besselj({n}, {x})', bessel_j(n, xv.real) if xv.imag == 0 else sum((-1) ** k / (math.factorial(k) * math.factorial(k + abs(n))) * (xv / 2) ** (2 * k + abs(n)) for k in range(60)), 14)
for n, x in [(0, '1'), (1, '3'), (2, '1/2'), (-1, '2'), (0, '-3/2'), (1, '1/2 + i')]:
    xv = cz(x)
    add(f'besseli({n}, {x})', sum((xv / 2) ** (2 * k + abs(n)) / (math.factorial(k) * math.factorial(k + abs(n))) for k in range(80)), 14)
for x in ['1/2', '-3/2', '2', '1/2 + i', '3*i/4']:
    xv = cz(x); add(f'erfi({x})', 2 / math.sqrt(math.pi) * sum(xv ** (2 * k + 1) / (math.factorial(k) * (2 * k + 1)) for k in range(120)), 14)
for a, b in [('1', '2'), ('3', '3'), ('1/2', '7'), ('5', '1/3')]:
    add(f'agm({a}, {b})', agm_r(float(cz(a).real), float(cz(b).real)), 14)
for m in ['0', '1/2', '-1', '9/10', '-5']:
    mv = float(cz(m).real); add(f'ellipk({m})', ellipk_r(mv), 14); add(f'ellipe({m})', ellipe_r(mv), 14)
add('ellipe(1)', 1, 14); add('ellipk(1)', 0, 14)
for x in ['1/2', '3', '-2']:
    add(f'expint({x})', Ei_r(float(cz(x).real)), 14)
for x in ['2', '3/2', '10']:
    add(f'li({x})', li_r(float(cz(x).real)), 14)
for x in ['1', '4', '-3/2', '1/2 + i']:
    z = cz(x); add(f'Si({x})', sum((-1) ** k * z ** (2 * k + 1) / ((2 * k + 1) * math.factorial(2 * k + 1)) for k in range(60)), 14)
for x in ['1', '4', '-3/2', '1/2 + i']:
    z = cz(x); add(f'Shi({x})', sum(z ** (2 * k + 1) / ((2 * k + 1) * math.factorial(2 * k + 1)) for k in range(80)), 14)
for x in ['1', '4', '-3/2', '1/2 + i']:
    z = cz(x); add(f'Chi({x})', 0.5772156649015329 + cmath.log(z) + sum(z ** (2 * k) / (2 * k * math.factorial(2 * k)) for k in range(1, 80)), 14)
for x in ['1/2', '-3/2', '2', '1/2 + i', '3*i/4']:
    z = cz(x); add(f'dawson({x})', cmath.exp(-z * z) * math.sqrt(math.pi) / 2 * (-1j) * erf_c(1j * z), 14)
for x in ['1', '4', '-3/2', '1/2 + i']:
    add(f'Ci({x})', Ci_c(cz(x)), 14)

# the roots of unity are a list
ROOTS = [(1, ), (2, ), (3, ), (5, )]

G_E = None
def run_case(k):
    e, ref, n = CASES[k]; t = time.time()
    try:
        v = G_E.dq(G_E.nth(G_E.V(f'c{k}'), n)); got = complex(float(v.r), float(v.i))
        ok = abs(got - ref) <= 2.0 ** -n + 1e-12; err = abs(got - ref)
    except BaseException as ex:
        got, ok, err = repr(ex)[:60], False, float('inf')
    return k, got, ok, err, time.time() - t

def main():
    SRC = "\n".join(f"c{k} in \\R := {e}" for k, (e, ref, n) in enumerate(CASES))
    SRC += "\nrt in List(\\R) := rootsofunity(3)\nrt0 in List(\\R) := rootsofunity(0)\n"
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'complex.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("every statement of the test program passes the class checker (real arguments pick the real function, complex ones the complex)", not errs, str(errs[:2]))
    if errs: return rep.done()
    P.build(); E = Env(P)
    groups = {}
    only = [x for a in sys.argv[1:] if a.startswith('--only=') for x in a.split('=', 1)[1].split(',')]
    first = '--first' in sys.argv
    jobs = int(([a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--jobs=')] or ['4'])[0])
    todo = list(range(len(CASES)))
    if only: todo = [k for k in todo if CASES[k][0].split('(')[0] in only]
    if first:
        seen = set(); keep = []
        for k in todo:
            nm = CASES[k][0].split('(')[0]
            if nm not in seen: seen.add(nm); keep.append(k)
        todo = keep
    global G_E
    G_E = E
    import multiprocessing as mp
    with mp.get_context('fork').Pool(jobs) as pool:
        for k, got, ok, err, dt in pool.imap_unordered(run_case, todo):
            e, ref, n = CASES[k]
            print(f"  [{dt:6.1f}s] {'ok ' if ok else 'BAD'} {e}  (err {err:.1e})", flush=True)
            groups.setdefault(e.split('(')[0], []).append((e, ref, got, ok, err, n))
    order = list(groups)
    for name in order:
        rows = groups[name]
        bad = [(e, ref, got) for e, ref, got, ok, err, n in rows if not ok]
        rep(f"{name}: {len(rows)} points, element N within 2^-N of the reference (worst error {max(r[4] for r in rows):.2e})", not bad,
            '' if not bad else "\n      " + "\n      ".join(f"{e}: expected {ref}, got {got}" for e, ref, got in bad[:4]))
    rt = E.lst(E.V('rt'))
    ok = len(rt) == 3 and all(abs(complex(float((q := E.dq(E.nth(r, 16))).r), float(q.i)) - cmath.exp(2j * math.pi * k / 3)) <= 2 ** -16 + 1e-12 for k, r in enumerate(rt))
    rep("rootsofunity(3) lists e^(2 pi i k / 3) for k = 0, 1, 2; rootsofunity(0) is empty", ok and not E.lst(E.V('rt0')))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
