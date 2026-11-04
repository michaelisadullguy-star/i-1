"""
layers.py -- the three notation systems of i-1 and the system documents that connect them.

  bin   only  1 0 .  space ( ) newline
        numeral      1011  1.01                (≤ 1 radix point)
        symbol       .B.                       B = a bit string (the code of the symbol, see doc 1)
        markers      .  =  ↦      ..  =  ≔      ...  =  ∶
  spec  unicode glyphs; the notation of the prelude (lib/*.imo); `⍝` starts a comment
  hum   ASCII/TeX-like notation (hum.py)

  doc 1   [spec sbl] := [bin sbl]            one line per symbol
  doc 2   [hum sbl]  := [spec sbl] or [bin sbl] ...
"""
import re, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import syntax
from syntax import lex, parse_statements, pp_statement, int_numeral_text

RESERVED_BIN = {'↦': '.', '≔': '..', '∶': '...'}
RESERVED_SPEC = {v: k for k, v in RESERVED_BIN.items()}

# ------------------------------------------------------------------ doc 1
class Doc1:
    def __init__(self):
        self.s2b, self.b2s = {}, {}
        self.local = {}

    @classmethod
    def parse(cls, text):
        d = cls()
        for ln in text.split('\n'):
            ln = ln.strip()
            if not ln or ln.startswith('⍝'): continue
            a, b = [x.strip() for x in ln.split(' := ')]
            assert re.fullmatch(r'\.[01]+\.', b), f"doc1: bad binary symbol {b!r}"
            assert a not in d.s2b and b not in d.b2s, f"doc1: duplicate {a} / {b}"
            d.s2b[a] = b; d.b2s[b] = a
        return d

    def next_code(self):
        n = max([int(b[1:-1], 2) for b in self.b2s] + [0]) + 1
        return '.' + bin(n)[2:] + '.'

    def code(self, name, allow_new):
        if name in self.s2b: return self.s2b[name]
        if not allow_new: raise KeyError(f"{name!r} has no binary symbol in doc 1")
        b = self.next_code()
        self.s2b[name] = b; self.b2s[b] = name; self.local[name] = b
        return b

    def render(self, names=None, header=()):
        lines = [f'⍝ {h}' for h in header]
        for a, b in self.s2b.items():
            if names is None or a in names: lines.append(f'{a} := {b}')
        return '\n'.join(lines) + '\n'

# ------------------------------------------------------------------ bin lexer / translators
def lex_bin(text):
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
            pts = s.count('.')
            if s in RESERVED_SPEC: toks.append(('MARK', s))
            elif pts == 0: toks.append(('NUM', s))
            elif pts == 1: toks.append(('NUM', s))
            elif re.fullmatch(r'\.[01]+\.', s): toks.append(('SYM', s))
            else: raise ValueError(f"bad binary token {s!r}")
            i = j
        else:
            raise ValueError(f"character {c!r} is not part of the binary notation")
    return toks

def render(tokens):
    """tokens -> text (spaces only between atoms; newlines kept)"""
    out, prev = [], None
    for t in tokens:
        if t == 'NL': out.append('\n'); prev = 'NL'; continue
        if t == ')' or prev in (None, '(', 'NL'): out.append(t)
        else: out.append(' ' + t)
        prev = t
    return ''.join(out)

def bin_to_spec_text(text, doc1):
    out = []
    for t in lex_bin(text):
        k = t[0]
        if k == 'NL': out.append('NL')
        elif k in '()': out.append(k)
        elif k == 'NUM': out.append(t[1])
        elif k == 'MARK': out.append(RESERVED_SPEC[t[1]])
        else:
            if t[1] not in doc1.b2s: raise KeyError(f"binary symbol {t[1]} is not defined in doc 1 (or the local table)")
            out.append(doc1.b2s[t[1]])
    return render(out)

def spec_statements_to_bin_text(statements, doc1, allow_new=True):
    out = []
    for st in statements:
        for t in lex(pp_statement(st)):
            k = t[0]
            if k in '()': out.append(k)
            elif k == 'NUM': out.append(t[1])
            elif k == 'NAME': out.append(RESERVED_BIN.get(t[1]) or doc1.code(t[1], allow_new))
            elif k == 'CHR': out += ['(', doc1.code('𝕔', allow_new), int_numeral_text(t[1]), ')']
            elif k == 'STR':
                for ch in t[1]: out += ['(', doc1.code('∷', allow_new), '(', doc1.code('𝕔', allow_new), int_numeral_text(ord(ch)), ')']
                out.append(doc1.code('⊘', allow_new)); out += [')'] * len(t[1])
        out.append('NL')
    return render(out)

def spec_term_to_bin(text, doc1):
    """one spec term (as text) -> the same term in bin notation, through doc 1 (literals are expanded as the reader expands them)"""
    out = []
    for t in lex(text):
        k = t[0]
        if k in '()': out.append(k)
        elif k == 'NUM': out.append(t[1])
        elif k == 'NAME': out.append(RESERVED_BIN.get(t[1]) or doc1.code(t[1], False))
        elif k == 'CHR': out += ['(', doc1.code('𝕔', False), int_numeral_text(t[1]), ')']
        elif k == 'STR':
            for ch in t[1]: out += ['(', doc1.code('∷', False), '(', doc1.code('𝕔', False), int_numeral_text(ord(ch)), ')']
            out.append(doc1.code('⊘', False)); out += [')'] * len(t[1])
    return render(out)

# ------------------------------------------------------------------ files: default notation by extension, `@bin` `@spec` `@hum` section headers
def split_sections(text, default):
    sections, cur, mode = [], [], default
    for ln in text.split('\n'):
        s = ln.strip()
        if s in ('@bin', '@spec', '@hum'):
            if cur: sections.append((mode, '\n'.join(cur))); cur = []
            mode = s[1:]
        else:
            cur.append(ln)
    if cur: sections.append((mode, '\n'.join(cur)))
    return sections

def default_notation(path):
    if path.endswith('.bin.imo'): return 'bin'
    if path.endswith('.hum.imo'): return 'hum'
    return 'spec'
