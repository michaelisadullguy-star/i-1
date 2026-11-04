"""
quote.py -- the compiler side of statements (docs/predicates.md, docs/prove.md).  A statement — a relation on ℝ[i], a relation or
predicate about an unknown, a connective with a statement operand (pymo/imotypes.py marks them ('quote', φ, …)) — is simplified
from DEFINITIONS whenever it is evaluated or output, so its checked term φ is replaced by a term that builds φ's CODE at run time:

    numeral / Char / String / closed number or Boolean     (𝔮ⁿ value)       — decided directly (a subset of ℚ[i] or 𝔹)
    symbol                                                (𝔮ˢ code)        — its doc 1 code (a numeral; a local code for the program's own symbols)
    unknown x (declared, never defined)                   (𝔮ˢ code of x)   — program-local codes, numbered in DECLARATION order
    application, λ, bound variable                        (𝔮ᵃ f a) (𝔮ˡ b) (𝔮ᵛ k)   — de Bruijn indices
    a variable bound outside φ, not a number              (𝔮ᵛ k) with k beyond φ's binders: an unknown, the same for every use
    a variable bound outside φ, of class Ω                its value (a statement IS its code)
    prop b, decide φ, ∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω                       transparent: the code of b or φ, and the plain connectives ∧ ∨ ¬ ⇒ ⇔

and the statement becomes  (simplify′ ε⌜⌝ ⌜φ⌝) — its simplest form, computed in the language by simplify′ (lib/solve.imo) — where  ε⌜⌝  is one table,
for the whole program, of (code, ⌜definition⌝) for the program's symbols that the codes mention (transitively), for the prelude
functions that are defined by series (exp, sin, cos, sinh, cosh, log, atan), and (code of x, ⌜𝔲 k⌝) for every unknown x that is
mentioned, k its domain (0 ℂ, 1 ℝ, 2 ℚ(i), 3 ℚ, 4 ℤ[i], 5 ℤ, 6 ℕ).  Nothing is decided here: this is a spelling of terms as numbers,
like the reader's expansion of numerals.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imotypes import K, ImoTypeError, REL_R, CONN_O
from base_b import to_digits, numeral

UNFOLD = ['exp', 'sin', 'cos', 'sinh', 'cosh', 'log', 'atan']
ENV = 'ε⌜⌝'
NUM = K('ℚ[i]')
TRANSPARENT = {'prop', 'decide', 'code_rd'}      # 𝔹 ↔ Ω: a truth value or a statement inside a statement is written as itself

def A(f, *xs): return ('app', ('var', f), list(xs))
def digits(text): return A('↓ᶻ', ('num', text))      # the digit string of a numeral (well-classed: ↓ᶻ ∶ ℚ[i] → 𝔇)
def nat(k): return digits(numeral(to_digits((k, 0))))

class Quoter:
    def __init__(self, program):
        self.P = program; self.C = program.checker
        self.defs = {}                     # program symbol -> (params, body, declared class)
        self.prelude = {}                  # prelude symbol -> (params, body)
        self.needed = []                   # symbols whose definitions go into the table, in order
        for (f, st, trusted), r in zip(program.statements, program.resolved):
            if r is None or r[0] != 'def': continue
            if trusted:
                if r[1] in UNFOLD: self.prelude[r[1]] = (r[2], r[3])
            else:
                self.defs[r[1]] = (r[2], r[3], self.C.sigs[r[1]][0])
        self.unknowns = {n: k for n, k in self.C.unknowns.items() if k is not None}
        for n in self.unknowns: self.P.doc1.code(n, True)       # program-local codes in declaration order (solutions list them so)
        self.stmt = {n for n, (ps, b, c) in self.defs.items() if self.has_quote(b)}   # definitions that contain a statement

    def code(self, name):
        b = self.P.doc1.code(CONN_O.get(name, name), True)
        return digits(b[1:-1])

    def need(self, name):
        if (name in self.defs or name in self.prelude or name in self.unknowns) and name not in self.needed: self.needed.append(name)

    # -- classes of sub-terms, to decide what is a value
    def klass(self, t, loc):
        try: return self.C.synth(t, loc)[0]
        except Exception: return None

    def is_value_class(self, c):
        if c is None: return False
        c = self.C.norm(c)
        if c[0] != 'K': return False
        return c == K('𝔹') or self.C.leq(c, NUM)

    @staticmethod
    def has_quote(t):
        if t[0] == 'quote': return True
        if t[0] == 'app': return Quoter.has_quote(t[1]) or any(Quoter.has_quote(a) for a in t[2])
        if t[0] == 'lam': return Quoter.has_quote(t[2])
        return False

    def has_rel(self, t):
        """must t be written as a code (not evaluated): does it contain a statement, a relation on ℝ[i], or a symbol whose
        definition contains a statement?"""
        if t[0] == 'quote': return True
        if t[0] == 'var': return t[1] in REL_R or t[1] in CONN_O or t[1] in self.stmt
        if t[0] == 'app': return self.has_rel(t[1]) or any(self.has_rel(a) for a in t[2])
        if t[0] == 'lam': return self.has_rel(t[2])
        return False

    @staticmethod
    def free_in(t, names):
        if t[0] == 'var': return t[1] in names
        if t[0] == 'app': return Quoter.free_in(t[1], names) or any(Quoter.free_in(a, names) for a in t[2])
        if t[0] == 'lam':
            inner = names - {p[0] for p in t[1]}
            return Quoter.free_in(t[2], inner)
        if t[0] == 'quote': return Quoter.free_in(t[1], names)
        return False

    # -- the code of a term.  ib: binders inside the quote (innermost last) with their classes;  outer: classes of variables bound outside
    def q(self, t, ib, outer, typed=True):
        tag = t[0]
        if tag == 'quote': return self.q(t[1], ib, outer, typed)
        if tag in ('num', 'chr', 'str'): return A('𝔮ⁿ', t)
        names = [n for n, _ in ib]
        if tag == 'var':
            n = t[1]
            if n in names: return A('𝔮ᵛ', nat(len(names) - max(i for i, m in enumerate(names) if m == n)))
            if n in outer:
                if self.is_value_class(outer[n]): return A('𝔮ⁿ', t)
                if outer[n] is not None and self.C.is_prop(outer[n]): return A('code_rd', t)   # a statement: its value is its code
                return A('𝔮ᵛ', nat(len(names) + 1 + list(outer).index(n)))
            if n in self.unknowns:
                self.need(n); return A('𝔮ˢ', self.code(n))
            if typed and n not in self.defs and n in self.C.sigs and all(self.is_value_class(c) for c in self.C.sigs[n]):
                return A('𝔮ⁿ', t)
            if n in self.defs and self.is_value_class(self.defs[n][2]) and n not in self.stmt and not self.C.unknownish(n):
                return A('𝔮ⁿ', t)
            self.need(n)
            return A('𝔮ˢ', self.code(n))
        if tag == 'app':
            f = t[1]
            if typed and f[0] == 'var' and f[1] in TRANSPARENT and f[1] not in names and f[1] not in outer and len(t[2]) == 1:
                return self.q(t[2][0], ib, outer, typed)
            if (typed and not self.has_rel(t) and not self.free_in(t, set(names))
                    and not self.C.mentions(t, frozenset(outer) | frozenset(names))):
                loc = dict(outer); loc.update({n: c for n, c in ib})
                if self.is_value_class(self.klass(t, loc)): return A('𝔮ⁿ', t)
            out = self.q(t[1], ib, outer, typed)
            for a in t[2]: out = A('𝔮ᵃ', out, self.q(a, ib, outer, typed))
            return out
        if tag == 'lam':
            inner = list(ib)
            for n, c in t[1]: inner.append((n, c))
            out = self.q(t[2], inner, outer, typed)
            for _ in t[1]: out = A('𝔮ˡ', out)
            return out
        raise ImoTypeError(f"a statement cannot be written as a code: {tag}")

    def definition_code(self, name):
        if name in self.unknowns:                          # an unknown of domain k:  ⌜𝔲 k⌝
            return A('𝔮ᵃ', A('𝔮ˢ', self.code('𝔲')), A('𝔮ⁿ', ('num', numeral(to_digits((self.unknowns[name], 0))))))
        if name in self.defs:
            params, body, cls = self.defs[name]
            ps = []
            c = cls
            for p in params:
                c = self.C.norm(c); ps.append((p, c[2][0])); c = c[2][1]
            out = self.q(body, ps, {}, True)
        else:
            params, body = self.prelude[name]
            out = self.q(body, [(p, None) for p in params], {}, False)
        for _ in params: out = A('𝔮ˡ', out)
        return out

    def replace(self, t):
        tag = t[0]
        if tag == 'quote':
            return A('simplify′', ('var', ENV), self.q(t[1], [], t[2], True))
        if tag == 'app': return ('app', self.replace(t[1]), [self.replace(a) for a in t[2]])
        if tag == 'lam': return ('lam', t[1], self.replace(t[2]))
        return t

    def table(self):
        entries, k = [], 0
        while k < len(self.needed):                        # quoting a definition can need more definitions
            name = self.needed[k]; k += 1
            entries.append((name, A('⊗', self.code(name), self.definition_code(name))))
        # the unknowns come first, in DECLARATION order: that is the order in which solutions list them (a name that the library
        # also uses as a bound variable has a library code, so the order of the codes says nothing about the order of declaration)
        first = [e for n, e in sorted((e for e in entries if e[0] in self.unknowns), key=lambda e: list(self.unknowns).index(e[0]))]
        entries = first + [e for n, e in entries if n not in self.unknowns]
        out = ('var', '⊘')
        for e in reversed(entries): out = A('∷', e, out)
        return out
