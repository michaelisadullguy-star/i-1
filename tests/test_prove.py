"""test_prove.py -- relations on ℝ[i] simplified by logic, from the definitions of their elements (lib/prove.imo, lib/solve.imo, pymo/quote.py).
Every case is a human-notation relation; the expected answer is the mathematical truth (checked independently with floating point
where that is possible), so the suite checks that a relation is never simplified to the wrong truth value, and that the answer is
"undetermined" (⍰) rather than a guess when no rule applies.                                             python3 tests/test_prove.py"""
import os, sys, math, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *                                  # the core under test: --core pymo (default) or --core haskimo

rep = Report()

DEFS = r'''
pi in \RR := sum(2, k in \QQ |-> k / (2 * k + 1))
e in \RR := sum(1, k in \QQ |-> 1 / k)
z in \R := pi + e * i
twice(x) in \R -> Bool := x + x == 2 * x
shifted(x) in \R -> Bool := x == x + 1
'''
PI, E = math.pi, math.e
CASES = [   # (name, human relation, expected, what it exercises)
    ('ring1', 'pi + e - pi == e', True, 'ring normal form'),
    ('ring2', '(pi + e) * (pi + e) == pi * pi + 2 * pi * e + e * e', True, 'ring normal form (products)'),
    ('ring3', 'z * conj(z) == pi * pi + e * e', True, 'conjugation of series'),
    ('val1', '1/3 + 1/6 == 1/2', True, 'a ℚ[i] relation is evaluated'),
    ('val2', '2 == 3', False, 'a ℚ[i] relation is evaluated'),
    ('iso1', 'exp(1) == e', True, 'logical expansion of exp + isomorphism of series'),
    ('iso2', 'sum(2, j in \\QQ |-> j / (1 + 2 * j)) == pi', True, 'isomorphism: the same ratio written differently'),
    ('iso3', '4 * atan(1) == pi', True, "Euler's arctangent series at 1 is π's series (β-reduction of atan)"),
    ('exp1', 'e * e == exp(2)', True, 'rule exp a · exp b = exp(a + b)'),
    ('exp2', 'sin(1/2) * sin(1/2) + cos(1/2) * cos(1/2) == 1', True, 'sine and cosine series are exponentials'),
    ('exp3', 'exp(i / 2) == cos(1/2) + i * sin(1/2)', True, "Euler's formula"),
    ('exp4', 'cosh(1/3) * cosh(1/3) - sinh(1/3) * sinh(1/3) == 1', True, 'hyperbolic series are exponentials'),
    ('sqrt1', 'sqrt(2) * sqrt(2) == 2', True, 'rule (√c)² = c'),
    ('sqrt2', 'sqrt(9/4) == 3/2', True, 'an exact root in ℚ(i)'),
    ('sqrt3', 'sqrt(3) * sqrt(2) == sqrt(6)', True, 'rule √a·√b = √(ab), a, b ≥ 0'),
    ('num1', 'pi == e', False, 'certified discs refute ='),
    ('num2', 'pi gt 3', True, 'certified discs decide <'),
    ('num3', 'pi lt 22 / 7', True, 'certified discs decide < (Archimedes)'),
    ('num4', 'sqrt(2) lt 1.414', False, 'the modulus of √ decides <'),
    ('num5', 'pi * pi == 10', False, 'discs of products'),
    ('log1', '(pi != e) and (e lt pi)', True, 'connectives: and = min, not, !='),
    ('log2', 'pi + 0 == pi or 1 gt 2', True, 'or = max over a decided and an evaluated relation'),
    ('log3', 'not (pi == e) implies (e lt 3)', True, 'implies'),
    ('var1', 'twice(pi)', True, 'an unknown x: x + x = 2x holds for every x'),
    ('var2', 'shifted(e)', False, 'an unknown x: x = x + 1 is refuted for every x (the difference is the constant −1)'),
]
UNDECIDED = [('und1', 'sqrt(8) == 2 * sqrt(2)', 'true, but no rule extracts square factors yet')]

tf = tri                                                # True, False, or None (undetermined)

