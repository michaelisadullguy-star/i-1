"""Reference arithmetic for base b = i-1 with digits {0,1}.  Gaussian integers as (re, im) int pairs."""
import itertools, random

def gmul(a, b): return (a[0]*b[0] - a[1]*b[1], a[0]*b[1] + a[1]*b[0])
def gadd(a, b): return (a[0]+b[0], a[1]+b[1])
B = (-1, 1)

def val(digs):                     # digs LSB first
    s = (0, 0); p = (1, 0)
    for d in digs:
        if d: s = gadd(s, p)
        p = gmul(p, B)
    return s

def to_digits(z):                  # Penney: canonical LSB-first digit list of a Gaussian integer
    x, y = z; out = []
    for _ in range(10**6):
        if (x, y) == (0, 0): return out
        d = (x + y) & 1
        out.append(d); x -= d
        x, y = (-x + y)//2, (-x - y)//2
    raise RuntimeError

def numeral(digs):                 # MSB-first text
    return ''.join(str(d) for d in reversed(digs)) or '0'

def trim(digs):
    digs = list(digs)
    while digs and digs[-1] == 0: digs.pop()
    return digs

# ---- carry set: carries are canonical numerals; transition  c'' = tail(c) + m*110  (110 = b + b^2 = -1-i)
KAPPA = (-1, -1)
assert val([0, 1, 1]) == KAPPA
carries = {(0, 0)}; frontier = [(0, 0)]
while frontier:
    c = frontier.pop()
    cd = to_digits(c)
    t = cd[1:]
    for nxt in (val(t), gadd(val(t), KAPPA)):
        if nxt not in carries:
            carries.add(nxt); frontier.append(nxt)
C = sorted(carries)
tails = {}
for c in C:
    t = tuple(to_digits(c)[1:])
    tails[t] = to_digits(gadd(val(t), KAPPA))      # tail + 110
TABLE = [(list(t), v) for t, v in tails.items()]

def eqlist(a, b): return trim(a) == trim(b)
def lookup(t):
    for k, v in TABLE:
        if eqlist(k, t): return v
    raise KeyError(t)

def add_digits(p, q):
    """serial adder, carry is a numeral (digit list); mirrors the language definition"""
    out = []; c = []; p = list(p); q = list(q)
    steps = 0
    while p or q or c:
        x = p.pop(0) if p else 0
        y = q.pop(0) if q else 0
        d = c[0] if c else 0
        t = c[1:]
        out.append(x ^ y ^ d)
        m = 1 if x + y + d >= 2 else 0
        c = lookup(t) if m else t
        steps += 1
        assert steps < 10**5
    return out

def mul_digits(p, q):
    r = []
    for k, d in enumerate(q):
        if d:
            r = add_digits(r, [0]*k + list(p))
    return r

if __name__ == '__main__':
    print("carry numerals (MSB first):", [numeral(to_digits(c)) for c in C], len(C))
    print("table  tail -> tail+110   :", [(numeral(k), numeral(v)) for k, v in TABLE])
    # exhaustive: all digit strings of length <= 8 (pairs)
    bad = 0; n = 0
    for L1 in range(0, 9):
        for L2 in range(0, 9):
            for a in itertools.product((0, 1), repeat=L1):
                for b in itertools.product((0, 1), repeat=L2):
                    n += 1
                    if val(add_digits(a, b)) != gadd(val(a), val(b)): bad += 1
    print("exhaustive add up to 8 digits:", n, "pairs, mismatches:", bad)
    random.seed(3)
    bad = 0
    for _ in range(20000):
        a = [random.randint(0, 1) for _ in range(random.randint(0, 70))]
        b = [random.randint(0, 1) for _ in range(random.randint(0, 70))]
        bad += val(add_digits(a, b)) != gadd(val(a), val(b))
        c = [random.randint(0, 1) for _ in range(random.randint(0, 14))]
        d = [random.randint(0, 1) for _ in range(random.randint(0, 14))]
        bad += val(mul_digits(c, d)) != gmul(val(c), val(d))
    print("random add (<=70 digits) / mul (<=14 digits), mismatches:", bad)
