"""mkref.py -- generate the symbol reference tables (markdown) from doc 1, doc 2 and the declared classes, so the README never drifts."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imo
from syntax import show_type
P = imo.Program()
for f in imo.PRELUDE: P.add_file(f, trusted=True)
P.check()
C = P.checker
rev = {}
for e in P.doc2.entries:
    for r in e['rhs']:
        rev.setdefault(r, []).append(e['hum'] + (' (prefix)' if e['role'] == 'prefix' else ''))
D = {
 # classes
 '𝔹':'Booleans ⊤ ⊥ (also the digits 1 and 0)', '𝔇':'digit strings = Gaussian integers in base i−1 (representation of ℤ[i]); ≣ 𝔏 𝔹', 'ℕ':'natural numbers', 'ℤ':'integers',
 'ℚ':'real rationals', 'ℝ':'real numbers (lazy streams of ℚ[i] with imaginary part 0)', 'ℤ[i]':'**the foundation**: Gaussian integers, binary strings in base i − 1', 'ℚ[i]':'Gaussian rationals: pairs (numerator, denominator) of Gaussian integers',
 'ℝ[i]':'lazy complex numbers = streams over ℚ[i]  (= ℂ, \\R, \\CC);  ≣ 𝔖 ℚ[i]', '𝔻':'Cayley–Dickson tower over ℚ[i]  (complex numbers → quaternions → octonions → sedenions → …, depth unbounded);  ≣ 𝔗 ℚ[i]',
 '𝕮':'characters (a code point, as a natural numeral)', '𝕊':'strings;  ≣ 𝔏 𝕮', '→':'function class  A → B', '𝔏':'lazy lists', '𝔖':'infinite streams', '𝔗':'Cayley–Dickson trees over a class',
 '𝔄':'algebra records over a class (+ × neg conj 0 1)', '𝔓':'pairs',
 # logic
 '⊤':'true','⊥':'false','¬':'not','∧':'and','∨':'or','⊻':'xor','⊼':'majority of three (carry bit)','⁇':'if b then x else y','⊗':'pair','◀':'first component','▶':'second component',
 '∷':'cons','⊘':'empty list','⌃':'head digit','⌄':'tail','∅':'is the list empty?','≡':'digit strings equal (trailing zeros ignored)','𝕓':'multiply by (i−1): prepend the digit 0','⧺':'append','⫶':'map','ℓ':'length','ord':'code point of a Char',
 # number
 '⌕':'table lookup used by the carry rule','κ':'carry table: tail ↦ tail + 110','⊞ᶜ':'serial adder with a numeral as carry','⊞ᶻ':'ℤ[i] addition on digit strings','⊠ᶻ':'ℤ[i] multiplication (shift-and-add)',
 '∗ᶻ':'ℤ[i] conjugation  z̄ = d₀ + 110·conj(z′)','⊞':'addition','⊠':'multiplication','⊖':'negation','∗':'complex conjugation','÷':'division (denominator must be non-zero)','≐':'equality of ℚ[i] elements (cross-multiplied)',
 '⊟':'subtraction','⩾ᶻ′':'sign search (helper)','⩾ᶻ':'order on real Gaussian integers','⩾':'x ≥ y on ℚ','⩽':'x ≤ y','≻':'x > y','≺':'x < y',
 # algebra
 '⌘':'build an algebra record','Ⓐ':'record: add','Ⓜ':'record: multiply','Ⓝ':'record: negate','Ⓒ':'record: conjugate','Ⓩ':'record: zero','Ⓞ':'record: one','𝔸ℚ[i]':'the algebra ℚ[i]',
 '⫴':'zip-with on streams','⁂':'constant stream','𝕃':'algebra of lazy streams over an algebra (pointwise)','𝔸ℝ[i]':'the algebra ℝ[i] = 𝕃 𝔸ℚ[i]','⇡':'embed a constant into streams (ℚ[i] → ℝ[i])',
 '⊕':'ℝ[i] addition','⊛':'ℝ[i] multiplication','⊖ᴿ':'ℝ[i] negation','∗ᴿ':'ℝ[i] conjugation','⊟ᴿ':'ℝ[i] subtraction','Σ′':'series driver (helper)','Σ':'exact series: Σ first-term ratio  gives the stream of partial sums t₀, t₀(1+ρ₁), …',
 '❀':'Cayley–Dickson leaf','❁':'Cayley–Dickson node (a, b)','↥':'lift a ↦ (a, 0) (the only way depths are reconciled)','∔':'tower addition','⊖ᵀ':'tower negation','∗ᵀ':'tower conjugation (a,b)* = (a*, −b)',
 '⊠ᵀ':'tower product (a,b)(c,d) = (ac − d*b, da + bc*)','𝕋':'algebra of Cayley–Dickson trees over an algebra','≐ᵀ':'tower equality (up to lifting) given an equality on the base','↑':'ℚ[i] → 𝔻  (a ↦ leaf a)',
 '⊞𝔻':'𝔻 addition','⊠𝔻':'𝔻 multiplication','⊖𝔻':'𝔻 negation','∗𝔻':'𝔻 conjugation','⊟𝔻':'𝔻 subtraction','𝕛':'the generator (0, 1):  j² = −1','𝕜':'i·j',
 '𝔉':'function-space algebra  ℚ[i] → A  (pointwise, infinite-dimensional)','⟨⟩′':'inner-product partial sums (helper)','⟨⟩':'inner product ⟨f,g⟩ = Σ conj(f n)·g n  as a stream of partial sums','δ':'standard basis vector δₘ(n) = 1 if n = m else 0',
 # comparisons, digit-level arithmetic (number.imo)
 '𝔒':'comparisons: ⋖ less, ≖ same, ⋗ greater (also the three values of a predicate: false, undetermined, true)','⋖':'less','≖':'same','⋗':'greater',
 '⋚':'three-way comparison on ℚ (one pass over the digits)','⋚ʳ':'sign of Re z, read off the digits (blocks of four)','⋚ⁱ':'sign of Im z','ℜᶻ':'Re z as a real Gaussian integer (linear time)','ℑᶻ':'Im z as a real Gaussian integer',
 '⊟ᶻ':'ℤ[i] subtraction (serial transducer, 47 carry numerals)','⊖ᶻ':'ℤ[i] negation','∅ᶻ':'is the Gaussian integer 0?','⌕′':'adder carry table as a decision tree (generated)','⌕⁺':'subtractor carry table t + 110 (generated)','⌕⁻':'subtractor carry table t − 110 (generated)',
 # arith.imo
 '⊜':'canonical form z/m: m the least natural with m·x ∈ ℤ[i]; equal values have identical forms','numer':'z of the canonical form','denom':'m of the canonical form','ℜ':'real part','ℑ':'imaginary part','𝒩':'norm x·x̄ = |x|²',
 '⌊':'floor','⌈':'ceiling','round':'nearest integer (halves up)','div':'integer division (floor; x div 0 = 0)','mod':'remainder (floor; x mod 0 = x)','abs':'absolute value','sgn':'sign −1, 0, 1','max':'maximum','min':'minimum',
 'gcd':'gcd (binary gcd on ℤ; Gaussian Euclid on ℤ[i], normalised Re > 0, Im ≥ 0)','lcm':'lcm','quo':'Gaussian quotient (nearest)','rem':'Gaussian remainder, N(r) ≤ N(b)/2','^':'power (square-and-multiply on the exponent digits; negative exponents on ℚ, ℚ[i])',
 'fact':'factorial','choose':'binomial coefficient','isqrt':'⌊√n⌋ (Newton)','÷ᶻ':'exact division in ℤ[i] (Hensel, from the low digits)','gcdᶻ':'binary gcd of real integers','⫽ᶻ':'division with remainder of naturals (long division in base 4)',
 '⊡':'canonical digit string (trailing zeros removed, one pass)','↓ᶻ':'the Gaussian integer of an integral value',
 # list.imo
 '⇒':'implies','⇔':'iff','hd':'head (⊥ for the empty list)','foldr':'right fold','foldl':'left fold','filter':'filter','take':'first n elements','drop':'all but the first n','nth':'element n (from 0)','last':'last element',
 'reverse':'reverse','concat':'concatenation of a list of lists','zip':'pairs','zipwith':'zip with a function','replicate':'n copies','iterate':'x, f x, f (f x), …','tabulate':'the stream f(0), f(1), …','sumof':'sum of a list','prodof':'product of a list',
 'elem':'membership in a list (≐)','upto':'a, a+1, …, b','sort':'insertion sort on ℚ','eqlist':'equality of lists given an equality of elements','≐ˢ':'equality of strings',
 'band':'digit-wise and of base-(i−1) expansions','bor':'digit-wise or','bxor':'digit-wise xor','shl':'z·bⁿ (prepend n zero digits)','shr':'drop the n lowest digits','ndigits':'number of digits of the expansion','digit':'digit n of the expansion',
 '𝕔':'the Char with a code point (unchecked; how bin writes a Char literal)','chr':'the Char with a code point (U+FFFD outside Unicode)',
 # real.imo
 '÷ᴿ':'pointwise division of streams','ℜᴿ':'real part of a lazy complex number','ℑᴿ':'imaginary part','⟐':'diagonal: element n of f(xₙ) — extends a function to lazy arguments','√':'square root: element n is ⌊√(x·4ⁿ)⌋/2ⁿ (within 2⁻ⁿ); principal root on ℚ[i]',
 'log':'logarithm (artanh series), x > 0 / Re z > 0','atan':"arctangent (Euler's series, every real x)",'sinh':'hyperbolic sine','cosh':'hyperbolic cosine','tan':'tangent (pointwise sin/cos)','tanh':'hyperbolic tangent',
 'expᴿ':'exp of a lazy argument','sinᴿ':'sin of a lazy argument','cosᴿ':'cos of a lazy argument','√ᴿ':'√ of a lazy argument','logᴿ':'log of a lazy argument','atanᴿ':'atan of a lazy argument','absᴿ':'|z| of a lazy complex number',
 '∂':'derivative: central differences with h = 2⁻ⁿ','∫':'integral: midpoint rule with n + 1 parts',
 # linalg.imo
 'vadd':'vector sum','vscale':'scalar times vector','dot':'dot product','madd':'matrix sum','transpose':'transpose','mmul':'matrix product','mvec':'matrix times vector','unitv':'unit vector','idm':'identity matrix',
 'det':'determinant (exact elimination)','solve':'solution of A x = b (A invertible)','inverse':'inverse matrix',
 # set.imo
 '∈':'membership (a set is its test)','∅ˢ':'the empty set','𝕌':'the universal set','∪':'union','∩':'intersection','∖':'difference','∁':'complement','setof':'the set of the elements of a list','members':'the members of a set among a list',
 # text.imo
 'dec':'an integer in decimal (Horner on decimal digits, no division)','bits':'a Gaussian integer in base i − 1','showq':'a real rational as text','showc':'a Gaussian rational as human-notation text','showb':'true / false',
 'decimals':'x rounded to k decimal places','unlines':'join lines','join':'join with a separator','decⁿ':'decimal digits of a natural (generated tables)',
 # prove.imo
 '≐ᴿ':'equality of elements of ℝ[i]: a predicate (true, false or undetermined)','≠ᴿ':'≠ on ℝ[i]: a predicate','≺ᴿ':'< on ℝ: a predicate','⩽ᴿ':'≤ on ℝ','≻ᴿ':'> on ℝ','⩾ᴿ':'≥ on ℝ',
 '≠':'≠ on ℚ[i]','⍰':'undetermined: absorbs its arguments; reported by the host, never printed as true or false','ι':'Iverson bracket ⊤ ↦ 1, ⊥ ↦ 0 (canonical coercion 𝔹 → ℕ)','supp':'support: n ↦ (n ≠ 0)',
 '𝔔':'codes of terms (terms written with numbers)','𝔮ⁿ':'code of a value','𝔮ˢ':'code of a symbol (its doc 1 code)','𝔮ᵃ':'code of an application','𝔮ˡ':'code of a λ','𝔮ᵛ':'code of a bound variable (de Bruijn)',
 'unfold':'logical expansion (definitions, β-reduction)','normR':'ring normal form of an ℝ[i] code','evQ':'evaluation of a ℚ[i] code','ratQ':'rational form of a ratio k ↦ ρ(k)',
 'recog':'proof rules: exp, sinh/cosh (sine, cosine) series as exponentials','≡ˢ':'isomorphism of two series','certs':'certified discs of a series (ratio test)','eqᴾ':'decide x = 0','sgnᴾ':'decide the sign of x','fo':'three-valued logic over relations',
}
def table(names, with_class=True):
    rows = ['| spec | bin | human | class | meaning |', '|:--:|:--|:--|:--|:--|']
    for n in names:
        sigs = C.sigs.get(n, [])
        cl = '<br>'.join('`' + show_type(s).replace('|', '\\|') + '`' for s in sigs) if sigs else ('class' if n in C.classes else '—')
        hum = ', '.join('`' + h + '`' for h in rev.get(n, [])) or ''
        rows.append(f"| `{n}` | `{P.doc1.s2b.get(n, '')}` | {hum} | {cl} | {D.get(n, '')} |")
    return '\n'.join(rows)
groups = [
 ('Classes', ['𝔹','𝔇','ℕ','ℤ','ℚ','ℝ','ℤ[i]','ℚ[i]','ℝ[i]','𝔻','𝕮','𝕊','→','𝔏','𝔖','𝔗','𝔄','𝔓']),
 ('Logic, pairs, lists, text', ['⊤','⊥','¬','∧','∨','⊻','⁇','⊗','◀','▶','∷','⊘','⌃','⌄','∅','≡','𝕓','⧺','⫶','ℓ','ord']),
 ('Numbers: ℤ[i] digit arithmetic and the field ℚ[i]', ['⊞ᶻ','⊠ᶻ','∗ᶻ','⊞','⊟','⊠','⊖','∗','÷','≐','⩾','⩽','≻','≺']),
 ('Algebras, lazy ℝ[i], series', ['⌘','Ⓐ','Ⓜ','Ⓝ','Ⓒ','Ⓩ','Ⓞ','𝔸ℚ[i]','𝕃','𝔸ℝ[i]','⇡','⊕','⊟ᴿ','⊛','⊖ᴿ','∗ᴿ','Σ']),
 ('Cayley–Dickson tower', ['❀','❁','↑','∔','⊠ᵀ','⊖ᵀ','∗ᵀ','≐ᵀ','𝕋','⊞𝔻','⊟𝔻','⊠𝔻','⊖𝔻','∗𝔻','𝕛','𝕜']),
 ('Function spaces', ['𝔉','⟨⟩','δ']),
 ('Bounded quantifiers and ranges', ['∀ₗ','∃ₗ','⍳']),
 ('Analysis (power series)', ['exp','sin','cos']),
 ('Comparisons and exact arithmetic on ℚ[i]', ['𝔒','⋖','≖','⋗','⋚','⊜','numer','denom','ℜ','ℑ','𝒩','⌊','⌈','round','div','mod','abs','sgn','max','min','gcd','lcm','quo','rem','^','fact','choose','isqrt']),
 ('Lists, streams, Booleans, digits, characters', ['⇒','⇔','hd','foldr','foldl','filter','take','drop','nth','last','reverse','concat','zip','zipwith','replicate','iterate','tabulate','sumof','prodof','elem','upto','sort','eqlist','≐ˢ','band','bor','bxor','shl','shr','ndigits','digit','𝕔','chr']),
 ('Analysis on the lazy ℝ[i]', ['÷ᴿ','ℜᴿ','ℑᴿ','⟐','√','log','atan','sinh','cosh','tan','tanh','expᴿ','sinᴿ','cosᴿ','√ᴿ','logᴿ','atanᴿ','absᴿ','∂','∫']),
 ('Linear algebra (exact)', ['vadd','vscale','dot','madd','transpose','mmul','mvec','unitv','idm','det','solve','inverse']),
 ('Sets as characteristic functions', ['∈','∅ˢ','𝕌','∪','∩','∖','∁','setof','members']),
 ('Text', ['dec','bits','showq','showc','showb','decimals','unlines','join']),
 ('Predicates on ℝ[i]: relations decided by logic (lib/prove.imo)', ['≐ᴿ','≠ᴿ','≺ᴿ','⩽ᴿ','≻ᴿ','⩾ᴿ','≠','⍰','ι','supp','𝔔','𝔮ⁿ','𝔮ˢ','𝔮ᵃ','𝔮ˡ','𝔮ᵛ','unfold','normR','evQ','ratQ','recog','≡ˢ','certs','eqᴾ','sgnᴾ','fo']),
 ('Internal helpers (trusted, not meant to be called directly)', ['⊼','⌕','κ','⊞ᶜ','⩾ᶻ′','⩾ᶻ','⫴','⁂','Σ′','↥','⟨⟩′','⍳′','⋚ʳ','⋚ⁱ','ℜᶻ','ℑᶻ','⊟ᶻ','⊖ᶻ','∅ᶻ','⌕′','⌕⁺','⌕⁻','÷ᶻ','gcdᶻ','⫽ᶻ','⊡','↓ᶻ','decⁿ']),
]
# ---- descriptions written in the source: a declaration line may end with  ⍝ description   (name ∶ class   ⍝ what it is)
import re as _re
decl_order = []                                            # (file, symbol) in order of first declaration
for f in imo.PRELUDE:
    for ln in open(f, encoding='utf-8').read().split('\n'):
        m = _re.match(r'^(\S+) ∶ .*?(?:\s⍝ (.*))?$', ln)
        if not m or ln.startswith('⍝'): continue
        name, desc = m.group(1), m.group(2)
        if desc and name not in D: D[name] = desc.strip()
        if (f, name) not in decl_order and all(n != name for _, n in decl_order): decl_order.append((f, name))
# ---- every public symbol (one with a human name or a description) not listed above gets a group of its source file
listed = {n for _, ns in groups for n in ns}
for f in imo.PRELUDE:
    names = [n for g, n in decl_order if g == f and n not in listed and (n in rev or n in D) and n in P.doc1.s2b and n in C.sigs]
    if not names: continue
    head = open(f, encoding='utf-8').readline()
    title = head.split(':', 1)[1].strip() if ':' in head else os.path.basename(f)
    title = title[0].upper() + title[1:]
    groups.insert(len(groups) - 1, (f"{title} (`lib/{os.path.basename(f)}`)", names))
    listed |= set(names)
out = []
for title, names in groups:
    missing = [n for n in names if n not in P.doc1.s2b]
    assert not missing, missing
    out.append(f"### {title}\n\n" + table(names) + "\n")
open(os.path.join(imo.ROOT, 'docs', 'reference.generated.md'), 'w', encoding='utf-8').write('\n'.join(out))
allnames = {n for _, ns in groups for n in ns}
left = sorted(set(P.doc1.s2b) - allnames)
print("symbols in doc 1:", len(P.doc1.s2b), " tabulated:", len(allnames), " not tabulated (bound variables and helpers):", len(left))
helpers = [n for n in left if n in C.sigs or n in C.classes]
open(os.path.join(imo.ROOT, 'docs', 'reference.generated.md'), 'a', encoding='utf-8').write(
    "\n**Further helpers** (named in doc 1, described in the source files): " + ' '.join(f"`{n}`" for n in helpers) + "\n")

# ---- doc 2 as tables
rows = ['| human | resolves to (overload set) | role | precedence |', '|:--|:--|:--|:--:|']
for e in P.doc2.entries:
    rhs = ' \\| '.join(f"`{x}`" for x in e['rhs'])
    rows.append(f"| `{e['hum'].replace('|', chr(92) + '|')}` | {rhs} | {e['role']} | {e['prec'] if e['prec'] is not None else ''} |")
open(os.path.join(imo.ROOT, 'docs', 'doc2.generated.md'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
