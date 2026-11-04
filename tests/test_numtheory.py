"""test_numtheory.py -- lib/numtheory.imo (number theory over ℤ and ℤ[i]) used from the HUMAN notation: every statement goes through
doc 2, overload resolution and the class checker, is evaluated in the language, decoded, and compared with an independent python
computation (plain loops, standard library only).
python3 tests/test_numtheory.py            (all groups)
python3 tests/test_numtheory.py fib pell   (only the groups whose name contains one of the words)"""
import os, sys, math, time
from fractions import Fraction as Fr
from math import gcd, comb, factorial, isqrt, prod
from functools import reduce
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()

# ---------------------------------------------------------------------------------------------------------------------------------
# independent references
def lcm2(a, b): return 0 if a == 0 or b == 0 else abs(a * b) // gcd(a, b)

def is_prime_td(n):
    if n < 2: return False
    d = 2
    while d * d <= n:
        if n % d == 0: return False
        d += 1
    return True

FIRST13 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
def is_sprp(n, a):
    d, s = n - 1, 0
    while d % 2 == 0: d //= 2; s += 1
    x = pow(a, d, n)
    if x in (1, n - 1): return True
    for _ in range(s - 1):
        x = x * x % n
        if x == n - 1: return True
    return False

def is_prime_mr(n):                       # deterministic below 3.3·10²⁴ (bases 2 … 41, A014233)
    if n < 2: return False
    for p in FIRST13:
        if n % p == 0: return n == p
    return all(is_sprp(n, a) for a in FIRST13)

def factor_ref(n):
    n = abs(n); out = []
    if n < 2: return out
    d = 2
    while d * d <= n:
        e = 0
        while n % d == 0: n //= d; e += 1
        if e: out.append((d, e))
        d += 1 if d == 2 else 2
    if n > 1: out.append((n, 1))
    return out

def divisors_ref(n):
    n = abs(n)
    return [d for d in range(1, n + 1) if n % d == 0] if n else []

def totient_ref(n):
    n = abs(n)
    return sum(1 for k in range(1, n + 1) if gcd(k, n) == 1) if n else 0

def order_ref(a, n):
    if n == 1: return 1
    if gcd(a, n) != 1: return 0
    x, k = a % n, 1
    while x != 1: x = x * a % n; k += 1
    return k

def carmichael_ref(n):
    n = abs(n)
    if n == 0: return 0
    return reduce(lcm2, [order_ref(a, n) for a in range(1, n + 1) if gcd(a, n) == 1], 1)

def mobius_ref(n):
    if n == 0: return 0
    f = factor_ref(n)
    return 0 if any(e > 1 for p, e in f) else (-1) ** len(f)

