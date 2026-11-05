"""test_strings.py -- lib/strings.imo against Python oracles (character classes, case, splitting, searching, padding, bases, Roman
numerals, edit distance, run lengths).   python3 tests/test_strings.py [--core pymo|haskimo|rustimo]"""
import itertools, random, sys
from langtest import *

R = random.Random(1104)
POOL_CH = list('abcxyzABCXYZ0189 \t.,;!-+_~') + list('éüÀÖßÿ×÷') + list('αλωΣςΩ') + list('ядЯЖ')
ASCII_WS = list('ab cd\tef\n') + ['  ']
def chars(n_max=9, pool=POOL_CH): return ''.join(R.choice(pool) for _ in range(R.randint(0, n_max)))
def txt(n_max=9): return ''.join(R.choice('abAB xy\t\n,;.') for _ in range(R.randint(0, n_max)))
def wsx(n_max=12): return ''.join(R.choice('ab \t\n') for _ in range(R.randint(0, n_max)))

S = Suite('characters and strings')
add = S.add
SP = ''.join(sorted(set(POOL_CH)))
# character classes and case: against Python's own tables on the letters that the module covers
for c in POOL_CH:
    q = lit(c, 'C')
    add(f'isdigit {c!r}', f'isdigit({q})', 'B', c in '0123456789')
    add(f'isuppercase {c!r}', f'isuppercase({q})', 'B', c.isupper())
    add(f'islowercase {c!r}', f'islowercase({q})', 'B', c.islower())
    add(f'isalpha {c!r}', f'isalpha({q})', 'B', c.isalpha())
    add(f'isalnum {c!r}', f'isalnum({q})', 'B', c.isalnum() and c not in '²³¹')
    add(f'isspace {c!r}', f'isspace({q})', 'B', c in ' \t\n')
    add(f'ispunct {c!r}', f'ispunct({q})', 'B', c in '.,;!-+_~')
    u = c.upper(); lo = c.lower()
    add(f'upper {c!r}', f'upper({q})', 'C', u if len(u) == 1 and ord(c) - ord(u) == 32 else c)
    add(f'lower {c!r}', f'lower({q})', 'C', lo if len(lo) == 1 and ord(lo) - ord(c) == 32 else c)
for cp in (0xA0, 0x2003, 0x3000, 0x0B, 0x0C, 0x0D):
    add(f'isspace U+{cp:04X}', f'isspace(chr({cp}))', 'B', True)
add('isspace U+2028 is not white space here', 'isspace(chr(8232))', 'B', False)

for t in range(8):
    s = chars(); w = wsx(); t2 = txt()
    add(f'toupper {s!r}', f'toupper({lit(s, "S")})', 'S', ''.join((c.upper() if len(c.upper()) == 1 and ord(c) - ord(c.upper()) == 32 else c) for c in s))
    add(f'tolower {s!r}', f'tolower({lit(s, "S")})', 'S', ''.join((c.lower() if len(c.lower()) == 1 and ord(c.lower()) - ord(c) == 32 else c) for c in s))
    cap = s[:1].upper() if s and len(s[0].upper()) == 1 and ord(s[0]) - ord(s[0].upper()) == 32 else s[:1]
    add(f'capitalize {s!r}', f'capitalize({lit(s, "S")})', 'S', cap + ''.join((c.lower() if len(c.lower()) == 1 and ord(c.lower()) - ord(c) == 32 else c) for c in s[1:]))
    add(f'trim {w!r}', f'trim({lit(w, "S")})', 'S', w.strip(' \t\n'))
    add(f'ltrim {w!r}', f'ltrim({lit(w, "S")})', 'S', w.lstrip(' \t\n'))
    add(f'rtrim {w!r}', f'rtrim({lit(w, "S")})', 'S', w.rstrip(' \t\n'))
    add(f'words {w!r}', f'words({lit(w, "S")})', ('L', 'S'), w.split())
    add(f'unwords', f'unwords({lit(w.split(), ("L", "S"))})', 'S', ' '.join(w.split()))
    add(f'lines {t2!r}', f'lines({lit(t2, "S")})', ('L', 'S'), [] if t2 == '' else (t2[:-1] if t2.endswith('\n') else t2).split('\n'))
    add(f'split {t2!r}', f'split(\',\', {lit(t2, "S")})', ('L', 'S'), t2.split(','))
    p = ''.join(R.choice('ab') for _ in range(R.randint(1, 2)))
    base = ''.join(R.choice('abx') for _ in range(R.randint(0, 9)))
    add(f'splitstr {p!r} {base!r}', f'splitstr({lit(p, "S")}, {lit(base, "S")})', ('L', 'S'), base.split(p))
    add(f'replace {p!r} {base!r}', f'replace({lit(base, "S")}, {lit(p, "S")}, "--")', 'S', base.replace(p, '--'))
    add(f'replace shrink {p!r} {base!r}', f'replace({lit(base, "S")}, {lit(p, "S")}, "")', 'S', base.replace(p, ''))
    add(f'startswith {p!r} {base!r}', f'startswith({lit(base, "S")}, {lit(p, "S")})', 'B', base.startswith(p))
    add(f'endswith {p!r} {base!r}', f'endswith({lit(base, "S")}, {lit(p, "S")})', 'B', base.endswith(p))
    add(f'contains {p!r} {base!r}', f'contains({lit(base, "S")}, {lit(p, "S")})', 'B', p in base)
    add(f'indexof {p!r} {base!r}', f'indexof({lit(base, "S")}, {lit(p, "S")})', ('L', 'N'), [base.find(p)] if p in base else [])
    n = R.randint(0, 9)
    add(f'padleft {n} {base!r}', f'padleft({n}, \'*\', {lit(base, "S")})', 'S', base.rjust(n, '*'))
    add(f'padright {n} {base!r}', f'padright({n}, \'*\', {lit(base, "S")})', 'S', base.ljust(n, '*'))
    pad = max(0, n - len(base)); left = pad // 2
    add(f'padcenter {n} {base!r}', f'padcenter({n}, \'*\', {lit(base, "S")})', 'S', '*' * left + base + '*' * (pad - left) if pad else base)
    add(f'repeatstr {base!r}', f'repeatstr({n % 4}, {lit(base, "S")})', 'S', base * (n % 4))
    add(f'ispalindrome {base!r}', f'ispalindrome({lit(base, "S")})', 'B', base == base[::-1])
    k = R.randint(-30, 30)
    cz = ''.join(R.choice('abcxyzABCXYZ -,') for _ in range(R.randint(0, 9)))
    cc = ''.join((chr((ord(c) - 97 + k) % 26 + 97) if 'a' <= c <= 'z' else chr((ord(c) - 65 + k) % 26 + 65) if 'A' <= c <= 'Z' else c) for c in cz)
    add(f'caesar {k} {cz!r}', f'caesar({k}, {lit(cz, "S")})', 'S', cc)
