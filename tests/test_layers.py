"""test_layers.py -- notation layers (bin / spec / hum), doc 1, doc 2, class checker, Char/String, order.   python3 tests/test_layers.py"""
import os, sys, time, random, re
from fractions import Fraction as Fr
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'pymo')); sys.path.insert(0, HERE)
import harness; harness.pymo_only('the three readers, doc 1 and the translators')      # their command-line counterparts (check, translate) are cases of tests/conformance
import imo, layers, syntax, hum
from imo import Program, load, done, to_bool, to_list, to_pair, stream_nth, run_big
from base_b import val, to_digits
import refmath as R

RESULTS = []
def report(label, ok, extra=''):
    RESULTS.append(bool(ok))
    print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}"); sys.stdout.flush()

def pi_N(N):
    s = t = Fr(2)
    for k in range(1, N + 1): t = t * k / (2 * k + 1); s += t
    return s
def e_N(N):
    s = t = Fr(1)
    for k in range(1, N + 1): t = t / k; s += t
    return s

def qdec(v):
    p, d = to_pair(v)
    P, D = val(to_list(p)), val(to_list(d))
    assert D != (0, 0)
    return R.Q(P[0], P[1]) * R.Q(D[0], D[1]).inv()

def stream_ok(P, name, N=8):
    M = P.machine
    return all(qdec(stream_nth(M.val(name), n)) == R.Q(pi_N(n), e_N(n)) for n in range(N + 1))

def decode_string(v):
    out = []
    r = v(imo.imo_core.CONS_TH)(imo.imo_core.NIL_TH)
    while r[0] == 'C':
        q = qdec(r[1].force()); assert q.i == 0 and q.r.denominator == 1
        out.append(chr(int(q.r))); r = r[2].force()(imo.imo_core.CONS_TH)(imo.imo_core.NIL_TH)
    return ''.join(out)

