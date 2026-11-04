"""
output.py -- printing values: the output side of the three notations, and the `main` entry point.

A value is printed as a NORMAL-FORM TERM in the chosen notation, so that what is printed can be read back, in that notation, as a
term that denotes the same value.  Nothing is computed on the host:

  * the normal forms are computed IN THE LANGUAGE:  ⊜ (canonical z/m) for spec and bin numbers, showq / showc (decimal text,
    reduced real and imaginary parts) for human numbers, decimals for the approximations shown next to stream elements;
  * the host walks the value as its declared class describes it (a list cell by cell, a pair as two parts, a tree node by node),
    reads digit strings (a digit is ⊤ or ⊥) and spells them, and turns code points into characters — the isomorphism
    "digit string ↔ Gaussian integer" (base_b.val) is the only arithmetic it ever does, and only to name a character.

`main`
  * main ∶ 𝕊           its text is the output, written as it is (the program formats itself: lib/text.imo);
  * main ∶ 𝔏 𝕊 / 𝔖 𝕊   one line per element (a stream of lines is printed as long as it lasts, or `n` lines);
  * any other class    the value, as a normal-form term in the output notation, and a newline.

Statements (class Prop, spec Ω — docs/predicates.md): a value of Ω is the CODE of a statement in simplest form (computed in the
language by simplify′).  The host spells the code in the human notation (Speller: reverse doc 2, infix with precedences, numbers by
the language's showc); for spec and bin output that text is read again — in the program's context, unknowns declared — by the
human reader and the class checker, and the resulting spec term is printed (bin: re-spelled by doc 1), so every printed statement
reads back.  A Bool that is undetermined (⍰, e.g. decide of a statement that is neither true nor false) is reported, not printed.

The output notation:  `--out bin|spec|hum`  on the command line, else an `@out bin|spec|hum` line in the program, else the notation
in which `main` is defined (a hum program prints hum, a bin program prints bin: output can be pasted back into the same notation).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from imo_core import done, to_bool, to_list, stream_nth, CONS_TH, NIL_TH, PAIR_TH
from base_b import val, numeral, to_digits
from imotypes import K, ImoTypeError, UnknownError
from syntax import show_type, pp_term
import layers, hum

MODES = ('bin', 'spec', 'hum')
NUM = K('ℚ[i]')
PROP = K('Ω')

class PrintError(Exception): pass

UNDETERMINED = ("undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a "
                "relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)")

def cell(v):
    """take a list / string cell apart; ⍰ (an undetermined Boolean inside the text) is reported, never printed as text"""
    r = v(CONS_TH)(NIL_TH)
    if not isinstance(r, tuple): raise PrintError(UNDETERMINED)
    return r

def boolean(v):
    r = v(done('T'))(done('F'))
    if r == 'T': return True
    if r == 'F': return False
    raise PrintError(UNDETERMINED)

def esc(s, q):
    return s.replace('\\', '\\\\').replace(q, '\\' + q).replace('\n', '\\n').replace('\t', '\\t')

class Printer:
    def __init__(self, P, mode, n=10):
        assert mode in MODES, mode
        self.P, self.mode, self.n = P, mode, n
        self.M = P.machine; self.C = P.checker

    # ---------------------------------------------------------------- helpers that call the language
    def call(self, f, *args):
        v = self.M.val(f)
        for a in args: v = v(done(a))
        return v

    def text_of(self, v):
        """a 𝕊 value -> python str (code point by code point)"""
        out, r = [], cell(v)
        while r[0] == 'C':
            out.append(self.char(r[1].force())); r = cell(r[2].force())
        return ''.join(out)

    def char(self, v):
        """a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> python character; its canonical form is a pair (n, 1)"""
        z, m = self.pair(self.call('⊜', v))
        cp = val(to_list(z))
        return chr(cp[0]) if cp[1] == 0 and 0 <= cp[0] <= 0x10FFFF and to_list(m) == [1] else '\ufffd'

    def pair(self, v):
        a, b = v(PAIR_TH)
        return a.force(), b.force()

    def digits(self, v): return numeral(to_list(v))          # a digit string, most significant digit first ('0' for zero)

    # ---------------------------------------------------------------- spelling, by class
    def is_(self, cls, name):
        return self.C.leq(cls, K(name)) and self.C.leq(K(name), cls)

    def term(self, v, cls):
        """the normal-form term of v (of class cls) in spec or hum notation (bin is spelled from spec)"""
        C, hum = self.C, self.mode == 'hum'
        raw = cls
        cls = C.norm(cls)
        if cls[0] != 'K': raise PrintError(f"cannot print a value whose class is not known ({show_type(raw)})")
        head, args = cls[1], cls[2]
        if cls == PROP: return self.statement(v)
        if self.is_(raw, '𝕊') or (head == '𝔏' and args and C.norm(args[0]) == K('𝕮')):
            s = self.text_of(v); return '"' + esc(s, '"') + '"'
        if C.leq(raw, K('𝕮')):
            return "'" + esc(self.char(v), "'") + "'"
        if C.leq(raw, NUM): return self.number(v, raw)
        if head == '𝔹': return ('true' if boolean(v) else 'false') if hum else ('⊤' if boolean(v) else '⊥')
        if head == '𝔒':
            k = v(done(0))(done(1))(done(2))
            return (['less', 'same', 'greater'] if hum else ['⋖', '≖', '⋗'])[k]
        if head == '𝔏':
            el, items, r = args[0], [], cell(v)
            if C.norm(el) == K('𝔹') and not hum:                 # a digit string 𝔇 = 𝔏 𝔹 is a Gaussian integer: (◀ numeral)
                return f"(◀ {self.digits(v)})"
            while r[0] == 'C':
                items.append(self.term(r[1].force(), el)); r = cell(r[2].force())
            if hum: return '[' + ', '.join(items) + ']'
            out = '⊘'
            for x in reversed(items): out = f'(∷ {x} {out})'
            return out
        if head == '𝔓':
            a, b = self.pair(v)
            x, y = self.term(a, args[0]), self.term(b, args[1])
            return f'pair({x}, {y})' if hum else f'(⊗ {x} {y})'
        if head == '𝔗':
            tag, body = self.pair(v)
            if to_bool(tag):
                a, b = self.pair(body)
                x, y = self.term(a, cls), self.term(b, cls)
                return f'node({x}, {y})' if hum else f'(❁ {x} {y})'
            x = self.term(body, args[0])
            return f'leaf({x})' if hum else f'(❀ {x})'
        if head == '𝔖':
            return self.term(stream_nth(v, self.n), args[0])
        if head in ('→', '𝔄'):
            raise PrintError(f"a value of class {show_type(raw)} has no normal form to print (it is a function)")
        raise PrintError(f"cannot print a value of class {show_type(raw)}")

    # ---------------------------------------------------------------- statements (class Ω)
    def statement(self, v):
        """a statement (its code) in the output notation: hum text; spec / bin: that text read again and checked"""
        text = Speller(self).spell(v)
        return text if self.mode == 'hum' else self.reread(text)

    def reread(self, text):
        """the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ,
        inserts ⇡ and prop, and marks statements — the marks are dropped, the term is what a reader of the output reads back"""
        P, C = self.P, self.C
        try:
            ts = hum.lex_hum(text)
            term, j = P.hum.expr(ts, 0, 0, set())
            if j != len(ts): raise SyntaxError(f"unexpected {ts[j]}")
        except (SyntaxError, AssertionError, IndexError) as e:
            raise PrintError(f"the statement {text!r} cannot be read in the human notation ({e})")
        saved, C.local_names = C.local_names, set()
        try:
            cls, t = C.synth(term, {})
            fitted = C.fit(t, cls, PROP)
        except ImoTypeError as e:
            raise PrintError(f"the statement {text!r} does not read back in this program: {e}")
        finally:
            C.local_names = saved
        if fitted is None: raise PrintError(f"{text!r} reads back as a {show_type(cls)}, not as a statement")
        return pp_term(strip_quotes(fitted))

    def number(self, v, cls):
        if self.mode == 'hum':
            f = 'showq' if self.C.leq(cls, K('ℚ')) else 'showc'
            return self.text_of(self.call(f, v))
        z, m = self.pair(self.call('⊜', v))
        zt, mt = self.digits(z), self.digits(m)
        return zt if mt == '1' else f'(÷ {zt} {mt})'

    def comment(self, v, cls):
        """the remark printed after a stream element (none in bin: the binary notation has no comments)"""
        cls = self.C.norm(cls)
        if self.mode == 'bin' or not (cls[0] == 'K' and cls[1] == '𝔖'): return ''
        mark = '--' if self.mode == 'hum' else '⍝'
        el = cls[2][0]
        approx = ''
        if self.C.leq(el, NUM):
            x = stream_nth(v, self.n)
            re = self.text_of(self.call('decimals', self.call('ℜ', x), self.lit(12)))
            im = self.call('ℑ', x)
            if not to_bool(self.call('≐', im, self.lit(0))):
                imt = self.text_of(self.call('decimals', im, self.lit(12)))
                approx = f', ≈ {re} {"-" if imt.startswith("-") else "+"} {imt.lstrip("-")} i'
            else:
                approx = f', ≈ {re}'
        return f'   {mark} element {self.n} of the stream{approx}'

    def lit(self, k):
        """the language value of a small natural number, built from its digits (the reader's numeral expansion)"""
        from base_b import to_digits
        from imo_core import list_value
        return self.call('⊗', list_value(self.M, to_digits((k, 0))), list_value(self.M, [1]))

    def show(self, v, cls):
        t = self.term(v, cls)
        if self.mode == 'bin': t = layers.spec_term_to_bin(t, self.P.doc1)
        return t + self.comment(v, cls)

def strip_quotes(t):
    """a checked term without the statement marks of the class checker"""
    if t[0] == 'quote': return strip_quotes(t[1])
    if t[0] == 'app': return ('app', strip_quotes(t[1]), [strip_quotes(a) for a in t[2]])
    if t[0] == 'lam': return ('lam', t[1], strip_quotes(t[2]))
    return t

# the five constructors of a code (lib/prove.imo):  (code cn cs ca cl cv)
CODE_CB = (done(lambda x: ('n', x)), done(lambda c: ('s', c)), done(lambda f: (lambda a: ('a', f, a))),
           done(lambda b: ('l', b)), done(lambda k: ('v', k)))
FORMULA_ARGS = {'∧', '∨', '¬', '⇒', '⇔', '∧Ω', '∨Ω', '¬Ω', '⇒Ω', '⇔Ω', 'prop', 'decide', 'code_rd'}   # their operands are statements
TRANSPARENT = {'⇡', 'prop', 'decide', 'code_rd'}                       # embeddings: spelled as their argument
TIGHT = {'*', '/', '^'}                                                  # infix operators written without spaces
ASSOC = {'+', '*'}                                                       # right operand not parenthesised at equal precedence

class Speller:
    """the human spelling of the code of a statement (docs/predicates.md §5; the rules are fixed — the engine's tests use them):
         ⊤ true, ⊥ false, ∨ or (2), ∧ and (3; an ∧ directly inside an ∨ is parenthesised), ¬ not (prefix 4), relations == != lt leq
         gt geq (4), + - (6, left), * / (7, left), prefix - (8), ^ (9, right; its base is parenthesised unless atomic), √ ∗ ℜ ℑ as
         sqrt conj re im, root(p, k) with p a coefficient list, any other symbol by its human name (reverse doc 2), unknowns and
         symbols of the program by their own names.  An operand is parenthesised when its precedence is lower than required
         (the right operand of - and / also when it is equal).  A number (𝔮ⁿ q) is spelled by the language's showc; its
         precedence: a non-negative real integer 10, a negative real integer 8, a real fraction 7, a pure imaginary 7, both parts 6."""
    def __init__(self, printer):
        self.pr = printer; self.P = printer.P
        self.rev = {}
        for e in self.P.doc2.entries:
            if e['role'] in ('value', 'infixl', 'infixr', 'infix', 'prefix'):
                for x in e['rhs']: self.rev.setdefault(x, e)

    def spell(self, v): return self.go(v, True)[0]

    @staticmethod
    def node(v):
        cn, cs, ca, cl, cv = CODE_CB
        try: r = v(cn)(cs)(ca)(cl)(cv)
        except UnknownError: raise
        except Exception: r = None
        if not isinstance(r, tuple): raise PrintError("a statement whose code is not a code (undetermined, or not built by the simplifier)")
        return r

    def symbol(self, c):
        """the spec name of a symbol code (a digit string: the doc 1 code, or a program-local code)"""
        b = '.' + numeral(to_digits(val(to_list(c)))) + '.'
        name = self.P.doc1.b2s.get(b)
        if name is None: raise PrintError(f"a statement mentions the symbol code {b}, which neither doc 1 nor this program names")
        return name

    def go(self, v, formula):
        """-> (text, precedence, kind) of the code v; formula: a statement position (else a term position)"""
        n = self.node(v)
        if n[0] == 'n':
            x = n[1].force()
            if formula:
                r = x(done('T'))(done('F'))
                if r not in ('T', 'F'): raise PrintError(UNDETERMINED)
                return ('true' if r == 'T' else 'false'), 10, 'atom'
            return self.number(x)
        if n[0] == 's': return self.app(self.symbol(n[1].force()), [], formula)
        if n[0] == 'a':
            args = []
            while n[0] == 'a':
                args.append(n[2].force()); n = self.node(n[1].force())
            if n[0] != 's': raise PrintError("a statement applies something that is not a symbol (a λ): it has no human spelling")
            return self.app(self.symbol(n[1].force()), args[::-1], formula)
        raise PrintError("a statement contains a λ or a bound variable: it has no human spelling yet")

    def number(self, q):
        try: t = self.pr.text_of(self.pr.call('showc', q))
        except (UnknownError, PrintError): raise
        except Exception: raise PrintError("a statement holds a value that is not a number where a number is expected") from None
        if ' + ' in t or ' - ' in t: p = 6
        elif t.endswith('i') or '/' in t: p = 7
        elif t.startswith('-'): p = 8
        else: p = 10
        return t, p, 'num'

    @staticmethod
    def par(x, need, avoid=()):
        return f'({x[0]})' if x[1] < need or x[2] in avoid else x[0]

    def app(self, name, args, formula):
        k = len(args)
        if name in ('⊤', '⊥') and k == 0: return ('true' if name == '⊤' else 'false'), 10, 'atom'
        if name in TRANSPARENT and k == 1: return self.go(args[0], formula and name != '⇡')
        if name == '⊘' and k == 0: return '[]', 10, 'atom'
        if name == '∷' and k == 2:                               # a list code:  [a, b, …]
            items, rest = [self.go(args[0], False)[0]], args[1]
            while True:
                n = self.node(rest)
                if n[0] == 's' and self.symbol(n[1].force()) == '⊘': break
                if n[0] == 'a':
                    h = self.node(n[1].force())
                    if h[0] == 'a':
                        hh = self.node(h[1].force())
                        if hh[0] == 's' and self.symbol(hh[1].force()) == '∷':
                            items.append(self.go(h[2].force(), False)[0]); rest = n[2].force(); continue
                raise PrintError("a list code that does not end in ⊘")
            return '[' + ', '.join(items) + ']', 10, 'atom'
        sub = name in FORMULA_ARGS
        if name in ('∨', '∨Ω') and k == 2:
            a, b = self.go(args[0], True), self.go(args[1], True)
            return f"{self.par(a, 3, ('and',))} or {self.par(b, 2, ('and',))}", 2, 'or'
        if name in ('∧', '∧Ω') and k == 2:
            a, b = self.go(args[0], True), self.go(args[1], True)
            return f"{self.par(a, 4)} and {self.par(b, 3)}", 3, 'and'
        if name in ('¬', '¬Ω') and k == 1:
            return 'not ' + self.par(self.go(args[0], True), 4), 4, 'not'
        e = self.rev.get(name)
        h = e['hum'] if e else name
        role = e['role'] if e else 'value'
        if role in ('infixl', 'infixr', 'infix') and k == 2:
            P_ = e['prec']
            a, b = self.go(args[0], sub), self.go(args[1], sub)
            if h == '^': ln, rn = 10, P_                                  # the base of ^ is parenthesised unless atomic
            elif role == 'infixl': ln, rn = P_, (P_ if h in ASSOC else P_ + 1)
            elif role == 'infixr': ln, rn = P_ + 1, P_
            else: ln, rn = P_ + 1, P_ + 1
            sep = h if h in TIGHT else f' {h} '
            return f"{self.par(a, ln)}{sep}{self.par(b, rn)}", P_, 'op'
        if role == 'prefix' and k == 1:
            P_ = e['prec']
            a = self.go(args[0], sub)
            x = self.par(a, P_)
            if h == '-' and x.startswith('-'): x = f'({a[0]})'         # never "--" (the human notation's comment mark)
            return (f'{h} {x}' if h[:1].isalpha() else f'{h}{x}'), P_, 'op'
        if k == 0 and role == 'value': return h, 10, 'atom'
        if role != 'value': raise PrintError(f"{h} applied to {k} argument(s) has no human spelling")
        return h + '(' + ', '.join(self.go(a, sub)[0] for a in args) + ')', 10, 'atom'

# -------------------------------------------------------------------- main
def output_mode(P, override=None, name='main'):
    if override: return override
    if P.out_mode: return P.out_mode
    return P.notation_of.get(name, 'spec')

def run_main(P, mode=None, n=None, write=None):
    """evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported
    (PrintError), as an undetermined truth value is."""
    try: return _run_main(P, mode, n, write)
    except UnknownError as e: raise PrintError(str(e)) from None

def _run_main(P, mode=None, n=None, write=None):
    write = write or (lambda s: (sys.stdout.write(s), sys.stdout.flush()))
    if 'main' not in P.checker.sigs:
        raise PrintError("this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)")
    mode = output_mode(P, mode)
    cls = P.checker.sigs['main'][0]
    C = P.checker; v = P.val('main')
    pr = Printer(P, mode, 10 if n is None else n)
    if C.leq(cls, K('𝕊')):
        r = cell(v)
        while r[0] == 'C':                                  # stream the text: an infinite String prints as long as it lasts
            write(pr.char(r[1].force())); r = cell(r[2].force())
        return mode
    c = C.norm(cls)
    if c[0] == 'K' and c[1] in ('𝔏', '𝔖') and C.norm(c[2][0]) == C.norm(K('𝕊')):
        r, k = cell(v), 0
        while r[0] == 'C' and (n is None or k < n):
            write(pr.text_of(r[1].force()) + '\n'); r = cell(r[2].force()); k += 1
        return mode
    write(pr.show(v, cls) + '\n')
    return mode
