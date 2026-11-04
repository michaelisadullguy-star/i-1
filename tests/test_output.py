"""test_output.py -- the entry point `main` and the three output notations.
  * a value printed in a notation reads back, in that notation, as a term with the same canonical form (round trip);
  * main ∶ String prints its text, List/Stream(String) print lines;
  * the output notation: --out, else @out, else the notation main is written in.            python3 tests/test_output.py"""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *
pymo_only('the printer and the readers')      # their command-line counterparts (run --out, translate) are cases of tests/conformance
from base_b import numeral
import output, layers, syntax

rep = Report()
I1 = os.path.join(ROOT, 'pymo', 'i1.py')

HUMCLASS = {'ℕ': r'\NN', 'ℤ': r'\ZZ', 'ℚ': r'\QQ', 'ℝ': r'\RR', 'ℤ[i]': r'\Z', 'ℚ[i]': r'\Q', 'ℝ[i]': r'\R', '𝔻': r'\D',
            '𝔹': 'Bool', '𝕮': 'Char', '𝕊': 'String', '𝔇': 'Digits', '𝔒': 'Ordering',
            '𝔏': 'List', '𝔖': 'Stream', '𝔗': 'Tree', '𝔓': 'Pair'}
def hum_class(t):
    if t[0] == 'K' and t[1] == '→': return f'({hum_class(t[2][0])} -> {hum_class(t[2][1])})'
    if not t[2]: return HUMCLASS[t[1]]
    return HUMCLASS[t[1]] + '(' + ', '.join(hum_class(a) for a in t[2]) + ')'

CASES = [                       # (human class, human expression)
    (r'\NN', '2 ^ 70'),
    (r'\ZZ', '-12345678901234567890'),
    (r'\QQ', '-22 / 7'),
    (r'\Q', '(1 + 2 * i) / (3 - i) - 5'),
    (r'\Q', '-i / 2'),
    (r'\Z', '0'),
    ('Bool', '1 geq 2'),
    ('Char', "'λ'"),
    ('Ordering', 'compare(1/3, 1/4)'),
    (r'List(\Q)', '[1/2, -3, 2 - i/3, 0]'),
    (r'List(\NN)', '[]'),
    ('List(String)', '["héllo", "with \\"quotes\\"", ""]'),
    (r'Pair(\QQ, Bool)', 'pair(3/4, true)'),
    (r'\D', 'j * k + 1'),
    (r'\D', '(1 + 2 * i) * j'),
    (r'List(List(\Q))', 'inverse([[1, 2], [3, 4]])'),
]

def program(cls, expr):
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_text(f"main in {cls} := {expr}", 'case.hum.imo', notation='hum')
    errs = P.check(collect=True)
    assert not errs, errs
    P.build(); return P

def canonical(P, name):
    """the spec normal form of a symbol's value (canonical forms are unique, so equal values give equal text)"""
    return output.Printer(P, 'spec').term(P.val(name), P.checker.sigs[name][0])

def read_back(text, mode, cls_spec):
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    if mode == 'hum':
        P.add_text(f"again in {hum_class(cls_spec)} := {text}", 'back.hum.imo', notation='hum')
    else:
        term = text if mode == 'spec' else layers.bin_to_spec_text(text, P.doc1).strip()
        P.add_text(f"again ∶ {syntax.pp_type(cls_spec)}\nagain ≔ {term}", 'back.imo', notation='spec')
    errs = P.check(collect=True)
    assert not errs, (text, errs)
    P.build(); return P

