"""test_encode.py -- lib/encode.imo (libsrc/encode.hum.imo): encodings and checksums against Python's base64, binascii, urllib.parse, zlib and codecs.
Oracles: bin* = & | ^ << >> on ints; utf8 = str.encode / bytes.decode(strict); hex = binascii.hexlify / unhexlify; base64 = base64.b64encode / b64decode(validate=True);
percent = urllib.parse.quote(safe='') / unquote(errors='strict'); adler32, crc32 = zlib; Luhn = the textbook algorithm; numwords = a second implementation here; Vigenere = textbook.
python3 tests/test_encode.py [--core pymo|haskimo|rustimo|compimo|ocamimo|schimo|cimo]"""
import base64, binascii, random, sys, urllib.parse, zlib
from langtest import *

R = random.Random(20261110)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 6) if SMALL else k
S = Suite('encodings and checksums')
add = S.add
LN = ('L', 'N'); LS = ('L', 'S'); LLN = ('L', LN)

def nat(): return R.choice([0, 1, 2, 3, 255, 256, 65535, 4294967295]) if R.random() < 0.3 else R.randint(0, 2 ** R.randint(1, 48))
def rbytes(m=12): return [R.randint(0, 255) for _ in range(R.randint(0, m))]
POOL = list('abcXYZ019 _-.~%/+=?&#\n\t') + ['é', 'ß', 'λ', '中', '€', '😀', '߿', 'ࠀ', '￿', '\U00010000', '\U0010ffff']
def rstr(m=8): return ''.join(R.choice(POOL) for _ in range(R.randint(0, m)))

# binary operations on natural numbers
for t in range(n(40)):
    a, b, k = nat(), nat(), R.randint(0, 40)
    add(f'binand {a} {b}', f'binand({a}, {b})', 'N', a & b)
    add(f'binor {a} {b}', f'binor({a}, {b})', 'N', a | b)
    add(f'binxor {a} {b}', f'binxor({a}, {b})', 'N', a ^ b)
    add(f'binshl {a} {k}', f'binshl({a}, {k})', 'N', a << k)
    add(f'binshr {a} {k}', f'binshr({a}, {k})', 'N', a >> k)
    add(f'graycode {a}', f'graycode({a})', 'N', a ^ (a >> 1))
    g = a ^ (a >> 1)
    add(f'fromgray {g}', f'fromgray({g})', 'N', a)
for a in range(0, 9):
    add(f'gray code of {a}', f'graycode({a})', 'N', a ^ (a >> 1))

# UTF-8
for t in range(n(60)):
    s = rstr()
    add(f'utf8bytes {s!r}', f'utf8bytes({lit(s, "S")})', LN, list(s.encode('utf-8')))
    add(f'utf8string of utf8bytes {s!r}', f'utf8string(utf8bytes({lit(s, "S")}))', LS, [s])
def decode(bs):
    try: return [bytes(bs).decode('utf-8')]
    except UnicodeDecodeError: return []
BAD = [[0xc0, 0x80], [0xc1, 0xbf], [0xe0, 0x80, 0x80], [0xe0, 0x9f, 0xbf], [0xed, 0xa0, 0x80], [0xed, 0xbf, 0xbf], [0xf0, 0x80, 0x80, 0x80], [0xf0, 0x8f, 0xbf, 0xbf], [0xf4, 0x90, 0x80, 0x80],
       [0xf5, 0x80, 0x80, 0x80], [0xff], [0x80], [0xc3], [0xe2, 0x82], [0xf0, 0x9f, 0x98], [0xc3, 0x28], [0xe2, 0x28, 0xa1], [0xf8, 0x88, 0x80, 0x80, 0x80]]
for bs in BAD + [rbytes(5) for _ in range(n(40))] + [[0x7f], [0xc2, 0x80], [0xdf, 0xbf], [0xe0, 0xa0, 0x80], [0xef, 0xbf, 0xbf], [0xf0, 0x90, 0x80, 0x80], [0xf4, 0x8f, 0xbf, 0xbf]]:
    add(f'utf8string {bs}', f'utf8string({lit(bs, LN)})', LS, decode(bs))

