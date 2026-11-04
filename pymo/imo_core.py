"""
imo.py -- reader + lazy evaluator for  i-1  (source files: *.imo).

Axiomic alphabet:   1 0 . <space> ( ) <newline>
Numerals:   a maximal run of 0/1 with at most one radix point is a number of Q[i], written in base i-1.
            `101`    is the Gaussian integer  1 + (i-1)^2  as the fraction  101 / 1
            `0.1`    is  1 / (i-1)          (digits after the point divide by (i-1)^k)
            The foundation is the Gaussian integers: a Gaussian integer is a lazy list of digits, least significant first.
            A Gaussian rational is built from them, a pair (numerator, denominator); the reader holds every numeral as such a
            pair (a Gaussian integer with denominator 1), so one set of operations serves integers and fractions.
Terms:      numeral | name | ( t t ... )  application | ( x y ... ↦ t )  abstraction
Programs:   one definition per logical line:   name x y ... ≔ term      (names may be recursive)
Everything that is not 1 0 . space ( ) newline is a name (non-axiomic).
Evaluation is lazy (call-by-need), so infinite objects (streams, function spaces) are ordinary values.
"""
import sys, threading

# ------------------------------------------------------------ lexer
def lex(text):
    toks, i, n, depth = [], 0, len(text), 0
    while i < n:
        c = text[i]
        if c in ' \t\r': i += 1
        elif c == '\n':
            if depth == 0: toks.append(('NL',))
            i += 1
        elif c in '()':
            depth += 1 if c == '(' else -1
            toks.append((c,)); i += 1
        elif c in '01.':
            j = i
            while j < n and text[j] in '01.': j += 1
            s = text[i:j]
            assert s.count('.') <= 1, s
            toks.append(('NUM', s)); i = j
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()01.': j += 1
            toks.append(('NAME', text[i:j])); i = j
    return toks

# ------------------------------------------------------------ parser -> de Bruijn AST
# ('V',k) ('L',b) ('A',f,x) ('G',name)
def num_ast(s):
    def int_ast(bits):
        r = ('G', '⊥')
        for ch in bits:                      # MSB first -> build LSB-first list from the top down
            r = ('A', ('A', ('G', '∷'), ('G', '⊤' if ch == '1' else '⊥')), r)
        return r
    if '.' not in s:
        return ('A', ('A', ('G', '⊗'), int_ast(s)), int_ast('1'))
    a, b = s.split('.')
    bits = a + b
    assert bits, "empty numeral"
    den = '1' + '0' * len(b)
    return ('A', ('A', ('G', '⊗'), int_ast(bits)), int_ast(den))

def parse_seq(ts, i, end, scope):
    items = []
    while i < end:
        a, i = parse_item(ts, i, scope)
        items.append(a)
    assert items, "empty application"
    ast = items[0]
    for x in items[1:]:
        ast = ('A', ast, x)
    return ast

def match_paren(ts, i):
    depth = 0
    k = i
    while True:
        if ts[k][0] == '(': depth += 1
        elif ts[k][0] == ')':
            depth -= 1
            if depth == 0: return k
        k += 1

def parse_item(ts, i, scope):
    t = ts[i]
    if t[0] == 'NUM': return num_ast(t[1]), i + 1
    if t[0] == 'NAME':
        nm = t[1]
        if nm in scope:
            return ('V', scope[::-1].index(nm) + 1), i + 1
        return ('G', nm), i + 1
    assert t[0] == '(', t
    close = match_paren(ts, i)
    arrow, depth = None, 0
    for k in range(i + 1, close):
        if ts[k][0] == '(': depth += 1
        elif ts[k][0] == ')': depth -= 1
        elif depth == 0 and ts[k] == ('NAME', '↦'): arrow = k
    if arrow is not None:
        params = [ts[m][1] for m in range(i + 1, arrow)]
        ast = parse_seq(ts, arrow + 1, close, scope + params)
        for _ in params: ast = ('L', ast)
        return ast, close + 1
    return parse_seq(ts, i + 1, close, scope), close + 1

def parse_program(text):
    toks = lex(text)
    lines, cur = [], []
    for t in toks:
        if t[0] == 'NL':
            if cur: lines.append(cur); cur = []
        else: cur.append(t)
    if cur: lines.append(cur)
    defs = []
    for ln in lines:
        a = ln.index(('NAME', '≔'))
        head = [t[1] for t in ln[:a]]
        name, params = head[0], head[1:]
        ast = parse_seq(ln, a + 1, len(ln), params)
        for _ in params: ast = ('L', ast)
        defs.append((name, ast))
    return defs

