"""test_solve.py -- the predicate simplifier (lib/solve.imo): a statement about unknowns is reduced to its simplest form.
Part 1: hand-checked answers (the examples of docs/predicates.md and one case or more for every domain and every solver).
Part 2: a randomized check of the real-line solver against independent arithmetic: random polynomial statements are simplified by the
        engine; the original statement and the answer are then evaluated at many sample points with exact rational arithmetic.
Every statement goes through the human notation, the class checker, the quoter and the engine, which runs in the language.
python3 tests/test_solve.py"""
import os, sys, re, random, math
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *

rep = Report()

def run_prog(src, name='solve.hum.imo'):
    """simplify every statement of `main in List(Prop)`; returns the list of printed answers"""
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(src, name, notation='hum')
    errs = P.check(collect=True)
    if errs: raise SystemExit(f"class errors: {errs[:2]}")
    P.build()
    lines = []
    run_main(P, 'hum', None, write=lines.append)
    text = ''.join(lines).strip()
    return split_list(text)

def split_list(text):
    """'[a, b, c]' -> ['a', 'b', 'c'] (commas inside brackets or parentheses do not split)"""
    assert text.startswith('[') and text.endswith(']'), text[:80]
    out, depth, cur = [], 0, ''
    for ch in text[1:-1]:
        if ch in '([': depth += 1
        if ch in ')]': depth -= 1
        if ch == ',' and depth == 0: out.append(cur.strip()); cur = ''
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

# ----------------------------------------------------------------------------------------------------------- part 1: hand-checked
CASES = [  # (title, declarations, [(statement, expected answer)])
 ("the examples of the specification (one real unknown)", "x in \\RR", [
   ("x^2 gt 7 and x^3 lt 27", "x lt -sqrt(7) or (sqrt(7) lt x and x lt 3)"),
   ("x^2 + 1 == 0", "false"),
   ("x^2 - 2 geq 0", "x leq -sqrt(2) or sqrt(2) leq x"),
   ("(x - 1)*(x - 2)*(x - 3) lt 0", "x lt 1 or (2 lt x and x lt 3)"),
   ("x^3 == 2", "x == root([-2, 0, 0, 1], 1)"),
   ("x^2 geq 0", "true"), ("x^2 + 1 gt 0", "true"),
   ("(x gt 1 or x lt -1) and x^2 lt 4", "(-2 lt x and x lt -1) or (1 lt x and x lt 2)"),
   ("x != 1 and x^2 == 1", "x == -1"),
   ("x gt 2 implies x^2 gt 4", "true"),
   ("x^2 == 2 or x == 1", "x == -sqrt(2) or x == 1 or x == sqrt(2)"),
   ("x^2 lt 0", "false"), ("x == x", "true"), ("x == x + 1", "false"),
   ("x^4 - 5*x^2 + 4 == 0", "x == -2 or x == -1 or x == 1 or x == 2"),
   ("x^3 - x gt 0", "(-1 lt x and x lt 0) or 1 lt x"),
   ("x^5 - x + 1 gt 0", "root([1, -1, 0, 0, 0, 1], 1) lt x"),
   ("not (x gt 0)", "x leq 0"), ("(x gt 0) iff (x^3 gt 0)", "true")]),
 ("one rational unknown", "q in \\QQ", [
   ("q^2 == 2", "false"), ("q^2 lt 2", "-sqrt(2) lt q and q lt sqrt(2)"), ("q^2 leq 4", "-2 leq q and q leq 2"),
   ("q^2 == 4", "q == -2 or q == 2"), ("2*q == 3", "q == 3/2"), ("q^2 gt 2", "q lt -sqrt(2) or sqrt(2) lt q"),
   ("q != 1", "q != 1")]),
 ("one integer unknown", "n in \\ZZ", [
   ("n^2 lt 10", "-3 leq n and n leq 3"), ("2*n == 3", "false"), ("n^2 != 1", "n != -1 and n != 1"),
   ("n^2 == 4", "n == -2 or n == 2"), ("n gt 2 and n lt 6", "3 leq n and n leq 5"), ("n^3 lt 30", "n leq 3"),
   ("n^2 geq 0", "true"), ("n^2 gt 5", "n leq -3 or 3 leq n")]),
 ("one natural unknown", "m in \\NN", [
   ("m^2 lt 10", "m leq 3"), ("m^2 leq 16 and m != 2", "m leq 1 or (3 leq m and m leq 4)"), ("m gt 5", "6 leq m"),
   ("m != 0", "1 leq m"), ("m + 1 == 0", "false"), ("m geq 0", "true")]),
 ("one complex unknown", "y in \\CC", [
   ("y^2 + 1 == 0", "y == -i or y == i"),
   ("y^2 + y + 1 == 0", "y == -1/2 - 1/2*sqrt(-3) or y == -1/2 + 1/2*sqrt(-3)"),
   ("y^3 == 2", "y^3 == 2"), ("y^2 == -4", "y == -2*i or y == 2*i"), ("not (y^2 == 1)", "y != -1 and y != 1"),
   ("y^2 - 2 == 0", "y == -sqrt(2) or y == sqrt(2)"), ("y^4 - 1 == 0", "y == -1 or y == -i or y == i or y == 1"),
   ("y != 1 and y^2 == 1", "y == -1"), ("y == y", "true"), ("y == y + 1", "false")]),
 ("one Gaussian rational unknown", "w in \\Q", [
   ("w^2 + 1 == 0", "w == -i or w == i"), ("w^2 == 2", "false"), ("2*w == 1 + i", "w == 1/2 + 1/2*i"),
   ("w^2 - 1 == 0 or w == 3", "w == -1 or w == 1 or w == 3")]),
 ("one Gaussian integer unknown", "v in \\Z", [
   ("v^2 + 1 == 0", "v == -i or v == i"), ("2*v == 1 + i", "false"), ("v^2 == 4 and v != 2", "v == -2")]),
 ("a complex unknown with conj, re, im (split into real and imaginary parts)", "z in \\CC", [
   ("z * conj(z) + 1 == 0", "false"), ("z == conj(z)", "im(z) == 0"), ("z * conj(z) == 0", "re(z) == 0 and im(z) == 0"),
   ("z + conj(z) == 2", "re(z) == 1"), ("z - conj(z) == 2*i", "im(z) == 1"),
   ("re(z) == 1 and im(z) == 2", "re(z) == 1 and im(z) == 2"), ("re(z)^2 + im(z)^2 geq 0", "true")]),
 ("two real unknowns", "x in \\RR\ny in \\RR", [
   ("x + y == 3 and x - y == 1", "x == 2 and y == 1"), ("x^2 + y^2 + 1 gt 0", "true"), ("x^2 + y^2 == 0", "x == 0 and y == 0"),
   ("x*y == 1", "x*y == 1"), ("x == 2 and x*y == 4", "x == 2 and y == 2"), ("x + y == 3", "x + y == 3"),
   ("x^2 + y^2 geq 0", "true"), ("x^2 + y^2 lt 0", "false"), ("x + y == 1 and x + y == 2", "false"),
   ("x gt 1 or y lt 2", "x gt 1 or y lt 2"), ("2*x*y == 2", "x*y == 1"), ("x^2 + y^2 leq 0", "x == 0 and y == 0"),
   ("x^2*y^2 == 0", "x == 0 or y == 0"), ("x + 2*y - 3 leq 0", "x + 2*y leq 3")]),
 ("two complex unknowns", "p in \\CC\nr in \\CC", [("p + r == 3 and p - r == 1", "p == 2 and r == 1")]),
 ("unknowns declared in a different order are listed in declaration order", "b in \\RR\na in \\RR", [
   ("b + a == 3 and b - a == 1", "b == 2 and a == 1")]),
]

