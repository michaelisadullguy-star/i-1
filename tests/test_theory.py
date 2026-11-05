"""test_theory.py -- the theories (lib/theory.imo, theories.imo, th_*.imo): the simplifier and the decision of statements under axiomatic packages.

  python3 tests/test_theory.py [--core pymo|haskimo|rustimo]

What is tested
  * every theory: its embedded theorems hold (checktheory), and the mechanism of packages (defaults, use, unuse, requirements, conflicts);
  * curated statements per theory with the exact verdict (1 true for all values, 0 false for all values, 2 undetermined);
  * random statements against exact Python oracles:
      propositional formulas (truth tables), polynomial identities (dictionary polynomials), closed numerical statements (Fractions),
      implications between linear inequalities (Fourier–Motzkin in Python), words of free and of abelian groups (free reduction, exponent sums),
      identities and inclusions of sets (truth tables over membership types), linear statements about probabilities (the vertices of the simplex),
      hereditarily finite sets (frozensets), chains of morphisms (associativity and identities), intuitionistic logic (Glivenko's theorem).
Pymo is two orders of magnitude slower than the other cores: it runs a sample (every fourth curated statement, a few random ones)."""
import itertools, random, re, sys
from fractions import Fraction as F
from langtest import *

R = random.Random(20261104)
SMALL = CORE == 'pymo'
def n(k): return max(2, k // 8) if SMALL else k

PRE = '''denv in Env := defaultenv
ienv in Env := use("intuitionistic", defaultenv)
genv in Env := envwith(["group"])
aenv in Env := envwith(["abelian"])
senv in Env := envwith(["sets"])
kenv in Env := envwith(["kolmogorov"])
zenv in Env := envwith(["zfc"])
penv in Env := envwith(["peano"])
eenv in Env := envwith(["etcs"])
lenv in Env := envwith(["lattice"])
wenv in Env := envwith(["piecewise"])
defenv in Env := defaultenv
ienv2 in Env := envwith(["incidence"])
uenv in Env := envwith(["euclid"])
henv in Env := envwith(["hilbert"])
benv in Env := envwith(["hyperbolic"])
xenv in Env := envwith(["elliptic"])
tenv in Env := envwith(["topology"])
menv in Env := envwith(["monoid"])
cmenv in Env := envwith(["cmonoid"])'''
S = Suite('theories', PRE)
LS = ('L', 'S')
_count = [0]
def add(label, e, c, x, always=False):
    _count[0] += 1
    if SMALL and not always and _count[0] % 4: return
    S.add(label, e, c, x)
def verdict(env, text, want, always=False):
    add(f'{env}: {text}', f'holdsv({env}, {lit(text, "S")})', 'N', want, always)
def provable(env, text, want, always=False):
    add(f'{env} proves? {text}', f'holdsv({env}, {lit(text, "S")}) == 1', 'B', want, always)
def simp(env, text, want):
    add(f'simpe {env}: {text}', f'simpe({env}, {lit(text, "S")})', 'S', want)

# ---------------------------------------------------------------------------------------------------------------------------- the theories
THEORIES = ['core', 'classical', 'intuitionistic', 'arith', 'reals', 'peano', 'integers', 'group', 'abelian', 'sets', 'lattice', 'zfc', 'etcs', 'kolmogorov', 'piecewise', 'incidence', 'euclid', 'hilbert', 'hyperbolic', 'elliptic', 'topology', 'monoid', 'cmonoid']
add('theorynames', 'theorynames', LS, THEORIES, True)
for t in THEORIES:
    if SMALL and t not in ('core', 'classical', 'sets', 'group'): continue
    add(f'checktheory {t}: every embedded theorem holds', f'checktheory({lit(t, "S")})', LS, [], True)
    add(f'{t} has axioms, theorems and a description', f'(length(axiomsof({lit(t, "S")})) geq 1) and (length(theoremsof({lit(t, "S")})) geq 1) and (length(describe({lit(t, "S")})) geq 1)', 'B', True)
add('describe of an unknown theory', 'describe("nonsense")', 'S', 'unknown theory')

# ---- the packages
def act(e): return f'activetheories({e})'
add('default theories', act('defaultenv'), LS, ['core', 'classical', 'arith', 'reals'], True)
add('use peano: it conflicts with the reals', act('use("peano", defaultenv)'), LS, ['core', 'classical', 'arith', 'peano'])
add('use integers: it conflicts with the reals', act('use("integers", defaultenv)'), LS, ['core', 'classical', 'arith', 'integers'])
add('use zfc', act('use("zfc", defaultenv)'), LS, ['core', 'classical', 'arith', 'reals', 'zfc'])
add('use etcs after zfc: zfc goes', act('use("etcs", use("zfc", defaultenv))'), LS, ['core', 'classical', 'arith', 'reals', 'etcs'])
add('use zfc after etcs: etcs goes', act('use("zfc", use("etcs", defaultenv))'), LS, ['core', 'classical', 'arith', 'reals', 'zfc'])
add('unuse arith: the reals need it', act('unuse("arith", defaultenv)'), LS, ['core', 'classical'])
add('unuse core: everything needs it', act('unuse("core", defaultenv)'), LS, [])
add('use intuitionistic: classical goes', act('use("intuitionistic", defaultenv)'), LS, ['core', 'arith', 'reals', 'intuitionistic'])
add('use classical again', act('use("classical", use("intuitionistic", defaultenv))'), LS, ['core', 'arith', 'reals', 'classical'])
add('use kolmogorov', act('use("kolmogorov", defaultenv)'), LS, ['core', 'classical', 'arith', 'reals', 'kolmogorov'])
add('sets and kolmogorov exclude each other', act('use("sets", use("kolmogorov", defaultenv))'), LS, ['core', 'classical', 'arith', 'reals', 'sets'])
add('kolmogorov after sets', act('use("kolmogorov", use("sets", defaultenv))'), LS, ['core', 'classical', 'arith', 'reals', 'kolmogorov'])
add('zfc and sets exclude each other', act('use("zfc", use("sets", defaultenv))'), LS, ['core', 'classical', 'arith', 'reals', 'zfc'])
add('abelian brings group', act('envwith(["abelian"])'), LS, ['core', 'classical', 'arith', 'reals', 'group', 'abelian'])
add('lattice', act('envwith(["lattice"])'), LS, ['core', 'classical', 'arith', 'reals', 'lattice'])
add('piecewise needs arith and lives with the reals', act('envwith(["piecewise"])'), LS, ['core', 'classical', 'arith', 'reals', 'piecewise'])
B0 = "['core', 'classical', 'arith', 'reals'"
add('euclid brings incidence', act('envwith(["euclid"])'), LS, ['core', 'classical', 'arith', 'reals', 'incidence', 'euclid'])
add('hilbert brings euclid', act('envwith(["hilbert"])'), LS, ['core', 'classical', 'arith', 'reals', 'incidence', 'euclid', 'hilbert'])
add('hyperbolic replaces euclid and hilbert', act('use("hyperbolic", envwith(["hilbert"]))'), LS, ['core', 'classical', 'arith', 'reals', 'incidence', 'hyperbolic'])
add('elliptic replaces hyperbolic', act('use("elliptic", envwith(["hyperbolic"]))'), LS, ['core', 'classical', 'arith', 'reals', 'incidence', 'elliptic'])
add('euclid replaces elliptic', act('use("euclid", envwith(["elliptic"]))'), LS, ['core', 'classical', 'arith', 'reals', 'incidence', 'euclid'])
add('unuse incidence: every geometry needs it', act('unuse("incidence", envwith(["hilbert"]))'), LS, ['core', 'classical', 'arith', 'reals'])
add('hilbert after hyperbolic: the geometry flips back', act('use("hilbert", envwith(["hyperbolic"]))'), LS, ['core', 'classical', 'arith', 'reals', 'incidence', 'euclid', 'hilbert'])
add('topology brings sets', act('envwith(["topology"])'), LS, ['core', 'classical', 'arith', 'reals', 'sets', 'topology'])
add('zfc replaces sets and topology', act('use("zfc", envwith(["topology"]))'), LS, ['core', 'classical', 'arith', 'reals', 'zfc'])
add('topology after zfc: zfc goes', act('use("topology", envwith(["zfc"]))'), LS, ['core', 'classical', 'arith', 'reals', 'sets', 'topology'])
add('kolmogorov replaces sets and topology', act('use("kolmogorov", envwith(["topology"]))'), LS, ['core', 'classical', 'arith', 'reals', 'kolmogorov'])
add('cmonoid replaces monoid', act('use("cmonoid", envwith(["monoid"]))'), LS, ['core', 'classical', 'arith', 'reals', 'cmonoid'])
add('monoid and group live together', act('usetheories(["monoid", "group"], defaultenv)'), LS, ['core', 'classical', 'arith', 'reals', 'monoid', 'group'])
add('piecewise with peano', act('usetheories(["peano", "piecewise"], defaultenv)'), LS, ['core', 'classical', 'arith', 'peano', 'piecewise'])
add('isactive', 'isactive("reals", defaultenv) and (not isactive("peano", defaultenv)) and isactive("peano", use("peano", defaultenv))', 'B', True, True)
add('usetheories is use one after the other', act('usetheories(["abelian", "sets"], defaultenv)'), LS, ['core', 'classical', 'arith', 'reals', 'group', 'abelian', 'sets'])
add('unuse a theory that is not on', act('unuse("zfc", defaultenv)'), LS, ['core', 'classical', 'arith', 'reals'])
add('use a theory that is on changes nothing', act('use("reals", defaultenv)'), LS, ['core', 'classical', 'arith', 'reals'])

# ---------------------------------------------------------------------------------------------------------------------------- curated
# logic: classical decides by diagrams
for t, v in [('p || ¬p', 1), ('p && ¬p', 0), ('p => p', 1), ('p => q', 2), ('¬¬p <=> p', 1), ('(p => q) <=> (¬q => ¬p)', 1), ('((p => q) => p) => p', 1),
             ('p xor p', 0), ('ite(p, q, q) <=> q', 1), ('x = x', 1), ('x = y', 2), ('x != x', 0), ('(p && q) => p', 1), ('p => (p && q)', 2),
             ('¬(p && q) <=> (¬p || ¬q)', 1), ('(p => q) && (q => r) => (p => r)', 1), ('(p || q) && ¬p => q', 1), ('(p <=> q) <=> ((p => q) && (q => p))', 1)]:
    verdict('denv', t, v)
# intuitionistic logic: no excluded middle
for t, v in [('p || ¬p', 2), ('¬¬p => p', 2), ('((p => q) => p) => p', 2), ('p => ¬¬p', 1), ('¬¬¬p <=> ¬p', 1), ('¬(p && ¬p)', 1), ('(p => q) => (¬q => ¬p)', 1),
             ('(¬p || q) => (p => q)', 1), ('(p => q) => (¬p || q)', 2), ('¬¬(p || ¬p)', 1), ('p && ¬p', 0), ('¬(p || q) <=> (¬p && ¬q)', 1),
             ('¬(p && q) => (¬p || ¬q)', 2), ('(¬p || ¬q) => ¬(p && q)', 1), ('p => (q => p)', 1), ('((p => q) => p) => ¬¬p', 1), ('p || q => q || p', 1)]:
    verdict('ienv', t, v)
# arithmetic over the reals
for t, v in [('x + 0 = x', 1), ('x * 1 = x', 1), ('x * 0 = 0', 1), ('(x + y)^2 = x^2 + 2*x*y + y^2', 1), ('(x + y)^2 = x^2 + y^2', 2), ('x + 1 = x', 0),
             ('2 + 2 = 4', 1), ('2 + 2 = 5', 0), ('x - x = 0', 1), ('x / 2 + x / 2 = x', 1), ('(x - y) * (x + y) = x^2 - y^2', 1), ('x <= x', 1), ('x < x', 0),
             ('x < y || x = y || x > y', 1), ('x <= y && y <= x => x = y', 1), ('x < y => x <= y', 1), ('x <= y && y <= z => x <= z', 1), ('x + y <= x + y + 1', 1),
             ('x^2 >= 0', 1), ('x^2 + 1 > 0', 1), ('x^2 + 1 = 0', 0), ('x^2 = -1', 0), ('x * x >= 0', 1), ('x <= y => x + z <= y + z', 1), ('x <= y => 2*x <= 2*y', 1),
             ('x < y && y < x', 0), ('x < y && y < z => x < z', 1), ('x <= y || y <= x', 1), ('x + y = y + x', 1), ('x * (y + z) = x * y + x * z', 1),
             ('3/4 + 1/4 = 1', 1), ('x^3 - x^3 = 0', 1), ('x < y => x - y < 0', 1), ('x <= y && x >= y => x = y', 1)]:
    verdict('denv', t, v)
# the natural numbers (Peano arithmetic): every number is >= 0
for t, v in [('x >= 0', 1), ('x < 0', 0), ('x + 1 > x', 1), ('x + y >= x', 1), ('x * y >= 0', 1), ('x = 0 || x > 0', 1), ('x + y = 0 => x = 0', 1),
             ('x + y = y + x', 1), ('(x + y) + z = x + (y + z)', 1), ('x * (y + 1) = x * y + x', 1), ('x + 1 = 0', 0), ('x < x + 1', 1), ('2 + 3 = 5', 1), ('x <= y => x <= y + 1', 1)]:
    verdict('penv', t, v)
# groups
for t, v in [('x · e = x', 1), ('e · x = x', 1), ('x · inv(x) = e', 1), ('inv(x) · x = e', 1), ('inv(x · y) = inv(y) · inv(x)', 1), ('x · y = y · x', 2), ('inv(inv(x)) = x', 1),
             ('e = e', 1), ('(x · y) · z = x · (y · z)', 1), ('x · y · inv(y) = x', 1), ('inv(e) = e', 1), ('x = y', 2), ('x · y · inv(x · y) = e', 1), ('inv(x) · (x · y) = y', 1)]:
    verdict('genv', t, v)
for t, v in [('x · y = y · x', 1), ('inv(x · y) = inv(x) · inv(y)', 1), ('x · y · inv(x) = y', 1), ('x · y = x · z', 2), ('x · y · z = z · y · x', 1)]:
    verdict('aenv', t, v)
# the algebra of sets
for t, v in [('A ∪ B = B ∪ A', 1), ('(A ∪ B)ᶜ = Aᶜ ∩ Bᶜ', 1), ('A ⊆ A ∪ B', 1), ('A ∩ B ⊆ A', 1), ('A ⊆ B', 2), ('A ∪ Aᶜ = U', 1), ('A ∩ Aᶜ = ∅', 1), ('∅ = U', 0),
             ('A \\ B = A ∩ Bᶜ', 1), ('A ⊆ B && B ⊆ A => A ∪ B = A ∩ B', 1), ('A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C)', 1), ('A ∪ (B ∩ C) = (A ∪ B) ∩ (A ∪ C)', 1), ('A ∪ B = A ∩ B', 2),
             ('A ⊆ ∅ => A = ∅', 1), ('A ⊆ B <=> Bᶜ ⊆ Aᶜ', 1), ('(A ∪ B) \\ B ⊆ A', 1), ('A ∩ B = A <=> A ⊆ B', 1), ('U ⊆ ∅', 0)]:
    verdict('senv', t, v)
# lattices
for t, v in [('x ⊔ x = x', 1), ('x ⊓ (x ⊔ y) = x', 1), ('x ⊔ (x ⊓ y) = x', 1), ('x ⊔ y = y ⊔ x', 1), ('x ⊓ y ⊑ x', 1), ('x ⊑ x ⊔ y', 1), ('x ⊔ y = x ⊓ y', 2),
             ('(x ⊔ y) ⊔ z = x ⊔ (y ⊔ z)', 1), ('x ⊑ x', 1)]:
    verdict('lenv', t, v)
# ZFC on hereditarily finite sets
for t, v in [('{1, 2} ∪ {2, 3} = {1, 2, 3}', 1), ('2 ∈ {1, 2}', 1), ('3 ∈ {1, 2}', 0), ('{1} ⊆ {1, 2}', 1), ('{1, 2} ⊆ {1}', 0), ('card(powerset({1, 2, 3})) = 8', 1),
             ('A ∈ A', 0), ('∅ ⊆ A', 1), ('{a, b} = {b, a}', 1), ('{1, 2} = {1, 3}', 0), ('ord(3) = {∅, {∅}, {∅, {∅}}}', 1), ('{a, a} = {a}', 1), ('A ∈ B && B ∈ A', 0),
             ('{1, 2} ∩ {2, 3} = {2}', 1), ('powerset(∅) = {∅}', 1), ('card({1, 2} × {1, 2, 3}) = 6', 1), ('bigunion({{1}, {2, 3}}) = {1, 2, 3}', 1),
             ('opair(1, 2) = opair(2, 1)', 0), ('{∅} ∈ ord(2)', 1), ('succ(ord(3)) = ord(4)', 1), ('∅ ∈ ord(1)', 1), ('card(ord(5)) = 5', 1)]:
    verdict('zenv', t, v)
# ETCS: a cartesian closed category with a terminal object
for t, v in [('id ∘ f = f', 1), ('f ∘ id = f', 1), ('(f ∘ g) ∘ h = f ∘ (g ∘ h)', 1), ('p1 ∘ pr(f, g) = f', 1), ('p2 ∘ pr(f, g) = g', 1), ('f ∘ g = g ∘ f', 2),
             ('bang ∘ f = bang', 1), ('pr(p1, p2) = id', 1), ('pr(f, g) ∘ h = pr(f ∘ h, g ∘ h)', 1), ('ev ∘ pr(lam(f) ∘ p1, p2) = f', 1), ('f = g', 2), ('lam(ev) = id', 1)]:
    verdict('eenv', t, v)
# Kolmogorov: probability on finitely many events
for t, v in [('P(A) >= 0', 1), ('P(A) <= 1', 1), ('P(A) > 1', 0), ('P(A ∪ B) = P(A) + P(B) - P(A ∩ B)', 1), ('P(A ∪ B) = P(A) + P(B)', 2), ('P(A) + P(Aᶜ) = 1', 1),
             ('P(∅) = 0', 1), ('P(Ω) = 1', 1), ('P(A ∩ B) <= P(A)', 1), ('P(A) <= P(A ∩ B)', 2), ('P(A ∪ B) <= P(A) + P(B)', 1), ('P(A) = 2', 0), ('P(A) + P(B) > 2', 0),
             ('P(A) + P(B) >= 1 => P(A ∩ B) >= P(A) + P(B) - 1', 1), ('P(A \\ B) = P(A) - P(A ∩ B)', 1), ('P(A ∪ B ∪ C) <= P(A) + P(B) + P(C)', 1),
             ('P(A ∩ B ∩ C) <= P(A ∩ B)', 1), ('P(A ∩ B) = P(A) * P(B) => P(A ∩ B) <= P(A)', 1),
             ('P(A ∪ B ∪ C) = P(A) + P(B) + P(C) - P(A ∩ B) - P(A ∩ C) - P(B ∩ C) + P(A ∩ B ∩ C)', 1), ('P(A ∩ B) > P(A)', 0), ('P(A) + P(B) = 3', 0)]:
    verdict('kenv', t, v)
# simplification (the simplest form)
simp('denv', 'x + 0', 'x'); simp('denv', 'x * 1 + 0 * y', 'x'); simp('denv', 'p && p', 'p'); simp('denv', 'p || false', 'p'); simp('denv', 'p && true', 'p')
simp('denv', '2 + 3 * 4', '14'); simp('denv', '¬¬p', 'p'); simp('denv', 'x - x', '0'); simp('denv', 'x = x', '⊤'); simp('senv', 'A ∪ A', 'A'); simp('senv', 'A ∩ ∅', '∅')

# ---------------------------------------------------------------------------------------------------------------------------- oracles
# ---- propositional formulas: the truth table decides (1 tautology, 0 contradiction, 2 otherwise); intuitionistic logic via Glivenko
def rformula(d):
    if d == 0 or R.random() < 0.2: return R.choice([('v', 'p'), ('v', 'q'), ('v', 'r'), ('v', 'p'), ('v', 'q'), ('c', True), ('c', False)])
    op = R.choice(['and', 'or', 'not', 'imp', 'iff', 'xor', 'imp', 'and', 'or'])
    return (op, rformula(d - 1)) if op == 'not' else (op, rformula(d - 1), rformula(d - 1))
def fstr(f):
    k = f[0]
    if k == 'v': return f[1]
    if k == 'c': return 'true' if f[1] else 'false'
    if k == 'not': return '¬(' + fstr(f[1]) + ')'
    sym = {'and': '&&', 'or': '||', 'imp': '=>', 'iff': '<=>', 'xor': 'xor'}[k]
    return f'({fstr(f[1])} {sym} {fstr(f[2])})'
def feval(f, a):
    k = f[0]
    if k == 'v': return a[f[1]]
    if k == 'c': return f[1]
    if k == 'not': return not feval(f[1], a)
    x, y = feval(f[1], a), feval(f[2], a)
    return {'and': x and y, 'or': x or y, 'imp': (not x) or y, 'iff': x == y, 'xor': x != y}[k]
def table(f):
    return [feval(f, dict(zip('pqr', bits))) for bits in itertools.product([False, True], repeat=3)]
for _ in range(n(40)):
    f = rformula(R.randint(1, 4)); t = table(f); s = fstr(f)
    want = 1 if all(t) else (0 if not any(t) else 2)
    verdict('denv', s, want)
    # intuitionistic logic: refutable exactly when contradictory; a satisfiable non-tautology is undetermined; Glivenko: ¬¬f is provable iff f is a classical tautology
    if not any(t): verdict('ienv', s, 0)
    elif not all(t): verdict('ienv', s, 2)
    provable('ienv', '¬¬(' + s + ')', all(t))
    if not all(t): provable('ienv', s, False)

# ---- polynomial identities: the normal form in a dictionary
def pvar(v): return {tuple(1 if i == 'xyz'.index(v) else 0 for i in range(3)): F(1)}
def pcon(c): return {(0, 0, 0): F(c)} if c else {}
def padd(a, b, s=1):
    r = dict(a)
    for m, c in b.items():
        r[m] = r.get(m, 0) + s * c
        if r[m] == 0: del r[m]
    return r
def pmul(a, b):
    r = {}
    for m, c in a.items():
        for m2, c2 in b.items():
            k = tuple(x + y for x, y in zip(m, m2)); r[k] = r.get(k, 0) + c * c2
            if r[k] == 0: del r[k]
    return r
def ppow(a, e):
    r = pcon(1)
    for _ in range(e): r = pmul(r, a)
    return r
def rsmall(d=1):
    """a small expression: (text, polynomial)"""
    if d == 0 or R.random() < 0.4:
        if R.random() < 0.6: v = R.choice('xyz'); return v, pvar(v)
        c = R.randint(0, 4); return str(c), pcon(c)
    a, b = rsmall(d - 1), rsmall(d - 1)
    if R.random() < 0.5: return f'({a[0]} + {b[0]})', padd(a[1], b[1])
    if R.random() < 0.5: return f'({a[0]} - {b[0]})', padd(a[1], b[1], -1)
    return f'({a[0]} * {b[0]})', pmul(a[1], b[1])
TEMPLATES = [
    ('({a} + {b})^2', '{a}^2 + 2 * {a} * {b} + {b}^2'), ('({a} - {b}) * ({a} + {b})', '{a}^2 - {b}^2'), ('{a} * ({b} + {c})', '{a} * {b} + {a} * {c}'),
    ('({a} + {b})^3', '{a}^3 + 3 * {a}^2 * {b} + 3 * {a} * {b}^2 + {b}^3'), ('({a} + {b} + {c})^2', '{a}^2 + {b}^2 + {c}^2 + 2 * {a} * {b} + 2 * {a} * {c} + 2 * {b} * {c}'),
    ('({a} - {b})^2', '{a}^2 - 2 * {a} * {b} + {b}^2'), ('{a} * {b} - {b} * {a}', '0'), ('({a} + {b}) - ({b} + {a})', '0'), ('{a}^2 * {a}', '{a}^3'),
    ('({a} + {b}) * ({a} + {b}) - ({a} - {b}) * ({a} - {b})', '4 * {a} * {b}'), ('{a} * ({b} - {c}) + {c} * {a}', '{a} * {b}')]
def parse_poly(text, vars_):
    """a tiny recursive parser for  + - * ^ ( ) numbers and x y z  (own implementation, used for the oracle only)"""
    toks = re.findall(r'\d+|[xyz]|[-+*^()]', text); pos = [0]
    def peek(): return toks[pos[0]] if pos[0] < len(toks) else None
    def eat(): pos[0] += 1; return toks[pos[0] - 1]
    def atom():
        t = eat()
        if t == '(': v = expr(); eat(); return v
        if t in 'xyz': return pvar(t)
        return pcon(int(t))
    def power():
        b = atom()
        if peek() == '^': eat(); e = int(eat()); return ppow(b, e)
        return b
    def unary():
        if peek() == '-': eat(); return padd({}, unary(), -1)
        return power()
    def term():
        v = unary()
        while peek() == '*': eat(); v = pmul(v, unary())
        return v
    def expr():
        v = term()
        while peek() in ('+', '-'):
            op = eat(); w = term(); v = padd(v, w, 1 if op == '+' else -1)
        return v
    return expr()
for _ in range(n(40)):
    lhs_t, rhs_t = R.choice(TEMPLATES)
    parts = {k: rsmall(1)[0] for k in 'abc'}
    l, r = lhs_t.format(**parts), rhs_t.format(**parts)
    if R.random() < 0.4:                                     # break the identity: another coefficient, exponent or sign somewhere
        r = re.sub(r'\d', lambda m: str((int(m.group()) + 1) % 5), r, count=1)
    pl, pr = parse_poly(l, 'xyz'), parse_poly(r, 'xyz')
    diff = padd(pl, pr, -1)
    ident = not diff
    provable('denv', f'{l} = {r}', ident)
    if ident: verdict('denv', f'{l} = {r}', 1)
    elif set(diff) == {(0, 0, 0)}: verdict('denv', f'{l} = {r}', 0)

# ---- closed numerical statements: exact rational arithmetic
def rnum(d):
    if d == 0 or R.random() < 0.3:
        c = R.randint(0, 9); return str(c), F(c)
    a, b = rnum(d - 1), rnum(d - 1)
    op = R.choice(['+', '-', '*', '/', '^'])
    if op == '/' and b[1] == 0: op = '+'
    if op == '^':
        e = R.randint(0, 3); return f'({a[0]})^{e}', a[1] ** e
    v = {'+': a[1] + b[1], '-': a[1] - b[1], '*': a[1] * b[1], '/': (a[1] / b[1] if b[1] != 0 else 0)}[op]
    return f'({a[0]} {op} {b[0]})', v
for _ in range(n(40)):
    a, b = rnum(2), rnum(2); rel = R.choice(['=', '<', '<=', '>', '>=', '!='])
    ok = {'=': a[1] == b[1], '<': a[1] < b[1], '<=': a[1] <= b[1], '>': a[1] > b[1], '>=': a[1] >= b[1], '!=': a[1] != b[1]}[rel]
    verdict('denv', f'{a[0]} {rel} {b[0]}', 1 if ok else 0)

# ---- quadratic polynomials: the exact positive semidefiniteness test (lib/psd.imo) against the principal minors and a solvability test written separately here.
# p = (x, 1) M (x, 1)^T;  p >= 0 for all values iff M is positive semidefinite (all principal minors >= 0);  p > 0 for all values iff, besides, M (x, 1) = 0 has no solution x.
def det(m):
    k = len(m)
    if k == 0: return F(1)
    m = [row[:] for row in m]; d = F(1)
    for i in range(k):
        q = next((r for r in range(i, k) if m[r][i] != 0), None)
        if q is None: return F(0)
        if q != i: m[i], m[q] = m[q], m[i]; d = -d
        d *= m[i][i]
        for r in range(i + 1, k):
            f = m[r][i] / m[i][i]
            for c in range(i, k): m[r][c] -= f * m[i][c]
    return d
def psd(m):
    k = len(m)
    return all(det([[m[i][j] for j in idx] for i in idx]) >= 0 for size in range(1, k + 1) for idx in itertools.combinations(range(k), size))
def solvable(m):
    k = len(m) - 1
    rows = [[m[i][j] for j in range(k)] + [-m[i][k]] for i in range(k + 1)]
    r = 0
    for c in range(k):
        q = next((i for i in range(r, len(rows)) if rows[i][c] != 0), None)
        if q is None: continue
        rows[r], rows[q] = rows[q], rows[r]
        for i in range(len(rows)):
            if i != r and rows[i][c] != 0:
                f = rows[i][c] / rows[r][c]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r])]
        r += 1
    return all(not (all(x == 0 for x in row[:k]) and row[k] != 0) for row in rows)
