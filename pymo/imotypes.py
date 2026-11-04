"""
types.py -- the class checker of i-1.

Rules (all enforced here)
  * every symbol must be DECLARED  (name ∶ class)  before it is defined or used;
  * classes are terms:  atoms (ℕ ℤ ℚ ℝ ℤ[i] ℚ[i] ℝ[i] 𝔹 𝕮 𝕊 𝔻 …)  and constructors  (→ A B) (𝔏 A) (𝔖 A) (𝔗 A) (𝔄 A) (𝔓 A B);
  * a symbol may carry several declarations (overloads = an intersection of classes);
  * facts   (⊆ A B)  subclass,   (≣ A B)  class equation,   (↪ f)  f is a canonical (widening) coercion;
  * lambda binders must be annotated   (x ∶ A ↦ …);   definition parameters take their classes from the declaration;
  * numerals get the smallest class containing their value:  ℕ ⊆ ℤ ⊆ ℤ[i] ⊆ ℚ[i],  ℤ ⊆ ℚ ⊆ ℚ[i],  radix numerals are ℚ or ℚ[i];
  * 'trusted' files (the prelude) have their signatures recorded but their bodies are NOT checked.

Statements (the class Prop, spec Ω — docs/predicates.md)
  * a user symbol that is declared and never defined is an UNKNOWN; its class must be one of the number classes
    ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] or a class below one of them (its domain is the smallest);  evaluating it is a run-time error;
  * STATEMENTS have class Ω and are marked ('quote', φ, classes of the variables bound outside φ): pymo/quote.py writes φ as a
    code and the simplifier (lib/solve.imo, simplify′) computes its simplest form when it is evaluated.  They are
      - a relation on ℝ[i] (≐ᴿ ≺ᴿ …),
      - an application whose class is 𝔹 or Ω and one of whose arguments mentions an unknown (outside quoted statements) — a
        relation about an unknown (x == 1), a predicate of the program or of the prelude applied to an unknown,
      - a connective on statements (∧Ω ∨Ω ¬Ω ⇒Ω ⇔Ω — the human and, or, not, implies, iff with an Ω operand: one statement,
        simplified together);
    a closed relation on ℚ[i] stays 𝔹 (decided by evaluation);
  * 𝔹 → Ω (prop) and Ω → 𝔹 (decide) are canonical coercions; decide loses information (a statement that is neither true nor
    false becomes ⍰), so it costs 2: where both readings fit, the one in Ω is chosen;  a list or pair literal is made to fit
    element by element ([x == 1, false] is a List(Prop)).
"""
import sys
from fractions import Fraction
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from syntax import show_type, CLASS_VARS
from base_b import val, gmul

class ImoTypeError(Exception): pass

COV = {'𝔏', '𝔖', '𝔗', '𝔓'}
REL_R = {'≐ᴿ', '≠ᴿ', '≺ᴿ', '⩽ᴿ', '≻ᴿ', '⩾ᴿ'}
REL_Q = {'≐', '≠', '≺', '⩽', '≻', '⩾'}
CONN_O = {'∧Ω': '∧', '∨Ω': '∨', '¬Ω': '¬', '⇒Ω': '⇒', '⇔Ω': '⇔'}     # connectives on statements -> the connective their code uses
COERCION_COST = {'decide': 2}                                         # a lossy coercion costs more than a widening one
# the domains of unknowns (docs/predicates.md §2): the first number class (in this order) that contains the declared class
DOMAINS = [('ℕ', 6), ('ℤ', 5), ('ℚ', 3), ('ℤ[i]', 4), ('ℚ[i]', 2), ('ℝ', 1), ('ℝ[i]', 0)]

class UnknownError(RuntimeError):
    """raised (at run time) when the value of an unknown is needed"""

BUILTIN_CLASSES = {'→': 2, '𝒦': 0, '𝒮': 0}
BOTTOM = ('F', '⊥')                     # flexible class of an as-yet-unconstrained polymorphic constant

def K(name, *args): return ('K', name, tuple(args))
ARROW = '→'
PROP = K('Ω')