def part1():
    for title, decls, rows in CASES:
        src = decls + "\nmain in List(Prop) := [" + ", ".join(s for s, _ in rows) + "]\n"
        got = run_prog(src)
        bad = [(s, e, g) for (s, e), g in zip(rows, got) if e != g]
        if len(got) != len(rows): bad.append(("(length)", len(rows), len(got)))
        rep(f"{title}: " + ";  ".join(f"{s}  →  {e}" for s, e in rows[:4]) + ("  …" if len(rows) > 4 else "") + f"   [{len(rows)} statements]",
            not bad, '' if not bad else "\n      " + "\n      ".join(f"{s!r}: expected {e!r}, got {g!r}" for s, e, g in bad))

# ----------------------------------------------------------------------------------------------------------- part 2: random check
_SQ = {}
def sqrt_fr(q, digits=60):
    if q not in _SQ: _SQ[q] = _sqrt_fr(q, digits)
    return _SQ[q]

def _sqrt_fr(q, digits=60):
    """sqrt of a non-negative Fraction as a Fraction accurate to 10^-digits"""
    n, d = q.numerator, q.denominator
    s = math.isqrt(n * d * 10 ** (2 * digits))
    return Fr(s, d * 10 ** digits)

_ROOTS = {}
def root_fr(coefs, k, digits=40):
    key = (tuple(coefs), k)
    if key not in _ROOTS: _ROOTS[key] = _root_fr(coefs, k, digits)
    return _ROOTS[key]

