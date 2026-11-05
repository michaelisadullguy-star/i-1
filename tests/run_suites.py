"""run_suites.py -- run the test suites on the cores that they support.

The test suite is shared by the three cores of i-1 (README §2.1, §16.3).  Nineteen of the twenty-three suites use only the program-and-value API
of tests/harness.py and run on Pymo, Haskimo and Rustimo alike (`--core pymo`, `--core haskimo`, `--core rustimo`); four test the Python API
of Pymo itself (its readers, its printer, its quoting) and run on Pymo only — what they check has command-line counterparts in
tests/conformance, which runs on all the cores.

  python3 tests/run_suites.py                    every suite on every core it supports and that is built (a few minutes with Rustimo or
                                                 Haskimo, about 15 more with Pymo)
  python3 tests/run_suites.py --core rustimo     only Rustimo        (pymo, haskimo, rustimo, or all)
  python3 tests/run_suites.py --only poly,codec  only these suites
  python3 tests/run_suites.py --logs             also write tests/logs/<suite>.txt (Pymo), <suite>.haskimo.txt and <suite>.rustimo.txt
Exit status 0 when every run passed.
"""
import argparse, concurrent.futures as cf, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BOTH, PYMO = ('pymo', 'haskimo', 'rustimo'), ('pymo',)
SUITES = [   # (suite, cores) — heavy ones first
    ('complex', BOTH), ('linalg', BOTH), ('galois', BOTH), ('numtheory', BOTH), ('predicates', PYMO), ('solve', BOTH), ('output', PYMO),
    ('field', BOTH), ('ring', BOTH), ('prove', BOTH), ('codec', BOTH), ('poly', BOTH), ('algebra', BOTH), ('group', BOTH), ('axioms', BOTH),
    ('layers', PYMO), ('library', BOTH), ('classes', BOTH), ('lists', BOTH), ('strings', BOTH), ('dict', BOTH), ('calendar', BOTH), ('graph', BOTH), ('stats', BOTH), ('geom', BOTH), ('regex', BOTH), ('encode', BOTH), ('prng', BOTH), ('combin', BOTH), ('theory', BOTH), ('readme', PYMO)]
LABEL = {'pymo': 'Pymo', 'haskimo': 'Haskimo', 'rustimo': 'Rustimo'}


def run(suite, core, timeout):
    t = time.time()
    cmd = [sys.executable, os.path.join(HERE, f'test_{suite}.py')] + (['--core', core] if core != 'pymo' else [])
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
        out, rc = p.stdout.decode('utf-8', 'replace') + p.stderr.decode('utf-8', 'replace'), p.returncode
    except subprocess.TimeoutExpired:
        out, rc = 'timeout', -9
    m = re.search(r'(\d+)/(\d+) passed\s+\(([\d.]+)s\)', out)
    return dict(suite=suite, core=core, out=out, rc=rc, secs=time.time() - t, passed=int(m.group(1)) if m else 0, total=int(m.group(2)) if m else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--core', choices=['pymo', 'haskimo', 'rustimo', 'all', 'both'], default='all', help='both = all (kept from the time of two cores)')
    ap.add_argument('--only', help='comma-separated suites')
    ap.add_argument('--jobs', '-j', type=int, default=4)
    ap.add_argument('--timeout', type=int, default=7200)
    ap.add_argument('--logs', action='store_true', help='write the output of every run to tests/logs/')
    a = ap.parse_args()
    only = set(a.only.split(',')) if a.only else None
    built = {'pymo': True, 'haskimo': os.path.exists(os.path.join(ROOT, 'build', 'haskimo')), 'rustimo': os.path.exists(os.path.join(ROOT, 'build', 'rustimo'))}
    if a.core in ('all', 'both'):
        for c in ('haskimo', 'rustimo'):
            if not built[c]: print(f"run_suites: {c} was not found (make {c}); it is skipped", file=sys.stderr)
    jobs = [(s, c) for s, cores in SUITES for c in cores if (only is None or s in only) and (a.core in ('all', 'both') and built[c] or a.core == c)]
    if not jobs: sys.exit("no suite selected")
    os.makedirs(os.path.join(HERE, 'logs'), exist_ok=True)
    results = []
    t0 = time.time()
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for r in ex.map(lambda sc: run(sc[0], sc[1], a.timeout), jobs):
            ok = r['rc'] == 0 and r['total'] > 0 and r['passed'] == r['total']
            r['ok'] = ok
            results.append(r)
            print(f"{'PASS' if ok else 'FAIL'}  {r['suite']:<11}{LABEL[r['core']]:<9} {r['passed']}/{r['total']}  ({r['secs']:.0f} s)", flush=True)
            if not ok: print('      ' + '\n      '.join(r['out'].strip().split('\n')[-6:]), flush=True)
            if a.logs:
                name = f"{r['suite']}.txt" if r['core'] == 'pymo' else f"{r['suite']}.{r['core']}.txt"
                with open(os.path.join(HERE, 'logs', name), 'w', encoding='utf-8') as f: f.write(r['out'])
    bad = [r for r in results if not r['ok']]
    print(f"\n{len(results) - len(bad)}/{len(results)} runs passed  ({time.time() - t0:.0f} s wall)")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