# ------------------------------------------------------------ evaluator (call-by-need)
class Th:
    __slots__ = ('f', 'v')
    def __init__(s, f): s.f = f
    def force(s):
        f = s.f
        if f is not None:
            s.v = f(); s.f = None
        return s.v
class Val:
    """an argument that is already a value (a lambda, a global function): forcing it is free"""
    __slots__ = ('v',)
    def __init__(s, v): s.v = v
    def force(s): return s.v
def done(v): return Val(v)

class Machine:
    """compiles the de Bruijn terms of all definitions to Python closures (call-by-need, same semantics as a graph reducer):
       * a bound variable is a Python local holding a thunk; a global is a shared thunk;
       * an argument is passed as a thunk, except variables, globals and lambdas, which need none;
       * every closed sub-term (numerals, string literals, ...) is evaluated at most once for the whole run (it is floated out);
       * sub-terms nested too deeply for one Python expression are lifted into helper functions of their free variables."""
    DEEP = 40

    def __init__(self, defs):
        self.G = {}
        for name, ast in defs:
            assert name not in self.G, name
            self.G[name] = Th(None); self.G[name].f = _unset(name)
        missing = set()
        def scan(a):
            if a[0] == 'G':
                if a[1] not in self.G: missing.add(a[1])
            elif a[0] == 'L': scan(a[1])
            elif a[0] == 'A': scan(a[1]); scan(a[2])
        for _, a in defs: scan(a)
        assert not missing, missing
        self.ns = {'Th': Th, 'done': Val}
        self.fun = {name for name, ast in defs if ast[0] == 'L'}     # globals whose value is a lambda: bound directly
        self.gname = {}
        self.consts = {}                 # closed term -> name of its shared thunk
        self.out = []                    # generated helper definitions
        self.n = 0
        self.arity, self.uncurried = {}, {}
        for name, ast in defs:                         # a global function of n parameters is also a Python function of n arguments
            if ast[0] == 'L':
                n, b = 0, ast
                while b[0] == 'L': n += 1; b = b[1]
                self.arity[name] = n
        bodies = []
        for name, ast in defs:
            if name in self.arity:
                n, b = self.arity[name], ast
                for _ in range(n): b = b[1]
                self.uncurried[name], _ = self.value(b, n)
                e = None
            else:
                e, _ = self.value(ast, 0)
            bodies.append((name, e))
        src = '\n'.join(self.out) + '\n'
        for name, e in bodies:
            if name in self.fun:
                n = self.arity[name]
                ps = ', '.join(f'v{k}' for k in range(n))
                src += f'def {self.Fname(name)}({ps}):\n    return {self.uncurried[name]}\n'
                cur = f'{self.Fname(name)}({ps})'
                for k in reversed(range(n)): cur = f'(lambda v{k}: {cur})'
                src += f'{self.fname(name)} = {cur}\n'
        src += 'def _install(G):\n    pass\n'
        for name, e in bodies:
            if name not in self.fun: src += f'    G[{name!r}].f = (lambda: {e})\n'
        exec(compile(src, '<imo>', 'exec'), self.ns)
        for name in self.fun:
            self.G[name].f = None; self.G[name].v = self.ns[self.fname(name)]
        self.ns['_install'](self.G)

    # -- names
    def g(self, name):
        if name not in self.gname:
            k = f'g{len(self.gname)}'; self.gname[name] = k; self.ns[k] = self.G[name]
        return self.gname[name]
    def fname(self, name):
        self.g(name); return 'f' + self.gname[name][1:]
    def Fname(self, name):
        self.g(name); return 'F' + self.gname[name][1:]
    def fresh(self, p):
        self.n += 1; return f'{p}{self.n}'

    @staticmethod
    def free(t, d, acc, d0=None):
        """levels (0-based, from the root) of the variables free in t — bound outside t — for t at binder depth d"""
        if d0 is None: d0 = d
        if t[0] == 'V':
            if t[1] <= d and d - t[1] < d0: acc.add(d - t[1])
        elif t[0] == 'L': Machine.free(t[1], d + 1, acc, d0)
        elif t[0] == 'A': Machine.free(t[1], d, acc, d0); Machine.free(t[2], d, acc, d0)
        return acc

    def closed(self, t, d):
        return not Machine.free(t, d, set())

    def const(self, t):
        key = repr(t)
        if key not in self.consts:
            e, _ = self.value(t, 0)
            k = self.fresh('c'); self.consts[key] = k
            self.ns[k] = Th(None)
            self.out.append(f'{k}.f = (lambda: {e})')
        return self.consts[key]

    def lift(self, t, d, e):
        """turn an expression that is nested too deeply into a call of a helper function of its free variables"""
        fv = sorted(Machine.free(t, d, set()))
        args = ', '.join(f'v{l}' for l in fv)
        h = self.fresh('h')
        self.out.append(f'def {h}({args}):\n    return {e}')
        return f'{h}({args})', 1

    # -- code generation:  value(t, d) -> python expression for the value (WHNF) of t;  thunk(t, d) -> expression for a thunk of t
    def value(self, t, d):
        tag = t[0]
        if tag == 'G': return (self.fname(t[1]) if t[1] in self.fun else f'{self.g(t[1])}.force()'), 1
        if tag == 'V': return f'v{d - t[1]}.force()', 1
        if tag == 'L':
            b, nb = self.value(t[1], d + 1)
            e, n = f'(lambda v{d}: {b})', nb + 1
        else:
            if d > 0 and self.closed(t, d):
                return f'{self.const(t)}.force()', 1
            spine = []
            while t[0] == 'A': spine.append(t[2]); t = t[1]
            spine.reverse()
            if t[0] == 'G' and t[1] in self.arity and len(spine) >= self.arity[t[1]]:
                k = self.arity[t[1]]                    # a saturated call of a global function: one Python call
                xs = [self.thunk(a, d) for a in spine[:k]]
                n = max([x[1] for x in xs] + [0]) + 1
                parts = [f"{self.Fname(t[1])}({', '.join(x[0] for x in xs)})"]
                spine = spine[k:]
            else:
                f, n = self.value(t, d)
                parts = [f]
            for a in spine:
                x, na = self.thunk(a, d)
                parts.append(f'({x})'); n = max(n, na + 1)
            e = ''.join(parts); n += 1
            t = None
        if n > self.DEEP and t is not None:
            return self.lift(t, d, e)
        return e, n

    def thunk(self, t, d):
        tag = t[0]
        if tag == 'G': return self.g(t[1]), 0
        if tag == 'V': return f'v{d - t[1]}', 0
        if tag == 'A' and self.closed(t, d): return self.const(t), 0
        e, n = self.value(t, d)
        if n > self.DEEP:
            e, n = self.lift(t, d, e)
        if tag == 'L': return f'done({e})', n + 1
        return f'Th(lambda: {e})', n + 1

    def val(self, name): return self.G[name].force()