def main():
    ok_all, bad = True, []
    for cls, expr in CASES:
        P = program(cls, expr)
        c = P.checker.sigs['main'][0]
        want = canonical(P, 'main')
        for mode in output.MODES:
            text = output.Printer(P, mode).show(P.val('main'), c)
            try:
                got = canonical(read_back(text, mode, c), 'again')
            except Exception as e:
                got = f'<{e}>'
            if got != want: ok_all = False; bad.append((cls, expr, mode, text, got, want))
    rep(f"round trip: {len(CASES)} values × 3 notations — the printed term reads back to the same canonical form", ok_all, str(bad[:1]) if bad else '')
    P = program(r'\Q', '(1 + 2 * i) / (3 - i)')
    outs = {m: output.Printer(P, m).show(P.val('main'), P.checker.sigs['main'][0]) for m in output.MODES}
    rep("one value in the three notations:  hum 1/10 + 7/10*i,  spec (÷ 1111010 111001100),  bin (.111110. 1111010 111001100)",
        outs == {'hum': '1/10 + 7/10*i', 'spec': '(÷ 1111010 111001100)', 'bin': f"({P.doc1.s2b['÷']} 1111010 111001100)"}, str(outs))
    alpha = set('10. ()\n')
    P = program(r'List(\Q)', '[1/2, -3, 2 - i/3]')
    t = output.Printer(P, 'bin').show(P.val('main'), P.checker.sigs['main'][0])
    rep("bin output uses only the binary alphabet  1 0 . space ( )", set(t) <= alpha, t)
    P = program(r'\RR', 'sqrt(2)')
    t = output.Printer(P, 'hum', n=20).show(P.val('main'), P.checker.sigs['main'][0])
    import math
    x = Fr(math.isqrt(2 * 4 ** 20), 2 ** 20)
    rep("a stream prints its element n, with an approximation computed in the language:  " + t, t.startswith(f'{x.numerator}/{x.denominator}') and f'≈ {float(x):.12f}' in t)

    # ---- running files: text output, lines, the default notation, @out, --out
    with tempfile.TemporaryDirectory() as d:
        def run(name, text, *args):
            path = os.path.join(d, name); open(path, 'w', encoding='utf-8').write(text)
            r = subprocess.run([sys.executable, I1, path, *args], capture_output=True, text=True, timeout=600)
            return r.stdout, r.returncode
        o, _ = run('hello.hum.imo', 'main in String := "Hello, " ++ str(6 * 7) ++ "!\\n"')
        rep("main ∶ String: the text is the output (the program formats itself)", o == "Hello, 42!\n", repr(o))
        o, _ = run('lines.hum.imo', 'main in List(String) := ["a", "b" ++ "c"]')
        rep("main ∶ List(String): one line per element", o == "a\nbc\n", repr(o))
        o, _ = run('forever.hum.imo', 'main in Stream(String) := seq(k in \\NN |-> str(2 ^ k))', '--n', '5')
        rep("main ∶ Stream(String): an infinite stream of lines, cut at --n", o == "1\n2\n4\n8\n16\n", repr(o))
        val_h = 'main in \\Q := 3 / 2 - i / 2'
        o1, _ = run('v.hum.imo', val_h)
        o2, _ = run('v.imo', 'main ∶ ℚ[i]\nmain ≔ (⊟ (÷ 1101 1100) (÷ 11 1100))')
        P0 = imo.Program()
        o3, _ = run('v.bin.imo', f"{P0.doc1.s2b['main']} ... {P0.doc1.s2b['ℚ[i]']}\n{P0.doc1.s2b['main']} .. ({P0.doc1.s2b['⊟']} ({P0.doc1.s2b['÷']} 1101 1100) ({P0.doc1.s2b['÷']} 11 1100))")
        z = numeral(to_digits((3, -1)))                           # 3/2 − i/2 = (3 − i)/2
        rep("default output notation = the notation main is written in (hum → hum, spec → spec, bin → bin)",
            (o1, o2, o3) == ("3/2 - 1/2*i\n", f"(÷ {z} 1100)\n", f"({P0.doc1.s2b['÷']} {z} 1100)\n"), str((o1, o2, o3)))
        o4, _ = run('w.hum.imo', '@out spec\n' + val_h)
        o5, _ = run('w.hum.imo', '@out spec\n' + val_h, '--out', 'bin')
        rep("@out in the program overrides the default, --out on the command line overrides @out", o4 == f"(÷ {z} 1100)\n" and o5 == f"({P0.doc1.s2b['÷']} {z} 1100)\n", str((o4, o5)))
        o, rc = run('fn.hum.imo', 'f(x) in \\Q -> \\Q := x\nmain in \\Q -> \\Q := f')
        rep("a function has no normal form: running it is an error, not a guess", rc == 1 and 'no normal form' in o, o.strip())
        o, rc = run('none.hum.imo', 'x in \\Q := 1')
        rep("a program without main says so", rc == 1 and 'no main' in o, o.strip())
    return rep.done()

sys.exit(0 if run_big(main) else 1)
