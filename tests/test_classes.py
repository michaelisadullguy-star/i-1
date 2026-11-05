"""test_classes.py -- the class system (README §7): lattice, coercions, overload sets, polymorphism, human operators.

Three things are checked, through the command line (`check`) of the core under test, so that the suite runs on every core
(`--core pymo|haskimo|rustimo`):

 1. THE LATTICE.  For 137 classes (the atoms of the prelude, user classes with subclass facts, a cycle of facts, a diamond, and
    𝔏 𝔖 𝔗 𝔄 𝔓 → over them) and every pair (C, D): a program declares  a ∶ C  and  t ∶ D ; t ≔ a  and the checker accepts it iff C fits D.
    The expected answer comes from a MODEL written in this file from README §7.3–7.4 only (subclass facts, class equations, variance,
    one canonical coercion), not from any core.
 2. THE OVERLOAD SETS AND POLYMORPHISM.  Every generic or overloaded declaration of the prelude is applied to many tuples of argument
    classes (instances of its own parameter classes, sub- and superclasses, unrelated classes) inside a definition whose declared class
    can never fit, so that the message of the checker shows the class it found, or why it refused.  The messages are compared, as a
    digest, with tests/classes.golden.json, which --bless writes only if all the cores that are built print the same bytes.
 3. THE HUMAN OPERATORS (overload sets across symbols: + - * / ^ == lt and or ++ …): the same, in the human notation, and a table
    of resolutions that README §7.4 / docs/predicates.md state in words.

  python3 tests/test_classes.py                    the core under test (Pymo by default)
  python3 tests/test_classes.py --core rustimo
  python3 tests/test_classes.py --bless            run every core that is built, record the digests if they all agree
  python3 tests/test_classes.py --compare          run every core that is built and show where they differ
"""
import hashlib, json, os, random, re, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'pymo'))
import imo as _imo
_Program = _imo.Program                      # the Python Program of Pymo, before tests/harness.py puts another core's in its place
from imotypes import chain, has_var
BLESS = '--bless' in sys.argv; COMPARE = '--compare' in sys.argv
for flag in ('--bless', '--compare'):
    if flag in sys.argv: sys.argv.remove(flag)
import harness
from harness import CORE, Report

GOLDEN = os.path.join(HERE, 'classes.golden.json')


# ---------------------------------------------------------------------------------------------- running a core
def exe_of(core):
    if core == 'pymo': return [sys.executable, os.path.join(ROOT, 'pymo', 'i1.py')]
    path = os.path.join(ROOT, 'build', core)
    return [path] if os.path.isfile(path) else None