def quadmatrix(coef, k):
    m = [[F(0)] * (k + 1) for _ in range(k + 1)]
    for mono, c in coef.items():
        if sum(mono) == 0: m[k][k] += c
        elif sum(mono) == 1: i = mono.index(1); m[i][k] += F(c) / 2; m[k][i] += F(c) / 2
        elif max(mono) == 2: i = mono.index(2); m[i][i] += c
        else: i, j = [t for t in range(k) if mono[t] == 1]; m[i][j] += F(c) / 2; m[j][i] += F(c) / 2
    return m
def polytext(coef, names):
    out = []
    for mono, c in sorted(coef.items(), reverse=True):
        if c == 0: continue
        fac = [f'{names[i]}^{e}' if e > 1 else names[i] for i, e in enumerate(mono) if e]
        body = '*'.join(([str(abs(c))] if (abs(c) != 1 or not fac) else []) + fac)
        out.append(('- ' if c < 0 else '+ ') + body)
    if not out: return '0'
    t = ' '.join(out)
    return t[2:] if t.startswith('+ ') else '-' + t[2:]
def quadverdicts(m):
    nm = [[-x for x in row] for row in m]
    nonneg, nonpos = psd(m), psd(nm)
    pos, neg = nonneg and not solvable(m), nonpos and not solvable(nm)
    return {'>= 0': 1 if nonneg else (0 if neg else 2), '> 0': 1 if pos else (0 if nonpos else 2), '<= 0': 1 if nonpos else (0 if pos else 2),
            '< 0': 1 if neg else (0 if nonneg else 2), '= 0': 0 if (pos or neg) else 2}