def term_to_type(t):
    if t[0] == 'var':
        return ('V', t[1]) if t[1] in CLASS_VARS else K(t[1])
    if t[0] == 'app' and t[1][0] == 'var':
        return ('K', t[1][1], tuple(term_to_type(a) for a in t[2]))
    raise ImoTypeError(f"not a class expression: {t}")

def chain(t):
    out = []
    while t[0] == 'K' and t[1] == ARROW:
        out.append(t[2][0]); t = t[2][1]
    return out, t

def mk_chain(ps, r):
    for p in reversed(ps): r = K(ARROW, p, r)
    return r

def has_var(t):
    if t[0] == 'V': return True
    if t[0] == 'K': return any(has_var(a) for a in t[2])
    return False

def subst(t, S, flex=False):
    if t[0] == 'V':
        if t[1] in S: return S[t[1]]
        return BOTTOM if flex else t
    if t[0] == 'K': return ('K', t[1], tuple(subst(a, S, flex) for a in t[2]))
    return t

def num_class(text):
    """smallest class containing the value of a numeral written in base i-1"""
    B = (-1, 1)
    if '.' in text:
        a, b = text.split('.')
        bits, k = a + b, len(b)
    else:
        bits, k = text, 0
    z = val([int(c) for c in reversed(bits)])
    den = (1, 0)
    for _ in range(k): den = gmul(den, B)
    n = den[0] ** 2 + den[1] ** 2
    re = Fraction(z[0] * den[0] + z[1] * den[1], n)
    im = Fraction(z[1] * den[0] - z[0] * den[1], n)
    if im == 0:
        if re.denominator == 1: return K('ℕ') if re >= 0 else K('ℤ')
        return K('ℚ')
    return K('ℤ[i]') if (re.denominator == 1 and im.denominator == 1) else K('ℚ[i]')

