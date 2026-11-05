"""
mkconformance.py -- writes the LIBRARY SWEEP of the conformance suite (tests/conformance/programs/lib/*.hum.imo).

A type-directed generator: for every function of the standard library that has a human name (doc 2, role `value`) and a signature made
of classes it can write literals for (ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] 𝔹 𝕊 𝕮, lists, lists of lists and pairs of these), it writes a one-line
program

    main in <class of the call> := name(sample arguments)

(the class is the one the Python class checker assigns to the call, written in human notation).  The programs are then run by both
interpreters (tests/conformance/run.py): the sweep puts every corner of the library, and every shape of value the printer knows, through
both of them.  The generated files are kept in the repository; running this script again rewrites them, and  --cases  writes the list
of all the cases of the suite (tests/conformance/cases.txt) from the files that are there.

  python3 pymo/mkconformance.py [--variants N] [--limit K] [--only NAME]     write the sweep programs
  python3 pymo/mkconformance.py --cases                                      (re)write tests/conformance/cases.txt from the programs
"""
import zlib, argparse, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import imo, hum
from imotypes import ImoTypeError, chain, has_var, K

CONF = os.path.join(ROOT, 'tests', 'conformance')
OUT = os.path.join(CONF, 'programs', 'lib')
# sweep programs that take Pymo more than about 20 s (the library claims them correct, the conformance suite does not wait for them)
SLOW_LIB = {'algroot.1', 'altgroup.1', 'cyclotomicfactors.1', 'eigenvals.1', 'eigenvals.2', 'ellipe.2', 'fpfactor.1', 'gf.1', 'gfgalois.1', 'gfgalois.2',
            'gramschmidt.1', 'irreduciblepoly.1', 'lstsq.1', 'lstsq.2', 'matexp.1', 'mpow.1', 'mpow.2', 'pinv.1', 'pinv.2', 'polycrt.1', 'polycrt.2',
            'polypowmod.3', 'primitivepoly.1', 'qrpow.2', 'symgroup.1', 'tan.3', 'tanh.3', 'zeta.2'}
# cases that take Pymo more than about 15 s
SLOW_CASES = {'ex.run.decode.hum.imo', 'ex.run.main.hum.imo'}
# the documented eval commands (README §2, §15)
EVALS = [('target.hum.imo', 'pi', 14), ('target.hum.imo', 'e', 14), ('target.hum.imo', 'z', 14), ('analysis.hum.imo', 'euler', 14),
         ('quaternion.hum.imo', 'q1', None), ('quaternion.hum.imo', 'q2', None), ('quaternion.hum.imo', 'q3', None), ('quaternion.hum.imo', 'q4', None),
         ('sedenion.hum.imo', 'x', None), ('sedenion.hum.imo', 'y', None),
         ('spaces.hum.imo', 'ip', 6), ('spaces.hum.imo', 'norm2', 6), ('hello.hum.imo', 'greeting', None), ('hello.bin.imo', 'main', None),
         ('main.hum.imo', 'x', None), ('main.hum.imo', 'pi', 20), ('norm.hum.imo', 'v', None), ('predicates.hum.imo', 'x', None)]

# literals by spec class: several values per class (a list literal uses consecutive ones, a variant starts further on)
POOL = {
    'ℕ': ['12', '5', '7', '3', '9', '2'],
    'ℤ': ['-7', '4', '9', '-2', '6', '-3'],
    'ℚ': ['3/4', '-5/2', '7/3', '1/6', '2', '-1/3'],
    'ℤ[i]': ['2 + 3*i', '1 - i', '-4 + i', '3', '2*i', '1 + i'],
    'ℚ[i]': ['1/2 + 3/4*i', '2 - 1/3*i', '3/5', '-2*i', '1 + i', '1/7'],
    'ℝ': ['sqrt(2)', 'sqrt(3)', '1/3'],
    'ℝ[i]': ['1 + sqrt(2)*i', '1/2', 'sqrt(2)'],
    '𝔹': ['true', 'false', 'true', 'false'],
    '𝕊': ['"abc"', '"xy"', '"Hello"', '"i-1"'],
    '𝕮': ["'a'", "'z'", "'Q'", "'7'"],
}
SKIP = {'iterate', 'seq', 'forall', 'exists', 'sum', 'sumof', 'prodof', 'if', 'delta', 'iverson', 'prop', 'decide', 'embed', 'ord', 'chr',
        'derive', 'integral', 'setof', 'cons', 'nil', 'true', 'false', 'i', 'j', 'k', 'e', 'pi', 'alpha', 'beta', 'gamma'}   # higher-order, literals, or defined by the examples