for _ in range(n(40)):
    k = R.randint(1, 3); names = 'xyz'[:k]
    coef = {}
    def bump(mono, c): coef[mono] = coef.get(mono, 0) + c
    if R.random() < 0.55:                       # a sum of squares of affine forms, plus a constant
        for _s in range(R.randint(1, 3)):
            a = [R.randint(-2, 2) for _ in range(k)]; b = R.randint(-2, 2); w = R.choice([1, 1, 2, 3])
            for i in range(k):
                for j in range(i, k):
                    mono = tuple(2 if t == i == j else (1 if t in (i, j) else 0) for t in range(k))
                    bump(mono, w * a[i] * a[j] * (1 if i == j else 2))
                bump(tuple(1 if t == i else 0 for t in range(k)), 2 * w * a[i] * b)
            bump(tuple([0] * k), w * b * b)
        bump(tuple([0] * k), R.choice([0, 0, 1, 2, -1]))
        if R.random() < 0.25: coef = {m_: -c for m_, c in coef.items()}
    else:
        for i in range(k):
            for j in range(i, k):
                mono = tuple(2 if t == i == j else (1 if t in (i, j) else 0) for t in range(k))
                if R.random() < 0.7: bump(mono, R.randint(-3, 3))
            if R.random() < 0.6: bump(tuple(1 if t == i else 0 for t in range(k)), R.randint(-3, 3))
        bump(tuple([0] * k), R.randint(-3, 3))
    coef = {m_: c for m_, c in coef.items() if c != 0}
    text = polytext(coef, names)
    for rel, want in quadverdicts(quadmatrix(coef, k)).items():
        verdict('denv', f'{text} {rel}', want)
