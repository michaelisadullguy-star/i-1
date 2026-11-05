"""
syntax.py -- the SPEC notation reader of i-1.

spec text  ->  statements:
    ('def',  name, params, body)        name x y ≔ term
    ('decl', name, type)                name ∶ type
    ('fact', term)                      (⊆ A B)   (≣ A B)   (↪ f)
Named term AST:
    ('num', text) ('chr', codepoint) ('str', python_str) ('var', name)
    ('app', f, [args]) ('lam', [(name, type|None)], body)
Types:  ('K', name, (args...))  class constructor application;  ('V', name)  class variable;   '→' is the constructor of functions.
Comment: everything after the name ⍝ up to the end of the line.
"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import imo_core
from base_b import to_digits, numeral

CLASS_VARS = {'α', 'β', 'γ', 'δ', 'ε'}      # class variables (a declaration's classes are universally quantified over them)
RESERVED = {'≔', '↦', '∶'}

# ------------------------------------------------------------------ lexer
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
            assert s.count('.') <= 1, f"bad numeral {s!r} (spec notation allows one radix point)"
            toks.append(('NUM', s)); i = j
        elif c in '\'"':
            q, j, buf = c, i + 1, []
            while j < n and text[j] != q:
                if text[j] == '\\':
                    j += 1
                    buf.append({'n': '\n', 't': '\t'}.get(text[j], text[j]))
                else:
                    buf.append(text[j])
                j += 1
            assert j < n, "unterminated literal"
            s = ''.join(buf)
            if q == "'":
                assert len(s) == 1, f"char literal needs exactly one character: {s!r}"
                toks.append(('CHR', ord(s)))
            else:
                toks.append(('STR', s))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()01.\'"': j += 1
            name = text[i:j]
            if name == '⍝':                       # comment to end of line
                while i < n and text[i] != '\n': i += 1
                continue
            toks.append(('NAME', name)); i = j
    return toks

def logical_lines(toks):
    lines, cur = [], []
    for t in toks:
        if t[0] == 'NL':
            if cur: lines.append(cur); cur = []
        else:
            cur.append(t)
    if cur: lines.append(cur)
    return lines

def match(ts, i):
    depth, k = 0, i
    while True:
        if ts[k][0] == '(': depth += 1
        elif ts[k][0] == ')':
            depth -= 1
            if depth == 0: return k
        k += 1

# ------------------------------------------------------------------ terms
def parse_term_item(ts, i):
    t = ts[i]
    if t[0] == 'NUM': return ('num', t[1]), i + 1
    if t[0] == 'CHR': return ('chr', t[1]), i + 1
    if t[0] == 'STR': return ('str', t[1]), i + 1
    if t[0] == 'NAME': return ('var', t[1]), i + 1
    assert t[0] == '(', f"unexpected {t}"
    close = match(ts, i)
    arrow, depth = None, 0
    for k in range(i + 1, close):
        if ts[k][0] == '(': depth += 1
        elif ts[k][0] == ')': depth -= 1
        elif depth == 0 and ts[k] == ('NAME', '↦'): arrow = k
    if arrow is not None:
        params = parse_binders(ts, i + 1, arrow)
        body = parse_term_seq(ts, arrow + 1, close)
        return ('lam', params, body), close + 1
    return parse_term_seq(ts, i + 1, close), close + 1

def parse_binders(ts, a, b):
    out, k = [], a
    while k < b:
        assert ts[k][0] == 'NAME', f"bad binder {ts[k]}"
        name = ts[k][1]; k += 1
        ty = None
        if k < b and ts[k] == ('NAME', '∶'):
            k += 1
            ty, k = parse_type_atom(ts, k)
        out.append((name, ty))
    return out

def parse_term_seq(ts, i, end):
    items = []
    while i < end:
        a, i = parse_term_item(ts, i)
        items.append(a)
    assert items, "empty application"
    return items[0] if len(items) == 1 else ('app', items[0], items[1:])

# ------------------------------------------------------------------ types
def parse_type_atom(ts, i):
    t = ts[i]
    if t[0] == 'NAME':
        return (('V', t[1]) if t[1] in CLASS_VARS else ('K', t[1], ())), i + 1
    assert t[0] == '(', f"bad type {t}"
    close = match(ts, i)
    inner = ts[i + 1:close]
    return parse_type_seq(inner), close + 1

def parse_type_seq(inner):
    if not inner: raise AssertionError("empty type")
    if inner[0] == ('NAME', '→'):                       # explicit application form (→ A B)
        args, k = [], 1
        while k < len(inner):
            a, k = parse_type_atom(inner, k); args.append(a)
        assert len(args) == 2, "→ takes two classes"
        return ('K', '→', tuple(args))
    depth, cut = 0, None
    for k, t in enumerate(inner):
        if t[0] == '(': depth += 1
        elif t[0] == ')': depth -= 1
        elif depth == 0 and t == ('NAME', '→'):
            cut = k; break
    if cut is not None:                                 # arrow chain  A → B → C  (right associative)
        left = parse_type_seq(inner[:cut]); right = parse_type_seq(inner[cut + 1:])
        return ('K', '→', (left, right))
    head, k = parse_type_atom(inner, 0)
    args = []
    while k < len(inner):
        a, k = parse_type_atom(inner, k); args.append(a)
    if not args: return head
    assert head[0] == 'K' and not head[2], f"bad class application {head}"
    return ('K', head[1], tuple(args))

def show_type(t):
    if t[0] == 'V': return t[1]
    if t[0] == 'F': return '⊥'
    name, args = t[1], t[2]
    if name == '→':
        l = show_type(args[0])
        if args[0][0] == 'K' and args[0][1] == '→': l = f'({l})'
        return f'{l} → {show_type(args[1])}'
    if not args: return name
    return f'({name} ' + ' '.join(f'({show_type(a)})' if a[0] == 'K' and a[1] == '→' else show_type(a) for a in args) + ')'

# ------------------------------------------------------------------ statements
def parse_statements(text):
    out = []
    for ln in logical_lines(lex(text)):
        if ('NAME', '≔') in [t for t in ln]:
            # find the first top-level ≔
            depth, a = 0, None
            for k, t in enumerate(ln):
                if t[0] == '(': depth += 1
                elif t[0] == ')': depth -= 1
                elif depth == 0 and t == ('NAME', '≔'): a = k; break
            assert a is not None
            head = [t[1] for t in ln[:a]]
            assert head and all(t[0] == 'NAME' for t in ln[:a]), f"bad definition head {head}"
            body = parse_term_seq(ln, a + 1, len(ln))
            out.append(('def', head[0], head[1:], body))
        elif len(ln) >= 3 and ln[1] == ('NAME', '∶'):
            assert ln[0][0] == 'NAME'
            out.append(('decl', ln[0][1], parse_type_seq(ln[2:])))
        else:
            out.append(('fact', parse_term_seq(ln, 0, len(ln))))
    return out

# ------------------------------------------------------------------ erasure to the runtime (de Bruijn) AST
def int_numeral_text(n):
    return numeral(to_digits((n, 0)))

def erase(t, scope=()):
    tag = t[0]
    if tag == 'num': return imo_core.num_ast(t[1])
    if tag == 'chr': return imo_core.num_ast(int_numeral_text(t[1]))
    if tag == 'str':
        r = ('G', '⊘')
        for ch in reversed(t[1]):
            r = ('A', ('A', ('G', '∷'), imo_core.num_ast(int_numeral_text(ord(ch)))), r)
        return r
    if tag == 'var':
        nm = t[1]
        if nm in scope:
            return ('V', scope[::-1].index(nm) + 1)
        return ('G', nm)
    if tag == 'app':
        ast = erase(t[1], scope)
        for a in t[2]: ast = ('A', ast, erase(a, scope))
        return ast
    if tag == 'lam':
        names = [p[0] for p in t[1]]
        ast = erase(t[2], scope + tuple(names))
        for _ in names: ast = ('L', ast)
        return ast
    raise ValueError(tag)

def erase_def(name, params, body):
    ast = erase(body, tuple(params))
    for _ in params: ast = ('L', ast)
    return (name, ast)

def expand_literals(t):
    """a term with its Char and String literals written out as the binary notation writes them (numerals and ∷ … ⊘)"""
    tag = t[0]
    if tag == 'chr': return ('app', ('var', '𝕔'), [('num', int_numeral_text(t[1]))])
    if tag == 'str':
        r = ('var', '⊘')
        for ch in reversed(t[1]): r = ('app', ('var', '∷'), [('app', ('var', '𝕔'), [('num', int_numeral_text(ord(ch)))]), r])
        return r
    if tag == 'app': return ('app', expand_literals(t[1]), [expand_literals(a) for a in t[2]])
    if tag == 'lam': return ('lam', t[1], expand_literals(t[2]))
    return t

def expand_statement(st):
    if st[0] == 'def': return ('def', st[1], st[2], expand_literals(st[3]))
    if st[0] == 'fact': return ('fact', expand_literals(st[1]))
    return st

# ------------------------------------------------------------------ pretty printer (spec text)
def pp_type(t):
    if t[0] == 'V': return t[1]
    name, args = t[1], t[2]
    if name == '→': return f'(→ {pp_type(args[0])} {pp_type(args[1])})'
    return name if not args else '(' + name + ' ' + ' '.join(pp_type(a) for a in args) + ')'

def pp_term(t):
    tag = t[0]
    if tag == 'num': return t[1]
    if tag == 'chr': return "'" + chr(t[1]).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"
    if tag == 'str': return '"' + t[1].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if tag == 'var': return t[1]
    if tag == 'app': return '(' + ' '.join([pp_term(t[1])] + [pp_term(a) for a in t[2]]) + ')'
    if tag == 'lam':
        ps = ' '.join(n if ty is None else f'{n} ∶ {pp_type(ty)}' for n, ty in t[1])
        return f'({ps} ↦ {pp_term(t[2])})'
    raise ValueError(tag)

def pp_statement(s):
    if s[0] == 'def':
        return ' '.join([s[1]] + list(s[2])) + ' ≔ ' + pp_term(s[3])
    if s[0] == 'decl': return f'{s[1]} ∶ {pp_type(s[2])}'
    return pp_term(s[1])
