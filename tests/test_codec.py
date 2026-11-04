"""test_codec.py -- types as decoding keys (lib/codec.imo), from the HUMAN notation.  The same binary string is decoded by different keys:
110101 is 1 - 6i in Z[i], the pair (1, -6) in Z^2, the fraction -1/6; a pair of strings is one Gaussian integer a + b·i whose parts are the codes of the
strings.  Every statement goes through doc 2 and the class checker, is evaluated in the language, decoded and compared with an independent python
computation (base i-1 by the python twin base_b, the bijective numeration over the 1114112 code points by integer arithmetic).
python3 tests/test_codec.py"""
import os, sys, random
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()
rng = random.Random(20261028)
B = 1114112

# ------------------------------------------------------------------------------------------------ python references
def bits_of(z):                       # most significant digit first, "0" for 0
    d = to_digits(z)
    return ''.join('1' if x else '0' for x in reversed(d)) if d else '0'
def strnat_ref(s):
    n = 0
    for c in s: n = n * B + ord(c) + 1
    return n
def natstr_ref(n):
    out = []
    while n:
        n -= 1; out.append(chr(n % B)); n //= B
    return ''.join(reversed(out))
def hq(x):
    x = Fr(x); t = str(x.numerator) + (f"/{x.denominator}" if x.denominator != 1 else "")
    return f"({t})" if x < 0 else t
def hs(s): return '"' + s + '"'

SAMPLE_Z = [(rng.randint(-50, 50), rng.randint(-50, 50)) for _ in range(12)] + [(0, 0), (1, 0), (0, 1), (1, -6), (-7, 3)]
SAMPLE_PAIRS = [(rng.randint(-30, 30), rng.randint(-30, 30)) for _ in range(6)]
STRS = ["", "a", "Hi", "yo", "A\0B", "ab\u00e9", "\U0001F600!", "i - 1"]
USER1, USER2 = "Hello, world!", "Welcome to i - 1!"

SRC = '''
a1 in String := decode(parsebits("110101"))
a2 in String := decode((parsebits("110101") in Z2))
a3 in \\QQ := fracz((parsebits("110101") in Z2))
a4 in String := decode(5)
a5 in String := decode((5 in Z2))
a6 in String := decode(1/2 + i/3)
a7 in String := bits(parsebits("110101"))
a8 in \\Z := parsebits("110101")
a9 in String := decode((parsebits("110101") in String2))
'''
for k, (a, b) in enumerate(SAMPLE_Z):
    z = (a, b)
    SRC += f'''
z{k} in \\Z := parsebits("{bits_of(z)}")
y{k} in String := bits(pairz({a}, {b}) + 0)
w{k} in Z2 := pairz({hq(a)}, {hq(b)})
f{k} in \\ZZ := fstz(w{k})
g{k} in \\ZZ := sndz(w{k})
t{k} in String := decode(w{k})
'''.replace("pairz(%s, %s) + 0" % (a, b), "gaussian(pairz(%s, %s))" % (hq(a), hq(b)))
for k, (a, b) in enumerate(SAMPLE_PAIRS):
    c, d = (a * 3 % 17) - 8, (b * 5 % 13) - 6
    SRC += f'''
p{k} in Z2 := pairz({hq(a)}, {hq(b)}) + pairz({hq(c)}, {hq(d)})
q{k} in Z2 := pairz({hq(a)}, {hq(b)}) - pairz({hq(c)}, {hq(d)})
r{k} in Z2 := -pairz({hq(a)}, {hq(b)})
s{k} in Z2 := {hq(c)} * pairz({hq(a)}, {hq(b)})
e{k} in Bool := pairz({hq(a)}, {hq(b)}) == pairz({hq(c)}, {hq(d)})
e{k}x in Bool := pairz({hq(a)}, {hq(b)}) == pairz({hq(a)}, {hq(b)})
'''
FR = [Fr(-1, 6), Fr(3, 4), Fr(5), Fr(0), Fr(-7, 3), Fr(1, 2)]
for k, x in enumerate(FR):
    SRC += f'''
qp{k} in Z2 := qpair(({hq(x)} in \\QQ))
qf{k} in \\QQ := fracz(qp{k})
qd{k} in String := decode(qp{k})
'''
SRC += '\nzf in \\QQ := fracz(pairz(3, 0))\nzg in \\QQ := fracz(pairz(0, 5))\n'
for k, s in enumerate(STRS):
    lit = hs(s) if all(ord(c) >= 32 and c not in '"\\' for c in s) else None
    if lit is None: continue
    SRC += f'''
n{k} in \\NN := strnat({lit})
m{k} in String := natstr(strnat({lit}))
'''
SRC += '''
nz1 in String := natstr(0)
nz2 in String := natstr(1)
nz3 in \\NN := strnat("")
nz4 in String := natstr(2)
c1 in String2 := strpair("Hi", "yo")
c2 in String := strfst(c1)
c3 in String := strsnd(c1)
c4 in String := decode(c1)
c5 in String := bits(gaussian(c1))
c6 in String2 := strpair("", "a")
c7 in String := decode(c6)
c8 in String := decode((parsebits("1100") in String2))
c9 in String := decode((parsebits("11101") in String2))
'''
SRC += f'''
u1 in String2 := strpair({hs(USER1)}, {hs(USER2)})
u2 in String := bits(gaussian(u1))
u3 in String := strfst(u1)
u4 in String := strsnd(u1)
u5 in String := decode(u1)
'''

