"""numeral.py -- write numbers as spec-notation numerals (base i − 1), for people writing prelude code by hand.

  python3 pymo/numeral.py 7 -3 2+3i -i 1/2 -5/4+1/3i 0.75
      7        111011101
      -3       10001
      2+3i     1011
      ...
      1/2      (÷ 1 1100)            a fraction is written as a division of two numerals

Accepted forms: integers, Gaussian integers a+bi / a-bi / bi / i / -i, fractions p/q of those, decimals.  Remember that in spec
and bin a bare digit string is ALWAYS read in base i − 1: `10` is −1 + i, `1100` is 2, `11` is i.  (In the human notation
numerals are decimal.)

  python3 pymo/numeral.py --read 1100 11101 0.1     the other direction: the value of numerals"""
import os, sys, re
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_b import numeral, to_digits, val, gmul

def gauss(text):
    """'2+3i' -> (Fraction 2, Fraction 3)"""
    t = text.replace(' ', '').replace('−', '-')
    if t in ('i', '+i'): return Fraction(0), Fraction(1)
    if t == '-i': return Fraction(0), Fraction(-1)
    m = re.fullmatch(r'([+-]?[\d./]+)?(?:([+-])([\d./]*)i)?', t)
    if m and (m.group(1) or m.group(2)):
        re_ = Fraction(m.group(1)) if m.group(1) else Fraction(0)
        im_ = Fraction(0)
        if m.group(2):
            im_ = Fraction(m.group(3)) if m.group(3) else Fraction(1)
            if m.group(2) == '-': im_ = -im_
        return re_, im_
    m = re.fullmatch(r'([+-]?[\d./]*)i', t)
    if m: return Fraction(0), Fraction(m.group(1) or 1)
    raise SystemExit(f"cannot read {text!r}")

def spec(re_, im_):
    from math import lcm
    d = lcm(re_.denominator, im_.denominator)
    z = (int(re_ * d), int(im_ * d))
    n = numeral(to_digits(z))
    return n if d == 1 else f"(÷ {n} {numeral(to_digits((d, 0)))})"

def read(text):
    if '.' in text: a, b = text.split('.'); bits, k = a + b, len(b)
    else: bits, k = text, 0
    z = val([int(c) for c in reversed(bits)])
    den = (1, 0)
    for _ in range(k): den = gmul(den, (-1, 1))
    n = den[0] ** 2 + den[1] ** 2
    re_ = Fraction(z[0] * den[0] + z[1] * den[1], n); im_ = Fraction(z[1] * den[0] - z[0] * den[1], n)
    return f"{re_}" + (f" {'+' if im_ > 0 else '-'} {abs(im_)}i" if im_ else '')

def main(argv):
    if not argv: print(__doc__); return
    if argv[0] == '--read':
        for a in argv[1:]: print(f"{a:<24} {read(a)}")
        return
    for a in argv: print(f"{a:<12} {spec(*gauss(a))}")

if __name__ == '__main__':
    main(sys.argv[1:])