def _unset(name):
    def f(): raise RuntimeError(f"{name} has no compiled body")
    return f

# ------------------------------------------------------------ decoding
TT, FF = done('T'), done('F')
def to_bool(v): return v(TT)(FF) == 'T'
CONS_TH = done(lambda h: lambda t: ('C', h, t))
NIL_TH = done(('N',))
def to_list(v):
    out = []
    r = v(CONS_TH)(NIL_TH)
    while r[0] == 'C':
        out.append(1 if to_bool(r[1].force()) else 0)
        r = r[2].force()(CONS_TH)(NIL_TH)
    return out
PAIR_TH = done(lambda a: lambda b: (a, b))
def to_pair(v):
    a, b = v(PAIR_TH)
    return a.force(), b.force()
def stream_nth(v, n):
    for _ in range(n):
        r = v(CONS_TH)(NIL_TH)
        v = r[2].force()
    r = v(CONS_TH)(NIL_TH)
    return r[1].force()

def list_value(M, digs):
    """python digit list (LSB first) -> language value"""
    TV = M.val('⊤'); FV = M.val('⊥'); CONS = M.val('∷')
    v = FV
    for d in reversed(digs):
        v = CONS(done(TV if d else FV))(done(v))
    return v

def load(*paths):
    """parse and link one or more .imo files into a Machine"""
    defs = []
    for p in paths:
        defs += parse_program(open(p, encoding='utf-8').read())
    return Machine(defs)

def run_big(fn):
    sys.setrecursionlimit(10**7)
    threading.stack_size(1 << 29)
    res = {}
    def w():
        try: res['v'] = fn()
        except BaseException as e:
            import traceback; traceback.print_exc(); res['e'] = e
    th = threading.Thread(target=w); th.start(); th.join()
    return res.get('v')