def main():
    src = DEFS + '\n'.join(f"{n} in Bool := {expr}" for n, expr, *_ in CASES + UNDECIDED)
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(src, 'prove.hum.imo', notation='hum')
    errs = P.check(collect=True)
    rep("every relation passes the class checker; relations on ℝ[i] are compiled to  simplify′ ε⌜⌝ ⌜φ⌝", not errs and
        (CORE != 'pymo' or all(r is None or r[0] != 'def' or 'quote' not in repr(r[3]) for r in P.resolved)), str(errs[:1]))      # the marks are looked at in Pymo
    if errs: return rep.done()
    P.build()
    spec = P.spec_text()
    rep("the code of a relation names symbols by their doc 1 codes (⊕ is 𝔮ˢ (↓ᶻ %s))" % P.doc1.s2b['⊕'][1:-1],
        f"(𝔮ˢ (↓ᶻ {P.doc1.s2b['⊕'][1:-1]}))" in spec and 'ε⌜⌝ ≔ (∷ (⊗' in spec)
    ok = subprocess.run([sys.executable, os.path.join(ROOT, 'pymo', 'mkprove.py'), '--check'], capture_output=True).returncode == 0
    rep("the symbol codes inside lib/prove.imo agree with doc 1 (pymo/mkprove.py --check)", ok)
    groups = {}
    for n, expr, want, what in CASES:
        got = tf(P.val(n))
        groups.setdefault(what, []).append((n, expr, want, got))
    for what, rows in groups.items():
        rep(f"{what}: " + ';  '.join(f"{expr}  →  {'true' if got else 'false' if got is False else 'undetermined'}" for n, expr, want, got in rows),
            all(got == want for n, expr, want, got in rows))
    for n, expr, why in UNDECIDED:
        v = P.val(n)
        rep(f"undetermined, not guessed: {expr}  ({why})", tf(v) is None)
    # the printer reports ⍰ instead of printing true or false
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'u.hum.imo')
        open(p, 'w', encoding='utf-8').write('main in Bool := sqrt(8) == 2 * sqrt(2)\n')
        r = subprocess.run(cli() + [p], capture_output=True, text=True, timeout=900)
        rep("running a program whose main is undetermined reports it (exit code 1), it does not print true or false",
            r.returncode == 1 and 'undetermined' in r.stdout, r.stdout.strip()[:80])
    # the same decisions from the all-binary program: the prover runs on numeric codes, from 1 0 . ( ) alone
    def run(*files):
        return subprocess.run(cli() + [*files], capture_output=True, text=True, timeout=1800).stdout
    hb = run(os.path.join(ROOT, 'examples', 'prove.hum.imo'))
    bb = run(os.path.join(ROOT, 'lib', 'prelude.bin.imo'), os.path.join(ROOT, 'examples', 'prove.bin.imo'))
    text = open(os.path.join(ROOT, 'examples', 'prove.bin.imo'), encoding='utf-8').read()
    rep("examples/prove.bin.imo (only 1 0 . space ( ) newline) with lib/prelude.bin.imo decides exactly as examples/prove.hum.imo",
        set(text) <= set('10. ()\n') and hb == bb and [ln.split()[-1] for ln in hb.splitlines()[:9]] == ['true'] * 7 + ['false', 'true'], f"({len(text)} characters)")
    # independent truth of the numeric cases
    truth = {'num1': PI == E, 'num2': PI > 3, 'num3': PI < 22 / 7, 'num4': math.sqrt(2) < 1.414, 'num5': abs(PI * PI - 10) < 1e-12}
    rep("the expected answers of the numeric cases agree with floating point", all(truth[n] == want for n, _, want, _ in CASES if n in truth))

    # ---- one system: truth values are the digits 1 and 0
    Q = imo.Program()
    for f in imo.PRELUDE: Q.add_file(f, trusted=True)
    laws = []
    for a in ('true', 'false'):
        for b in ('true', 'false'):
            laws += [f"iverson({a} or {b}) == max(iverson({a}), iverson({b}))", f"iverson({a} and {b}) == iverson({a}) * iverson({b})",
                     f"iverson({a} and {b}) == min(iverson({a}), iverson({b}))", f"({a} + {b}) == ({a} or {b})", f"({a} * {b}) == ({a} and {b})",
                     f"max({a}, {b}) == ({a} or {b})"]
    for m in range(4):
        for n in range(4):
            laws += [f"supp({m} + {n}) == (supp({m}) or supp({n}))", f"supp({m} * {n}) == (supp({m}) and supp({n}))"]
    laws += ["member(3, setof([1]) + setof([3])) == (member(3, setof([1])) or member(3, setof([3])))",
             "member(2, max(setof([1]), setof([2]))) == member(2, union(setof([1]), setof([2])))", "1 + true == 2"]
    Q.add_text('\n'.join(f"law{k} in Bool := {x}" for k, x in enumerate(laws)), 'laws.hum.imo', notation='hum')
    errs = Q.check(collect=True)
    ok = not errs
    if ok:
        Q.build(); ok = all(tf(Q.val(f'law{k}')) is True for k in range(len(laws)))
    rep(f"one system: ⊤/⊥ are 1/0 (iverson), or = max = + on truth values, and = min = ×, supp(m + n) = supp m or supp n, "
        f"union = or of the tests = + on sets — {len(laws)} laws evaluated in the language", ok, str(errs[:1]))
    return rep.done()

sys.exit(0 if run_big(main) else 1)