def check(core, text, tag):
    """the output of `check` on a spec or human program"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, tag)
        with open(path, 'w', encoding='utf-8') as f: f.write(text)
        p = subprocess.run(exe_of(core) + ['check', path], capture_output=True, text=True, encoding='utf-8')
    return p.stdout + p.stderr


# ---------------------------------------------------------------------------------------------- the model (README §7.3, §7.4)
PRELUDE_EQ = {'𝔇': ('𝔏', '𝔹'), '𝕊': ('𝔏', '𝕮'), 'ℝ[i]': ('𝔖', 'ℚ[i]'), 'ℝ': ('𝔖', 'ℚ'), '𝔻': ('𝔗', 'ℚ[i]'),
              'ℚ[i][x]': ('𝔏', 'ℚ[i]'), 'ℚ[i][𝐱]': ('𝔏', ('𝔓', 'ℚ[i]', ('𝔏', 'ℕ')))}
PRELUDE_FACTS = [('ℕ', 'ℤ'), ('ℤ', 'ℚ'), ('ℤ', 'ℤ[i]'), ('ℚ', 'ℚ[i]'), ('ℤ[i]', 'ℚ[i]'), ('ℝ', 'ℝ[i]'), ('𝕮', 'ℕ')]
USER_CLASSES = ['Foo', 'Bar', 'Baz', 'Qux', 'Dia', 'Cya', 'Cyb']
USER_FACTS = [('Foo', 'ℕ'), ('Bar', 'Foo'), ('Baz', 'ℚ'), ('Dia', 'ℚ'), ('Dia', 'ℤ[i]'), ('Cya', 'Cyb'), ('Cyb', 'Cya'), ('Cya', 'ℕ')]
COERCIONS = [('ℚ', 'ℝ'), ('ℚ[i]', 'ℝ[i]'), ('ℚ[i]', '𝔻'), ('ℤ[i]', 'ℤ²'), ('ℤ[i]', '𝕊²'), ('𝔹', 'ℕ'), ('𝔹', 'Ω'), ('Ω', '𝔹')]
COV = {'𝔏', '𝔖', '𝔗', '𝔓'}
FACTS = PRELUDE_FACTS + USER_FACTS

def norm(c):
    if isinstance(c, str): return norm(PRELUDE_EQ[c]) if c in PRELUDE_EQ else c
    return (c[0],) + tuple(norm(a) for a in c[1:])

def leq(a, b, seen=frozenset()):
    a, b = norm(a), norm(b)
    if a == b: return True
    if isinstance(a, tuple) and isinstance(b, tuple) and a[0] == b[0] and len(a) == len(b):
        if a[0] == '→':
            if leq(b[1], a[1]) and leq(a[2], b[2]): return True
        elif a[0] in COV:
            if all(leq(x, y) for x, y in zip(a[1:], b[1:])): return True
    if isinstance(a, str):
        for x, y in FACTS:
            if norm(x) == a and (a, y) not in seen and leq(y, b, seen | {(a, y)}): return True
    return False

def fits(c, d):
    """C fits D: it is a subclass, or one canonical coercion makes it one"""
    return leq(c, d) or any(leq(c, x) and leq(y, d) for x, y in COERCIONS)

ATOMS = ['ℕ', 'ℤ', 'ℚ', 'ℝ', 'ℤ[i]', 'ℚ[i]', 'ℝ[i]', '𝔻', '𝔹', '𝕮', '𝕊', '𝔇', '𝔒', 'Ω', 'ℤ²', '𝕊²', 'ℚ[i][x]'] + USER_CLASSES
ARGS = ['ℕ', 'ℤ', 'ℚ', 'ℤ[i]', 'ℚ[i]', 'ℝ[i]', '𝔹', '𝕮', 'Foo', 'Bar', 'Qux']
SMALL = ['ℕ', 'ℤ', 'ℚ[i]', '𝕮', 'Foo']
FUN = ['ℕ', 'ℤ', 'ℚ[i]', '𝕮', 'Foo', 'ℝ[i]']

def universe():
    U = list(ATOMS)
    for h in ('𝔏', '𝔖', '𝔗', '𝔄'): U += [(h, x) for x in ARGS]
    U += [('𝔓', x, y) for x in SMALL for y in SMALL] + [('→', x, y) for x in FUN for y in FUN]
    U += [('𝔏', ('𝔏', x)) for x in ('ℕ', 'ℤ', '𝕮')]
    U += [('𝔖', ('𝔏', 'ℕ')), ('→', ('→', 'ℕ', 'ℕ'), 'ℕ'), ('→', 'ℕ', ('→', 'ℕ', 'ℕ')), ('→', ('𝔏', 'ℕ'), ('𝔏', 'ℤ')), ('→', ('𝔏', 'ℤ'), ('𝔏', 'ℕ'))]
    out, seen = [], set()
    for c in U:
        if c not in seen: seen.add(c); out.append(c)
    return out

def spec(c): return c if isinstance(c, str) else '(' + c[0] + ' ' + ' '.join(spec(a) for a in c[1:]) + ')'

def name_of(prefix, n):                       # names without the digits 0 and 1
    s, n = '', n + 1
    while n:
        n, r = divmod(n - 1, 9); s = 'дцшщфчюяз'[r] + s
    return prefix + s


# ---------------------------------------------------------------------------------------------- 1. the lattice
def lattice(core, rep=None):
    U = universe(); idx = {c: i for i, c in enumerate(U)}
    pairs = [(c, d) for c in U for d in U]
    head = ['Foo ∶ 𝒦', 'Bar ∶ 𝒦', 'Baz ∶ 𝒦', 'Qux ∶ 𝒦', 'Dia ∶ 𝒦', 'Cya ∶ 𝒦', 'Cyb ∶ 𝒦'] + [f'(⊆ {x} {y})' for x, y in USER_FACTS]
    head += [f'{name_of("ж", i)} ∶ {spec(c)}' for i, c in enumerate(U)]
    rejected, step = set(), 4000
    for lo in range(0, len(pairs), step):
        body = []
        for k, (c, d) in enumerate(pairs[lo:lo + step]):
            t = name_of('щ', k)
            body += [f'{t} ∶ {spec(d)}', f'{t} ≔ {name_of("ж", idx[c])}']
        out = check(core, '\n'.join(head + body) + '\n', 'lattice.spec.imo')
        bad = {m.group(1) for m in re.finditer(r'^error in [^:]+: (щ[дцшщфчюяз]+):', out, re.M)}
        rejected |= {lo + k for k in range(len(pairs[lo:lo + step])) if name_of('щ', k) in bad}
    want = {k for k, (c, d) in enumerate(pairs) if not fits(c, d)}
    return len(U), len(pairs), rejected, want, pairs


# ---------------------------------------------------------------------------------------------- 2. overload sets and polymorphism
POOL = ['ℕ', 'ℤ', 'ℚ', 'ℤ[i]', 'ℚ[i]', 'ℝ', 'ℝ[i]', '𝔻', '𝔹', '𝕮', '𝕊', '(𝔏 ℕ)', '(𝔏 ℤ)', '(𝔏 ℚ[i])', '(𝔖 ℚ[i])', '(𝔗 ℚ[i])', 'Ω']
INST = {'α': ['ℕ', '𝕮', 'ℚ[i]', '𝕊', '(𝔏 ℕ)', '𝔹'], 'β': ['ℤ', '𝔹', 'ℚ', '(𝔖 ℕ)'], 'γ': ['ℕ', 'ℚ[i]', '𝕊'], 'δ': ['ℕ', 'ℚ[i]'], 'ε': ['ℕ', 'ℚ[i]']}
BINDERS = ['ξ', 'η', 'ζ', 'θ', 'ι', 'κ′', 'μ', 'ν', 'ο', 'π′', 'ρ′']

def prefix_class(t):
    if t[0] == 'V': return t[1]
    if t[0] == 'F': return 'ℕ'
    return t[1] if not t[2] else '(' + t[1] + ' ' + ' '.join(prefix_class(a) for a in t[2]) + ')'

def instances(t, rng, tries=3):
    def sub(u):
        if u[0] == 'V': return ('K', rng.choice(INST.get(u[1], ['ℕ', 'ℚ[i]'])), ())
        if u[0] == 'K': return ('K', u[1], tuple(sub(a) for a in u[2]))
        return u
    return [prefix_class(sub(t)) for _ in range(tries)]

def overload_programs():
    P = _Program()
    for f in _imo.PRELUDE: P.add_file(f, trusted=True)
    P.check(collect=True)
    rng = random.Random(7)
    decls = [(n, chain(t)[0]) for n, ts in sorted(P.checker.sigs.items()) if any(has_var(t) for t in ts) or len(ts) >= 2 for t in ts]
    decls = [(n, ps) for n, ps in decls if 1 <= len(ps) <= 10]
    probes, k = [], 0
    for name, ps in decls:
        n = len(ps); cand = [list(POOL) + instances(p, rng) for p in ps]
        if n == 1: tuples = [(a,) for a in cand[0]]
        elif n == 2: tuples = [(a, b) for a in cand[0] for b in cand[1]]
        else:
            tuples = [tuple(rng.choice(c) for c in cand) for _ in range(400 if n == 3 else 200)]
            tuples += [tuple(instances(p, rng, 1)[0] for p in ps) for _ in range(6)]
        for tup in dict.fromkeys(tuples):
            k += 1
            nm = name_of('щ', k)
            sig = f'(→ {tup[-1]} Probe)'
            for c in reversed(tup[:-1]): sig = f'(→ {c} {sig})'
            probes.append(f'{nm} ∶ {sig}\n{nm} {" ".join(BINDERS[:n])} ≔ ({name} {" ".join(BINDERS[:n])})')
    progs = []
    for lo in range(0, len(probes), 10000):
        progs.append('Probe ∶ 𝒦\n' + '\n'.join(probes[lo:lo + 10000]) + '\n')
    return progs, len(probes)

def overloads(core, programs):
    msgs = {}
    for i, text in enumerate(programs):
        out = check(core, text, 'overloads.spec.imo')
        for m in re.finditer(r'^error in [^:]+: (щ\S+?): (.*)$', out, re.M): msgs[m.group(1)] = m.group(2)
        for ln in out.splitlines():
            if not ln.startswith(('error in', 'ok:')): msgs.setdefault('#other:' + ln[:80], ln)
    return msgs


# ---------------------------------------------------------------------------------------------- 3. the human operators
HPOOL = {'ℕ': r'\NN', 'ℤ': r'\ZZ', 'ℚ': r'\QQ', 'ℤ[i]': r'\Z', 'ℚ[i]': r'\Q', 'ℝ': r'\RR', 'ℝ[i]': r'\R', '𝔻': r'\D', '𝔹': 'Bool', '𝕮': 'Char',
         '𝕊': 'String', '𝔏ℕ': r'List(\NN)', '𝔏ℚ[i]': r'List(\Q)', '𝔏𝔏ℚ[i]': r'List(List(\Q))', '𝔖ℚ[i]': r'Stream(\Q)', '𝔓': r'Pair(\NN, \NN)',
         'ℚ[i]→𝔹': r'(\Q -> Bool)', 'ℚ[i]→ℚ[i]': r'(\Q -> \Q)'}
HBIN = ['+', '-', '*', '/', '^', '==', '!=', 'lt', 'leq', 'gt', 'geq', 'and', 'or', '++', 'div', 'mod', 'implies', 'iff']

def pname(k): return re.sub(r'\d', lambda m: 'abcdefghij'[int(m.group())], f'q{k}')

def human_program():
    lines, probes, k = [], [], 0
    for op in HBIN:
        for a in HPOOL:
            for b in HPOOL:
                k += 1; lines.append(f'{pname(k)}(x, y) in {HPOOL[a]} -> {HPOOL[b]} -> Char := x {op} y'); probes.append((pname(k), op, a, b))
    for op in ('-', 'not'):
        for a in HPOOL:
            k += 1; lines.append(f'{pname(k)}(x) in {HPOOL[a]} -> Char := {op if op == "-" else "not"} x'); probes.append((pname(k), 'u' + op, a, ''))
    return '\n'.join(lines) + '\n', probes

def human(core, text):
    out = check(core, text, 'human.hum.imo')
    return {m.group(1): m.group(2) for m in re.finditer(r'^error in [^:]+: (q[a-j]+): (.*)$', out, re.M)}

# what README §7.4 and docs/predicates.md say in words: (operator, class of x, class of y) -> the class of the result
EXPECT = [('+', 'ℕ', 'ℕ', 'ℕ'), ('+', 'ℕ', 'ℤ', 'ℤ'), ('+', 'ℤ', 'ℚ', 'ℚ'), ('+', 'ℤ[i]', 'ℚ', 'ℚ[i]'), ('+', 'ℤ', 'ℤ[i]', 'ℤ[i]'),
          ('+', 'ℚ[i]', 'ℚ[i]', 'ℚ[i]'), ('+', 'ℕ', 'ℝ', '(𝔖 ℚ)'), ('+', 'ℚ[i]', 'ℝ[i]', '(𝔖 ℚ[i])'), ('+', 'ℝ', 'ℝ[i]', '(𝔖 ℚ[i])'),
          ('+', '𝔻', '𝔻', '(𝔗 ℚ[i])'), ('+', 'ℚ[i]', '𝔻', '(𝔗 ℚ[i])'), ('+', '𝔻', 'ℚ', '(𝔗 ℚ[i])'),
          ('+', '𝔹', '𝔹', '𝔹'), ('+', '𝔹', 'ℕ', 'ℕ'), ('*', 'ℕ', 'ℤ', 'ℤ'), ('*', '𝔹', '𝔹', '𝔹'), ('*', 'ℤ', 'ℚ', 'ℚ'),
          ('-', 'ℕ', 'ℕ', 'ℤ'), ('-', 'ℤ[i]', 'ℤ[i]', 'ℤ[i]'), ('/', 'ℤ', 'ℤ', 'ℚ'), ('/', 'ℚ[i]', 'ℚ[i]', 'ℚ[i]'),
          ('==', 'ℕ', 'ℕ', '𝔹'), ('==', 'ℚ[i]', 'ℚ[i]', '𝔹'), ('==', 'ℕ', 'ℝ', 'Ω'), ('lt', 'ℕ', 'ℕ', '𝔹'), ('lt', 'ℕ', 'ℝ', 'Ω'), ('lt', 'ℚ', 'ℚ', '𝔹'),
          ('and', '𝔹', '𝔹', '𝔹'), ('or', '𝔹', '𝔹', '𝔹'), ('++', '𝕊', '𝕊', '(𝔏 𝕮)'), ('++', '𝔏ℕ', '𝔏ℕ', '(𝔏 ℕ)'), ('^', 'ℕ', 'ℕ', 'ℕ'), ('^', 'ℕ', 'ℤ', 'ℚ'),
          ('div', 'ℤ', 'ℤ', 'ℤ'), ('mod', 'ℕ', 'ℕ', 'ℕ')]
REFUSED = [('+', 'ℕ', '𝕊'), ('+', 'ℕ', '𝔏ℕ'), ('==', 'ℕ', '𝕊'), ('++', 'ℕ', 'ℕ'), ('lt', '𝔻', '𝔻'), ('-', '𝕊', '𝕊'), ('*', 'ℚ[i]→ℚ[i]', 'ℕ')]

def digest(msgs):
    h = hashlib.sha256()
    for k in sorted(msgs): h.update(f'{k}\t{msgs[k]}\n'.encode('utf-8'))
    return h.hexdigest()

def measure(core, programs, nprobes, hum_text):
    """everything one core says, as the data the golden file keeps"""
    ov = overloads(core, programs); hm = human(core, hum_text)
    return {'overload probes': nprobes, 'overload messages': len(ov), 'overload digest': digest(ov),
            'human messages': len(hm), 'human digest': digest(hm)}, ov, hm


def main():
    t0 = time.time()
    programs, nprobes = overload_programs(); hum_text, hprobes = human_program()
    if BLESS or COMPARE:
        cores = [c for c in ('pymo', 'haskimo', 'rustimo') if exe_of(c)]
        res = {c: measure(c, programs, nprobes, hum_text) for c in cores}
        base = cores[0]; same = True
        for c in cores[1:]:
            for what, i in (('overload', 1), ('human', 2)):
                a, b = res[base][i], res[c][i]
                diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
                if diff:
                    same = False; print(f'{base} and {c} differ on {len(diff)} {what} probes, e.g.')
                    for k in diff[:5]: print('   ', k, '\n      ', base, a.get(k), '\n      ', c, b.get(k))
        print(f"cores compared: {', '.join(cores)}: {'identical' if same else 'DIFFERENT'}")
        if BLESS:
            if not same: print('not recorded'); return False
            json.dump(res[base][0], open(GOLDEN, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
            print('recorded', os.path.relpath(GOLDEN, ROOT))
        return same
    rep = Report()
    nU, nP, rejected, want, pairs = lattice(CORE)
    extra, missing = rejected - want, want - rejected
    rep(f"the lattice: {nP} pairs of {nU} classes — the checker accepts exactly the pairs that fit (subclass facts, equations, variance, one coercion)", not extra and not missing,
        f"(refused but fit: {[spec(pairs[k][0]) + ' → ' + spec(pairs[k][1]) for k in sorted(extra)[:4]]}; accepted but do not fit: {[spec(pairs[k][0]) + ' → ' + spec(pairs[k][1]) for k in sorted(missing)[:4]]})" if extra or missing else '')
    got, ov, hm = measure(CORE, programs, nprobes, hum_text)
    gold = json.load(open(GOLDEN, encoding='utf-8')) if os.path.exists(GOLDEN) else {}
    rep(f"overload sets and polymorphism: {nprobes} probes — the messages are the ones all the cores printed", gold.get('overload digest') == got['overload digest'],
        f"(golden {gold.get('overload probes')} probes, now {nprobes}; run --compare, then --bless if the library grew)" if gold.get('overload digest') != got['overload digest'] else '')
    rep(f"human operators: {len(hprobes)} probes — the messages are the ones all the cores printed", gold.get('human digest') == got['human digest'])
    rep("no probe is ambiguous: no overload set of the prelude is ambiguous on the classes of the pool", not any('ambiguous' in m for m in list(ov.values()) + list(hm.values())))
    rep("no probe crashed the checker (every message is a message of the checker)", not any(k.startswith('#other') for k in ov) and not any('Traceback' in m for m in list(ov.values()) + list(hm.values())))
    table = {(p[1], p[2], p[3]): hm.get(p[0]) for p in hprobes}
    bad = []
    for op, a, b, res_ in EXPECT:
        m = table.get((op, a, b)); w = f'the body has class {res_} but 𝕮 was declared'
        if m != w: bad.append((op, a, b, res_, m))
    rep(f"README §7.4 in words: {len(EXPECT)} resolutions of human operators give the class that the text says", not bad, str(bad[:3]))
    bad = [(op, a, b, table.get((op, a, b))) for op, a, b in REFUSED if not (table.get((op, a, b)) or '').startswith('no declaration')]
    rep(f"{len(REFUSED)} combinations that make no sense are refused (no declaration accepts them)", not bad, str(bad[:3]))
    print(f"\n(wall {time.time() - t0:.0f}s)")
    return rep.done()


sys.exit(0 if main() else 1)
