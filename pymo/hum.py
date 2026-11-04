r"""
hum.py -- the HUMAN notation of i-1 and doc 2.

doc 2 line   <hum symbol> := <rhs> | <rhs> | ...  ; <role>          (⍝ starts a comment)
    rhs   a spec symbol, or a bin symbol (a numeral such as 11, or .B.)
    role  class | value | literal | infixl P | infixr P | infix P | prefix P
    several rhs  = an overload set; the checker picks one by the classes of the arguments.

human statements (one per logical line)
    name in Class := expr                      declaration + definition
    name in Class                              declaration only: an UNKNOWN of a number class (docs/predicates.md)
    name(x, y) in A -> B -> C := expr          parameters take their classes from the declaration
    A subseteq B                               fact (⊆ A B)
human terms
    1, 12, 3.25   "text"  'c'   f(a, b)   a + b   a - b   -a   a * b   a / b   a == b   a geq b   (e in Class)
    x in Class |-> body                        lambda (binder classes are mandatory)
classes
    \NN \ZZ \QQ \RR \Z \Q \R \CC \D  Bool Char String  List(A) Stream(A) Alg(A)  A -> B
"""
import re, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from syntax import int_numeral_text, CLASS_VARS

# ------------------------------------------------------------------ doc 2
class Doc2:
    def __init__(self):
        self.entries = []          # dict(hum, rhs, role, prec)

    @classmethod
    def parse(cls, text):
        d = cls()
        for ln in text.split('\n'):
            ln = ln.strip()
            if not ln or ln.startswith('⍝'): continue
            ln = ln.split(' ⍝ ')[0]
            head, rest = ln.split(' := ', 1)
            rhs, _, role = rest.rpartition(' ; ')
            role = role.split()
            d.entries.append(dict(hum=head.strip(), rhs=[x.strip() for x in rhs.split(' | ')],
                                  role=role[0], prec=int(role[1]) if len(role) > 1 else None))
        return d

    def find(self, hum, roles):
        for e in self.entries:
            if e['hum'] == hum and e['role'] in roles: return e
        return None

    def overload_table(self):
        """key -> [spec symbols]  (bin-literal right-hand sides are handled by the reader, not listed here)"""
        t = {}
        for e in self.entries:
            if e['role'] in ('class', 'literal', 'syntax'): continue
            key = 'hum:prefix ' + e['hum'] if e['role'] == 'prefix' else 'hum:' + e['hum']
            t[key] = [x for x in e['rhs'] if not re.fullmatch(r'[01.]+', x)]
        return t

# ------------------------------------------------------------------ lexer
TOKEN = re.compile(r"""\s*(?:
    (?P<num>\d+(?:\.\d+)?)|
    (?P<str>"(?:[^"\\]|\\.)*")|
    (?P<chr>'(?:[^'\\]|\\.)')|
    (?P<mac>\\[A-Za-z]+)|
    (?P<id>[A-Za-z_][A-Za-z_0-9]*)|
    (?P<op>:=|\|->|->|==|!=|\+\+|[-+*/^(),\[\]])
)""", re.X)

def unescape(s):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), s)

def lex_hum(line):
    pos, out = 0, []
    line = line.rstrip()
    while pos < len(line):
        m = TOKEN.match(line, pos)
        if not m or m.end() == pos: raise SyntaxError(f"human notation: cannot read {line[pos:pos+12]!r}")
        pos = m.end()
        k = m.lastgroup; v = m.group(k)
        if k == 'str': out.append(('STR', unescape(v[1:-1])))
        elif k == 'chr': out.append(('CHR', ord(unescape(v[1:-1]))))
        elif k in ('id', 'mac'): out.append(('ID', v))
        elif k == 'num': out.append(('NUM', v))
        else: out.append(('OP', v))
    return out

