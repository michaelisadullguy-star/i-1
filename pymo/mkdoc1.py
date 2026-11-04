"""mkdoc1.py -- (re)generate docs/doc1.sbl : one binary symbol .B. for every symbol of the prelude.

Append-only: the codes already in docs/doc1.sbl are kept exactly; a symbol that is new gets the next ordinal (in order of
first appearance, scanning the prelude files in imo.PRELUDE order).  A symbol that has disappeared from the prelude keeps its
code (it is never reassigned), so programs written against an older doc 1 keep their meaning."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layers import Doc1, RESERVED_BIN
from syntax import lex
import imo
ROOT = imo.ROOT
D1 = os.path.join(ROOT, 'docs', 'doc1.sbl')
ENTRY = ['main']
d = Doc1.parse(open(D1, encoding='utf-8').read()) if os.path.exists(D1) else Doc1()
before = len(d.s2b)
for f in imo.PRELUDE:
    for t in lex(open(f, encoding='utf-8').read()):
        if t[0] == 'NAME' and t[1] not in RESERVED_BIN: d.code(t[1], True)
# entry points: symbols a program defines but the host looks for, so that a bin program can name them without a local table
for name in ENTRY: d.code(name, True)
header = ["doc 1   [spec sbl] := [bin sbl]",
          "every symbol of the prelude (lib/*.imo) has one binary symbol  .B.  where B is an ordinal, in binary.",
          "reserved tokens (not listed):   ↦ = .      ≔ = ..      ∶ = ...",
          "append-only: a released code is never reassigned; new symbols get the next ordinal (pymo/mkdoc1.py).",
          "retired, code kept and unused: reduce, reduce′ (a relation is simplified whenever it is evaluated; nothing asks for it)."]
open(D1, 'w', encoding='utf-8').write(d.render(header=header))
print(len(d.s2b), "symbols", f"({len(d.s2b) - before} new)")
