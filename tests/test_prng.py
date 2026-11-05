"""test_prng.py -- lib/prng.imo (libsrc/prng.hum.imo): generators, shuffles, radical inverses and hashes against models written here in Python (big integers, Fractions).
Known answers: the first xorshift64 output from the seed 1, the FNV-1a hashes of a, the first minstd output from the seed 1.
python3 tests/test_prng.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import random, sys
from fractions import Fraction as F
from langtest import *

R = random.Random(20261111)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('pseudo-random numbers')
add = S.add
LN = ('L', 'N'); LS = ('L', 'S')
M32, M64 = 2 ** 32, 2 ** 64
def minstd(s): return 48271 * s % 2147483647
def lcgansi(s): return (1103515245 * s + 12345) % 2 ** 31
def lcgmmix(s): return (6364136223846793005 * s + 1442695040888963407) % M64
def xs32(s):
    s %= M32; s ^= (s << 13) % M32; s ^= s >> 17; s ^= (s << 5) % M32; return s
def xs64(s):
    s %= M64; s ^= (s << 13) % M64; s ^= s >> 7; s ^= (s << 17) % M64; return s
GENS = [('minstd', minstd, 31), ('lcgansi', lcgansi, 31), ('lcgmmix', lcgmmix, 64), ('xorshift32', xs32, 32), ('xorshift64', xs64, 64)]
def stream(f, s, k):
    out = []
    for _ in range(k): s = f(s); out.append(s)
    return out
def shuffle(f, s, xs):
    xs = list(xs); t = f(s); out = []
    while xs:
        out.append(xs.pop(t % len(xs))); t = f(t)
    return out
assert xs64(1) == 1082269761 and minstd(1) == 48271

for name, f, bits in GENS:
    for t in range(n(6)):
        s = R.randint(1, 2 ** bits - 1); k = R.randint(0, 3 if bits == 64 else 4)
        add(f'prngstream {name} {s} {k}', f'prngstream({name}, {s}, {k})', LN, stream(f, s, k))
    add(f'{name} of 1', f'{name}(1)', 'N', f(1))
add('xorshift64 known answer', 'xorshift64(1)', 'N', 1082269761)
add('minstd known answer', 'minstd(1)', 'N', 48271)
for t in range(n(10)):
    s = R.randint(1, 2 ** 31 - 2); b = R.randint(1, 50); k = R.randint(0, 6)
    add(f'prngbelow minstd {s} {b} {k}', f'prngbelow(minstd, {s}, {b}, {k})', LN, [x % b for x in stream(minstd, s, k)])
    s32 = R.randint(1, 2 ** 32 - 1)
    add(f'prngbelow xorshift32 {s32} {b} {k}', f'prngbelow(xorshift32, {s32}, {b}, {k})', LN, [x % b for x in stream(xs32, s32, k)])
for t in range(n(12)):
    s = R.randint(1, 2 ** 31 - 2); xs = [R.randint(0, 99) for _ in range(R.randint(0, 7))]; w = [R.choice('abcdef') + str(i) for i in range(R.randint(0, 6))]
    add(f'shuffle {s} {xs}', f'shuffle(minstd, {s}, {lit(xs, LN)})', LN, shuffle(minstd, s, xs))
    add(f'shuffle strings {s} {w}', f'shuffle(minstd, {s}, {lit(w, LS)})', LS, shuffle(minstd, s, w))
    k = R.randint(0, len(xs))
    add(f'sample {s} {k} {xs}', f'sample(minstd, {s}, {k}, {lit(xs, LN)})', LN, shuffle(minstd, s, xs)[:k])
    add(f'choice {s} {xs}', f'choice(minstd, {s}, {lit(xs, LN)})', LN, [xs[minstd(s) % len(xs)]] if xs else [])

def vdc(b, k):
    x, f = F(0), F(1, b)
    if b < 2: return F(0)
    while k: x += (k % b) * f; k //= b; f /= b
    return x
for t in range(n(25)):
    b = R.randint(2, 9); k = R.randint(0, 3000)
    add(f'vandercorput {b} {k}', f'vandercorput({b}, {k})', 'Q', vdc(b, k))
for k in range(0, 9):
    add(f'vandercorput 2 {k}', f'vandercorput(2, {k})', 'Q', vdc(2, k))
    add(f'halton {k}', f'halton({k})', ('P', 'Q', 'Q'), (vdc(2, k), vdc(3, k)))
add('vandercorput base 1 is 0', 'vandercorput(1, 5)', 'Q', F(0))

def fnv32(bs):
    h = 2166136261
    for b in bs: h ^= b; h = h * 16777619 % M32
    return h
def fnv64(bs):
    h = 14695981039346656037
    for b in bs: h ^= b; h = h * 1099511628211 % M64
    return h
def djb(bs):
    h = 5381
    for b in bs: h = (h * 33 + b) % M32
    return h
assert fnv32(b'a') == 0xE40C292C and fnv64(b'a') == 0xAF63DC4C8601EC8C and fnv32(b'') == 2166136261
for t in range(n(14)):
    bs = [R.randint(0, 255) for _ in range(R.randint(0, 10))]
    add(f'fnvhash32 {bs}', f'fnvhash32({lit(bs, LN)})', 'N', fnv32(bs))
    add(f'fnvhash64 {bs}', f'fnvhash64({lit(bs, LN)})', 'N', fnv64(bs))
    add(f'djbhash {bs}', f'djbhash({lit(bs, LN)})', 'N', djb(bs))
add('fnvhash32 of a', 'fnvhash32([97])', 'N', 0xE40C292C)
add('fnvhash64 of a', 'fnvhash64([97])', 'N', 0xAF63DC4C8601EC8C)
add('fnvhash32 of nothing', 'fnvhash32([])', 'N', 2166136261)
add('djbhash of nothing', 'djbhash([])', 'N', 5381)

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