def _root_fr(coefs, k, digits=40):
    """the k-th (1-based) real root of the polynomial (coefficient list, lowest first), by sign changes and bisection"""
    f = lambda x: sum(c * x ** i for i, c in enumerate(coefs))
    # isolate with a fine grid on [-B, B] (Cauchy bound), then bisect; adequate for the test polynomials (small coefficients)
    B = 1 + max(abs(Fr(c, coefs[-1])) for c in coefs[:-1])
    N = 4000
    xs = [-B + 2 * B * Fr(i, N) for i in range(N + 1)]
    roots = []
    for a, b in zip(xs, xs[1:]):
        fa, fb = f(a), f(b)
        if fa == 0 and (not roots or roots[-1] != a): roots.append(a)
        elif fa * fb < 0:
            lo, hi = a, b
            for _ in range(digits * 4):
                m = (lo + hi) / 2
                if f(lo) * f(m) <= 0: hi = m
                else: lo = m
            roots.append((lo + hi) / 2)
    if f(xs[-1]) == 0: roots.append(xs[-1])
    return roots[k - 1]

def truth_of_answer(ans, x):
    """evaluate an answer like  'x lt -sqrt(7) or (sqrt(7) lt x and x lt 3)'  at x (a Fraction), with exact rational arithmetic
    (square roots and roots of polynomials to 40 digits)"""
    if ans == 'true': return True
    if ans == 'false': return False
    t = ans
    t = re.sub(r'root\(\[([^\]]*)\],\s*(\d+)\)', lambda m: "R_(%r, %s)" % (m.group(1), m.group(2)), t)
    t = re.sub(r'sqrt\(', 'S_(', t)
    for a_, b_ in ((' leq ', ' <= '), (' geq ', ' >= '), (' lt ', ' < '), (' gt ', ' > ')): t = t.replace(a_, b_)
    t = t.replace('^', '**')
    # numbers (but not inside the quoted coefficient lists of R_) become Fractions
    parts = re.split(r"('[^']*')", t)
    parts = [p_ if p_.startswith("'") else re.sub(r'(?<![\w.])(\d+)(?![\w.])', r'F_(\1)', p_) for p_ in parts]
    t = ''.join(parts)
    def R_(sl, k): return root_fr([Fr(c) for c in sl.split(",")], int(k))
    def S_(q): return sqrt_fr(Fr(q))
    return bool(eval(t, {'F_': Fr, 'S_': S_, 'R_': R_, '__builtins__': {}}, {'x': x}))

REL = [('==', lambda a, b: a == b, '=='), ('!=', lambda a, b: a != b, '!='), ('lt', lambda a, b: a < b, 'lt'), ('leq', lambda a, b: a <= b, 'leq'),
       ('gt', lambda a, b: a > b, 'gt'), ('geq', lambda a, b: a >= b, 'geq')]

def rand_poly(rng, maxdeg=4):
    d = rng.randint(1, maxdeg)
    cs = [rng.randint(-4, 4) for _ in range(d)] + [rng.choice([-2, -1, 1, 2, 3])]
    return cs

def poly_text(cs):
    terms = [f"({c})*x^{i}" if i > 1 else (f"({c})*x" if i == 1 else f"({c})") for i, c in enumerate(cs) if c != 0]
    return " + ".join(terms) if terms else "0"

def part2(seed=20261026, count=40):
    rng = random.Random(seed)
    stmts, meta = [], []
    for _ in range(count):
        kind = rng.choice(['single', 'single', 'and', 'or'])
        parts = []
        for _ in range(1 if kind == 'single' else 2):
            cs = rand_poly(rng); r = rng.choice(REL); parts.append((cs, r))
        text = (f" {kind} ".join(f"{poly_text(cs)} {r[0]} 0" for cs, r in parts)) if kind != 'single' else f"{poly_text(parts[0][0])} {parts[0][1][0]} 0"
        stmts.append(text); meta.append((kind, parts))
    src = "x in \\RR\nmain in List(Prop) := [" + ", ".join(stmts) + "]\n"
    got = run_prog(src)
    assert len(got) == len(stmts), (len(got), len(stmts))
    pts = sorted({Fr(a, b) for b in (1, 2, 3, 5, 7, 11) for a in range(-14 * b, 14 * b + 1, max(1, b // 2) if b > 1 else 1)})
    bad = []
    for text, (kind, parts), ans in zip(stmts, meta, got):
        def orig(xv):
            vals = []
            for cs, r in parts:
                v = sum(Fr(c) * xv ** i for i, c in enumerate(cs))
                vals.append(r[1](v, 0))
            return vals[0] if kind == 'single' else (vals[0] and vals[1] if kind == 'and' else vals[0] or vals[1])
        try:
            wrong = [str(xv) for xv in pts if orig(xv) != truth_of_answer(ans, xv)]
        except Exception as e:
            wrong = [f"cannot evaluate the answer: {e}"]
        if wrong: bad.append((text, ans, wrong[:3]))
    rep(f"random check: {count} random polynomial statements (degree ≤ 4, one real unknown) — the answer and the statement agree at {len(pts)} sample points each",
        not bad, '' if not bad else "\n      " + "\n      ".join(f"{t}  →  {a}   differs at {w}" for t, a, w in bad[:5]))

def main():
    part1()
    part2()
    return rep.done()

sys.exit(0 if run_big(main) else 1)