# hexadecimal
for t in range(n(50)):
    bs = rbytes()
    h = binascii.hexlify(bytes(bs)).decode()
    add(f'hexencode {bs}', f'hexencode({lit(bs, LN)})', 'S', h)
    add(f'hexdecode {h!r}', f'hexdecode({lit(h, "S")})', LLN, [bs])
    add(f'hexdecode upper {h.upper()!r}', f'hexdecode({lit(h.upper(), "S")})', LLN, [bs])
for h in ['abc', 'zz', '0g', 'f', '0x10', ' 00', '+1']:
    add(f'hexdecode bad {h!r}', f'hexdecode({lit(h, "S")})', LLN, [])

# Base 64
def b64dec(s):
    try: return [list(base64.b64decode(s.encode('ascii'), validate=True))]
    except Exception: return []
for t in range(n(60)):
    bs = rbytes(10)
    e = base64.b64encode(bytes(bs)).decode()
    add(f'base64encode {bs}', f'base64encode({lit(bs, LN)})', 'S', e)
    add(f'base64decode {e!r}', f'base64decode({lit(e, "S")})', LLN, [bs])
for s in ['', 'Zg==', 'Zg=', 'Zg', 'Zm8=', 'Zm8', 'Zm9v', 'Zm9vYg==', 'Zm9vYg=', 'Zm9vYmE=', 'Zm9vYmFy', 'Z===', '====', 'Zg==Zg==', 'Zm9v!A==', 'Zm9v\n', 'Zm 9v', 'Zh==', 'Zm9=', 'Zm9vYmF', '-_-_', 'Zg=a', 'Z=g=']:
    add(f'base64decode {s!r}', f'base64decode({lit(s, "S")})', LLN, b64dec(s))
for s in ['', 'f', 'fo', 'foo', 'foob', 'fooba', 'foobar']:        # the vectors of RFC 4648
    add(f'base64 RFC 4648 {s!r}', f'base64encode(utf8bytes({lit(s, "S")}))', 'S', base64.b64encode(s.encode()).decode())

# percent-encoding
def pdec(s):
    try:
        if not all(ord(c) < 128 for c in s): return []
        raw = urllib.parse.unquote_to_bytes(s)
        if '%' in s:                                                  # unquote_to_bytes passes a bad escape through; the module rejects it
            import re
            if re.search(r'%(?![0-9a-fA-F]{2})', s): return []
        return [raw.decode('utf-8')]
    except UnicodeDecodeError: return []
for t in range(n(60)):
    s = rstr()
    q = urllib.parse.quote(s, safe='')
    add(f'percentencode {s!r}', f'percentencode({lit(s, "S")})', 'S', q)
    add(f'percentdecode {q!r}', f'percentdecode({lit(q, "S")})', LS, [s])
for s in ['%', '%4', '%zz', '%41', '%e4%b8%ad', '%e4%b8', '%C3%A9', '%c0%80', 'a b', 'a%20b', 'é', '100%25', '%%41', '%4%41']:
    add(f'percentdecode {s!r}', f'percentdecode({lit(s, "S")})', LS, pdec(s))

# checksums
for t in range(n(60)):
    bs = rbytes(30)
    add(f'adler32 {bs}', f'adler32({lit(bs, LN)})', 'N', zlib.adler32(bytes(bs)))
    add(f'crc32 {bs}', f'crc32({lit(bs, LN)})', 'N', zlib.crc32(bytes(bs)))
add('crc32 of 123456789', f'crc32(utf8bytes("123456789"))', 'N', 0xCBF43926)
add('adler32 of Wikipedia', f'adler32(utf8bytes("Wikipedia"))', 'N', 0x11E60398)
add('crc32 of the empty list', 'crc32([])', 'N', 0)
add('adler32 of the empty list', 'adler32([])', 'N', 1)
big = [R.randint(0, 255) for _ in range(300)]
add('adler32 of 300 bytes', f'adler32({lit(big, LN)})', 'N', zlib.adler32(bytes(big)))
add('crc32 of 300 bytes', f'crc32({lit(big, LN)})', 'N', zlib.crc32(bytes(big)))

