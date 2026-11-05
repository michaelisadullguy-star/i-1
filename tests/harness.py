"""harness.py -- shared helpers for the test-suites: build language values from python numbers and decode them back.
Only the isomorphism  digit string <-> Gaussian integer  (base_b.val / to_digits) is used on the python side.

The CORE under test is Pymo (the default), Haskimo or Rustimo:   python3 tests/test_poly.py --core rustimo     (or  I1_CORE=rustimo ...)
The suites that use only imo.Program, Env and the decoders below run on any core (README §16.3); with --core haskimo or --core rustimo the
program is built and evaluated by  haskimo serve  or  rustimo serve  (tests/core_serve.py) and a value is a handle into that process.  A
suite that tests the Python API of Pymo itself (its readers, its checker, its printer) says so and refuses the other cores."""
import os, sys, time
from fractions import Fraction as Fr
from math import lcm
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'pymo')); sys.path.insert(0, HERE)
import imo
from imo import done, to_bool, to_list, to_pair, stream_nth, list_value, run_big
from base_b import val, to_digits
import refmath as R

def _core():
    c = os.environ.get('I1_CORE', 'pymo')
    if '--core' in sys.argv:
        i = sys.argv.index('--core'); c = sys.argv[i + 1]; del sys.argv[i:i + 2]
    c = {'py': 'pymo', 'hs': 'haskimo', 'rs': 'rustimo', 'cs': 'compimo', 'oc': 'ocamimo', 'sm': 'schimo', 'ci': 'cimo', 'ri': 'rimo'}.get(c, c)
    if c not in ('pymo', 'haskimo', 'rustimo', 'compimo', 'ocamimo', 'schimo', 'cimo', 'rimo'): raise SystemExit(f"--core takes pymo, haskimo, rustimo, compimo, ocamimo, schimo, cimo or rimo, not {c!r}")
    return c
CORE = _core()

def pymo_only(why):
    """a suite that tests the Python API of Pymo itself calls this first: it has no counterpart for Haskimo"""
    if CORE != 'pymo':
        raise SystemExit(f"this suite tests {why} of Pymo through its Python API, so it runs on Pymo only; "
                         f"what it checks has command-line counterparts in tests/conformance, which run on both cores")

class Env:
    """a loaded program with helpers:  E.call('⊞', x, y),  E.q(Fraction or R.Q) -> value,  E.dq(value) -> R.Q"""
    def __init__(self, P):
        self.P = P; self.M = P.machine; self.V = self.M.val
    def call(self, f, *a):
        f = self.V(f) if isinstance(f, str) else f
        for x in a: f = f(x if hasattr(x, 'force') else done(x))
        return f
    def z(self, z):                       # python Gaussian integer (re, im) or int -> digit list value
        if isinstance(z, int): z = (z, 0)
        return list_value(self.M, to_digits(z))
    def raw(self, digs): return list_value(self.M, digs)
    def q(self, x, den=None):             # R.Q / Fraction / int -> ℚ[i] value (as a pair over a natural denominator)
        if den is not None: return self.call('⊗', self.z(x), self.z(den))
        if not isinstance(x, R.Q): x = R.Q(x)
        D = lcm(x.r.denominator, x.i.denominator)
        return self.call('⊗', self.z((int(x.r * D), int(x.i * D))), self.z((D, 0)))
    def dz(self, v): return val(to_list(v))
    def digits(self, v): return to_list(v)
    def dq(self, v):
        p, d = to_pair(v); P_, D_ = val(to_list(p)), val(to_list(d))
        assert D_ != (0, 0), "denominator 0"
        return R.Q(P_[0], P_[1]) * R.Q(D_[0], D_[1]).inv()
    def pair_digits(self, v):
        p, d = to_pair(v); return to_list(p), to_list(d)
    def b(self, v): return to_bool(v)
    def ord3(self, v):                    # 𝔒 value -> -1 / 0 / 1
        return v(done(-1))(done(0))(done(1))
    def lst(self, v, dec=None):           # Scott list -> python list of (decoded) elements
        from imo_core import CONS_TH, NIL_TH
        out, r = [], v(CONS_TH)(NIL_TH)
        while r[0] == 'C':
            h = r[1].force(); out.append(dec(h) if dec else h); r = r[2].force()(CONS_TH)(NIL_TH)
        return out
    def nth(self, v, n): return stream_nth(v, n)

if CORE != 'pymo':
    import core_serve
    core_serve.CORE_NAME = CORE
    from core_serve import Handle
    imo.Program = core_serve.ServeProgram                # the suites build their programs with imo.Program()
    PymoEnv = Env
    Env = core_serve.ServeEnv
    _to_pair, _to_list, _to_bool, _stream_nth = to_pair, to_list, to_bool, stream_nth
    def to_pair(v): return v.srv.pair(v) if isinstance(v, Handle) else _to_pair(v)
    def to_list(v): return v.srv.digits(v) if isinstance(v, Handle) else _to_list(v)
    def to_bool(v): return v.srv.boolean(v) if isinstance(v, Handle) else _to_bool(v)
    def stream_nth(v, n): return v.srv.nth(v, n) if isinstance(v, Handle) else _stream_nth(v, n)
    print(f"core: {CORE.capitalize()}", flush=True)

def tri(v):
    """a truth value: True, False, or None when it is neither (the undetermined ⍰)"""
    if CORE != 'pymo': return v.srv.tri(v)
    r = v(done('T'))(done('F'))
    return True if r == 'T' else False if r == 'F' else None

def cli():
    """the command line of the core under test, to be followed by run / check / translate ... and files"""
    if CORE != 'pymo':
        return [core_serve.find_exe()]
    return [sys.executable, os.path.join(ROOT, 'pymo', 'i1.py')]

def run_main(P, mode=None, n=None, write=None):
    """what `run` prints for the program P (output.run_main on Pymo, haskimo run / rustimo run on the others); returns the notation used when it knows"""
    if CORE != 'pymo':
        text = P.run_main(mode, n)
        (write or sys.stdout.write)(text)
        return mode
    import output
    return output.run_main(P, mode, n, write=write)

def load_env(files=(), **kw):
    files = [os.path.join(ROOT, f) if not os.path.isabs(f) else f for f in files]
    if CORE != 'pymo':                                   # the prelude is inside the executable
        P = imo.Program()
        for f in files: P.add_file(f)
        P.check(); P.build()
        return Env(P)
    return Env(imo.load(files, **kw))

class Report:
    def __init__(self): self.results = []; self.t0 = time.time()
    def __call__(self, label, ok, extra=''):
        self.results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {label} {extra}".rstrip() + ' '); sys.stdout.flush()
    def done(self):
        print(f"\n{sum(self.results)}/{len(self.results)} passed  ({time.time()-self.t0:.1f}s)")
        return all(self.results)

def sgn(x): return (x > 0) - (x < 0)