def legendre_euler(a, p):
    r = pow(a, (p - 1) // 2, p)
    return -1 if r == p - 1 else r

def jacobi_ref(a, n):
    if n <= 0 or n % 2 == 0: return 0
    return prod(legendre_euler(a % p, p) ** e for p, e in factor_ref(n))

def kronecker_ref(a, n):
    if n == 0: return 1 if abs(a) == 1 else 0
    r = -1 if (n < 0 and a < 0) else 1
    n = abs(n)
    while n % 2 == 0:
        n //= 2
        r *= 0 if a % 2 == 0 else (1 if a % 8 in (1, 7) else -1)
    return r * (prod(legendre_euler(a % p, p) ** e for p, e in factor_ref(n)) if n > 1 else 1)

def sqrtmod_ref(a, n):
    if n == 0:
        if a < 0: return -1
        r = isqrt(a); return r if r * r == a else -1
    for x in range(n):
        if (x * x - a) % n == 0: return x
    return -1

def crt_ref(rs, ms):
    pairs = list(zip(rs, ms))
    M = reduce(lcm2, [m for r, m in pairs], 1)
    if M == 0:
        x = [r for r, m in pairs if m == 0][0]
        ok = all(((x - r) % m == 0) if m else x == r for r, m in pairs)
        return (True, (x, 0)) if ok else (False, (0, 0))
    for x in range(M):
        if all((x - r) % m == 0 for r, m in pairs): return (True, (x, M))
    return (False, (0, 0))

def primroot_ref(n):
    if n < 2: return 0
    ph = totient_ref(n)
    for g in range(1, n):
        if gcd(g, n) == 1 and order_ref(g, n) == ph: return g
    return 0

def dlog_ref(a, b, n):
    for x in range(2 * n + 10):
        if (pow(a, x, n) - b) % n == 0: return x
    return -1

def contfrac_ref(q):
    q = Fr(q); out = []
    while True:
        a = q.numerator // q.denominator; out.append(a); q -= a
        if q == 0: return out
        q = 1 / q

def convergents_ref(cf):
    out, h0, h1, k0, k1 = [], 0, 1, 1, 0
    for a in cf:
        h0, h1 = h1, a * h1 + h0; k0, k1 = k1, a * k1 + k0
        out.append(Fr(h1, k1) if k1 else 0)
    return out

def cfsqrt_ref(n):
    a0 = isqrt(n)
    if a0 * a0 == n: return (a0, [])
    m, d, a, per = 0, 1, a0, []
    while a != 2 * a0:
        m = d * a - m; d = (n - m * m) // d; a = (a0 + m) // d; per.append(a)
    return (a0, per)

def pell_brute(D):
    y = 1
    while True:
        x2 = 1 + D * y * y; x = isqrt(x2)
        if x * x == x2: return (x, y)
        y += 1

def fib_ref(n):
    a, b = 0, 1
    for _ in range(abs(n)): a, b = b, a + b
    return a if n >= 0 or n % 2 else -a

def lucas_ref(n):
    a, b = 2, 1
    for _ in range(abs(n)): a, b = b, a + b
    return a if n >= 0 or n % 2 == 0 else -a

def bell_ref(n):
    B = [1]
    for m in range(n): B.append(sum(comb(m, k) * B[k] for k in range(m + 1)))
    return B[n]

def stirling1_ref(n, k):                  # coefficient of xᵏ in x(x−1)…(x−n+1)
    c = [1]
    for j in range(n):
        c = [(c[i - 1] if i else 0) - j * (c[i] if i < len(c) else 0) for i in range(len(c) + 1)]
    return c[k] if k < len(c) else 0

def stirling2_ref(n, k):
    return sum((-1) ** j * comb(k, j) * (k - j) ** n for j in range(k + 1)) // factorial(k)

def partitions_ref(n):
    p = [1] + [0] * n
    for part in range(1, n + 1):
        for m in range(part, n + 1): p[m] += p[m - part]
    return p[n]

def bernoulli_ref(n):
    B = [Fr(1)]
    for m in range(1, n + 1): B.append(-sum(comb(m + 1, k) * B[k] for k in range(m)) / (m + 1))
    return B[n]

def zetaeven_ref(n):
    if n == 0: return Fr(-1, 2)
    return (-1) ** (n + 1) * bernoulli_ref(2 * n) * 2 ** (2 * n) / (2 * factorial(2 * n))

def harmonic_ref(n): return sum((Fr(1, k) for k in range(1, n + 1)), Fr(0))

def digitsum_ref(n, b):
    n = abs(n)
    if b == 0: return 0
    if b == 1: return n
    s = 0
    while n: s += n % b; n //= b
    return s

def iroot_ref(n, k):
    if k == 0: return 0
    lo, hi = 0, 1
    while hi ** k <= n: hi *= 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if mid ** k <= n: lo = mid
        else: hi = mid
    return lo

def ispower_ref(n):
    if n in (0, 1, -1): return True
    m = abs(n)
    for k in range(2, m.bit_length() + 1):
        r = iroot_ref(m, k)
        if r ** k == m and (n > 0 or k % 2 == 1): return True
    return False

# Gaussian integers as (re, im)
def gmul(a, b): return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])
def gadd(a, b): return (a[0] + b[0], a[1] + b[1])
def gnorm(a): return a[0] * a[0] + a[1] * a[1]
def gdivexact(a, b):
    n = gnorm(b); c = gmul(a, (b[0], -b[1]))
    return (c[0] // n, c[1] // n) if c[0] % n == 0 and c[1] % n == 0 else None
def gnormalise(z):
    for _ in range(4):
        if z[0] > 0 and z[1] >= 0: return z
        z = (-z[1], z[0])
    return z
def gpow(z, e):
    r = (1, 0)
    for _ in range(e): r = gmul(r, z)
    return r
def gprimes_over(p):
    if p == 2: return [(1, 1)]
    if p % 4 == 3: return [(p, 0)]
    for b in range(1, isqrt(p) + 1):
        a = isqrt(p - b * b)
        if a * a + b * b == p and a > b: return [(a, b), (b, a)]
def gaussfactor_ref(z):
    if z == (0, 0): return ((0, 0), [])
    out = []
    for p, _ in factor_ref(gnorm(z)):
        for pi in gprimes_over(p):
            e = 0
            while True:
                q = gdivexact(z, pi)
                if q is None: break
                z, e = q, e + 1
            if e: out.append((pi, e))
    out.sort(key=lambda t: (gnorm(t[0]), t[0][1]))
    return (z, out)
def isgaussprime_ref(z):
    if z == (0, 0): return False
    u, f = gaussfactor_ref(z)
    return len(f) == 1 and f[0][1] == 1
def sumtwosquares_ref(n):
    if n < 0: return []
    out = []
    for b in range(isqrt(n // 2) + 1):
        a2 = n - b * b; a = isqrt(a2)
        if a * a == a2 and a >= b: out.append((a, b))
    return out
def gaussprimes_ref(n):
    out = [(a, b) for a in range(1, isqrt(n) + 1) for b in range(0, isqrt(n) + 1) if a * a + b * b <= n and isgaussprime_ref((a, b))]
    return sorted(out, key=lambda z: (gnorm(z), z[1]))
def ggcd_ref(a, b):
    while b != (0, 0):
        n = gnorm(b); c = gmul(a, (b[0], -b[1]))
        q = ((2 * c[0] + n) // (2 * n), (2 * c[1] + n) // (2 * n))
        qb = gmul(q, b); a, b = b, (a[0] - qb[0], a[1] - qb[1])
    return gnormalise(a) if a != (0, 0) else a
def gdivides(m, z):                        # m | z in ℤ[i]
    return z == (0, 0) if m == (0, 0) else gdivexact(z, m) is not None
def slprp_ref(n):                          # strong Lucas probable prime (Selfridge), U and V by their linear recurrences
    if n == 2: return True
    if n < 2 or n % 2 == 0 or isqrt(n) ** 2 == n: return False
    D = 5
    while True:
        g = gcd(abs(D), n)
        if 1 < g < n: return False
        if jacobi_ref(D, n) == -1: break
        D = -D - 2 if D > 0 else -D + 2
    P, Q = 1, (1 - D) // 4
    d, s = n + 1, 0
    while d % 2 == 0: d //= 2; s += 1
    U, V = [0, 1], [2, P]
    for k in range(2, n + 2):
        U.append((P * U[-1] - Q * U[-2]) % n); V.append((P * V[-1] - Q * V[-2]) % n)
    return U[d] == 0 or any(V[d * 2 ** r] == 0 for r in range(s))
def isgausspower_ref(z):
    if z == (0, 0) or gnorm(z) == 1: return True
    N = gnorm(z)
    for k in range(2, N.bit_length() + 1):
        m = iroot_ref(N, k)
        if m ** k != N: continue
        for a in range(-isqrt(m), isqrt(m) + 1):
            b = isqrt(m - a * a)
            if b * b == m - a * a and any(gpow((a, c), k) == z for c in (b, -b)): return True
    return False
def ramanujansum_ref(q, n):
    if q == 0: return 0
    return round(sum(math.cos(2 * math.pi * k * n / q) for k in range(1, q + 1) if gcd(k, q) == 1))

# ---------------------------------------------------------------------------------------------------------------------------------
# the cases: (class, human expression, expected value or predicate) in groups
G = {}
def case(group, cls, expr, want): G.setdefault(group, []).append((cls, expr, want))
def hz(z):                                 # a Gaussian integer in the human notation
    a, b = z
    if b == 0: return str(a)
    return f"({a} + {b} * i)" if b > 0 else f"({a} - {-b} * i)"
def hl(xs): return '[' + ', '.join(str(x) for x in xs) + ']'

# egcd
for a, b in [(240, 46), (-240, 46), (240, -46), (17, 0), (0, -5), (0, 0), (12, 18), (1, 1), (-7, -21), (1000000007, 998244353)]:
    case('egcd', 'Pair(\\NN, Pair(\\ZZ, \\ZZ))', f"egcd({a}, {b})",
         (lambda a, b: lambda v: v[0] == gcd(a, b) and v[1][0] * a + v[1][1] * b == v[0] and (a, b) != (0, 0) or v == (0, (0, 0)))(a, b))
for a, b in [((11, 3), (1, 8)), ((4, 2), (3, 1)), ((5, 0), (2, 1)), ((0, 0), (3, 3)), ((3, 0), (0, 2)), ((0, 0), (0, 0)), ((-6, 8), (2, 4))]:
    case('egcd Gaussian', 'Pair(\\Z, Pair(\\Z, \\Z))', f"egcd({hz(a)} + 0 * i, {hz(b)} + 0 * i)",
         (lambda a, b: lambda v: v[0] == ggcd_ref(a, b) and gadd(gmul(v[1][0], a), gmul(v[1][1], b)) == v[0])(a, b))
# modinv
for a, n in [(3, 7), (10, 7), (-3, 7), (6, 9), (5, 1), (0, 5), (1, 0), (2, 0), (12345, 1000003), (7, 1000000)]:
    want = 0
    if n > 1 and gcd(a, n) == 1: want = pow(a, -1, n)
    if n == 0: want = 1 if a == 1 else 0
    case('modinv', '\\NN' if a >= 0 else '\\ZZ', f"modinv({a}, {n})", want)
case('modinv', '\\ZZ', "modinv(-1, 0)", -1)
for a, m in [((2, 1), (3, 0)), ((1, 2), (5, 4)), ((3, 0), (0, 2)), ((1, 1), (2, 0))]:
    def chk(v, a=a, m=m):
        if ggcd_ref(a, m) != (1, 0): return v == (0, 0)
        d = gmul(a, v); return gdivides(m, (d[0] - 1, d[1]))
    case('modinv Gaussian', '\\Z', f"modinv({hz(a)} + 0 * i, {hz(m)} + 0 * i)", chk)
# powmod
for a, e, n in [(3, 100, 101), (2, 10, 1000), (-2, 5, 9), (7, 0, 13), (7, 0, 1), (0, 0, 7), (0, 5, 7), (5, -1, 7), (5, -3, 7), (4, -1, 8),
                (3, 200, 1024), (123456789, 987654321, 1000000007), (2, 64, 18446744073709551557)]:
    want = pow(a, e, n) if e >= 0 or gcd(a, n) == 1 else 0
    case('powmod', '\\NN' if a >= 0 else '\\ZZ', f"powmod({a}, {e}, {n})", want)
case('powmod', '\\ZZ', "powmod(-2, 3, 0)", -8)
case('powmod', '\\NN', "powmod(3, 4, 0)", 81)
case('powmod', '\\ZZ', "powmod(-3, 5, 7)", pow(-3, 5, 7))
# isprime
for n in [-7, -2, 0, 1, 2, 3, 4, 9, 25, 41, 42, 43, 47, 49, 53, 97, 561, 1105, 1729, 1849, 2047, 2809, 3599, 7919, 65537, 1373653, 25326001,
          104729, 999983, 1000000007, 3215031751, 2152302898747, 999999999989]:
    case('isprime', 'Bool', f"isprime({n})", is_prime_mr(n))
case('isprime', 'List(\\NN)', "filter(k in \\NN |-> isprime(k), range(300))", [k for k in range(300) if is_prime_td(k)])
case('isprime', 'List(\\NN)', "filter(k in \\NN |-> isprime(k), upto(1840, 1870))", [k for k in range(1840, 1871) if is_prime_td(k)])
# nextprime, prevprime
for n in [-5, 0, 1, 2, 3, 13, 89, 113, 1000000]:
    case('nextprime', '\\NN', f"nextprime({n})", next(k for k in range(max(n + 1, 2), 10 ** 7) if is_prime_td(k)))
for n in [-5, 0, 1, 2, 3, 4, 13, 90, 1000000]:
    case('prevprime', '\\NN', f"prevprime({n})", next((k for k in range(n - 1, 1, -1) if is_prime_td(k)), 0))
# primes, primepi, nthprime
for n in [-3, 0, 1, 2, 3, 10, 100, 211]:
    case('primes', 'List(\\NN)', f"primes({n})", [k for k in range(n + 1) if is_prime_td(k)])
for n in [-1, 0, 1, 2, 100, 1000]:
    case('primepi', '\\NN', f"primepi({n})", sum(1 for k in range(n + 1) if is_prime_td(k)))
PR = [k for k in range(2, 4000) if is_prime_td(k)]
for k in [0, 1, 2, 3, 4, 5, 6, 7, 10, 25, 168, 500]:
    case('nthprime', '\\NN', f"nthprime({k})", PR[k - 1] if k else 0)
# factor, primefactors
for n in [0, 1, -1, 2, -12, 360, 1001, 1024, 8633, 2 ** 5 * 3 ** 4 * 47 ** 2, 2809, 53 * 59, 600851475143 // 1471, 9998000099,
          2 * 1000003, 3 ** 13]:
    case('factor', 'List(Pair(\\NN, \\NN))', f"factor({n})", factor_ref(n))
for n in [0, 1, 360, -97, 2 ** 10]:
    case('primefactors', 'List(\\NN)', f"primefactors({n})", [p for p, e in factor_ref(n)])
# divisor functions
for n in [0, 1, -12, 28, 36, 97, 360, 1024]:
    case('divisors', 'List(\\NN)', f"divisors({n})", divisors_ref(n))
    case('numdivisors', '\\NN', f"numdivisors({n})", len(divisors_ref(n)))
    case('totient', '\\NN', f"totient({n})", totient_ref(n))
    case('carmichael', '\\NN', f"carmichael({n})", carmichael_ref(n))
    case('mobius', '\\ZZ', f"mobius({n})", mobius_ref(n))
    case('liouville', '\\ZZ', f"liouville({n})", (-1) ** sum(e for p, e in factor_ref(n)) if n else 0)
    case('omega', '\\NN', f"omega({n})", len(factor_ref(n)))
    case('bigomega', '\\NN', f"bigomega({n})", sum(e for p, e in factor_ref(n)))
    case('radical', '\\NN', f"radical({n})", prod(p for p, e in factor_ref(n)) if n else 0)
    case('issquarefree', 'Bool', f"issquarefree({n})", n != 0 and all(e == 1 for p, e in factor_ref(n)))
for k, n in [(0, 12), (1, 12), (2, 12), (3, 10), (1, 0), (1, 1), (2, -6)]:
    case('sigma', '\\NN', f"sigma({k}, {n})", sum(d ** k for d in divisors_ref(n)))
for n in [0, -6, 1, 6, 12, 28, 496, 8128, 8129]:
    case('isperfect', 'Bool', f"isperfect({n})", n > 0 and sum(divisors_ref(n)) == 2 * n)
for n in [8, 15, 16, 24, 80, 97 * 3, 2 * 3 * 5 * 7]:
    case('carmichael', '\\NN', f"carmichael({n})", carmichael_ref(n))
# quadratic symbols
for a, n in [(2, 7), (3, 7), (5, 11), (0, 7), (14, 7), (-1, 13), (-1, 7), (1001, 9907), (2, 15), (7, 45), (5, 1), (3, 8), (3, 0), (-5, 21)]:
    case('jacobi', '\\ZZ', f"jacobi({a}, {n})", jacobi_ref(a, n))
for a, p in [(2, 7), (3, 7), (6, 13), (-2, 13), (26, 13), (10, 101)]:
    case('legendre', '\\ZZ', f"legendre({a}, {p})", legendre_euler(a % p, p))
for a, n in [(2, 7), (3, 8), (5, 8), (2, 6), (-3, -5), (3, -5), (-1, 0), (1, 0), (2, 0), (0, 1), (0, 2), (6, 9), (-7, 16), (11, 24), (-1, -1)]:
    case('kronecker', '\\ZZ', f"kronecker({a}, {n})", kronecker_ref(a, n))
for a, n in [(2, 7), (3, 7), (-1, 13), (0, 11), (10, 101), (5, 2), (5, 1), (3, 15), (3, 0)]:
    r = pow(a, (n - 1) // 2, n) if n > 0 else 0
    case('eulercriterion', '\\ZZ', f"eulercriterion({a}, {n})", -1 if (n > 2 and r == n - 1) else r)
# sqrtmod
for a, n in [(2, 7), (3, 7), (0, 7), (1, 2), (0, 2), (5, 41), (10, 13), (-1, 13), (-1, 17), (13, 1000003), (3, 1000033), (4, 15), (2, 15),
             (9, 16), (8, 16), (0, 1), (49, 0), (50, 0), (-4, 0), (6, 73), (5, 7681)]:
    case('sqrtmod', '\\ZZ', f"sqrtmod({a}, {n})", sqrtmod_ref(a, n))
# crt
for rs, ms in [([2, 3, 2], [3, 5, 7]), ([1, 2], [4, 6]), ([1, 3], [4, 6]), ([], []), ([5], [0]), ([5, 2], [0, 3]), ([5, 1], [0, 3]),
               ([-1, -1], [5, 7]), ([3], [1]), ([0, 0, 1], [2, 3, 5]), ([7, 7], [0, 0]), ([7, 8], [0, 0]), ([1, 5, 7], [6, 10, 15])]:
    want = crt_ref(rs, ms)
    case('crt', 'Pair(Bool, Pair(\\NN, \\NN))', f"crt({hl(rs) if rs else '[]'}, {hl(ms) if ms else '[]'})", want)
# ordmod, primroot
for a, n in [(2, 7), (3, 7), (2, 9), (10, 21), (6, 9), (1, 1), (5, 1), (2, 1000003), (3, 1024), (1, 0), (-1, 0), (2, 0)]:
    want = order_ref(a, n) if n > 0 else {1: 1, -1: 2}.get(a, 0)
    case('ordmod', '\\NN', f"ordmod({a}, {n})", want)
for n in [0, 1, 2, 3, 4, 5, 7, 8, 9, 12, 18, 25, 41, 50, 54, 1000003]:
    case('primroot', '\\NN', f"primroot({n})", primroot_ref(n) if n < 10 ** 5 else 2)
# dlog
for a, b, n in [(2, 3, 11), (3, 13, 17), (2, 1, 7), (2, 7, 7), (2, 0, 8), (2, 4, 8), (2, 3, 8), (3, 1, 1), (6, 0, 9), (6, 3, 9),
                (5, 3, 10007), (2, 6, 12), (3, 4, 101), (7, 2, 2), (4, 2, 6)]:
    case('dlog', '\\ZZ', f"dlog({a}, {b}, {n})", dlog_ref(a, b, n))
case('dlog', '\\ZZ', "dlog(2, 1024, 0)", 10)
case('dlog', '\\ZZ', "dlog(-2, -8, 0)", 3)
case('dlog', '\\ZZ', "dlog(2, 6, 0)", -1)
case('dlog', '\\ZZ', "dlog(5, 1, 0)", 0)
case('dlog', '\\ZZ', "dlog(-1, -1, 0)", 1)
case('dlog', '\\ZZ', "dlog(0, 0, 0)", 1)
# quadratic residues
for n in [0, 1, 2, 7, 12, 16]:
    case('quadresidues', 'List(\\NN)', f"quadresidues({n})", sorted({x * x % n for x in range(n)}) if n else [])
# continued fractions
for q in [Fr(415, 93), Fr(-415, 93), Fr(0), Fr(7), Fr(-7), Fr(1, 3), Fr(-1, 3), Fr(355, 113), Fr(13, 8)]:
    case('contfrac', 'List(\\ZZ)', f"contfrac({q.numerator} / {q.denominator})", contfrac_ref(q))
for cf in [[4, 2, 6, 7], [1, 1, 1, 1, 1], [0, 3], [-5, 1, 2], [], [3]]:
    case('convergents', 'List(\\QQ)', f"convergents({hl(cf) if cf else '[]'})", convergents_ref(cf))
case('convergents', 'List(\\QQ)', "convergents(contfrac(355 / 113))", convergents_ref(contfrac_ref(Fr(355, 113))))
for n in [0, 1, 2, 3, 7, 13, 16, 19, 46, 61, 94]:
    case('cfsqrt', 'Pair(\\NN, List(\\NN))', f"cfsqrt({n})", cfsqrt_ref(n))
for D in [0, 1, 4, 2, 3, 5, 7, 13, 29]:
    case('pell', 'Pair(\\NN, \\NN)', f"pell({D})", (1, 0) if isqrt(D) ** 2 == D else pell_brute(D))
case('pell', 'Pair(\\NN, \\NN)', "pell(61)", (1766319049, 226153980))
case('pell', 'Pair(\\NN, \\NN)', "pell(109)", (158070671986249, 15140424455100))
# sequences
for n in [0, 1, 2, 10, 50, 100, -1, -2, -9, -10]:
    case('fib', '\\ZZ', f"fib({n})", fib_ref(n))
    case('lucas', '\\ZZ', f"lucas({n})", lucas_ref(n))
case('fib', 'List(\\NN)', "map(k in \\NN |-> fib(k), range(20))", [fib_ref(k) for k in range(20)])
for n in [0, 1, 2, 3, 10, 15]:
    case('catalan', '\\NN', f"catalan({n})", comb(2 * n, n) // (n + 1))
    case('bell', '\\NN', f"bell({n})", bell_ref(n))
for n, k in [(0, 0), (1, 0), (1, 1), (5, 2), (7, 3), (6, 6), (3, 5), (10, 4)]:
    case('stirling1', '\\ZZ', f"stirling1({n}, {k})", stirling1_ref(n, k))
    case('stirling2', '\\NN', f"stirling2({n}, {k})", stirling2_ref(n, k))
for n in [0, 1, 2, 3, 4, 5, 10, 30, 100]:
    case('partitions', '\\NN', f"partitions({n})", partitions_ref(n))
for n in [0, 1, 2, 3, 4, 6, 12, 20]:
    case('bernoulli', '\\QQ', f"bernoulli({n})", bernoulli_ref(n))
for n in [0, 1, 2, 3, 6]:
    case('zetaeven', '\\QQ', f"zetaeven({n})", zetaeven_ref(n))
for n in [0, 1, 2, 10, 30]:
    case('harmonic', '\\QQ', f"harmonic({n})", harmonic_ref(n))
# digits, roots, powers
for n, b in [(0, 10), (12345, 10), (-12345, 10), (255, 2), (255, 16), (7, 1), (7, 0), (10 ** 20, 7)]:
    case('digitsum', '\\NN', f"digitsum({n}, {b})", digitsum_ref(n, b))
for n, k in [(0, 3), (1, 5), (26, 3), (27, 3), (28, 3), (10 ** 12, 2), (10 ** 12 - 1, 2), (2 ** 64, 64), (2 ** 64 - 1, 64), (5, 1), (5, 0), (100, 7)]:
    case('iroot', '\\NN', f"iroot({n}, {k})", iroot_ref(n, k))
for n in [0, 1, -1, 2, 4, 8, -8, -4, 12, 27, -27, 32, 36, 1000000, 3 ** 13, 2 ** 31 - 1, 6 ** 7, -(6 ** 7), -(6 ** 8)]:
    case('ispower', 'Bool', f"ispower({n})", ispower_ref(n))
# Gaussian integers
for z in [(0, 0), (1, 0), (0, -1), (2, 0), (1, 1), (3, 0), (5, 0), (3, 4), (-7, 11), (12, -5), (0, 6), (100, 0), (13, 17), (-1, 1), (98, 21)]:
    u, f = gaussfactor_ref(z)
    case('gaussfactor', 'Pair(\\Z, List(Pair(\\Z, \\NN)))', f"gaussfactor({hz(z)} + 0 * i)", (u, f))
    case('isgaussprime', 'Bool', f"isgaussprime({hz(z)} + 0 * i)", isgaussprime_ref(z))
for n in [-5, 0, 1, 2, 3, 4, 5, 25, 50, 65, 325, 21, 9, 1105, 5525, 3 ** 4 * 5]:
    case('sumtwosquares', 'List(Pair(\\NN, \\NN))', f"sumtwosquares({n})", sumtwosquares_ref(n))
for n in [0, 1, 2, 10, 50]:
    case('gaussprimes', 'List(\\Z)', f"gaussprimes({n})", gaussprimes_ref(n))

# more
case('islucasprp', 'List(\\NN)', "filter(k in \\NN |-> islucasprp(k), range(150))", [k for k in range(150) if slprp_ref(k)])
for n in [-7, 5777, 10877, 16109, 18971, 5459, 5777 + 2, 999983 * 1000003, 1000003]:
    case('islucasprp', 'Bool', f"islucasprp({n})", slprp_ref(n) if n < 10 ** 5 else is_prime_mr(n))
for xs in [[12, 18, -30], [], [0, 0], [7], [-4], [0, 9], [2 ** 20, 6 ** 9]]:
    case('gcdlist', '\\NN', f"gcdlist({hl(xs) if xs else '[]'})", reduce(gcd, xs, 0))
for xs in [[(3, 1), (2, 4)], [(5, 0), (2, 1)], [(0, 0), (0, 6)], [(4, 2), (6, 0), (2, 2)]]:
    case('gcdlist', '\\Z', "gcdlist([" + ', '.join(hz(z) + ' + 0 * i' for z in xs) + "])", reduce(ggcd_ref, xs, (0, 0)))
for xs in [[4, 6, 10], [], [3, 0], [-4, 6], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [97]]:
    case('lcmlist', '\\NN', f"lcmlist({hl(xs) if xs else '[]'})", reduce(lcm2, xs, 1))
for n in [-4, 0, 1, 2, 49, 50, 10 ** 12, 10 ** 12 + 1]:
    case('issquare', 'Bool', f"issquare({n})", n >= 0 and isqrt(n) ** 2 == n)
for n in [0, 1, 2, 8, 12, 49, 97, 3 ** 13, -8, 1024, 36, 2 * 1000003]:
    case('isprimepower', 'Bool', f"isprimepower({n})", n > 0 and len(factor_ref(n)) == 1)
for a, b in [(12, 35), (12, 18), (0, 1), (0, 0), (-1, 0), (-15, 28)]:
    case('iscoprime', 'Bool', f"iscoprime({a}, {b})", gcd(a, b) == 1)
for a, b in [((2, 1), (2, -1)), ((1, 1), (2, 0)), ((3, 0), (2, 1)), ((0, 0), (0, 1)), ((5, 0), (1, 2))]:
    case('iscoprime', 'Bool', f"iscoprime({hz(a)} + 0 * i, {hz(b)} + 0 * i)", ggcd_ref(a, b) == (1, 0))
for n in [0, 1, 2, 12, 30]:
    case('totatives', 'List(\\NN)', f"totatives({n})", [k for k in range(1, n + 1) if gcd(k, n) == 1])
for n in [0, 1, 2, 4, 7, 8, 9, 18, 25, 41]:
    case('primitiveroots', 'List(\\NN)', f"primitiveroots({n})",
         [g for g in range(1, n) if gcd(g, n) == 1 and order_ref(g, n) == totient_ref(n)] if n > 1 else [])
for q, n in [(0, 5), (1, 7), (12, 0), (12, 4), (12, 6), (30, 10), (7, -3), (10, 25), (9, 3), (8, 8)]:
    case('ramanujansum', '\\ZZ', f"ramanujansum({q}, {n})", ramanujansum_ref(q, n))
case('wilson', 'List(\\NN)', "filter(k in \\NN |-> wilson(k), range(40))", [k for k in range(40) if is_prime_td(k)])
for n in [-7, 97, 91, 221]:
    case('wilson', 'Bool', f"wilson({n})", is_prime_td(n))
GP = gaussprimes_ref(400)
for z in [(0, 0), (1, 1), (2, 1), (1, 2), (3, 0), (5, 0), (-3, 4), (0, -7), (1, 0), (-1, -1), (6, 5)]:
    case('nextgaussprime', '\\Z', f"nextgaussprime({hz(z)} + 0 * i)", next(p for p in GP if (gnorm(p), p[1]) > (gnorm(z), z[1])))
for z in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, 2), (2, 0), (-4, 0), (4, 0), (3, 4), (-3, 4), (1, 1), (8, 0), (0, 8), (2, 11), (5, 0), (6, 0), (16, 0), (-16, 0), (0, -27), (7, 24)]:
    case('isgausspower', 'Bool', f"isgausspower({hz(z)} + 0 * i)", isgausspower_ref(z))

# ---------------------------------------------------------------------------------------------------------------------------------
def parse_cls(s):
    s = s.strip()
    for k in ('List(', 'Pair('):
        if s.startswith(k):
            inner, depth, parts, cur = s[len(k):-1], 0, [], ''
            for ch in inner:
                if ch == ',' and depth == 0: parts.append(cur); cur = ''; continue
                depth += (ch == '(') - (ch == ')'); cur += ch
            parts.append(cur)
            return (k[:-1], [parse_cls(p) for p in parts])
    return s

def main():
    words = sys.argv[1:]
    groups = [g for g in G if not words or any(w in g for w in words)]
    cases = [(g, k, c) for g in groups for k, c in enumerate(G[g])]
    names = {}
    lines = []
    for n, (g, k, (cls, expr, want)) in enumerate(cases):
        names[(g, k)] = f"c{n}"; lines.append(f"c{n} in {cls} := {expr}")
    SRC = '\n'.join(lines) + '\n'
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'numtheory.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("every statement of the number theory test program passes the class checker", not errs, str(errs[:3]) if errs else '')
    if errs: return rep.done()
    P.build(); E = Env(P)
    def norm(x): return int(x) if x.denominator == 1 else x
    def dec(v, c):
        if isinstance(c, tuple):
            if c[0] == 'List': return [dec(x, c[1][0]) for x in E.lst(v)]
            a, b = to_pair(v); return (dec(a, c[1][0]), dec(b, c[1][1]))
        if c == 'Bool': return E.b(v)
        q = E.dq(v)
        if c in ('\\Z', '\\Q'): return (norm(q.r), norm(q.i))
        return norm(q.r) if q.i == 0 else ('non-real', q.r, q.i)
    slow = []
    for g in groups:
        ok, bad, t0 = True, [], time.time()
        for k, (cls, expr, want) in enumerate(G[g]):
            t = time.time()
            try: got = dec(E.V(P.hum.spec_name(names[(g, k)])), parse_cls(cls))
            except Exception as e: got = f"error {type(e).__name__}: {e}"
            good = want(got) if callable(want) else got == want
            if not good: ok = False; bad.append(f"{expr} = {got}" + ('' if callable(want) else f", expected {want}"))
            if time.time() - t > 5: slow.append(f"{expr}: {time.time() - t:.1f}s")
        rep(f"{g}: {len(G[g])} cases ({time.time() - t0:.1f}s)", ok, ('\n      ' + '\n      '.join(bad[:6])) if bad else '')
    if slow: print("slow cases:\n  " + '\n  '.join(slow))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
