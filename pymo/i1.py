"""
i1.py -- command line of Pymo, the Python interpreter of i-1 (Haskimo, the Haskell one, and Rustimo, the Rust one, have the same commands and print the same bytes).

  python3 pymo/i1.py run       FILE... [--out bin|spec|hum] [--n N]
                                                        run the program: evaluate `main` and print it (also:  i1.py FILE...)
  python3 pymo/i1.py check     FILE...                 load the prelude and FILE(s), run the class checker
  python3 pymo/i1.py translate FILE... --to spec|bin   re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
  python3 pymo/i1.py eval      FILE... NAME [N]        evaluate NAME and print it by its declared class (ℚ[i] value, stream element N, tree, string, Bool)
  python3 pymo/i1.py text      FILE... NAME            evaluate NAME as a String and print it

`run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output
notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream
element shown for a stream (default 10), or the number of lines of a stream of strings.

FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imo, output
from imo import load, to_pair, to_list, stream_nth, run_big
from imotypes import ImoTypeError, UnknownError
from syntax import show_type
from base_b import val
from fractions import Fraction

def load_files(files):
    prelude = [f for f in files if f.endswith('prelude.bin.imo')]
    return load(files, trusted=prelude, prelude=not prelude, collect=True)

def qval(v):
    p, d = to_pair(v)
    a, b = val(to_list(p)), val(to_list(d))
    n = b[0] ** 2 + b[1] ** 2
    return Fraction(a[0] * b[0] + a[1] * b[1], n), Fraction(a[1] * b[0] - a[0] * b[1], n)

def qfmt(v):
    re, im = qval(v)
    s = f"{re}" if im == 0 else f"{re} + {im} i"
    return f"{s}   (≈ {float(re):.12g}" + ("" if im == 0 else f" + {float(im):.12g} i") + ")"

def sfmt(v):
    from imo_core import CONS_TH, NIL_TH
    out, r = [], v(CONS_TH)(NIL_TH)
    while r[0] == 'C':
        out.append(chr(int(qval(r[1].force())[0]))); r = r[2].force()(CONS_TH)(NIL_TH)
    return ''.join(out)

def tfmt(P, v, n=None):
    """a Cayley–Dickson tree; if its leaves are streams, show element n of each"""
    M = P.machine
    if imo.to_bool(M.val('◀')(imo.done(v))):
        a, b = to_pair(M.val('▶')(imo.done(v)))
        return '⟨' + tfmt(P, a, n) + ', ' + tfmt(P, b, n) + '⟩'
    leaf = M.val('▶')(imo.done(v))
    if n is not None: leaf = stream_nth(leaf, n)
    re, im = qval(leaf)
    return f"{float(re):.10g}" + ("" if im == 0 else f" + {float(im):.10g} i") if n is not None else (f"{re}" if im == 0 else f"({re} + {im} i)")

def show(P, name, n):
    """evaluate NAME and print it according to its declared class"""
    cls = P.checker.norm(P.checker.sigs[name][0])
    v = P.val(name)
    head = cls[1] if cls[0] == 'K' else ''
    if head == '𝔖' or (cls[0] == 'K' and cls[1] == 'ℝ'):
        if n is None: n = 10
        return f"element {n} of the stream:  " + qfmt(stream_nth(v, n))
    if head == '𝔏' and cls[2][0][1] == '𝕮':
        return sfmt(v)
    if head == '𝔗':
        inner = cls[2][0]
        streams = inner[0] == 'K' and inner[1] == '𝔖'
        return (f"element {n if n is not None else 10} of each leaf:  " if streams else '') + tfmt(P, v, (n if n is not None else 10) if streams else None)
    if head == '𝔹': return 'true' if imo.to_bool(v) else 'false'
    if 'Ω' in show_type(cls): return output.Printer(P, 'hum').show(v, cls)     # statements (Prop): in the human notation
    return qfmt(v)

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'): print(__doc__); return 0
    cmd, rest = args[0], args[1:]
    if cmd not in ('run', 'check', 'eval', 'text', 'translate') and os.path.exists(cmd):
        cmd, rest = 'run', args
    if cmd == 'run':
        out = n = None
        if '--out' in rest:
            k = rest.index('--out'); out = rest[k + 1]; rest = rest[:k] + rest[k + 2:]
            if out not in output.MODES: print(f"--out takes one of {', '.join(output.MODES)}"); return 2
        if '--n' in rest:
            k = rest.index('--n'); n = int(rest[k + 1]); rest = rest[:k] + rest[k + 2:]
        p = load_files(rest)
        if p.errors:
            for f, w, m in p.errors: print(f"error in {os.path.basename(f)}: " + (m if m.startswith(str(w)) else f"{w}: {m}"))
            return 1
        try:
            output.run_main(p, out, n)
        except output.PrintError as e:
            print(f"error: {e}"); return 1
        return 0
    if cmd == 'translate':
        to = rest[rest.index('--to') + 1]; files = [x for x in rest if x != '--to' and x != to]
        p = load_files(files)
        if p.errors:
            for f, w, m in p.errors: print(f"error in {os.path.basename(f)}: " + (m if m.startswith(str(w)) else f"{w}: {m}"))
            return 1
        print(p.spec_text() if to == 'spec' else p.bin_text(), end='')
        if to == 'bin' and p.doc1.local: print('\n' + p.local_table(), end='')
        return 0
    if cmd in ('check', 'eval', 'text'):
        n = None
        if cmd == 'check': files, name = rest, None
        else:
            files = [x for x in rest if os.path.exists(x)]; tail = [x for x in rest if not os.path.exists(x)]
            name = tail[0]; n = int(tail[1]) if len(tail) > 1 else None
        p = load_files(files)
        if name and not p.errors: name = p.hum.spec_name(name)
        if p.errors:
            for f, w, m in p.errors: print(f"error in {os.path.basename(f)}: " + (m if m.startswith(str(w)) else f"{w}: {m}"))
            return 1
        if cmd == 'check': print(f"ok: {len(p.user_statements())} statements checked"); return 0
        try:
            v = p.val(name)
            if cmd == 'text': print(sfmt(v)); return 0
            print(show(p, name, n)); return 0
        except (UnknownError, output.PrintError) as e:
            print(f"error: {e}"); return 1
    print(__doc__); return 2

if __name__ == '__main__':
    rc = run_big(main)
    sys.exit(1 if rc is None else rc)        # an uncaught exception (printed as a traceback) is a failure: exit status 1, as in Haskimo and Rustimo
