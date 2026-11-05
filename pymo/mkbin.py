"""mkbin.py -- derive the pure-binary files:  lib/prelude.bin.imo  and  examples/*.bin.imo (+ their local symbol tables *.sbl)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imo, layers, syntax
ROOT = imo.ROOT
# the prelude
p = imo.Program()
for f in imo.PRELUDE: p.add_file(f, trusted=True)
p.check()
out = layers.spec_statements_to_bin_text([r for r in p.resolved], p.doc1, allow_new=False)
open(os.path.join(ROOT, 'lib', 'prelude.bin.imo'), 'w', encoding='utf-8').write(out)
print("prelude.bin.imo:", len(out), "characters,", out.count('\n'), "lines; alphabet:", sorted(set(out)))
# examples (one shared numbering, so program-local symbols of different programs never collide)
EXAMPLES = [('target', 'target.spec.imo'), ('spaces', 'spaces.spec.imo'), ('hello', 'hello.hum.imo'), ('prove', 'prove.hum.imo')]
for _f, _ in EXAMPLES:
    try: os.remove(os.path.join(ROOT, 'examples', _f + '.sbl'))
    except FileNotFoundError: pass
shared = p.doc1
for name, src in EXAMPLES:
    q = imo.Program()
    q.doc1 = shared
    before = set(shared.local)
    for f in imo.PRELUDE: q.add_file(f, trusted=True)
    q.add_file(os.path.join(ROOT, 'examples', src))
    q.check()
    text = q.bin_text()
    used = {t[1] for t in syntax.lex(q.spec_text()) if t[0] == 'NAME'} | {st[1] for st in q.user_statements() if st[0] in ('decl', 'def')}
    mine = {n for n in shared.local if n in used}       # every program-local symbol this program uses (some were numbered by an earlier example)
    open(os.path.join(ROOT, 'examples', f'{name}.bin.imo'), 'w', encoding='utf-8').write(text)
    open(os.path.join(ROOT, 'examples', f'{name}.sbl'), 'w', encoding='utf-8').write(
        shared.render(names=mine, header=[f"program-local symbols of examples/{name} (same line format as doc 1)"]))
    print(f"{name}.bin.imo:", len(text), "characters; local symbols:", {k: shared.local[k] for k in mine})

# the CRLF twins of examples/hello.bin.imo and hello.sbl that the conformance suite keeps (tests/conformance/programs/misc/crlf_bin.*):
# derived here because their local codes move whenever doc 1 grows
for _src, _dst in (('hello.bin.imo', 'crlf_bin.bin.imo'), ('hello.sbl', 'crlf_bin.sbl')):
    _b = open(os.path.join(ROOT, 'examples', _src), 'rb').read().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    open(os.path.join(ROOT, 'tests', 'conformance', 'programs', 'misc', _dst), 'wb').write(_b)