for t, v in [('(x + 1)^2 >= 0', 1), ('x^2 + x + 1 > 0', 1), ('x^2 + y^2 >= 2*x*y', 1), ('x^2 + 2*x + 2 < 0', 0), ('-(x^2) - 2*x - 1 <= 0', 1), ('x^2 - 1 >= 0', 2), ('a^2 + b^2 + c^2 >= a*b + b*c + c*a', 1),
             ('x^2 + x >= 0', 2), ('x^2 + 2*x + 1 > 0', 2), ('y^2 + 1 > 0', 1), ('x^2 - 2*x*y + y^2 = 0', 2), ('(x - y)^2 >= 0', 1), ('4*x^2 + 4*x + 1 >= 0', 1), ('x^2 + y^2 + 2*x*y + 1 > 0', 1)]:
    verdict('denv', t, v)

# ---- implications between linear inequalities: Fourier–Motzkin in Python
def feasible(rows, nv):
    rows = [(list(c), k, s) for c, k, s in rows]
    for v in range(nv):
        pos = [r for r in rows if r[0][v] > 0]; neg = [r for r in rows if r[0][v] < 0]; new = [r for r in rows if r[0][v] == 0]
        for p in pos:
            for q in neg:
                a, b = p[0][v], -q[0][v]
                new.append(([b * pc + a * qc for pc, qc in zip(p[0], q[0])], b * p[1] + a * q[1], p[2] or q[2]))
        rows = new
    return all((k > 0) if s else (k >= 0) for _, k, s in rows)
