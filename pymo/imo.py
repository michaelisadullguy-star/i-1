"""
imo.py -- loader / driver for i-1 programs.

A file is read in the notation chosen by its extension (x.bin.imo, x.hum.imo, x.imo = spec) or by section headers
(@bin  @spec  @hum on a line of their own).  Every section is translated to spec statements, the whole program is
checked by the class checker, and the definitions are run by imo_core (lazy, call-by-need).

A symbol that the program declares and never defines is an UNKNOWN (docs/predicates.md): its class must be a number class, a
statement about it is simplified by lib/solve.imo, and evaluating it is a run-time error (UnknownError).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imo_core
from imo_core import Th, done, to_bool, to_list, to_pair, stream_nth, list_value, run_big
import syntax, layers, hum, quote
from imotypes import ImoTypeError, Checker, UnknownError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _manifest():
    """the prelude files, in loading order: lib/MANIFEST (one file name per line, ⍝ starts a comment) — the list every core shares"""
    with open(os.path.join(ROOT, 'lib', 'MANIFEST'), encoding='utf-8', newline='') as f:
        names = [ln.strip() for ln in f.read().split('\n')]
    return [os.path.join(ROOT, 'lib', n) for n in names if n and not n.startswith('⍝')]
PRELUDE = _manifest()

class Program:
    def __init__(self, doc1=None, doc2=None):
        self.doc1 = layers.Doc1.parse(open(doc1 or os.path.join(ROOT, 'docs', 'doc1.sbl'), encoding='utf-8', newline='').read())
        self.doc2 = hum.Doc2.parse(open(doc2 or os.path.join(ROOT, 'docs', 'doc2.sbl'), encoding='utf-8', newline='').read())
        import re as _re
        for e in self.doc2.entries:                      # a bin symbol on the right of doc 2 means the spec symbol that doc 1 gives that code to
            e['rhs'] = [self.doc1.b2s.get(x, x) if _re.fullmatch(r'\.[01]+\.', x) else x for x in e['rhs']]
        self.hum = hum.Hum(self.doc2)
        self.statements = []          # (file, statement, trusted)
        self.checker = Checker()
        self.checker.overloads = self.doc2.overload_table()
        self.resolved = []
        self.errors = []
        self.machine = None
        self.notation_of = {}         # defined symbol -> the notation of the section that defines it
        self.out_mode = None          # set by an  @out bin|spec|hum  line

    def add_text(self, text, name='<text>', trusted=False, notation='spec'):
        lines = []
        for ln in text.split('\n'):
            w = ln.split()
            if len(w) == 2 and w[0] == '@out':
                if w[1] not in ('bin', 'spec', 'hum'): raise ImoTypeError(f"{name}: @out takes bin, spec or hum, not {w[1]}")
                self.out_mode = w[1]; lines.append('')
            else: lines.append(ln)
        text = '\n'.join(lines)
        for mode, chunk in layers.split_sections(text, notation):
            if mode == 'spec': sts = syntax.parse_statements(chunk)
            elif mode == 'bin': sts = syntax.parse_statements(layers.bin_to_spec_text(chunk, self.doc1))
            else: sts = self.hum.statements(chunk)
            for st in sts:
                self.statements.append((name, st, trusted))
                if st[0] == 'def' and not trusted: self.notation_of[st[1]] = mode

    def add_file(self, path, trusted=False):
        local = path.rsplit('.imo', 1)[0].replace('.bin', '').replace('.hum', '').replace('.spec', '') + '.sbl'
        text = open(path, encoding='utf-8', newline='').read()          # verbatim: a carriage return is whitespace, or a character inside a literal
        uses_bin = layers.default_notation(path) == 'bin' or '\n@bin' in '\n' + text
        if uses_bin and os.path.exists(local):          # program-local symbol table of a bin program (same line format as doc 1)
            for line in open(local, encoding='utf-8', newline='').read().split('\n'):
                if ' := ' in line and not line.startswith('⍝'):
                    a, b = [x.strip() for x in line.split(' := ')]
                    if a in self.doc1.s2b: continue
                    if b in self.doc1.b2s:
                        raise ImoTypeError(f"{os.path.basename(local)}: local code {b} for {a} is already doc 1's code for {self.doc1.b2s[b]}"
                                           " (doc 1 grew: regenerate the local table with  i1.py translate … --to bin)")
                    self.doc1.s2b[a] = b; self.doc1.b2s[b] = a
        self.add_text(text, path, trusted, layers.default_notation(path))

    def check(self, collect=False):
        self.errors, self.resolved = [], []
        self.statements = [x for x in self.statements if x[0] != '<quote>']
        self._unknowns()
        for fname, st, trusted in self.statements:
            try:
                self.resolved.append(self.checker.check_statement(st, trusted))
            except ImoTypeError as e:
                what = st[1] if st[0] in ('def', 'decl') else syntax.pp_statement(st)
                if not collect: raise ImoTypeError(f"{os.path.basename(fname)}: {what}: {e}")
                self.errors.append((fname, what, str(e)))
                self.resolved.append(None)
        self.checker.settle_taint([(r[1], r[2], r[3]) for (f, st, t), r in zip(self.statements, self.resolved)
                                   if not t and r is not None and r[0] == 'def'])
        if not self.errors: self._codes()
        if not self.errors and any(r is not None and r[0] == 'def' and quote.Quoter.has_quote(r[3]) for r in self.resolved):
            self._quote()
        return self.errors

    def _unknowns(self):
        """the unknowns (declared by the program, defined nowhere), in declaration order, and a first estimate of which program
        definitions need their values (refined after checking: Checker.settle_taint)"""
        C = self.checker
        defined = {st[1] for f, st, t in self.statements if st[0] == 'def'}
        order = []
        for f, st, trusted in self.statements:
            if st[0] == 'decl' and not trusted and st[1] not in defined and st[1] not in order:
                r = st[2]
                while r[0] == 'K' and r[1] == '→': r = r[2][1]
                if r not in (('K', '𝒦', ()), ('K', '𝒮', ())): order.append(st[1])
        C.unknowns = {n: None for n in order}
        user = [(st[1], st[2], st[3]) for f, st, t in self.statements if st[0] == 'def' and not t]
        C.user_defined = {n for n, _, _ in user}
        def refs(t, bound, out):
            tag = t[0]
            if tag == 'var':
                if t[1] not in bound: out.update(C.overloads.get(t[1], [t[1]]))
            elif tag == 'app':
                refs(t[1], bound, out)
                for a in t[2]: refs(a, bound, out)
            elif tag == 'lam': refs(t[2], bound | {p[0] for p in t[1]}, out)
            elif tag == 'asc': refs(t[1], bound, out)
            return out
        uses = {n: refs(b, frozenset(ps), set()) for n, ps, b in user}
        tainted, changed = set(order), True
        while changed:
            changed = False
            for n, u in uses.items():
                if n not in tainted and u & tainted: tainted.add(n); changed = True
        C.raw_taint = tainted - set(order)
        C.taint = {}

    def _codes(self):
        """program-local codes (doc 1 format) for the program's own symbols, assigned when the program is checked and in a fixed
        order — the unknowns first, in declaration order (solutions list them so), then the other symbols in declaration order.
        Codes of statements name symbols by these numbers, so a re-spelled program (translate --to spec) names them as the
        original did; a bin program brings its codes in its local table."""
        order = list(self.checker.unknowns)
        order += [st[1] for f, st, t in self.statements if not t and st[0] == 'decl' and st[1] != quote.ENV and st[1] in self.checker.sigs]
        for n in order: self.doc1.code(n, True)

    def hum_name(self, spec):
        """the human name of a spec symbol (reverse doc 2; a symbol of the program is its own name)"""
        for e in self.doc2.entries:
            if e['role'] in ('value', 'infixl', 'infixr', 'infix', 'prefix') and spec in e['rhs']: return e['hum']
        return spec

    def _quote(self):
        """replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝  and add the table of definitions (pymo/quote.py)"""
        Q = quote.Quoter(self)
        for k, r in enumerate(self.resolved):
            if r is not None and r[0] == 'def' and quote.Quoter.has_quote(r[3]):
                self.resolved[k] = ('def', r[1], r[2], Q.replace(r[3]))
        tab = Q.table()
        self.checker.declare(quote.ENV, ('K', '𝔏', (('K', '𝔓', (('K', '𝔇', ()), ('K', '𝔔', ()))),)))
        # the table holds only numbers (codes), so it can stand before the program's own statements: a re-spelled program
        # (translate --to bin) then declares it before its first use
        at = next((k for k, (f, st, trusted) in enumerate(self.statements) if not trusted), len(self.statements))
        for k, st in enumerate((('decl', quote.ENV, ('K', '𝔏', (('K', '𝔓', (('K', '𝔇', ()), ('K', '𝔔', ()))),))), ('def', quote.ENV, [], tab))):
            self.statements.insert(at + k, ('<quote>', st, False)); self.resolved.insert(at + k, st)

    def build(self):
        defs = [syntax.erase_def(s[1], s[2], s[3]) for s in self.resolved if s[0] == 'def']
        unknowns = list(self.checker.unknowns)
        idle = ('A', ('L', ('V', 1)), ('L', ('V', 1)))           # a closed placeholder (not a λ, so its value is a thunk)
        self.machine = imo_core.Machine(defs + [(n, idle) for n in unknowns])
        for n in unknowns:                                       # an unknown has no value: forcing it is an error
            def boom(n=n, h=self.hum_name(n)):
                raise UnknownError(f"{h} is an unknown (it is declared and never defined, so it has no value); "
                                   f"use it in a statement — a relation such as {h} == 1 — which is simplified, not evaluated")
            self.machine.G[n].f = boom
        return self.machine

    def val(self, name): return self.machine.val(name)

    # -- re-spelling of the checked, user-level (non-prelude) statements
    def user_statements(self):
        return [r for (f, s, t), r in zip(self.statements, self.resolved) if not t]

    def spec_text(self):
        return '\n'.join(syntax.pp_statement(s) for s in self.user_statements()) + '\n'

    def bin_text(self):
        return layers.spec_statements_to_bin_text(self.user_statements(), self.doc1, allow_new=True)

    def local_table(self):
        return self.doc1.render(names=set(self.doc1.local), header=["program-local symbols (same format as doc 1)"])

def load(files, trusted=PRELUDE, collect=False, prelude=True):
    p = Program()
    if prelude:
        for f in PRELUDE: p.add_file(f, trusted=True)
    for f in files: p.add_file(f, trusted=(f in trusted))
    p.check(collect=collect)
    if not p.errors: p.build()
    return p
