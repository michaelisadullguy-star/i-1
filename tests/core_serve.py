"""core_serve.py -- Haskimo and Rustimo as cores of the shared test suite.

The library suites (test_poly.py, test_numtheory.py, ...) were written against the Python API of Pymo: build a Program, add the prelude and a
test program, check and build it, take the value of a symbol, decode it (Env.dq, Env.lst, Env.b, ...).  This module offers the same
names over  haskimo serve  (haskimo/src/I1/Serve.hs) and  rustimo serve  (rustimo/src/serve.rs), which speak one protocol, so that the
suites run on either as they run on Pymo:

    python3 tests/test_poly.py --core haskimo            (or  I1_CORE=rustimo python3 tests/test_poly.py)

harness.py puts ServeProgram in the place of imo.Program and ServeEnv in the place of Env when the core is not Pymo, and sets CORE_NAME.
A value is a handle (class Handle) that names a value inside the interpreter's process; only digit strings, truth values and the shape of
lists and pairs cross the pipe.  Nothing here evaluates anything: every decision about a value is made by the interpreter's evaluator.
"""
import atexit, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'pymo'))
from base_b import val, to_digits                      # the isomorphism digit string <-> Gaussian integer, used on the host side only


CORE_NAME = 'haskimo'                                        # set by harness.py: 'haskimo' or 'rustimo'


def find_exe(core=None):
    core = core or CORE_NAME
    env = {'haskimo': 'I1_HASKIMO', 'rustimo': 'I1_RUSTIMO', 'compimo': 'I1_COMPIMO', 'ocamimo': 'I1_OCAMIMO', 'schimo': 'I1_SCHIMO', 'cimo': 'I1_CIMO', 'rimo': 'I1_RIMO'}[core]
    for c in (os.environ.get(env), os.path.join(ROOT, 'build', core), os.path.join(ROOT, 'dist', core)):
        if c and os.path.isfile(c) and os.access(c, os.X_OK): return os.path.abspath(c)
    raise SystemExit(f"the {core.capitalize()} executable was not found: build it with  make {core}  (or set ${env})")


class ServeError(RuntimeError):
    """an error that the interpreter reports about a request (an evaluation error, a name that is not defined, ...)"""


class Handle:
    """a value that lives inside an interpreter process"""
    __slots__ = ('srv', 'id', 'gen')
    def __init__(self, srv, id): self.srv, self.id, self.gen = srv, id, srv.gen
    def __repr__(self): return f"<value {self.id}>"