PRINTABLE = {'ℕ', 'ℤ', 'ℚ', 'ℤ[i]', 'ℚ[i]', 'ℝ', 'ℝ[i]', '𝔹', '𝕮', '𝕊', '𝔏', '𝔓', '𝔒', '𝔖', '𝔇'}

def sample(C, ty, v, depth=0):
    """a literal (human text) of class ty, variant v; None when there is none"""
    ty = C.norm(ty)
    if ty[0] != 'K': return None
    name, args = ty[1], ty[2]
    if not args and name in POOL: return POOL[name][v % len(POOL[name])]
    if name == '𝔏' and depth < 2:
        els = [sample(C, args[0], v + k, depth + 1) for k in range(3)]
        return None if any(e is None for e in els) else '[' + ', '.join(els) + ']'
    if name == '𝔓':
        a, b = sample(C, args[0], v, depth + 1), sample(C, args[1], v + 1, depth + 1)
        return None if a is None or b is None else f'pair({a}, {b})'
    return None

def printable(C, ty):
    ty = C.norm(ty)
    return ty[0] == 'K' and ty[1] in PRINTABLE and all(printable(C, a) for a in ty[2])

def hum_class(P, ty):
    """a class in human notation (reverse doc 2)"""
    rev = {}
    for e in P.doc2.entries:
        if e['role'] == 'class': rev.setdefault(e['rhs'][0], e['hum'])
    def go(t):
        if t[0] != 'K': raise KeyError(t)
        name, args = t[1], t[2]
        if name == '→': raise KeyError(name)
        h = rev[name]
        return h if not args else h + '(' + ', '.join(go(a) for a in args) + ')'
    return go(P.checker.norm(ty))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variants', type=int, default=2)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--only')
    ap.add_argument('--cases', action='store_true', help='write tests/conformance/cases.txt')
    a = ap.parse_args()
    P = imo.Program()
    for f in imo.PRELUDE: P.add_file(f, trusted=True)
    P.check()
    C = P.checker
    if a.cases: return write_cases()
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.hum.imo'): os.remove(os.path.join(OUT, f))
    seen, n, counts = set(), 0, {}
    for e in P.doc2.entries:
        h = e['hum']
        if e['role'] != 'value' or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', h) or h in SKIP: continue
        if a.only and h != a.only: continue
        for sym in e['rhs']:
            if sym not in C.sigs: continue
            for sig in C.sigs[sym]:
                ps, r = chain(sig)
                if has_var(sig) or not ps or not printable(C, r): continue
                for v in range(a.variants):
                    args = [sample(C, p, v + 2 * k) for k, p in enumerate(ps)]
                    if any(x is None for x in args): continue
                    expr = f"{h}({', '.join(args)})"
                    try:
                        ts = hum.lex_hum(expr)
                        term, j = P.hum.expr(ts, 0, 0, set())
                        assert j == len(ts)
                        cls, _ = C.synth(term, {})
                        if not printable(C, cls): continue
                        text = f"main in {hum_class(P, cls)} := {expr}\n"
                    except (ImoTypeError, KeyError, AssertionError, SyntaxError, IndexError):
                        continue
                    if text in seen: continue
                    seen.add(text)
                    n += 1
                    counts[h] = counts.get(h, 0) + 1; k = counts[h]       # numbered before the slow ones are left out, so the names are stable
                    if f'{h}.{k}' in SLOW_LIB: continue
                    with open(os.path.join(OUT, f'{h}.{k}.hum.imo'), 'w', encoding='utf-8') as f:
                        f.write(text)
                    if a.limit and n >= a.limit: print(n, 'programs'); return
    print(n, 'programs written to', os.path.relpath(OUT, ROOT))