def logical_lines(text):
    """a logical line ends at a newline outside parentheses; `--` starts a comment"""
    lines, cur, depth = [], '', 0
    for ln in text.split('\n'):
        ln = ln.split('--')[0] if '--' in ln and '"' not in ln else ln
        cur += ' ' + ln
        depth += ln.count('(') - ln.count(')') + ln.count('[') - ln.count(']')
        if depth <= 0:
            if cur.strip(): lines.append(cur.strip())
            cur, depth = '', 0
    if cur.strip(): lines.append(cur.strip())
    return lines

# ------------------------------------------------------------------ parser
class Hum:
    def __init__(self, doc2):
        self.doc = doc2
        self.infix = {}
        self.prefix = {}
        for e in doc2.entries:
            if e['role'] in ('infixl', 'infixr', 'infix'): self.infix[e['hum']] = (e['prec'], e['role'])
            if e['role'] == 'prefix': self.prefix[e['hum']] = e['prec']

    # -- classes
    def class_atom(self, ts, i):
        t = ts[i]
        if t == ('OP', '('):
            c, i = self.class_expr(ts, i + 1)
            assert ts[i] == ('OP', ')'), "missing )"
            return c, i + 1
        assert t[0] == 'ID', f"class expected, found {t}"
        e = self.doc.find(t[1], ('class',))
        if e is None: raise SyntaxError(f"{t[1]} is not a class in doc 2")
        name = e['rhs'][0]
        if name in CLASS_VARS: return ('V', name), i + 1
        args = []
        if i + 1 < len(ts) and ts[i + 1] == ('OP', '('):
            i += 2
            while True:
                a, i = self.class_expr(ts, i); args.append(a)
                if ts[i] == ('OP', ','): i += 1; continue
                assert ts[i] == ('OP', ')'), "missing ) in class"; i += 1; break
            return ('K', name, tuple(args)), i
        return ('K', name, ()), i + 1

    def class_expr(self, ts, i):
        left, i = self.class_atom(ts, i)
        if i < len(ts) and ts[i] == ('OP', '->'):
            right, i = self.class_expr(ts, i + 1)
            return ('K', '→', (left, right)), i
        return left, i

    # -- terms
    def number(self, text):
        if '.' not in text: return ('num', int_numeral_text(int(text)))
        a, b = text.split('.')
        n, d = int(a + b), 10 ** len(b)
        return ('app', ('var', 'hum:/'), [('num', int_numeral_text(n)), ('num', int_numeral_text(d))])

    def atom(self, ts, i, scope):
        t = ts[i]
        if t[0] == 'NUM': return self.number(t[1]), i + 1
        if t[0] == 'STR': return ('str', t[1]), i + 1
        if t[0] == 'CHR': return ('chr', t[1]), i + 1
        if t == ('OP', '['):                              # list literal  [a, b, c]  =  cons(a, cons(b, cons(c, nil)))
            items, i = [], i + 1
            if ts[i] != ('OP', ']'):
                while True:
                    a, i = self.expr(ts, i, 0, scope); items.append(a)
                    if ts[i] == ('OP', ','): i += 1; continue
                    break
            assert ts[i] == ('OP', ']'), "missing ] in list"
            e = ('var', 'hum:nil')
            for a in reversed(items): e = ('app', ('var', 'hum:cons'), [a, e])
            return e, i + 1
        if t == ('OP', '('):
            e, i = self.expr(ts, i + 1, 0, scope)
            if i < len(ts) and ts[i] == ('ID', 'in'):
                c, i = self.class_expr(ts, i + 1)
                e = ('asc', e, c)
            assert ts[i] == ('OP', ')'), "missing )"
            return e, i + 1
        assert t[0] == 'ID', f"unexpected {t}"
        name = t[1]
        if name not in scope:
            lit = self.doc.find(name, ('literal',))
            if lit is not None and not (i + 1 < len(ts) and ts[i + 1] == ('OP', '(')):
                return ('num', lit['rhs'][0]), i + 1
        head = ('var', name) if (name in scope or self.doc.find(name, ('value',)) is None) else ('var', 'hum:' + name)
        if i + 1 < len(ts) and ts[i + 1] == ('OP', '('):
            args, i = [], i + 2
            if ts[i] == ('OP', ')'): i += 1
            else:
                while True:
                    a, i = self.expr(ts, i, 0, scope); args.append(a)
                    if ts[i] == ('OP', ','): i += 1; continue
                    assert ts[i] == ('OP', ')'), "missing ) in call"; i += 1; break
            return ('app', head, args), i
        return head, i + 1

    def expr(self, ts, i, minprec, scope):
        # lambda:  x in Class |-> body
        if ts[i][0] == 'ID' and i + 1 < len(ts) and ts[i + 1] == ('ID', 'in'):
            name = ts[i][1]
            c, j = self.class_expr(ts, i + 2)
            if j < len(ts) and ts[j] == ('OP', '|->'):
                body, j = self.expr(ts, j + 1, 0, scope | {name})
                return ('lam', [(name, c)], body), j
        # prefix operators
        t = ts[i]
        key = t[1] if t[0] in ('OP', 'ID') else None
        if key in self.prefix and t[0] in ('OP', 'ID') and not (t[0] == 'ID' and key in scope):
            arg, i = self.expr(ts, i + 1, self.prefix[key], scope)
            left = ('app', ('var', 'hum:prefix ' + key), [arg])
        else:
            left, i = self.atom(ts, i, scope)
        while i < len(ts) and ts[i][0] in ('OP', 'ID') and ts[i][1] in self.infix:
            op = ts[i][1]; prec, kind = self.infix[op]
            if prec < minprec: break
            right, i = self.expr(ts, i + 1, prec + 1 if kind != 'infixr' else prec, scope)
            left = ('app', ('var', 'hum:' + op), [left, right])
        return left, i

    # -- statements
    def spec_name(self, name):
        e = self.doc.find(name, ('value',))
        if e is not None and len(e['rhs']) == 1 and not re.fullmatch(r'[01.]+', e['rhs'][0]): return e['rhs'][0]
        return name

    def statement(self, line):
        ts = lex_hum(line)
        # class subseteq class
        for k, t in enumerate(ts):
            if t == ('ID', 'subseteq'):
                a, i = self.class_expr(ts, 0); assert i == k
                b, j = self.class_expr(ts, k + 1); assert j == len(ts)
                return [('fact', ('app', ('var', '⊆'), [type_to_term(a), type_to_term(b)]))]
        assert ts[0][0] == 'ID', f"statement must start with a name: {line!r}"
        name = ts[0][1]; i = 1; params = []
        if ts[i] == ('OP', '('):
            i += 1
            while ts[i] != ('OP', ')'):
                params.append(ts[i][1]); i += 1
                if ts[i] == ('OP', ','): i += 1
            i += 1
        assert ts[i] == ('ID', 'in'), f"declare the class first:  {name} in <Class> := …"
        cls, i = self.class_expr(ts, i + 1)
        if i == len(ts):                                  # name in Class   (no :=) declares an UNKNOWN (docs/predicates.md §2)
            if params: raise SyntaxError(f"{name}: a declaration without := takes no parameters (an unknown is a number)")
            return [('decl', self.spec_name(name), cls)]
        assert ts[i] == ('OP', ':='), "missing :="
        body, j = self.expr(ts, i + 1, 0, set(params))
        assert j == len(ts), f"unexpected {ts[j]}"
        sp = self.spec_name(name)
        return [('decl', sp, cls), ('def', sp, params, body)]

    def statements(self, text):
        out = []
        for ln in logical_lines(text): out += self.statement(ln)
        return out

def type_to_term(t):
    if t[0] == 'V': return ('var', t[1])
    if not t[2]: return ('var', t[1])
    return ('app', ('var', t[1]), [type_to_term(a) for a in t[2]])