add('replace with an empty pattern changes nothing', 'replace("abc", "", "x")', 'S', 'abc')
add('splitstr with an empty pattern', 'splitstr("", "abc")', ('L', 'S'), ['abc'])
add('lines: a lone line feed', 'lines("\\n")', ('L', 'S'), [''])
add('lines: empty', 'lines("")', ('L', 'S'), [])
add('isanagram', 'isanagram("Dormitory", "Dirty room")', 'B', True)
add('isanagram not', 'isanagram("abc", "abd")', 'B', False)

# numbers as text
for t in range(10):
    n = R.randint(0, 100000); b = R.randint(2, 36)
    digs = '0123456789abcdefghijklmnopqrstuvwxyz'
    def tob(n, b):
        s = ''
        while n: s = digs[n % b] + s; n //= b
        return s or '0'
    add(f'showbase {n} {b}', f'showbase({n}, {b})', 'S', tob(n, b))
    add(f'hex {n}', f'hex({n})', 'S', format(n, 'x'))
    add(f'octal {n}', f'octal({n})', 'S', format(n, 'o'))
    add(f'binary {n}', f'binary({n})', 'S', format(n, 'b'))
    add(f'readbase {b} {tob(n, b)!r}', f'readbase({b}, {lit(tob(n, b), "S")})', ('L', 'N'), [n])
    add(f'readnat {n}', f'readnat({lit(str(n), "S")})', ('L', 'N'), [n])
    add(f'readint {-n}', f'readint({lit(str(-n), "S")})', ('L', 'Z'), [-n])
    add(f'readint +{n}', f'readint({lit("+" + str(n), "S")})', ('L', 'Z'), [n])
for bad in ('', '12x', '-', ' 1', '1.5', 'a'):
    add(f'readnat {bad!r} is nothing', f'readnat({lit(bad, "S")})', ('L', 'N'), [])
add('readbase rejects a digit that is too big', 'readbase(2, "102")', ('L', 'N'), [])
add('readbase accepts capitals', 'readbase(16, "FF")', ('L', 'N'), [255])
add('digitval z', "digitval('z')", ('L', 'N'), [35])

# Roman numerals
def roman(n):
    out = ''
    for v, s in ((1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v: out += s; n -= v
    return out
for n in [1, 4, 9, 14, 40, 90, 400, 1994, 2024, 3999, 0] + [R.randint(1, 3999) for _ in range(12)]:
    add(f'roman {n}', f'roman({n})', 'S', roman(n))
    add(f'fromroman {roman(n)!r}', f'fromroman({lit(roman(n), "S")})', 'N', n)

# edit distance, run lengths
def lev(a, b):
    p = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        q = [i]
        for j, cb in enumerate(b, 1): q.append(min(p[j - 1] + (ca != cb), p[j] + 1, q[j - 1] + 1))
        p = q
    return p[-1]
for a, b in [('kitten', 'sitting'), ('', 'abc'), ('abc', ''), ('', ''), ('flaw', 'lawn'), ('same', 'same'), ('ab', 'ba')] + [(chars(7, list('abc')), chars(7, list('abc'))) for _ in range(10)]:
    add(f'levenshtein {a!r} {b!r}', f'levenshtein({lit(a, "S")}, {lit(b, "S")})', 'N', lev(a, b))
for s in ['', 'a', 'aaabcc', 'zzzzzzzzzzzz', 'abab'] + [''.join(R.choice('abc') for _ in range(R.randint(0, 14))) for _ in range(6)]:
    enc = ''.join(str(len(list(g))) + k for k, g in itertools.groupby(s))
    add(f'rle {s!r}', f'rle({lit(s, "S")})', 'S', enc)
    add(f'unrle {enc!r}', f'unrle({lit(enc, "S")})', 'S', s)

sys.exit(0 if report(S) else 1)
