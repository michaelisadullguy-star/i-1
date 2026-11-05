"""test_regex.py -- lib/regex.imo (libsrc/regex.hum.imo): regular expressions by derivatives against Python's re module.  A full match is the same in every implementation, so rxfull is compared with
re.fullmatch; the longest-match functions (rxprefix, rxsearch, rxfindall, rxreplace, rxsplit) are compared with definitions by brute force on top of re.fullmatch (leftmost, then longest).
python3 tests/test_regex.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import random, re, sys
from langtest import *

R = random.Random(20261109)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('regular expressions')
add = S.add
ATOMS = ['a', 'b', 'c', '.', '[ab]', '[^a]', '[a-c]', '[^a-b]', '\\d', '\\w', '\\W', '\\s', '\\D', '[\\d_]', '[a\\-c]', '\\.', '1']
def gen(d):
    if d == 0 or R.random() < 0.25: return R.choice(ATOMS)
    k = R.random()
    if k < 0.3: return gen(d - 1) + gen(d - 1)
    if k < 0.5: return '(' + gen(d - 1) + '|' + gen(d - 1) + ')'
    if k < 0.8: return '(' + gen(d - 1) + ')' + R.choice('*+?')
    if k < 0.9: return R.choice(ATOMS) + R.choice('*+?')
    return '(' + gen(d - 1) + ')'
def rtext(): return ''.join(R.choice('abc1 _.\n') for _ in range(R.randint(0, 7)))
def fm(p, s): return re.fullmatch(p, s) is not None
def longest(p, s, i):
    best = None
    for k in range(len(s) - i + 1):
        if fm(p, s[i:i + k]): best = k
    return best
def search(p, s):
    for i in range(len(s) + 1):
        k = longest(p, s, i)
        if k is not None: return [(i, k)]
    return []
def findall(p, s):
    out, i = [], 0
    while i < len(s):
        k = longest(p, s, i)
        if not k: i += 1
        else: out.append(s[i:i + k]); i += k
    return out
def replace(p, t, s):
    out, i = '', 0
    while i < len(s):
        k = longest(p, s, i)
        if not k: out += s[i]; i += 1
        else: out += t; i += k
    return out
def split(p, s):
    out, cur, i = [], '', 0
    while i < len(s):
        k = longest(p, s, i)
        if not k: cur += s[i]; i += 1
        else: out.append(cur); cur = ''; i += k
    out.append(cur)
    return out
LS = ('L', 'S'); LP = ('L', ('P', 'N', 'N'))
for t in range(n(60)):
    p = gen(3)
    for _ in range(3):
        s = rtext()
        add(f'rxfull {p!r} {s!r}', f'rxfull({lit(p, "S")}, {lit(s, "S")})', 'B', fm(p, s))
    s = rtext()
    k = longest(p, s, 0)
    add(f'rxprefix {p!r} {s!r}', f'rxprefix({lit(p, "S")}, {lit(s, "S")})', ('L', 'N'), [] if k is None else [k])
    add(f'rxsearch {p!r} {s!r}', f'rxsearch({lit(p, "S")}, {lit(s, "S")})', LP, search(p, s))
    add(f'rxfindall {p!r} {s!r}', f'rxfindall({lit(p, "S")}, {lit(s, "S")})', LS, findall(p, s))
    add(f'rxreplace {p!r} {s!r}', f'rxreplace({lit(p, "S")}, "<>", {lit(s, "S")})', 'S', replace(p, '<>', s))
    add(f'rxsplit {p!r} {s!r}', f'rxsplit({lit(p, "S")}, {lit(s, "S")})', LS, split(p, s))

# fixed cases: the usual examples
for (p, s, want) in [('a*b', 'aaab', True), ('a*b', 'aaa', False), ('(ab|cd)+', 'abcdab', True), ('(ab|cd)+', 'abc', False), ('[a-z]+@[a-z]+\\.com', 'me@home.com', True),
                     ('\\d\\d-\\d\\d', '12-34', True), ('\\d\\d-\\d\\d', '12-3x', False), ('', '', True), ('', 'a', False), ('a?', '', True), ('(a|b)*abb', 'ababb', True), ('[^a]*', 'bcd', True)]:
    add(f'rxfull {p!r} {s!r}', f'rxfull({lit(p, "S")}, {lit(s, "S")})', 'B', want)
    assert fm(p, s) == want
add('the leftmost longest match: a|ab on ab', f'rxsearch("a|ab", "xab")', LP, [(1, 2)])
add('rxfindall a+ on baaab aa', f'rxfindall("a+", "baaab aa")', LS, ['aaa', 'aa'])
add('rxreplace [0-9]+ by #', f'rxreplace({lit(chr(92) + "d+", "S")}, "#", "a12b345")', 'S', 'a#b#')
add('rxsplit , on a,b,,c', f'rxsplit(",", "a,b,,c")', LS, ['a', 'b', '', 'c'])

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