def write_cases():
    """cases.txt: the examples (every command, the output notations, the documented evals), the recorded sessions, the library sweep"""
    rel = lambda *p: '/'.join(p)
    L = []
    def add(cid, args, slow=False): L.append((cid, 'slow' if slow or cid in SLOW_CASES else '-', args))
    exdir = os.path.join(ROOT, 'examples')
    for f in sorted(os.listdir(exdir)):
        if not f.endswith('.imo'): continue
        ex = rel('examples', f)
        add(f'ex.run.{f}', ['run', ex]); add(f'ex.check.{f}', ['check', ex])
        add(f'ex.spec.{f}', ['translate', ex, '--to', 'spec']); add(f'ex.bin.{f}', ['translate', ex, '--to', 'bin'])
    for f in ('point.hum.imo', 'hello.hum.imo', 'main.hum.imo', 'prove.hum.imo', 'predicates.hum.imo', 'sedenion.hum.imo'):
        for m in ('bin', 'spec', 'hum'): add(f'ex.out-{m}.{f}', ['run', rel('examples', f), '--out', m])
    for f, name, n in EVALS:
        add(f'ex.eval.{f}.{name}', ['eval', rel('examples', f), name] + ([str(n)] if n is not None else []))
    add('ex.eval.spec-tower', ['eval', 'examples/target.spec.imo', 'examples/tower.spec.imo', 'w', '14'])
    add('ex.text.hello', ['text', 'examples/hello.hum.imo', 'greeting'])
    add('ex.check.bad', ['check', 'examples/bad.hum.imo'])
    for ex in ('hello.hum.imo', 'hello.bin.imo', 'prove.bin.imo'):
        add(f'prelude-bin.run.{ex}', ['run', 'lib/prelude.bin.imo', rel('examples', ex)])
    add('prelude-bin.check.point', ['check', 'lib/prelude.bin.imo', 'examples/point.hum.imo'])
    pdir = os.path.join(CONF, 'programs')
    for d in sorted(os.listdir(pdir)):
        full = os.path.join(pdir, d)
        if not re.fullmatch(r's\d+', d) or not os.path.isdir(full): continue
        files = [rel('tests', 'conformance', 'programs', d, f) for f in sorted(os.listdir(full)) if f.endswith('.imo')]
        add(f'{d}.check', ['check'] + files); add(f'{d}.spec', ['translate'] + files + ['--to', 'spec'])
        add(f'{d}.bin', ['translate'] + files + ['--to', 'bin']); add(f'{d}.run', ['run'] + files + ['--n', '6'])
    edir = os.path.join(pdir, 'err')                   # the programs of the README's error-message table (§7.6): every message is the checker's
    for f in sorted(os.listdir(edir)):
        if f.endswith('.imo'): add(f'err.{f[:-4]}', ['check', rel('tests', 'conformance', 'programs', 'err', f)])
    add('cli.bad-out', ['run', 'examples/hello.hum.imo', '--out', 'nothing'])
    add('cli.n-lines', ['run', 'tests/conformance/programs/misc/stream.hum.imo', '--n', '3'])
    mdir = os.path.join(pdir, 'misc')                  # hand-written edge cases: literals, comments, sections, errors, unknowns, big numbers
    for f in sorted(os.listdir(mdir)):
        if f.endswith('.imo'): add(f'misc.{f[:-4]}', ['run', rel('tests', 'conformance', 'programs', 'misc', f), '--n', '6'])
    libs = sorted(f for f in os.listdir(OUT) if f.endswith('.hum.imo'))
    for f in libs:
        stem = f[:-len('.hum.imo')]; path = rel('tests', 'conformance', 'programs', 'lib', f)
        h = zlib.crc32(stem.encode('utf-8'))             # which programs also run in the spec and bin output notations: by the name, so that a new library function moves none
        add(f'lib.{stem}', ['run', path, '--n', '4'])
        if h % 5 == 0: add(f'lib.{stem}.spec', ['run', path, '--n', '4', '--out', 'spec'])
        if h % 10 == 3: add(f'lib.{stem}.bin', ['run', path, '--n', '4', '--out', 'bin'])
    with open(os.path.join(CONF, 'cases.txt'), 'w', encoding='utf-8') as f:
        f.write('# id <TAB> flags <TAB> command line (relative to the repository root); written by pymo/mkconformance.py --cases\n')
        for cid, flags, args in L: f.write(f"{cid}\t{flags}\t{' '.join(args)}\n")
    print(len(L), 'cases written to tests/conformance/cases.txt')

if __name__ == '__main__':
    main()