# Luhn
def lsum(s):
    t = 0
    for i, c in enumerate(reversed(s)):
        d = int(c)
        if i % 2 == 1:
            d *= 2
            if d > 9: d -= 9
        t += d
    return t
def lcheck(s): return len(s) > 0 and s.isdigit() and s.isascii() and lsum(s) % 10 == 0
def ldigit(s): return (10 - lsum(s + '0') % 10) % 10
for s in ['79927398713', '4111111111111111', '5500005555555559', '378282246310005', '0', '00', '1234', '49927398716', '49927398717', '', 'abc', '1 2', '-0']:
    add(f'luhncheck {s!r}', f'luhncheck({lit(s, "S")})', 'B', lcheck(s))
for t in range(n(60)):
    s = ''.join(R.choice('0123456789') for _ in range(R.randint(1, 16)))
    add(f'luhncheck {s}', f'luhncheck({lit(s, "S")})', 'B', lcheck(s))
    add(f'luhndigit {s}', f'luhndigit({lit(s, "S")})', 'N', ldigit(s))
    s2 = s + str(ldigit(s))
    add(f'luhncheck with the check digit {s2}', f'luhncheck({lit(s2, "S")})', 'B', True)
add('luhndigit 7992739871', 'luhndigit("7992739871")', 'N', 3)

# English names of numbers
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = '- - twenty thirty forty fifty sixty seventy eighty ninety'.split()
SC = ['', 'thousand', 'million', 'billion', 'trillion', 'quadrillion', 'quintillion']
def words(m):
    if m == 0: return 'zero'
    def under1000(k):
        out = []
        if k >= 100: out += [ONES[k // 100], 'hundred']; k %= 100
        if k >= 20:
            out.append(TENS[k // 10] + ('-' + ONES[k % 10] if k % 10 else ''))
        elif k > 0 or not out: out.append(ONES[k]) if k > 0 else None
        return out
    parts = []
    i = 0
    while m:
        k = m % 1000
        if k: parts = under1000(k) + ([SC[i]] if SC[i] else []) + parts
        m //= 1000; i += 1
    return ' '.join(parts)
for m in [0, 1, 9, 10, 11, 19, 20, 21, 99, 100, 101, 110, 119, 120, 999, 1000, 1001, 1010, 1100, 12345, 100000, 999999, 1000000, 1000001, 123456789, 10 ** 9, 10 ** 12 + 5, 10 ** 15, 2 ** 63, 10 ** 18, 10 ** 21 - 1]:
    add(f'numwords {m}', f'numwords({m})', 'S', words(m))
for t in range(n(40)):
    m = R.randint(0, 10 ** R.randint(1, 20))
    add(f'numwords {m}', f'numwords({m})', 'S', words(m))

# Vigenere
def vig(key, s, sign):
    if not key: return s
    out, i = [], 0
    for c in s:
        if c.isascii() and c.isalpha():
            k = (ord(key[i % len(key)].lower()) - 97) * sign
            base = 65 if c.isupper() else 97
            out.append(chr(base + (ord(c) - base + k) % 26)); i += 1
        else: out.append(c)
    return ''.join(out)
for t in range(n(50)):
    key = ''.join(R.choice('abcxyzABCXYZ') for _ in range(R.randint(0, 5)))
    s = ''.join(R.choice('abcxyzABCXYZ ,.!é1') for _ in range(R.randint(0, 14)))
    add(f'vigenere {key!r} {s!r}', f'vigenere({lit(key, "S")}, {lit(s, "S")})', 'S', vig(key, s, 1))
    add(f'unvigenere {key!r} {s!r}', f'unvigenere({lit(key, "S")}, {lit(s, "S")})', 'S', vig(key, s, -1))
    add(f'unvigenere of vigenere {key!r} {s!r}', f'unvigenere({lit(key, "S")}, vigenere({lit(key, "S")}, {lit(s, "S")}))', 'S', s)
add('vigenere LEMON', 'vigenere("LEMON", "ATTACKATDAWN")', 'S', 'LXFOPVEFRNHR')

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