class Checker:
    def __init__(self):
        self.classes = dict(BUILTIN_CLASSES)    # name -> arity
        self.statement_formers = set()          # symbols whose declared result is 𝒮
        self.sigs = {}                          # value symbol -> [class, ...]
        self.facts = []                         # (sub, super)
        self.eqs = {}                           # atom -> class
        self.coercions = []                     # symbols
        self.defined = set()
        self.overloads = {}                     # human symbol -> [spec symbols]   (set by the human reader)
        self.unknowns = {}                      # unknown -> its domain code (0 ℂ … 6 ℕ), in declaration order
        self.user_defined = set()               # symbols defined by the (non-trusted) program
        self.raw_taint = set()                  # program symbols whose definitions mention an unknown (estimated before checking)
        self.taint = {}                         # program symbol -> does its checked body need the value of an unknown?

    # ------------------------------------------------------------ classes
    def norm(self, t):
        if t[0] == 'K':
            if not t[2] and t[1] in self.eqs: return self.norm(self.eqs[t[1]])
            return ('K', t[1], tuple(self.norm(a) for a in t[2]))
        return t

    def wf(self, t):
        if t[0] in ('V', 'F'): return
        name, args = t[1], t[2]
        if name not in self.classes: raise ImoTypeError(f"undeclared class {name}")
        if self.classes[name] != len(args):
            raise ImoTypeError(f"class {name} takes {self.classes[name]} argument(s), got {len(args)}")
        for a in args: self.wf(a)

    def leq(self, a, b, seen=frozenset()):
        a, b = self.norm(a), self.norm(b)
        if a == b or a == BOTTOM: return True
        if a[0] == 'K' and b[0] == 'K' and a[1] == b[1] and a[2] and len(a[2]) == len(b[2]):
            if a[1] == ARROW:
                if self.leq(b[2][0], a[2][0], seen) and self.leq(a[2][1], b[2][1], seen): return True
            elif a[1] in COV:
                if all(self.leq(x, y, seen) for x, y in zip(a[2], b[2])): return True
        for x, y in self.facts:
            if self.norm(x) == a and (a, y) not in seen:
                if self.leq(y, b, seen | {(a, y)}): return True
        return False

    def ups(self, a):
        """a and every class that contains it, by the declared subclass facts"""
        out, todo = [], [self.norm(a)]
        while todo:
            c = todo.pop()
            if c in out: continue
            out.append(c)
            todo += [self.norm(y) for x, y in self.facts if self.norm(x) == c]
        return out

    def join(self, a, b):
        """the least class containing both a and b (e.g. ℤ[i] and ℚ give ℚ[i]); None if there is none or it is not unique"""
        a, b = self.norm(a), self.norm(b)
        if a[0] == 'K' and b[0] == 'K' and a[1] == b[1] and a[1] in COV and a[2] and len(a[2]) == len(b[2]):      # 𝔏 x and 𝔏 y: 𝔏 (x ∨ y)
            js = [x if self.leq(y, x) else y if self.leq(x, y) else self.join(x, y) for x, y in zip(a[2], b[2])]
            return None if any(j is None for j in js) else ('K', a[1], tuple(js))
        ub = self.ups(b)
        common = [c for c in self.ups(a) if c in ub]
        least = [c for c in common if not any(d != c and self.leq(d, c) for d in common)]
        return least[0] if len(least) == 1 else None

    def match(self, p, a, S, mode):
        """match pattern p (may contain class variables) against actual class a; mode: pos (a <= p), neg (p <= a), eq"""
        p, a = self.norm(p), self.norm(a)
        if p[0] == 'V':
            if p[1] in S:
                b = S[p[1]]
                if mode == 'eq': return b == a
                if self.leq(a, b): return True
                if self.leq(b, a):
                    if mode == 'pos': S[p[1]] = a
                    return True
                if mode == 'pos':                       # two classes neither of which contains the other: their least common superclass
                    j = self.join(a, b)
                    if j is not None: S[p[1]] = j; return True
                return False
            S[p[1]] = a
            return True
        if not has_var(p):
            if a == BOTTOM: return True
            return {'pos': self.leq(a, p), 'neg': self.leq(p, a), 'eq': p == a}[mode]
        if a == BOTTOM: return True
        if a[0] == 'K' and a[1] == p[1] and len(a[2]) == len(p[2]):
            S0 = dict(S); ok = True
            for i, (pp, aa) in enumerate(zip(p[2], a[2])):
                if p[1] == ARROW: m = ({'pos': 'neg', 'neg': 'pos', 'eq': 'eq'}[mode] if i == 0 else mode)
                elif p[1] in COV: m = mode
                else: m = 'eq'
                if not self.match(pp, aa, S, m): ok = False; break
            if ok: return True
            S.clear(); S.update(S0)
        if mode == 'pos':
            for x, y in self.facts:
                if self.norm(x) == a:
                    S0 = dict(S)
                    if self.match(p, y, S, mode): return True
                    S.clear(); S.update(S0)
        return False

    def domain(self, t):
        """the domain code of an unknown of class t (docs/predicates.md §2): the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i]
        ℝ ℝ[i], that contains t (a class declared below a number class, (⊆ Foo ℕ), has that domain); None when there is none"""
        t = self.norm(t)
        if t[0] != 'K' or has_var(t): return None
        for name, k in DOMAINS:
            if name in self.classes and self.leq(t, K(name)): return k
        return None

    def unknownish(self, name):
        """is `name` an unknown, or a program symbol whose value needs the value of an unknown?"""
        if name in self.unknowns: return True
        return self.taint[name] if name in self.taint else name in self.raw_taint

    def mentions(self, t, bound=frozenset(), inside_quotes=False):
        """does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements unless asked?"""
        tag = t[0]
        if tag == 'var': return t[1] not in bound and self.unknownish(t[1])
        if tag == 'app': return self.mentions(t[1], bound, inside_quotes) or any(self.mentions(a, bound, inside_quotes) for a in t[2])
        if tag == 'lam': return self.mentions(t[2], bound | {p[0] for p in t[1]}, inside_quotes)
        if tag == 'quote': return inside_quotes and self.mentions(t[1], bound, inside_quotes)
        return False

    def is_prop(self, c): return self.norm(c) == PROP

    # ------------------------------------------------------------ declarations and facts
    def declare(self, name, t):
        ps, r = chain(t)
        if r == K('𝒦'):
            if any(p != K('𝒦') for p in ps): raise ImoTypeError(f"{name}: a class constructor takes classes only")
            self.classes[name] = len(ps); return
        if r == K('𝒮'):
            self.statement_formers.add(name); return
        self.wf(t)
        self.sigs.setdefault(name, [])
        if t not in self.sigs[name]: self.sigs[name].append(t)

    def fact(self, term):
        if term[0] != 'app' or term[1][0] != 'var' or term[1][1] not in self.statement_formers:
            raise ImoTypeError(f"not a declared statement: {term}")
        head, args = term[1][1], term[2]
        if head == '⊆':
            a, b = term_to_type(args[0]), term_to_type(args[1]); self.wf(a); self.wf(b)
            self.facts.append((a, b))
        elif head == '≣':
            a, b = term_to_type(args[0]), term_to_type(args[1]); self.wf(a); self.wf(b)
            assert a[0] == 'K' and not a[2], "class equation: left side must be an atomic class"
            self.eqs[a[1]] = b
        elif head == '↪':
            f = args[0][1]
            if f not in self.sigs: raise ImoTypeError(f"coercion {f} is not declared")
            self.coercions.append(f)
        else:
            raise ImoTypeError(f"unknown statement {head}")

    # ------------------------------------------------------------ terms
    def entries_for(self, head):
        """candidate (symbol, class) pairs for a head symbol"""
        names = self.overloads.get(head, [head]) if head not in self.local_names else [head]
        out = []
        for n in names:
            if n not in self.sigs: raise ImoTypeError(f"undeclared symbol {n}")
            out += [(n, e) for e in self.sigs[n]]
        return out

    def try_apply(self, entry, args):
        """apply a class `entry` to args [(class, term)].  -> (result class, new args, cost) or None"""
        S, cost, new = {}, 0, []
        t = entry
        i = 0
        while i < len(args):
            t = self.norm(t)
            if not (t[0] == 'K' and t[1] == ARROW): return None
            p = t[2][0]; A, term = args[i]
            if self.match(p, A, S, 'pos'):
                new.append(term)
            else:
                best = None
                for c in self.coercions:
                    for ce in self.sigs[c]:
                        cps, cr = chain(ce)
                        if len(cps) != 1: continue
                        S1 = dict(S)
                        if self.leq(A, cps[0]) and self.match(p, subst(cr, {}), S1, 'pos'):
                            if best is None or self.leq(cr, best[1]):
                                best = (c, cr, S1)
                if best is None: return None
                S.clear(); S.update(best[2])
                new.append(('app', ('var', best[0]), [term])); cost += COERCION_COST.get(best[0], 1)
            t = t[2][1]                     # keep class variables open: later arguments may still widen them (join)
            i += 1
        return subst(t, S, flex=True), new, cost

    def resolve_app(self, head, args, label):
        cands = []
        for name, entry in self.entries_for(head):
            r = self.try_apply(entry, args)
            if r is not None: cands.append((name, entry, r))
        if not cands:
            shown = ', '.join(f"{n} ∶ {show_type(e)}" for n, e in self.entries_for(head))
            got = ', '.join(show_type(a[0]) for a in args)
            raise ImoTypeError(f"no declaration of {label} accepts ({got});  candidates: {shown}")
        mn = min(c[2][2] for c in cands)
        cands = [c for c in cands if c[2][2] == mn]
        def more_specific(c1, c2):
            p1, _ = chain(c1[1]); p2, _ = chain(c2[1])
            n = min(len(args), len(p1), len(p2))
            return all(self.leq(x, y) for x, y in zip(p1[:n], p2[:n]))
        best = [c for c in cands if all(more_specific(c, d) for d in cands)]
        if len(best) != 1 and len({(c[0], str(c[2][0])) for c in best or cands}) != 1:
            shown = '; '.join(f"{c[0]} ∶ {show_type(c[1])}" for c in cands)
            raise ImoTypeError(f"ambiguous use of {label}: {shown}")
        c = (best or cands)[0]
        return c[0], c[2][0], c[2][1]

    def synth(self, t, loc):
        tag = t[0]
        if tag == 'num': return num_class(t[1]), t
        if tag == 'chr': return K('𝕮'), t
        if tag == 'str': return K('𝕊'), t
        if tag == 'var':
            n = t[1]
            if n in loc: return loc[n], t
            ents = self.entries_for(n) if True else None
            if len(ents) != 1:
                raise ImoTypeError(f"{n} is overloaded ({len(ents)} declarations): use it applied to arguments")
            name, e = ents[0]
            return subst(e, {}, flex=True), ('var', name)
        if tag == 'asc':
            self.wf(t[2])
            got, term = self.synth(t[1], loc)
            fixed = self.fit(term, got, t[2])
            if fixed is not None: return t[2], fixed
            raise ImoTypeError(f"ascription: a term of class {show_type(got)} is not in {show_type(t[2])}")
        if tag == 'lam':
            loc2 = dict(loc); ps = []
            for n, ty in t[1]:
                if ty is None: raise ImoTypeError(f"binder {n} has no class: write ({n} ∶ class ↦ …)")
                self.wf(ty); loc2[n] = ty; ps.append(ty)
            rt, body = self.synth(t[2], loc2)
            return mk_chain(ps, rt), ('lam', t[1], body)
        if tag == 'quote': return PROP, t
        if tag == 'app':
            args = [self.synth(a, loc) for a in t[2]]
            f = t[1]
            if f[0] == 'var' and f[1] not in loc:
                try:
                    name, rt, new = self.resolve_app(f[1], args, f[1])
                except ImoTypeError:
                    joined = self.join_list(t, loc)              # [a statement, false, …]: a list literal whose elements meet in Ω
                    if joined is None: raise
                    return joined
                return self.statement(name, rt, new, loc)
            ft, fterm = self.synth(f, loc)
            r = self.try_apply(ft, args)
            if r is None:
                raise ImoTypeError(f"cannot apply a function of class {show_type(ft)} to ({', '.join(show_type(a[0]) for a in args)})")
            return r[0], ('app', fterm, r[1])
        raise ImoTypeError(f"bad term {t}")

    def statement(self, name, rt, new, loc):
        """the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one"""
        app = ('app', ('var', name), new)
        bound = frozenset(loc)
        if name in REL_R and len(new) == 2:                  # a relation on ℝ[i] is decided by logic, from the definitions
            return PROP, ('quote', app, dict(loc))
        if name in CONN_O and self.is_prop(rt):              # a connective with a statement operand: one statement, simplified together
            return PROP, ('quote', app, dict(loc))
        r = self.norm(rt)
        if (r == PROP or r == K('𝔹')) and any(self.mentions(a, bound) for a in new):
            return PROP, ('quote', app, dict(loc))           # about an unknown: a statement, not a computation (x == 1, p(x), …)
        return rt, app

    def join_list(self, t, loc):
        """a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values
        are made statements (prop).  None when that is not the case."""
        items, tail = [], t
        while tail[0] == 'app' and tail[1][0] == 'var' and tail[1][1] in ('∷', 'hum:cons') and tail[1][1] not in loc and len(tail[2]) == 2:
            items.append(tail[2][0]); tail = tail[2][1]
        if not items or '∷' not in self.sigs: return None
        el = [self.synth(x, loc) for x in items]
        tc, tt = self.synth(tail, loc)
        if not (any(self.is_prop(c) for c, _ in el) or self.norm(tc) == K('𝔏', PROP)) or not self.leq(tc, K('𝔏', PROP)): return None
        out = tt
        for c, x in reversed(el):
            if self.is_prop(c): pass
            elif self.leq(c, K('𝔹')): x = ('app', ('var', 'prop'), [x])
            else: return None
            out = ('app', ('var', '∷'), [x, out])
        return K('𝔏', PROP), out

    def fit(self, term, got, want):
        """term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair
        literal, or — for a λ — by fitting its body.  None when it does not fit."""
        if self.leq(got, want): return term
        fixed = None
        for c in self.coercions:
            for ce in self.sigs[c]:
                cps, cr = chain(ce)
                if len(cps) == 1 and self.leq(got, cps[0]) and self.leq(cr, want):
                    fixed = ('app', ('var', c), [term])
        if fixed is not None: return fixed
        g, w = self.norm(got), self.norm(want)
        if term == ('var', '⊘') and w[0] == 'K' and w[1] == '𝔏': return term
        if term[0] == 'app' and term[1][0] == 'var' and len(term[2]) == 2 and g[0] == 'K' and w[0] == 'K' and g[1] == w[1]:
            if term[1][1] == '∷' and g[1] == '𝔏':             # [a, b, …] — each element made to fit
                h, t = self.fit(term[2][0], g[2][0], w[2][0]), self.fit(term[2][1], got, want)
                if h is not None and t is not None: return ('app', ('var', '∷'), [h, t])
            if term[1][1] == '⊗' and g[1] == '𝔓':             # pair(a, b)
                x, y = self.fit(term[2][0], g[2][0], w[2][0]), self.fit(term[2][1], g[2][1], w[2][1])
                if x is not None and y is not None: return ('app', ('var', '⊗'), [x, y])
        if term[0] == 'lam':
            n = len(term[1])
            pg, rg = chain(g); pw, rw = chain(w)
            if len(pg) >= n and len(pw) >= n and all(self.leq(b, a) for a, b in zip(pg[:n], pw[:n])):
                body = self.fit(term[2], mk_chain(pg[n:], rg), mk_chain(pw[n:], rw))
                if body is not None: return ('lam', term[1], body)
        return None

    def settle_taint(self, defs):
        """after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies)"""
        self.taint = {n: False for n, _, _ in defs}
        changed = True
        while changed:
            changed = False
            for n, ps, body in defs:
                if not self.taint[n] and self.mentions(body, frozenset(ps)):
                    self.taint[n] = True; changed = True

    # ------------------------------------------------------------ statements
    def check_statement(self, st, trusted):
        kind = st[0]
        if kind == 'decl':
            self.declare(st[1], st[2])
            if not trusted and st[1] in self.unknowns:
                if len(self.sigs.get(st[1], [])) > 1:
                    raise ImoTypeError(f"{st[1]} is declared but never defined, so it is an unknown, and an unknown has one class")
                k = self.domain(st[2])
                if k is None:
                    raise ImoTypeError(f"{st[1]} is declared but never defined, so it is an unknown; an unknown must be a number "
                                       f"(a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not {show_type(st[2])}")
                self.unknowns[st[1]] = k
            return st
        if kind == 'fact':
            self.fact(st[1]); return st
        name, params, body = st[1], st[2], st[3]
        if name in self.defined: raise ImoTypeError(f"{name} is defined twice")
        if name not in self.sigs:
            raise ImoTypeError(f"{name} is defined before it is declared:  write  {name} ∶ <class>  first")
        self.defined.add(name)
        if trusted: return st
        self.local_names = set()
        out = None
        for entry in self.sigs[name]:
            ps, r = chain(entry)
            if len(params) > len(ps):
                raise ImoTypeError(f"{name} has {len(params)} parameters but its class {show_type(entry)} has only {len(ps)}")
            loc = {p: ps[i] for i, p in enumerate(params)}
            self.local_names = set(loc)
            want = mk_chain(ps[len(params):], r)
            got, newbody = self.synth(body, loc)
            fixed = self.fit(newbody, got, want)          # as it is, or through one coercion on the result
            if fixed is None:
                raise ImoTypeError(f"{name}: the body has class {show_type(got)} but {show_type(want)} was declared")
            newbody = fixed
            if out is None:
                out = ('def', name, params, newbody)
                self.taint[name] = self.mentions(newbody, frozenset(params))    # its value needs the value of an unknown
        return out

    local_names = frozenset()