class Server:
    """one serve process for one program.  After a fork (test_complex.py's workers) the child starts a process of its own:
    the values of the parent live in the parent's process, and a handle made before the fork is stale in the child."""
    def __init__(self, files):
        self.files, self.gen = files, 0
        self._spawn()
        atexit.register(self.close)

    def _spawn(self):
        self.pid = os.getpid()
        self.proc = subprocess.Popen([find_exe(), 'serve'] + self.files, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        first = self.readline()
        self.errors = []
        if first.startswith('ERRORS'):
            for _ in range(int(first.split()[1])):
                f, w, m = self.readline().split('\t', 2)
                self.errors.append((f, w, m))
        elif first != 'OK':
            raise ServeError(f"{CORE_NAME} serve: unexpected first line {first!r}")

    def readline(self):
        line = self.proc.stdout.readline()
        if not line: raise ServeError(f"{CORE_NAME} serve stopped (see its message above)")
        return line.decode('utf-8').rstrip('\n')

    def ask(self, *words):
        if os.getpid() != self.pid:                              # we are a forked child: do not share the parent's pipe
            self.gen += 1
            self._spawn()
        self.proc.stdin.write((' '.join(str(w) for w in words) + '\n').encode('utf-8'))
        self.proc.stdin.flush()
        r = self.readline()
        if r.startswith('ERR '): raise ServeError(r[4:])
        return r

    def close(self):
        if os.getpid() != self.pid: return                       # the process belongs to the parent
        try:
            if self.proc.poll() is None:
                self.proc.stdin.write(b'QUIT\n'); self.proc.stdin.flush(); self.proc.stdin.close()
                self.proc.wait(timeout=5)
        except Exception:
            try: self.proc.kill()
            except Exception: pass

    # -- values
    def check(self, *hs):
        for h in hs:
            if h.gen != self.gen: raise ServeError("a value made before the fork was used after it")
    def handle(self, r): return Handle(self, int(r.split()[1]))
    def value(self, spec_name): return self.handle(self.ask('V', spec_name))
    def apply(self, f, *args): self.check(f, *args); return self.handle(self.ask('APPLY', f.id, *[a.id for a in args]))
    def mk(self, digits): return self.handle(self.ask('MK', ''.join('1' if d else '0' for d in digits)))
    # -- decoders
    def pair(self, v):
        self.check(v)
        _, a, b = self.ask('PAIR', v.id).split()
        return Handle(self, int(a)), Handle(self, int(b))
    def digits(self, v):
        self.check(v)
        return [int(c) for c in self.ask('DIGITS', v.id)[2:]]
    def pair_digits(self, v):
        self.check(v)
        z, d = self.ask('Q', v.id)[2:].split('|')
        return [int(c) for c in z], [int(c) for c in d]
    def boolean(self, v):
        self.check(v)
        return self.ask('BOOL', v.id).split()[1] == '1'
    def tri(self, v):
        self.check(v)
        return {'1': True, '0': False}.get(self.ask('BOOL', v.id).split()[1])
    def cells(self, v):
        self.check(v)
        r = self.ask('LIST', v.id).split()
        return [Handle(self, int(x)) for x in r[2:]]
    def nth(self, v, n):
        self.check(v)
        return self.handle(self.ask('NTH', v.id, n))
    def ordering(self, v):
        self.check(v)
        return int(self.ask('ORD', v.id).split()[1])


class _Hum:
    def __init__(self, P): self.P = P
    def spec_name(self, name): return self.P.srv.ask('NAME', name)[2:]


class _Sigs:
    def __init__(self, P): self.P = P
    def __getitem__(self, name):
        def tup(j): return ('V', j[1]) if j[0] == 'V' else ('F', j[1]) if j[0] == 'F' else ('K', j[1], tuple(tup(a) for a in j[2]))
        return [tup(json.loads(self.P.srv.ask('CLASS', name)[2:]))]
    def __contains__(self, name):
        try: self[name]; return True
        except ServeError: return False


class _Checker:
    def __init__(self, P): self.sigs = _Sigs(P)
    def norm(self, c): return c                        # the classes that the server sends are normalised


class ServeProgram:
    """the part of imo.Program that the suites use, over the serve protocol"""
    def __init__(self):
        self.files, self.srv, self.errors = [], None, None
        self.dir = tempfile.mkdtemp(prefix='i1-haskimo.')
        atexit.register(shutil.rmtree, self.dir, True)
        self.hum, self.checker = _Hum(self), _Checker(self)
        import imo
        self._prelude = {os.path.abspath(f) for f in imo.PRELUDE}

    def add_file(self, path, trusted=False):
        if trusted and os.path.abspath(path) in self._prelude: return              # the prelude is inside the executable
        self.files.append(os.path.abspath(path))

    def add_text(self, text, name='<text>', trusted=False, notation='spec'):
        ext = {'spec': '.imo', 'hum': '.hum.imo', 'bin': '.bin.imo'}[notation]
        stem = os.path.basename(name) if name and not name.startswith('<') else 'text'
        for e in ('.hum.imo', '.bin.imo', '.spec.imo', '.imo'):
            if stem.endswith(e): stem = stem[:-len(e)]; break
        d = os.path.join(self.dir, f'{len(self.files):03d}'); os.makedirs(d)
        path = os.path.join(d, stem + ext)
        with open(path, 'w', encoding='utf-8') as f: f.write(text)
        self.files.append(path)

    def check(self, collect=False):
        self.close()
        self.srv = Server(self.files)
        self.errors = self.srv.errors
        if self.errors and not collect:
            f, w, m = self.errors[0]
            raise RuntimeError(f"{os.path.basename(f)}: {w}: {m}")
        return self.errors

    def build(self):
        if self.srv is None: self.check(collect=True)
        if self.errors: raise RuntimeError(f"the program has class errors: {self.errors[:2]}")
        return self

    def val(self, name): return self.srv.value(name)

    def spec_text(self):
        """the program re-spelled in spec notation (what `translate --to spec` prints: the program, not the prelude)"""
        return subprocess.run([find_exe(), 'translate'] + self.files + ['--to', 'spec'], cwd=ROOT, capture_output=True).stdout.decode('utf-8')

    @property
    def doc1(self):
        """doc 1 is a data file shared by both cores: read it from there"""
        class Doc1: pass
        d = Doc1(); d.s2b = {}
        for ln in open(os.path.join(ROOT, 'docs', 'doc1.sbl'), encoding='utf-8').read().split('\n'):
            if ' := ' in ln and not ln.lstrip().startswith('⍝'):
                a, b = [x.strip() for x in ln.split(' := ')]; d.s2b[a] = b
        return d

    def close(self):
        if self.srv is not None: self.srv.close(); self.srv = None

    def run_main(self, mode=None, n=None):
        """the output of  run  on the program (what output.run_main writes)"""
        args = [find_exe(), 'run'] + self.files + (['--out', mode] if mode else []) + (['--n', str(n)] if n is not None else [])
        return subprocess.run(args, cwd=ROOT, capture_output=True).stdout.decode('utf-8')


class ServeEnv:
    """imo-side helpers of harness.Env over handles:  E.V(name), E.dq(v), E.lst(v), E.b(v), ..."""
    def __init__(self, P): self.P = P; self.S = P.srv
    def V(self, name): return self.S.value(name)
    def call(self, f, *a):
        f = self.V(f) if isinstance(f, str) else f
        return self.S.apply(f, *a)
    def z(self, z):
        if isinstance(z, int): z = (z, 0)
        return self.S.mk(to_digits(z))
    def raw(self, digs): return self.S.mk(digs)
    def q(self, x, den=None):
        from fractions import Fraction as Fr
        from math import lcm
        import refmath as R
        if den is not None: return self.call('⊗', self.z(x), self.z(den))
        if not isinstance(x, R.Q): x = R.Q(x)
        D = lcm(x.r.denominator, x.i.denominator)
        return self.call('⊗', self.z((int(x.r * D), int(x.i * D))), self.z((D, 0)))
    def dz(self, v): return val(self.S.digits(v))
    def digits(self, v): return self.S.digits(v)
    def dq(self, v):
        import refmath as R
        zd, dd = self.S.pair_digits(v)
        P_, D_ = val(zd), val(dd)
        assert D_ != (0, 0), "denominator 0"
        return R.Q(P_[0], P_[1]) * R.Q(D_[0], D_[1]).inv()
    def pair_digits(self, v): return self.S.pair_digits(v)
    def b(self, v): return self.S.boolean(v)
    def ord3(self, v): return (-1, 0, 1)[self.S.ordering(v)]
    def lst(self, v, dec=None):
        hs = self.S.cells(v)
        return [dec(h) for h in hs] if dec else hs
    def nth(self, v, n): return self.S.nth(v, n)