def rlin():
    """a linear form (text, coefficient list of x y z and constant)"""
    cs = [R.choice([0, 0, 1, -1, 2, -2]) for _ in range(3)]; k = R.choice([0, 0, 1, -1, 2])
    parts = [(f'{c} * {v}' if abs(c) != 1 else (v if c == 1 else f'-{v}')) for c, v in zip(cs, 'xyz') if c]
    if k or not parts: parts.append(str(k))
    return ' + '.join(parts).replace('+ -', '- '), cs + [k]
def ratom():
    (lt, lc), (rt, rc) = rlin(), rlin(); rel = R.choice(['<', '<=', '<=', '<'])
    d = [b - a for a, b in zip(lc, rc)]                           # rhs - lhs  (rel) 0
    return f'{lt} {rel} {rt}', (d[:3], d[3], rel == '<'), (([-x for x in d[:3]], -d[3], rel != '<'))   # the atom, its row, the row of its negation
for _ in range(n(40)):
    hs = [ratom() for _ in range(R.randint(1, 3))]; c = ratom()
    text = '(' + ' && '.join(f'({h[0]})' for h in hs) + f') => ({c[0]})'
    hrows = [h[1] for h in hs]
    valid = not feasible(hrows + [c[2]], 3)
    never = (not feasible([c[1]], 3)) and all(not feasible([h[2]], 3) for h in hs)
    verdict('denv', text, 1 if valid else (0 if never else 2))

# ---- piecewise-linear arithmetic: abs, min and max are expanded into their cases; the oracle expands the cases itself and decides every case by Fourier–Motzkin (feasible, above)
def lform(c, k=0): return list(c) + [k]
def vform(i): return [1 if t == i else 0 for t in range(3)] + [0]
def fadd(a, b, s=1): return [x + s * y for x, y in zip(a, b)]
def fneg(a): return [-x for x in a]
def rowge(f): return (f[:3], f[3], False)
def rowgt(f): return (f[:3], f[3], True)
def cases(e):
    """the cases of an expression: a list of (rows that the case needs, its linear form)"""
    t = e[0]
    if t == 'var': return [([], vform(e[1]))]
    if t == 'num': return [([], [0, 0, 0, e[1]])]
    if t == 'neg': return [(r, fneg(f)) for r, f in cases(e[1])]
    if t == 'mul': return [(r, [e[1] * x for x in f]) for r, f in cases(e[2])]
    if t == 'abs': return [x for r, f in cases(e[1]) for x in ((r + [rowge(f)], f), (r + [rowgt(fneg(f))], fneg(f)))]
    out = []
    for r1, f1 in cases(e[1]):
        for r2, f2 in cases(e[2]):
            if t in ('add', 'sub'): out.append((r1 + r2, fadd(f1, f2, 1 if t == 'add' else -1)))
            elif t == 'max': out += [(r1 + r2 + [rowge(fadd(f2, f1, -1))], f2), (r1 + r2 + [rowgt(fadd(f1, f2, -1))], f1)]
            elif t == 'min': out += [(r1 + r2 + [rowge(fadd(f2, f1, -1))], f1), (r1 + r2 + [rowgt(fadd(f1, f2, -1))], f2)]
    return out
def etext(e):
    t = e[0]
    if t == 'var': return 'xyz'[e[1]]
    if t == 'num': return str(e[1]) if e[1] >= 0 else f'({e[1]})'
    if t == 'neg': return f'(-{etext(e[1])})'
    if t == 'mul': return f'({e[1]} * {etext(e[2])})'
    if t == 'abs': return f'abs({etext(e[1])})'
    if t in ('max', 'min'): return f'{t}({etext(e[1])}, {etext(e[2])})'
    return f'({etext(e[1])} {"+" if t == "add" else "-"} {etext(e[2])})'
def rexpr(d):
    if d == 0 or R.random() < 0.25: return R.choice([('var', 0), ('var', 1), ('var', 2), ('num', R.randint(-2, 2))])
    k = R.random()
    if k < 0.25: return ('abs', rexpr(d - 1))
    if k < 0.45: return ('max', rexpr(d - 1), rexpr(d - 1))
    if k < 0.65: return ('min', rexpr(d - 1), rexpr(d - 1))
    if k < 0.8: return (R.choice(['add', 'sub']), rexpr(d - 1), rexpr(d - 1))
    if k < 0.9: return ('mul', R.choice([2, 3, -1, -2]), rexpr(d - 1))
    return ('neg', rexpr(d - 1))
def pverdict(l, rel, r):
    always_true, always_false = True, True
    for rl, fl in cases(l):
        for rr, fr in cases(r):
            region = rl + rr; d = fadd(fl, fr, -1)                     # d = l - r
            holds = {'<=': [rowge(fneg(d))], '<': [rowgt(fneg(d))], '>=': [rowge(d)], '>': [rowgt(d)], '=': [rowge(d), rowge(fneg(d))]}[rel]
            nots = {'<=': [[rowgt(d)]], '<': [[rowge(d)]], '>=': [[rowgt(fneg(d))]], '>': [[rowge(fneg(d))]], '=': [[rowgt(d)], [rowgt(fneg(d))]]}[rel]
            if feasible(region + holds, 3): always_false = False
            if any(feasible(region + nr, 3) for nr in nots): always_true = False
    return 1 if always_true else (0 if always_false else 2)
for _ in range(n(60)):
    l, r = rexpr(R.choice([1, 2, 2, 3])), rexpr(R.choice([1, 2]))
    rel = R.choice(['<=', '<', '>=', '>', '=', '<=', '>='])
    verdict('wenv', f'{etext(l)} {rel} {etext(r)}', pverdict(l, rel, r))
for t, v in [('abs(x) >= 0', 1), ('abs(x + y) <= abs(x) + abs(y)', 1), ('abs(x) = x', 2), ('abs(x) < 0', 0), ('max(x, y) = x', 2), ('abs(x) - abs(y) <= abs(x - y)', 1), ('min(x, y) <= x', 1),
             ('max(x, y) < min(x, y)', 0), ('sgn(x) * abs(x) = x', 1), ('sgn(x) = 1', 2), ('max(1, 2) = 2', 1), ('abs(-3) = 3', 1), ('min(2, -1) = -1', 1)]:
    verdict('wenv', t, v)