BAD = {
 'a string pair is not an integer pair': 'x in Z2 := strpair("a", "b")\n',
 'a pair of integers is not a string pair': 'x in String2 := pairz(1, 2)\n',
 'fstz of a string pair': 'x in \\ZZ := fstz(strpair("a", "b"))\n',
 'strfst of a plain string': 'x in String := strfst("abc")\n',
}

def main():
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(SRC, 'codec.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("the test program passes the class checker", not errs, str(errs[:2]))
    if errs: return rep.done()
    P.build(); E = Env(P)
    V = lambda n: E.V(P.hum.spec_name(n))
    def tx(n): return ''.join(chr(int(E.dq(c).r)) for c in E.lst(V(n)))
    def q(n): return E.dq(V(n))
    # ---- the user's example: one binary string, three keys
    rep("110101 decoded as Z[i] is 1 - 6i; as Z^2 the pair (1, -6); as a fraction -1/6; as String^2 the pair of the strings coded by 1 and 6 (the same digits, four decoding keys)",
        tx('a1') == "1 - 6*i" and tx('a2') == "(1, -6)" and q('a3').r == Fr(-1, 6) and q('a3').i == 0
        and tx('a9') == '("%s", "%s")' % (natstr_ref(1), natstr_ref(6)), f"{tx('a1')!r} {tx('a2')!r} {q('a3').r}")
    rep("parsebits and bits: the digits 110101 give the Gaussian integer 1 - 6i and back; an unascribed number decodes by the default key, 5 as a pair is (5, 0), a fraction decodes as itself",
        q('a8').r == 1 and q('a8').i == -6 and tx('a7') == "110101" and tx('a4') == "5" and tx('a5') == "(5, 0)" and tx('a6') == "1/2 + 1/3*i", tx('a6'))
    bad = []
    for k, (a, b) in enumerate(SAMPLE_Z):
        z = q(f'z{k}')
        if (z.r, z.i) != (a, b): bad.append(('parsebits', k, z))
        if tx(f'y{k}') != bits_of((a, b)): bad.append(('bits', k, tx(f'y{k}'), bits_of((a, b))))
        if q(f'f{k}').r != a or q(f'g{k}').r != b: bad.append(('fstz/sndz', k))
        if tx(f't{k}') != f"({a}, {b})": bad.append(('decode', k, tx(f't{k}')))
    rep(f"{len(SAMPLE_Z)} Gaussian integers: parsebits against the python base-(i-1) twin, bits, pairz / fstz / sndz (a + b·i is the pair (a, b)), decode in the key Z^2", not bad, str(bad[:3]))
    bad = []
    for k, (a, b) in enumerate(SAMPLE_PAIRS):
        c, d = (a * 3 % 17) - 8, (b * 5 % 13) - 6
        want = {'p': (a + c, b + d), 'q': (a - c, b - d), 'r': (-a, -b), 's': (c * a, c * b)}
        for key, w in want.items():
            z = q(f'{key}{k}')
            if (z.r, z.i) != w: bad.append((key, k, (z.r, z.i), w))
        if E.b(V(f'e{k}')) != ((a, b) == (c, d)) or not E.b(V(f'e{k}x')): bad.append(('eq', k))
    rep("the operations on pairs are those of the Gaussian integers: (a, b) + (c, d), (a, b) - (c, d), -(a, b), k·(a, b), == — through the human + - * ==", not bad, str(bad[:3]))
    bad = []
    for k, x in enumerate(FR):
        pr = q(f'qp{k}'); x = Fr(x)
        if (pr.r, pr.i) != (x.numerator, x.denominator): bad.append(('qpair', k, (pr.r, pr.i)))
        if q(f'qf{k}').r != x or q(f'qf{k}').i != 0: bad.append(('fracz', k))
    rep("qpair writes p/q as the pair (p, q) in lowest terms, fracz reads a pair (a, b) as a/b: fracz(qpair x) = x for 6 fractions; fracz of (a, 0) is 0 (total division)",
        not bad and q('zf').r == 0 and q('zg').r == 0, str(bad[:3]))
    bad = []
    for k, s in enumerate(STRS):
        if all(ord(c) >= 32 and c not in '"\\' for c in s):
            if int(q(f'n{k}').r) != strnat_ref(s): bad.append(('strnat', s, q(f'n{k}').r, strnat_ref(s)))
            if tx(f'm{k}') != s: bad.append(('natstr', s, tx(f'm{k}')))
    rep(f"strnat is the bijective numeration over the 1114112 code points (python integer arithmetic) and natstr inverts it, for {len(STRS)} strings with accents and a non-BMP character", not bad, str(bad[:3]))
    rep("natstr 0 is the empty string, natstr 1 is the string of the code point 0, natstr 2 that of the code point 1, strnat of the empty string is 0",
        tx('nz1') == "" and tx('nz2') == "\0" and int(q('nz3').r) == 0 and tx('nz4') == "\x01" and natstr_ref(1) == "\0" and strnat_ref("\x01") == 2)
    z = q('c1')
    ok = (int(z.r), int(z.i)) == (strnat_ref("Hi"), strnat_ref("yo")) and tx('c2') == "Hi" and tx('c3') == "yo" and tx('c4') == '("Hi", "yo")'
    ok = ok and tx('c5') == bits_of((strnat_ref("Hi"), strnat_ref("yo"))) and tx('c7') == '("", "a")'
    ok = ok and tx('c8') == '("%s", "")' % natstr_ref(2) and tx('c9') == '("%s", "")' % natstr_ref(1)
    rep("strpair(\"Hi\", \"yo\") is the Gaussian integer strnat(Hi) + strnat(yo)·i; strfst, strsnd, decode and bits read it; (\"\", \"a\") is purely imaginary; the numbers 2 and -1 decode as String^2 by |real| and |imaginary| part", ok, tx('c4'))
    a, b = strnat_ref(USER1), strnat_ref(USER2)
    t0 = tx('u2')
    rep(f"the example pair (\"{USER1}\", \"{USER2}\") is ONE binary string of {len(t0)} digits — the Gaussian integer {len(str(a))}-digit + {len(str(b))}-digit·i, equal to the python base-(i-1) expansion — and String^2 decodes it back",
        t0 == bits_of((a, b)) and tx('u3') == USER1 and tx('u4') == USER2 and tx('u5') == f'("{USER1}", "{USER2}")', f"{t0[:40]}...")
    # ---- the keys are not interchangeable without gaussian
    bad = []
    for name, text in BAD.items():
        Q = imo.Program()
        for f in imo.PRELUDE: Q.add_file(f, trusted=True)
        Q.add_text(text, 'bad.hum.imo', notation='hum')
        if not Q.check(collect=True): bad.append(name)
    rep("the class checker keeps the keys apart: a String^2 is not a Z^2, a Z^2 is not a String^2, fstz does not read a string pair (gaussian changes the key), strfst does not read a plain string", not bad, str(bad))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