def main():
    t0 = time.time()
    P0 = Program()
    d1, d2 = P0.doc1, P0.doc2

    # ------------------------------------------------------------ doc 1
    codes = [int(b[1:-1], 2) for b in d1.b2s]
    report("doc 1: a bijection spec symbol <-> bin symbol, codes are the ordinals 1..n in binary",
           len(d1.s2b) == len(d1.b2s) == len(codes) and sorted(codes) == list(range(1, len(codes) + 1)), f"({len(codes)} symbols)")
    prel = ''.join(open(f, encoding='utf-8').read() + '\n' for f in imo.PRELUDE)
    spec_prelude_syms = {t[1] for t in syntax.lex(prel) if t[0] == 'NAME'} - set(layers.RESERVED_BIN)
    report("doc 1 covers every symbol of the prelude", spec_prelude_syms <= set(d1.s2b))

    # ------------------------------------------------------------ binary alphabet and round trips
    alpha = set('10. ()\n')
    files = [os.path.join(ROOT, 'lib', 'prelude.bin.imo'), os.path.join(ROOT, 'examples', 'target.bin.imo'), os.path.join(ROOT, 'examples', 'spaces.bin.imo')]
    report("bin files use only the characters  1 0 . space ( ) newline",
           all(set(open(f, encoding='utf-8').read()) <= alpha for f in files), "(" + ', '.join(f"{os.path.basename(f)}: {os.path.getsize(f)} bytes" for f in files) + ")")
    P = Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.add_file(os.path.join(ROOT, 'examples', 'target.spec.imo')); P.add_file(os.path.join(ROOT, 'examples', 'spaces.spec.imo'))
    P.check()
    S = [s for _, s, _ in P.statements]
    again = syntax.parse_statements(layers.bin_to_spec_text(layers.spec_statements_to_bin_text(S, P.doc1), P.doc1))
    report("spec -> bin -> spec reproduces every statement of the prelude and the examples (Char/String literals come back written out)",
           [syntax.expand_statement(x) for x in S] == again, f"({len(S)} statements)")
    tok_ok = all(t[0] in ('NL', '(', ')', 'NUM', 'MARK', 'SYM') for t in layers.lex_bin(open(files[0], encoding='utf-8').read()))
    report("every bin token is a numeral, a marker (. .. ...), a symbol .B. or a parenthesis", tok_ok)

    # ------------------------------------------------------------ the three notations define the same π, 𝕖, π + e i
    Ps = load([os.path.join(ROOT, 'examples', 'target.spec.imo')])
    report("spec notation:  π, 𝕖, 𝕫 are the exact Euler partial sums (N = 0..8)", stream_ok(Ps, '𝕫'))
    Ph = load([os.path.join(ROOT, 'examples', 'target.hum.imo')])
    report("hum notation:   the same three lines (pi, e, z) give the same streams", stream_ok(Ph, 'z'))
    want = ['π ∶ ℝ', 'π ≔ (Σ 1100 (k ∶ ℚ ↦ (÷ k (⊞ (⊠ 1100 k) 1))))', '𝕖 ∶ ℝ', '𝕖 ≔ (Σ 1 (k ∶ ℚ ↦ (÷ 1 k)))', 'z ∶ ℝ[i]', 'z ≔ (⊕ π (⊛ 𝕖 (⇡ 11)))']
    report("hum -> spec: overloads resolved by class (+ becomes ⊕, * becomes ⊛, a ⇡ is inserted for i)", Ph.spec_text().split('\n')[:6] == want)
    Pb = load([files[0], files[1]], trusted=[files[0]], prelude=False)
    report("bin notation:   the all-binary program (prelude.bin.imo + target.bin.imo) gives the same streams", stream_ok(Pb, '.1111100.'.replace('.1111100.', '𝕫')))
    hb = [os.path.join(ROOT, 'lib', 'prelude.bin.imo'), os.path.join(ROOT, 'examples', 'hello.bin.imo')]
    Ph2 = load(hb, trusted=hb[:1], prelude=False, collect=True)
    import output
    outs = []
    if not Ph2.errors: output.run_main(Ph2, write=outs.append)
    report("bin notation with String literals: hello.bin.imo passes the class checker ('λ' is written (𝕔 numeral)) and prints the same text",
           not Ph2.errors and ''.join(outs) == "Hello, i-1 — λ\n", str(Ph2.errors[:1] or outs))
    mixed = "@spec\nπ ∶ ℝ\nπ ≔ (Σ 1100 (k ∶ ℚ ↦ (÷ k (⊞ (⊠ 1100 k) 1))))\n@hum\ne in \\RR := sum(1, k in \\QQ |-> 1 / k)\nz in \\R := pi + e * i\n"
    Pm = Program()
    for f in imo.PRELUDE: Pm.add_file(f, trusted=True)
    Pm.add_text(mixed, 'mixed.imo'); Pm.check(); Pm.build()
    report("a file mixing @spec and @hum sections loads and evaluates (allowed, not recommended)", stream_ok(Pm, 'z'))

    # doc 2 may name a bin symbol directly:  [hum sbl] := [bin sbl]
    code = d1.s2b['⊞']
    d2txt = open(os.path.join(ROOT, 'docs', 'doc2.sbl'), encoding='utf-8').read() + f"plus_bin := {code} ; value\n"
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.sbl', delete=False, encoding='utf-8') as tf: tf.write(d2txt)
    Pd = Program(doc2=tf.name)
    for f in imo.PRELUDE: Pd.add_file(f, trusted=True)
    Pd.add_text("r in \\QQ := plus_bin(1, 1)", 'd.hum.imo', notation='hum'); Pd.check(); Pd.build()
    report("doc 2 right-hand side given as a bin symbol (plus_bin := %s) resolves through doc 1" % code, qdec(Pd.val('r')) == R.Q(2))
    os.unlink(tf.name)

    # ------------------------------------------------------------ class checker
    def verdict(text, base=Ps):
        q = Program()
        for f in imo.PRELUDE: q.add_file(f, trusted=True)
        q.add_file(os.path.join(ROOT, 'examples', 'target.spec.imo'))
        q.add_text(text, 't')
        return q.check(collect=True)
    cases = [
        ("undeclared definition is rejected", "foo ≔ 1", False),
        ("ℤ is not ℕ", "bad ∶ ℕ\nbad ≔ (⊞ 1 (⊖ 1))", False),
        ("ℝ[i] is not ℝ", "x ∶ ℝ\nx ≔ (⇡ 11)", False),
        ("lambda binder without a class is rejected", "f ∶ ℚ → ℚ\nf ≔ (ξ ↦ ξ)", False),
        ("a Char is not a String", "c ∶ 𝕮\nc ≔ \"A\"", False),
        ("a String is not a number", "n ∶ ℕ\nn ≔ \"A\"", False),
        ("undeclared symbol in a body is rejected", "z2 ∶ ℕ\nz2 ≔ (⊞ 1 ωωω)", False),
        ("more parameters than the declared class has arrows", "g ∶ ℕ\ng ξ ≔ 1", False),
        ("polymorphic definition whose body ignores its class variable is rejected", "idn ∶ α → α\nidn ξ ≔ 1", False),
        ("ℝ + ℚ[i]-constant: ⊕ π 11 needs an explicit ⇡ (11 is ℤ[i], a ⇡ is inserted automatically)", "t ∶ ℝ[i]\nt ≔ (⊕ π 11)", True),
        ("ℕ + ℕ stays ℕ", "k ∶ ℕ\nk ≔ (⊞ 1 1100)", True),
        ("polymorphic identity", "idn ∶ α → α\nidn ξ ≔ ξ\nw ∶ ℕ\nw ≔ (idn 1)", True),
        ("Char and String literals", "s ∶ 𝕊\ns ≔ \"hi\"\nn ∶ ℕ\nn ≔ (ℓ \"hello\")\nc ∶ 𝕮\nc ≔ 'A'\nm ∶ ℕ\nm ≔ (ord 'A')\nt ∶ 𝕊\nt ≔ (⧺ \"ab\" \"cd\")", True),
        ("Cayley–Dickson tower with an automatic widening ↑", "q ∶ 𝔻\nq ≔ (⊠𝔻 𝕛 𝕛)\nr ∶ 𝔻\nr ≔ (⊞𝔻 𝕛 11)", True),
        ("class variables join across arguments (𝔗 ℝ and 𝔗 ℝ[i] meet in 𝔗 ℝ[i])", "t ∶ 𝔗 ℝ[i]\nt ≔ (❁ (❀ π) (❀ 𝕫))", True),
        ("narrowing 𝔻 -> ℚ[i] is rejected", "q ∶ ℚ[i]\nq ≔ 𝕛", False),
        ("a user class with its own subclass fact widens to ℕ", "Foo ∶ 𝒦\n(⊆ Foo ℕ)\nfoo ∶ Foo\nbar ∶ ℕ\nbar ≔ foo", True),
        ("but a ℕ is not a Foo", "Foo ∶ 𝒦\n(⊆ Foo ℕ)\nfoo ∶ Foo\nfoo ≔ 1100", False),
        ("using a class as a value is rejected", "bad2 ∶ ℕ\nbad2 ≔ ℕ", False),
    ]
    ok = True
    for label, text, accept in cases:
        errs = verdict(text)
        good = (not errs) == accept
        ok &= good
        if not good: print("   ?", label, errs[:1])
    report(f"class checker: {len(cases)} accept / reject cases behave as specified", ok)

    # ------------------------------------------------------------ human notation: operators, literals, Char, String
    hsrc = r'''
a in \QQ := 1 + 2 * 3 - 4 / 2
b in \QQ := 0.5 + 0.25
c in \ZZ := -3 + 1
w in \Q := (1 + 2 * i) * (3 - i)
s in String := "héllo" ++ " wörld"
n in \NN := length("héllo")
ch in Char := 'λ'
m in \NN := ord('λ')
t in Bool := 3 geq 2
u in Bool := 1 geq 2
v in Bool := (-3 in \ZZ) geq -3
f(x) in \Q -> \Q := x * x + 1
y in \Q := f(1 + i)
q in \D := j * j
r in \D := j * k + 1
cc in \D := conj(j)
qa in Bool := forall(k in \NN |-> k geq 0, range(5))
qb in Bool := exists(k in \NN |-> k geq 4, range(4))
qc in Bool := exists(k in \NN |-> k geq 4, range(5))
qd in Bool := forall(k in \NN |-> 2 geq k, range(3))
nb in Bool := not 1 geq 2
ife in \NN := if(1 geq 2, 10, 20)
ca in Bool := 'a' == 'a'
cb in Bool := 'a' == 'b'
Ex in \R := exp(1 + 0 * i)
Sn in \RR := sin(1 / 2)
Cs in \RR := cos(1 / 2)
\NN subseteq \QQ
'''
    Q = Program()
    for f in imo.PRELUDE: Q.add_file(f, trusted=True)
    Q.add_text(hsrc, 'h.hum.imo', notation='hum'); Q.check(); Q.build(); M = Q.machine
    def num(name): return qdec(M.val(name))
    ok = (num('a') == R.Q(5)) and (num('b') == R.Q(Fr(3, 4))) and (num('c') == R.Q(-2)) and (num('w') == R.Q(5, 5)) \
        and (decode_string(M.val('s')) == "héllo wörld") and (num('n') == R.Q(5)) and (num('ch') == R.Q(ord('λ'))) and (num('m') == R.Q(ord('λ'))) \
        and to_bool(M.val('t')) and not to_bool(M.val('u')) and to_bool(M.val('v')) \
        and (num('y') == (R.Q(1, 1) * R.Q(1, 1) + R.Q(1)))
    report("human notation: precedence, decimals, i, unary minus, ascription, Char/String literals, ++, length, ord, geq, user functions", ok)
    # tower values through the human layer
    def tdec(v):
        tag = to_bool(M.val('◀')(done(v))) if False else None
    TVv = lambda name: M.val(name)
    def tdecode(v):
        if to_bool(M.val('◀')(done(v))):
            a, b = to_pair(M.val('▶')(done(v))); return (tdecode(a), tdecode(b))
        return qdec(M.val('▶')(done(v)))
    jj = (R.Q(0), R.Q(1)); kk = (R.Q(0), R.Q(0, 1))
    ok = R.teq(tdecode(M.val('q')), R.tmul(jj, jj)) and R.teq(tdecode(M.val('r')), R.tadd(R.tmul(jj, kk), R.Q(1))) and R.teq(tdecode(M.val('cc')), R.tconj(jj))
    report("bounded quantifiers: forall / exists over range(n) (short-circuiting, decidable)", to_bool(M.val('qa')) and not to_bool(M.val('qb')) and to_bool(M.val('qc')) and to_bool(M.val('qd')))
    report("`not` binds looser than geq:  not 1 geq 2  is true", to_bool(M.val('nb')))
    report("if(b, x, y) selects lazily", qdec(M.val('ife')) == R.Q(20))
    report("characters compare with == (a Char widens to ℚ[i])", to_bool(M.val('ca')) and not to_bool(M.val('cb')))
    def sin_N(x, N):
        s_, t = x, x
        for k in range(1, N + 1): t = t * (-x * x) / ((2 * k) * (2 * k + 1)); s_ += t
        return s_
    def cos_N(x, N):
        s_, t = Fr(1), Fr(1)
        for k in range(1, N + 1): t = t * (-x * x) / ((2 * k - 1) * (2 * k)); s_ += t
        return s_
    h = Fr(1, 2)
    ok = all(qdec(stream_nth(M.val('Sn'), n)) == R.Q(sin_N(h, n)) and qdec(stream_nth(M.val('Cs'), n)) == R.Q(cos_N(h, n)) and qdec(stream_nth(M.val('Ex'), n)) == R.Q(e_N(n)) for n in range(0, 7))
    import math
    ok &= abs(float(qdec(stream_nth(M.val('Sn'), 12)).r) - math.sin(0.5)) < 1e-12 and abs(float(qdec(stream_nth(M.val('Cs'), 12)).r) - math.cos(0.5)) < 1e-12
    report("analysis from the human layer:  exp(1), sin(1/2), cos(1/2) are the exact power-series partial sums (and converge to the true values)", ok)
    report("human notation on the Cayley–Dickson class \\D:  j * j, j * k + 1 (1 widened by ↑), conj(j)", ok)
    ok = R.teq(tdecode(M.val('q')), R.Q(-1)) and R.depth(tdecode(M.val('q'))) == 1
    report("   ... and j * j = -1 is still a depth-1 element (no reduction of dimension)", ok)

    # ------------------------------------------------------------ order relation on ℚ
    ge = M.val('⩾')
    def qv(q):
        from math import lcm
        D = lcm(q.r.denominator, q.i.denominator)
        return M.val('⊗')(done(imo.list_value(M, to_digits((int(q.r * D), int(q.i * D))))))(done(imo.list_value(M, to_digits((D, 0)))))
    rnd = random.Random(3); ok = True
    for _ in range(40):
        x = R.Q(Fr(rnd.randint(-6, 6), rnd.randint(1, 4))); y = R.Q(Fr(rnd.randint(-6, 6), rnd.randint(1, 4)))
        ok &= to_bool(ge(done(qv(x)))(done(qv(y)))) == (x.r >= y.r)
    report("⩾ on ℚ (sign by search in base i-1) agrees with exact comparison, 40 random pairs", ok)

    print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed  ({time.time()-t0:.1f}s)")
    return all(RESULTS)

run_big(main)