simp('wenv', 'abs(-3) + max(1, 2)', '5')

# ---- geometry: the same words, three geometries.  Closed statements against exact rational arithmetic; constructions (affine maps of the base points) against linear forms.
def gdot(p, q): return p[0] * q[0] + p[1] * q[1]
def ptx(p): return f'pt({p[0]}, {p[1]})'
def sgn_form(kind): return {'euclid': None, 'hyperbolic': -1, 'elliptic': 1}[kind]
def ip(kind, p, q): return gdot(p, q) + sgn_form(kind)
def rightangle_py(kind, a, b, c):
    if kind == 'euclid': return gdot((a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])) == 0
    return ip(kind, a, c) * ip(kind, b, b) == ip(kind, a, b) * ip(kind, b, c)
def trig2(kind, p, q): return ip(kind, p, q) ** 2 / (ip(kind, p, p) * ip(kind, q, q))
def cong_py(kind, a, b, c, d):
    if kind == 'euclid': return gdot((a[0] - b[0], a[1] - b[1]), (a[0] - b[0], a[1] - b[1])) == gdot((c[0] - d[0], c[1] - d[1]), (c[0] - d[0], c[1] - d[1]))
    return trig2(kind, a, b) == trig2(kind, c, d)
def cross_py(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
def rpt(kind):
    if kind == 'euclid': return (F(R.randint(-4, 4)), F(R.randint(-4, 4)))
    while True:                                          # inside the unit disc, rational
        p = (F(R.randint(-6, 6), 8), F(R.randint(-6, 6), 8))
        if gdot(p, p) < 1: return p
def tf(p): return f'pt({lit(p[0], "Q")}, {lit(p[1], "Q")})'
GENV = {'euclid': 'uenv', 'hyperbolic': 'benv', 'elliptic': 'xenv'}
for kind, env in GENV.items():
    for _ in range(n(24)):
        a, b, c, d = rpt(kind), rpt(kind), rpt(kind), rpt(kind)
        verdict(env, f'collinear({tf(a)}, {tf(b)}, {tf(c)})', 1 if cross_py(a, b, c) == 0 else 0)
        verdict(env, f'rightangle({tf(a)}, {tf(b)}, {tf(c)})', 1 if rightangle_py(kind, a, b, c) else 0)
        verdict(env, f'cong({tf(a)}, {tf(b)}, {tf(c)}, {tf(d)})', 1 if cong_py(kind, a, b, c, d) else 0)
        rot = lambda p: (-p[1], p[0]); neg = lambda p: (-p[0], -p[1]); refl = lambda p: (p[0], -p[1])      # isometries of all three geometries
        f = R.choice([rot, neg, refl])
        verdict(env, f'cong({tf(a)}, {tf(b)}, {tf(f(a))}, {tf(f(b))})', 1)
        o = (F(0), F(0)); s_, t_ = F(R.randint(1, 3), 8), F(R.randint(1, 3), 8); k = F(R.randint(1, 3), 8)
        verdict(env, f'rightangle({tf((s_, t_))}, {tf(o)}, {tf((-k * t_, k * s_))})', 1)          # perpendicular directions at the centre
for _ in range(n(24)):                                   # euclid only: parallels, perpendiculars, betweenness
    a, b, c, d = rpt('euclid'), rpt('euclid'), rpt('euclid'), rpt('euclid')
    u, v = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    verdict('uenv', f'par({tf(a)}, {tf(b)}, {tf(c)}, {tf(d)})', 1 if u[0] * v[1] - u[1] * v[0] == 0 else 0)
    verdict('uenv', f'perp({tf(a)}, {tf(b)}, {tf(c)}, {tf(d)})', 1 if gdot(u, v) == 0 else 0)
    bt = cross_py(a, b, c) == 0 and gdot((a[0] - b[0], a[1] - b[1]), (c[0] - b[0], c[1] - b[1])) < 0
    verdict('uenv', f'between({tf(a)}, {tf(b)}, {tf(c)})', 1 if bt else 0)
    t = F(R.randint(1, 5), 6); m = (a[0] + t * (c[0] - a[0]), a[1] + t * (c[1] - a[1]))          # a point on the open segment, or beyond it
    verdict('uenv', f'between({tf(a)}, {tf(m)}, {tf(c)})', 1 if (a != c) else 0)
    verdict('uenv', f'between({tf(a)}, {tf((a[0] + 3 * (c[0] - a[0]), a[1] + 3 * (c[1] - a[1])))}, {tf(c)})', 0)
# constructions: every coordinate of a constructed point is a linear form in the coordinates of the base points
BASE = ['A', 'B', 'C', 'D']
def lform_pt(i): return ({(2 * i): F(1)}, {(2 * i + 1): F(1)})
def lcomb(*terms):
    out = {}
    for c, f in terms:
        for k_, v_ in f.items(): out[k_] = out.get(k_, 0) + c * v_
    return {k_: v_ for k_, v_ in out.items() if v_ != 0}
def construct(d):
    if d == 0 or R.random() < 0.3:
        i = R.randint(0, 3); return BASE[i], lform_pt(i)
    k = R.random()
    if k < 0.3:
        (t1, f1), (t2, f2) = construct(d - 1), construct(d - 1); return f'midpoint({t1}, {t2})', tuple(lcomb((F(1, 2), f1[j]), (F(1, 2), f2[j])) for j in (0, 1))
    if k < 0.5:
        (t1, f1), (t2, f2), (t3, f3) = construct(d - 1), construct(d - 1), construct(d - 1)
        return f'centroid({t1}, {t2}, {t3})', tuple(lcomb((F(1, 3), f1[j]), (F(1, 3), f2[j]), (F(1, 3), f3[j])) for j in (0, 1))
    if k < 0.7:
        (t1, f1), (t2, f2), (t3, f3) = construct(d - 1), construct(d - 1), construct(d - 1)
        return f'fourth({t1}, {t2}, {t3})', tuple(lcomb((F(1), f1[j]), (F(-1), f2[j]), (F(1), f3[j])) for j in (0, 1))
    if k < 0.85:
        (t1, f1), (t2, f2) = construct(d - 1), construct(d - 1); return f'reflect({t1}, {t2})', tuple(lcomb((F(2), f2[j]), (F(-1), f1[j])) for j in (0, 1))
    (t1, f1), (t2, f2) = construct(d - 1), construct(d - 1)
    return f'rot({t1}, {t2})', (lcomb((F(1), f2[0]), (F(-1), f1[1]), (F(1), f2[1])), lcomb((F(1), f2[1]), (F(1), f1[0]), (F(-1), f2[0])))
for _ in range(n(40)):
    (t1, f1), (t2, f2) = construct(2), construct(2)
    diffs = [lcomb((F(1), f1[j]), (F(-1), f2[j])) for j in (0, 1)]
    if all(not dd for dd in diffs): want = 1
    elif any(dd and all(k_ is None for k_ in dd) for dd in diffs): want = 0
    else: want = 2
    verdict('uenv', f'same({t1}, {t2})', want)
for t, v in [('rightangle(pt(3/4, 1/4), pt(1/2, 1/4), pt(1/2, 1/2))', 1)]: verdict('uenv', t, v)
for t, v in [('rightangle(pt(3/4, 1/4), pt(1/2, 1/4), pt(1/2, 1/2))', 0)]: verdict('benv', t, v); verdict('xenv', t, v)
RECT = 'rightangle(pt(3/4, 1/4), pt(1/2, 1/4), pt(1/2, 1/2)) && rightangle(pt(1/2, 1/4), pt(1/2, 1/2), pt(3/4, 1/2)) && rightangle(pt(1/2, 1/2), pt(3/4, 1/2), pt(3/4, 1/4)) && rightangle(pt(3/4, 1/2), pt(3/4, 1/4), pt(1/2, 1/4))'
verdict('uenv', RECT, 1); verdict('benv', RECT, 0); verdict('xenv', RECT, 0)
for t, v in [('collinear(A, B, C) => collinear(B, A, C)', 1), ('collinear(A, B, C)', 2), ('same(A, B)', 2), ('dist2(A, B) < 0', 0), ('dist2(A, B) >= 0', 1), ('dist2(A, B) > 0', 2), ('perp(A, B, B, C)', 2),
             ('par(A, B, A, B)', 1), ('cong(A, B, C, D)', 2), ('midpoint(A, B) = midpoint(B, A)', 1), ('cross(A, B, C) = 0', 2)]: verdict('uenv', t, v)
verdict('defenv', 'dist2(A, B) >= 0', 2)           # without the package the words mean nothing
verdict('defenv', 'rightangle(A, B, C)', 2)
simp('uenv', 'dist2(pt(0, 0), pt(3, 4))', '25')
simp('uenv', 'px(midpoint(pt(2, 4), pt(4, 8)))', '3')
simp('benv', 'coshsq(pt(0, 0), pt(1/2, 0))', '4/3')
simp('xenv', 'cossq(pt(0, 0), pt(1/2, 0))', '4/5')

# ---- topology: words in the closure k and the complement c.  The oracle is a set of finite topological spaces (preorders: cl(S) is the set of points below a point of S) with subsets;
# two words are equal when they agree everywhere there.  The 14 normal forms are told apart by the sample (asserted below), so the sample is complete for the monoid of Kuratowski.
def spaces(num):
    out = []
    for _ in range(num):
        m = R.randint(3, 7)
        le = [[i == j or R.random() < 0.18 for j in range(m)] for i in range(m)]
        for k_ in range(m):                                             # transitive closure
            for i in range(m):
                for j in range(m):
                    if le[i][k_] and le[k_][j]: le[i][j] = True
        out.append((m, le))
    return out
SP = spaces(60)
def kcl(sp, S): m, le = sp; return frozenset(i for i in range(m) if any(le[i][j] for j in S))
def kcomp(sp, S): return frozenset(range(sp[0])) - S
def run_word(w, sp, S):
    for letter in reversed(w): S = kcl(sp, S) if letter == 'k' else kcomp(sp, S)
    return S
SUBS = [(sp, frozenset(i for i in range(sp[0]) if R.random() < 0.5)) for sp in SP for _ in range(8)]
def signature(w): return tuple(run_word(w, sp, S) for sp, S in SUBS)
def words(maxlen):
    out = ['']
    for ln in range(1, maxlen + 1):
        out += [''.join(t) for t in itertools.product('kc', repeat=ln)]
    return out
SIGS = {w: signature(w) for w in words(8)}
assert len(set(SIGS.values())) == 14, len(set(SIGS.values()))           # Kuratowski's theorem: 14 operations, all told apart by the sample
def word_text(w):
    e = 'A'
    for letter in reversed(w): e = f'cl({e})' if letter == 'k' else f'({e})ᶜ'
    return e
ws = list(SIGS)
for _ in range(n(60)):
    w1, w2 = R.choice(ws), R.choice(ws)
    pairs = list(zip(SUBS, SIGS[w1], SIGS[w2]))
    if SIGS[w1] == SIGS[w2]: verdict('tenv', f'{word_text(w1)} = {word_text(w2)}', 1)
    elif all(a == kcomp(sp, b) for (sp, _), a, b in pairs): verdict('tenv', f'{word_text(w1)} = {word_text(w2)}', 0)         # X = X complement: false for all sets
    elif any(a == b for _, a, b in pairs): verdict('tenv', f'{word_text(w1)} = {word_text(w2)}', 2)
    else: provable('tenv', f'{word_text(w1)} = {word_text(w2)}', False)
for _ in range(n(40)):                                                  # inclusions: whatever the engine proves must hold in the sample (soundness)
    w1, w2 = R.choice(ws), R.choice(ws)
    holds = all(a <= b for a, b in zip(SIGS[w1], SIGS[w2]))
    if not holds: provable('tenv', f'{word_text(w1)} ⊆ {word_text(w2)}', False)
for w in ['kk', 'cc', 'kckckck', 'kckckckc', 'ckckckck', 'kckckckckck']:
    verdict('tenv', f'{word_text(w)} = {word_text({"kk": "k", "cc": "", "kckckck": "kck", "kckckckc": "kckc", "ckckckck": "ckck", "kckckckckck": "kck"}[w])}', 1)
for t, v in [('cl(A) = A', 2), ('cl(A) = int(A)', 2), ('cl(A ∩ B) = cl(A) ∩ cl(B)', 2), ('int(A ∪ B) = int(A) ∪ int(B)', 2), ('cl(A) ⊆ A', 2), ('A ⊆ cl(A)', 1), ('int(A) ⊆ A', 1), ('cl(∅) = ∅', 1),
             ('cl(A ∪ B) = cl(A) ∪ cl(B)', 1), ('bd(A) = bd(Aᶜ)', 1), ('A ⊆ int(A)', 2), ('open(A) && open(B) => open(A ∩ B)', 1), ('open(A) && open(B) => open(A ∪ B)', 2)]: verdict('tenv', t, v)
# ---- monoids: the words of the free monoid (letters x y z, the unit ε) and of the free commutative monoid
def mword(): return [R.choice('xyz') if R.random() < 0.85 else 'ε' for _ in range(R.randint(1, 5))]
def mtext(w):
    t = ' ⋆ '.join(w)
    return t
for _ in range(n(40)):
    w1, w2 = mword(), mword()
    f1, f2 = [c for c in w1 if c != 'ε'], [c for c in w2 if c != 'ε']
    verdict('menv', f'{mtext(w1)} = {mtext(w2)}', 1 if f1 == f2 else 2)
    verdict('cmenv', f'{mtext(w1)} = {mtext(w2)}', 1 if sorted(f1) == sorted(f2) else 2)
for env, t, v in [('menv', 'x ⋆ y = y ⋆ x', 2), ('cmenv', 'x ⋆ y = y ⋆ x', 1), ('menv', 'x ⋆ y = x ⋆ z => y = z', 2), ('cmenv', 'x ⋆ y = x ⋆ z => y = z', 2), ('menv', 'x ⋆ x = x', 2), ('menv', '(x ⋆ y) ⋆ z = x ⋆ (y ⋆ z)', 1),
                  ('menv', 'ε ⋆ x = x', 1), ('cmenv', 'x ⋆ y ⋆ x = x ⋆ x ⋆ y', 1), ('menv', 'x ⋆ y ⋆ x = x ⋆ x ⋆ y', 2)]: verdict(env, t, v)
verdict('genv', 'x · y = y · x', 2)

# ---- words of groups: free reduction decides the word problem of the free group, exponent sums that of the free abelian group
def rword(d=2):
    items = []
    for _ in range(R.randint(0, 5)):
        k = R.random()
        if k < 0.55: items.append(('g', R.choice('abc'), R.choice([1, -1])))
        elif k < 0.75 and d > 0: items.append(('w', rword(d - 1), 1))
        elif d > 0: items.append(('w', rword(d - 1), -1))
        else: items.append(('g', R.choice('abc'), 1))
    return items
def wflat(w):
    out = []
    for it in w:
        if it[0] == 'g': out.append((it[1], it[2]))
        else:
            sub = wflat(it[1])
            out += sub if it[2] == 1 else [(g, -e) for g, e in reversed(sub)]
    return out
def wstr(w):
    if not w: return 'e'
    parts = []
    for it in w:
        if it[0] == 'g': parts.append(it[1] if it[2] == 1 else f'inv({it[1]})')
        else: parts.append(f'({wstr(it[1])})' if it[2] == 1 else f'inv({wstr(it[1])})')
    return ' · '.join(parts)
def wreduce(fl):
    st = []
    for g, e in fl:
        if st and st[-1] == (g, -e): st.pop()
        else: st.append((g, e))
    return st
def wexps(fl):
    d = {}
    for g, e in fl: d[g] = d.get(g, 0) + e
    return {g: e for g, e in d.items() if e}
def wmutate(w):
    """an equal word: insert x x⁻¹ somewhere, or conjugate"""
    w = list(w); g = R.choice('abc'); pos = R.randint(0, len(w))
    w[pos:pos] = [('g', g, 1), ('g', g, -1)] if R.random() < 0.5 else [('g', g, -1), ('g', g, 1)]
    return w
for _ in range(n(30)):
    w1 = rword(); w2 = wmutate(w1) if R.random() < 0.5 else (rword() if R.random() < 0.7 else list(reversed(w1)))
    f1, f2 = wflat(w1), wflat(w2)
    verdict('genv', f'{wstr(w1)} = {wstr(w2)}', 1 if wreduce(f1) == wreduce(f2) else 2)
    verdict('aenv', f'{wstr(w1)} = {wstr(w2)}', 1 if wexps(f1) == wexps(f2) else 2)

# ---- the algebra of sets: truth tables over membership types
def rset(d):
    if d == 0 or R.random() < 0.25: return R.choice([('v', 'A'), ('v', 'B'), ('v', 'C'), ('v', 'A'), ('c', 'e'), ('c', 'u')])
    op = R.choice(['cup', 'cap', 'not', 'dif', 'cup', 'cap'])
    return (op, rset(d - 1)) if op == 'not' else (op, rset(d - 1), rset(d - 1))
def sstr(s):
    k = s[0]
    if k == 'v': return s[1]
    if k == 'c': return '∅' if s[1] == 'e' else 'U'
    if k == 'not': return f'({sstr(s[1])})ᶜ'
    sym = {'cup': '∪', 'cap': '∩', 'dif': '\\'}[k]
    return f'({sstr(s[1])} {sym} {sstr(s[2])})'
def seval(s, a):
    k = s[0]
    if k == 'v': return a[s[1]]
    if k == 'c': return s[1] == 'u'
    if k == 'not': return not seval(s[1], a)
    x, y = seval(s[1], a), seval(s[2], a)
    return {'cup': x or y, 'cap': x and y, 'dif': x and not y}[k]
TYPES = [dict(zip('ABC', bits)) for bits in itertools.product([False, True], repeat=3)]
for _ in range(n(30)):
    s, t = rset(3), rset(3)
    if R.random() < 0.3: t = s if R.random() < 0.5 else ('not', ('not', s))
    eqs = [seval(s, a) == seval(t, a) for a in TYPES]; subs = [(not seval(s, a)) or seval(t, a) for a in TYPES]
    verdict('senv', f'{sstr(s)} = {sstr(t)}', 1 if all(eqs) else (0 if not any(eqs) else 2))
    verdict('senv', f'{sstr(s)} ⊆ {sstr(t)}', 1 if all(subs) else (0 if not any(subs) else 2))

# ---- probability: a linear statement is decided by the vertices of the simplex of distributions on the minterms (the point masses)
def rset_p(d):
    if d == 0 or R.random() < 0.3: return ('v', R.choice('ABC'))
    op = R.choice(['cup', 'cap', 'not', 'dif'])
    return (op, rset_p(d - 1)) if op == 'not' else (op, rset_p(d - 1), rset_p(d - 1))
def pstr(s):
    k = s[0]
    if k == 'v': return s[1]
    if k == 'not': return f'({pstr(s[1])})ᶜ'
    sym = {'cup': '∪', 'cap': '∩', 'dif': '\\'}[k]
    return f'({pstr(s[1])} {sym} {pstr(s[2])})'
def peval(s, a):
    k = s[0]
    if k == 'v': return a[s[1]]
    if k == 'not': return not peval(s[1], a)
    x, y = peval(s[1], a), peval(s[2], a)
    return {'cup': x or y, 'cap': x and y, 'dif': x and not y}[k]
for _ in range(n(30)):
    nev = R.choice([1, 2, 2, 3]); evs = 'ABC'[:nev]
    terms = []
    for _ in range(R.randint(1, 2)):
        e = rset_p(R.choice([1, 2])); terms.append((R.choice([1, 1, 2, -1, 3]), e))
    # restrict the variables to the events chosen
    def ok(s): return set(re.findall('[ABC]', pstr(s))) <= set(evs)
    terms = [(c, e) for c, e in terms if ok(e)] or [(1, ('v', 'A'))]
    k = R.choice([0, 1, 1, 2, F(1, 2)]); rel = R.choice(['<=', '<', '=', '>=', '>'])
    lhs = ' + '.join(f'{c} * P({pstr(e)})' for c, e in terms).replace('+ -', '- ')
    kt = str(k) if not isinstance(k, F) else f'{k.numerator}/{k.denominator}'
    vals = [sum(c * (1 if peval(e, dict(zip(evs, bits))) else 0) for c, e in terms) for bits in itertools.product([False, True], repeat=nev)]
    lo, hi = min(vals), max(vals)
    if rel == '<=': v = 1 if hi <= k else (0 if lo > k else 2)
    elif rel == '<': v = 1 if hi < k else (0 if lo >= k else 2)
    elif rel == '>=': v = 1 if lo >= k else (0 if hi < k else 2)
    elif rel == '>': v = 1 if lo > k else (0 if hi <= k else 2)
    else: v = 1 if lo == hi == k else (0 if (k < lo or k > hi) else 2)
    verdict('kenv', f'{lhs} {rel} {kt}', v)

# ---- hereditarily finite sets: Python frozensets
def rhf(d):
    k = R.randint(0, 3); els = []
    for _ in range(k):
        els.append(rhf(d - 1) if d > 0 and R.random() < 0.4 else R.randint(1, 3))
    return frozenset(els)
def hfstr(s):
    if isinstance(s, int): return str(s)
    if not s: return '∅'
    return '{' + ', '.join(sorted(hfstr(x) for x in s)) + '}'
for _ in range(n(25)):
    a, b = rhf(2), rhf(2); x = R.choice([1, 2, 3, a, b, frozenset()])
    verdict('zenv', f'{hfstr(a)} = {hfstr(b)}', 1 if a == b else 0)
    verdict('zenv', f'{hfstr(a)} ⊆ {hfstr(b)}', 1 if a <= b else 0)
    verdict('zenv', f'{hfstr(x)} ∈ {hfstr(b)}', 1 if x in b else 0)
    verdict('zenv', f'card({hfstr(a)} ∪ {hfstr(b)}) = {len(a | b)}', 1)
    verdict('zenv', f'{hfstr(a)} \\ {hfstr(b)} = {hfstr(a - b)}', 1)

# ---- chains of morphisms: composition is associative and id is neutral
def rchain(k):
    gens = [R.choice(['f', 'g', 'h', 'k']) for _ in range(k)]
    def build(xs):
        if len(xs) == 1: return xs[0] if R.random() < 0.8 else f'(id ∘ {xs[0]})'
        i = R.randint(1, len(xs) - 1); return f'({build(xs[:i])} ∘ {build(xs[i:])})'
    return gens, build(gens)
for _ in range(n(20)):
    gens, e1 = rchain(R.randint(1, 5))
    verdict('eenv', f'{e1} = {" ∘ ".join(gens)}', 1)
    other = list(gens); R.shuffle(other)
    if other != gens: verdict('eenv', f'{e1} = {" ∘ ".join(other)}', 2)

# ---- lattices: instances of the laws with arbitrary terms
def rlat(d):
    if d == 0 or R.random() < 0.3: return R.choice('xyz')
    return f'({rlat(d - 1)} {R.choice(["⊔", "⊓"])} {rlat(d - 1)})'
for _ in range(n(10)):
    t, u = rlat(2), rlat(1)
    verdict('lenv', f'{u} ⊔ ({u} ⊓ {t}) = {u}', 1); verdict('lenv', f'{u} ⊓ ({u} ⊔ {t}) = {u}', 1)
    verdict('lenv', f'{t} ⊔ {u} = {u} ⊔ {t}', 1); verdict('lenv', f'{t} ⊔ {t} = {t}', 1)

if __name__ == '__main__': sys.exit(0 if report(S) else 1)
