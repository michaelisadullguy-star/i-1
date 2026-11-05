"""test_stats.py -- lib/stats.imo (libsrc/stats.hum.imo): exact statistics on lists of rationals against Python's fractions and statistics modules.
python3 tests/test_stats.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import math, random, statistics, sys
from fractions import Fraction as F
from langtest import *

R = random.Random(20261107)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('statistics')
add = S.add
LQ = ('L', 'Q')

def rl(nmax=9, den=4, lo=-12, hi=12): return [F(R.randint(lo, hi), R.randint(1, den)) for _ in range(R.randint(0, nmax))]
def mean(xs): return sum(xs, F(0)) / len(xs) if xs else F(0)
def pvar(xs): m = mean(xs); return sum(((x - m) ** 2 for x in xs), F(0)) / len(xs) if xs else F(0)
def svar(xs): m = mean(xs); return sum(((x - m) ** 2 for x in xs), F(0)) / (len(xs) - 1) if len(xs) > 1 else F(0)
def quantile(p, xs):
    if not xs: return F(0)
    s = sorted(xs); h = (len(s) - 1) * p; lo = math.floor(h); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (h - lo) * (s[hi] - s[lo])
def cov(xs, ys):
    k = min(len(xs), len(ys))
    if k == 0: return F(0)
    xs, ys = xs[:k], ys[:k]
    return sum((x * y for x, y in zip(xs, ys)), F(0)) / k - mean(xs) * mean(ys)

for t in range(n(40)):
    xs, ys = rl(), rl(); k = R.randint(0, 5); p = F(R.randint(0, 8), 8); ws = [F(R.randint(0, 5)) for _ in xs]
    add(f'total {xs}', f'total({lit(xs, LQ)})', 'Q', sum(xs, F(0)))
    add(f'average {xs}', f'average({lit(xs, LQ)})', 'Q', mean(xs))
    add(f'spread {xs}', f'spread({lit(xs, LQ)})', 'Q', (max(xs) - min(xs)) if xs else F(0))
    add(f'median {xs}', f'median({lit(xs, LQ)})', 'Q', F(statistics.median(xs)) if xs else F(0))
    cnt = {}
    for x in xs: cnt[x] = cnt.get(x, 0) + 1
    top = max(cnt.values()) if cnt else 0
    add(f'modes {xs}', f'modes({lit(xs, LQ)})', LQ, sorted(x for x, c in cnt.items() if c == top))
    add(f'variance {xs}', f'variance({lit(xs, LQ)})', 'Q', pvar(xs))
    add(f'svariance {xs}', f'svariance({lit(xs, LQ)})', 'Q', svar(xs))
    add(f'quantile {p} {xs}', f'quantile({lit(p, "Q")}, {lit(xs, LQ)})', 'Q', quantile(p, xs))
    add(f'iqr {xs}', f'iqr({lit(xs, LQ)})', 'Q', quantile(F(3, 4), xs) - quantile(F(1, 4), xs))
    add(f'covariance {xs} {ys}', f'covariance({lit(xs, LQ)}, {lit(ys, LQ)})', 'Q', cov(xs, ys))
    kk = min(len(xs), len(ys)); vx, vy = pvar(xs[:kk]), pvar(ys[:kk])
    # correlation2 and linreg use the variances of the whole lists (as the library does): compare with the same definitions
    vxf, vyf = pvar(xs), pvar(ys)
    add(f'correlation2 {xs} {ys}', f'correlation2({lit(xs, LQ)}, {lit(ys, LQ)})', 'Q', F(0) if vxf == 0 or vyf == 0 else cov(xs, ys) ** 2 / (vxf * vyf))
    if vxf == 0: lr = (F(0), mean(ys))
    else: slope = cov(xs, ys) / vxf; lr = (slope, mean(ys) - slope * mean(xs))
    add(f'linreg {xs} {ys}', f'linreg({lit(xs, LQ)}, {lit(ys, LQ)})', ('P', 'Q', 'Q'), lr)
    acc, cs = F(0), []
    for x in xs: acc += x; cs.append(acc)
    add(f'cumsum {xs}', f'cumsum({lit(xs, LQ)})', LQ, cs)
    add(f'movingavg {k} {xs}', f'movingavg({k}, {lit(xs, LQ)})', LQ, [] if k == 0 else [sum(xs[i:i + k], F(0)) / k for i in range(len(xs) - k + 1)])
    ws2 = ws[:len(xs)]
    sw = sum(ws, F(0))
    add(f'weightedmean {ws} {xs}', f'weightedmean({lit(ws, LQ)}, {lit(xs, LQ)})', 'Q', F(0) if sw == 0 else sum((w * x for w, x in zip(ws, xs)), F(0)) / sw)
    add(f'ranks {xs}', f'ranks({lit(xs, LQ)})', LQ, [F(sum(1 for y in xs if y < x)) + F(sum(1 for y in xs if y == x) + 1, 2) for x in xs])

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
