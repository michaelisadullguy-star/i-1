"""test_axioms.py -- the axiom audit of ℚ[i]: the laws that make the prelude's ℚ[i] a field (with total division), an ordered field on ℚ,
with an involutive automorphism (conjugation), a decidable equality that is a congruence, and unique canonical forms.
Every law is evaluated IN THE LANGUAGE (the python side only builds inputs and reads Booleans / digits back).
See docs/axioms.md for the statements, the proofs, and what is proved versus what is tested.        python3 tests/test_axioms.py"""
import os, sys, itertools, random, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from harness import *
from base_b import gmul

rep = Report()

def main():
    E = load_env()
    C = E.call
    eq = lambda x, y: E.b(C('≐', x, y))
    rnd = random.Random(7)

    # ------------------------------------------------------------------ representation: base i−1 digit strings
    ok = subprocess.run([sys.executable, os.path.join(ROOT, 'pymo', 'mkcarry.py'), '--check'], capture_output=True).returncode == 0
    rep("the carry tables in lib/number.imo are exactly the transitions derived from first principles (pymo/mkcarry.py --check)", ok)
    strings = [list(t) for L in range(0, 6) for t in itertools.product([0, 1], repeat=L)]
    bad = 0
    for a in strings:
        va = E.raw(a)
        for b in strings:
            x, y = val(a), val(b)
            bad += E.dz(C('⊟ᶻ', va, E.raw(b))) != (x[0] - y[0], x[1] - y[1])
    rep(f"ℤ[i] subtraction (its own serial transducer, 47 carry numerals) is exact on ALL {len(strings) ** 2} pairs of length ≤ 5", bad == 0)
    bad = 0; n = 0
    for L in range(0, 12):
        for t in itertools.product((0, 1), repeat=L):
            z = val(list(t)); v = E.raw(list(t)); n += 1
            bad += E.ord3(C('⋚ʳ', v)) != sgn(z[0]) or E.ord3(C('⋚ⁱ', v)) != sgn(z[1])
            if L <= 8:
                bad += E.dz(C('ℜᶻ', v)) != (z[0], 0) or E.dz(C('ℑᶻ', v)) != (z[1], 0) or E.dz(C('∗ᶻ', v)) != (z[0], -z[1])
                bad += E.digits(C('⊡', E.raw(list(t) + [0, 0]))) != to_digits(z)
    rep(f"sign of Re and Im (one pass over the digits) exact on ALL {n} digit strings of length ≤ 11; Re, Im, conjugation and canonical digits on all of length ≤ 8", bad == 0)
    # python twin of the sign automaton, much further
    def sign_re(d):
        s, odd = 0, False
        for j in range(0, len(d), 4):
            b = (d[j:j + 4] + [0, 0, 0, 0])[:4]
            r = b[0] - b[1] + 2 * b[3]
            if r: s = (1 if r > 0 else -1) * (-1 if odd else 1)
            odd = not odd
        return s
    bad = sum(sign_re(list(t)) != sgn(val(list(t))[0]) for L in range(0, 19) for t in itertools.product((0, 1), repeat=L))
    rep("the sign rule  sign Re z = sign(r_J)·(−1)^J  (python twin of the automaton) holds on all 524287 digit strings of length ≤ 18", bad == 0)

    # ------------------------------------------------------------------ the sample: values and several representations of the same values
    def rep_q(x, k=(1, 0)):
        """the value x written as (k·p)/(k·q) — a different pair for a different k"""
        D = math.lcm(x.r.denominator, x.i.denominator); p = (int(x.r * D), int(x.i * D))
        return C('⊗', E.z(gmul(p, k)), E.z(gmul((D, 0), k)))
    vals = [R.Q(0), R.Q(1), R.Q(-1), R.Q(0, 1), R.Q(1, 1), R.Q(Fr(1, 2)), R.Q(Fr(-3, 4), Fr(2, 3)), R.Q(Fr(2, 3), -1)]
    S = [rep_q(x) for x in vals]
    ks = [(2, 0), (0, 1), (1, -1), (-3, 2)]
    alt = [rep_q(x, ks[i % len(ks)]) for i, x in enumerate(vals)]                     # same values, other pairs
    half12 = C('⊗', E.z(1), E.z(2))                                                  # the pair (1, 2)
    num = [C('⊗', E.raw([1, 1, 1]), E.raw([0, 0, 1]))]                               # the numeral 1.11 = 111 / b² = (−i)/(−2i)
    rep("the numeral 1.11 is 1/2: it is ≐ to the pairs (1, 2), (2, 4) and (1·k, 2·k) for a complex k", all(eq(num[0], y) for y in (S[5], alt[5], half12)))
    zero, one = S[0], S[1]
    add = lambda x, y: C('⊞', x, y); mul = lambda x, y: C('⊠', x, y); neg = lambda x: C('⊖', x)
    inv = lambda x: C('÷', one, x); cj = lambda x: C('∗', x)

    # ------------------------------------------------------------------ ≐ is an equivalence and a congruence
    T = S + alt
    ok = all(eq(x, x) for x in T) and all(eq(x, y) == eq(y, x) for x in T for y in T)
    ok &= all(not (eq(x, y) and eq(y, z)) or eq(x, z) for x in T for y in T for z in T[:6] + alt[:4])
    rep(f"≐ is reflexive, symmetric and transitive on {len(T)} pairs representing {len(vals)} values (with total division no pair has denominator 0)", ok)
    ok = True
    for x, x2 in zip(S, alt):
        for y, y2 in zip(S, alt):
            ok &= eq(add(x, y), add(x2, y2)) and eq(mul(x, y), mul(x2, y2)) and eq(C('÷', x, y), C('÷', x2, y2))
        ok &= eq(neg(x), neg(x2)) and eq(cj(x), cj(x2)) and eq(inv(x), inv(x2))
    rep("≐ is a congruence: ⊞ ⊠ ÷ ⊖ ∗ give ≐ results on ≐ arguments (all pairs of the sample, two representations each)", ok)

    # ------------------------------------------------------------------ field axioms (commutative ring + inverses), and the meadow laws
    ok = True
    for x, y, z in itertools.product(S, repeat=3):
        ok &= eq(add(add(x, y), z), add(x, add(y, z))) and eq(mul(mul(x, y), z), mul(x, mul(y, z))) and eq(mul(x, add(y, z)), add(mul(x, y), mul(x, z)))
    rep(f"associativity of ⊞ and ⊠, distributivity: all {len(S) ** 3} triples of the sample", ok)
    ok = all(eq(add(x, y), add(y, x)) and eq(mul(x, y), mul(y, x)) for x in S for y in S)
    ok &= all(eq(add(x, zero), x) and eq(mul(x, one), x) and eq(add(x, neg(x)), zero) for x in S)
    ok &= all(eq(mul(x, inv(x)), one) for x in S[1:]) and not eq(zero, one)
    rep("commutativity, 0 and 1, additive inverses, x·x⁻¹ = 1 for x ≠ 0, and 0 ≠ 1", ok)
    ok = eq(inv(zero), zero) and all(eq(inv(inv(x)), x) and eq(mul(x, mul(x, inv(x))), x) for x in S + alt)
    rep("total division (a meadow, Bergstra–Tucker): 0⁻¹ = 0,  (x⁻¹)⁻¹ = x,  x·(x·x⁻¹) = x  for every x of the sample", ok)
    ok = True
    for _ in range(20):
        a, b, c = [R.randQ(rnd, 30) for _ in range(3)]
        A, B, Cc = E.q(a), E.q(b), E.q(c)
        ok &= E.dq(mul(add(A, B), Cc)) == (a + b) * c and E.dq(C('÷', A, B)) == (a * b.inv() if not b.iszero() else R.Q(0)) and E.dq(C('⊟', A, B)) == a - b
    rep("the field operations agree with exact Gaussian rationals on 20 random triples", ok)

    # ------------------------------------------------------------------ conjugation: an automorphism of order 2 fixing ℚ
    ok = all(eq(cj(cj(x)), x) for x in S) and all(eq(cj(add(x, y)), add(cj(x), cj(y))) and eq(cj(mul(x, y)), mul(cj(x), cj(y))) for x in S for y in S)
    ok &= all(eq(cj(x), x) == (v.i == 0) for x, v in zip(S, vals)) and eq(cj(S[3]), neg(S[3]))
    rep("conjugation is an involution, additive and multiplicative, fixes exactly the real elements, and ī = −i", ok)

    # ------------------------------------------------------------------ order on ℚ (an ordered field)
    reals = [E.q(Fr(n, d)) for n, d in [(0, 1), (1, 1), (-1, 1), (1, 2), (-7, 3), (22, 7), (355, 113), (-1, 1000)]] + [rep_q(R.Q(Fr(1, 2)), (0, 1)), rep_q(R.Q(Fr(-7, 3)), (1, 1))]
    ge = lambda x, y: E.b(C('⩾', x, y))
    ok = all(ge(x, y) or ge(y, x) for x in reals for y in reals)
    ok &= all(not (ge(x, y) and ge(y, x)) or eq(x, y) for x in reals for y in reals)
    ok &= all(not (ge(x, y) and ge(y, z)) or ge(x, z) for x in reals for y in reals for z in reals[:5])
    ok &= all(not ge(x, y) or ge(add(x, z), add(y, z)) for x in reals for y in reals for z in reals[:4])
    ok &= all(not (ge(x, zero) and ge(y, zero)) or ge(mul(x, y), zero) for x in reals for y in reals)
    rep("⩾ on ℚ is a total order (total, antisymmetric modulo ≐, transitive), compatible with + and with · of non-negatives", ok)
    ok = True
    for _ in range(40):
        x = Fr(rnd.randint(-10 ** 12, 10 ** 12), rnd.randint(1, 10 ** 6)); y = x if rnd.random() < .2 else Fr(rnd.randint(-10 ** 12, 10 ** 12), rnd.randint(1, 10 ** 6))
        ok &= E.ord3(C('⋚', E.q(x), E.q(y))) == sgn(x - y)
    rep("three-way comparison ⋚ agrees with exact comparison on 40 random pairs of size up to 10¹²  (no search: linear in the digits)", ok)

    # ------------------------------------------------------------------ canonical forms: equality of values is identity of canonical forms
    canon = lambda x: E.pair_digits(C('⊜', x))
    ok = all(canon(x) == canon(y) for x, y in zip(S, alt)) and canon(num[0]) == canon(S[5])
    ok &= all((canon(x) == canon(y)) == eq(x, y) for x in S for y in S)
    for x, v in zip(S, vals):
        zd, md = canon(x); z, m = val(zd), val(md)
        ok &= m[1] == 0 and m[0] >= 1 and math.gcd(math.gcd(z[0], z[1]), m[0]) == 1 and R.Q(z[0], z[1]) * R.Q(m[0]).inv() == v
        ok &= canon(C('⊜', x)) == (zd, md)
    rep("⊜ (canonical form z/m, m the least natural with m·x ∈ ℤ[i]): x ≐ y ⇔ ⊜x and ⊜y are the same digit strings; ⊜ is idempotent", ok)
    ok = all(eq(add(C('ℜ', x), mul(C('ℑ', x), S[3])), x) and eq(C('𝒩', x), mul(x, cj(x))) for x in S)
    rep("x = Re x + i·Im x and N(x) = x·x̄ on the sample", ok)
    return rep.done()

sys.exit(0 if run_big(main) else 1)
