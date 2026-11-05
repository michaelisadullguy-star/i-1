"""
run.py -- the conformance suite: the core-neutral test of the i-1 language.

i-1 has three parallel cores, three interpreters of one specification: Pymo (Python, pymo/, run as  python3 pymo/i1.py ...), Haskimo
(Haskell, haskimo/, the executable  haskimo) and Rustimo (Rust, rustimo/, the executable  rustimo).  None is the reference.  This runner
executes the SAME command lines on any of them and compares what they print with the expected output stored in
tests/conformance/expected.json, byte for byte (standard output and exit status).  The expected outputs are the bytes on which ALL the
cores agree: --bless runs them all and records a case only if they print the same; the cases on which they differ are listed, and a
person decides from the documentation which core is wrong (with three cores, usually the one that disagrees with the other two).

  python3 tests/conformance/run.py                       every core that is built, every case
  python3 tests/conformance/run.py --impl haskimo        only Haskimo (Python is needed only to run this script)
  python3 tests/conformance/run.py --impl pymo,rustimo --fast   two cores, without the slow cases   (py, hs and rs are short forms; both = pymo,haskimo)
  python3 tests/conformance/run.py --filter prove -v     the cases whose id contains "prove", with the details of a failure
  python3 tests/conformance/run.py --bless [--filter X]  record the output of the selected cases where all the cores agree
  python3 tests/conformance/run.py --bless-from pymo     record from ONE core, for a change that only that core has so far (the others
                                                         then fail until they follow)
  python3 tests/conformance/run.py --list                list the cases

Cases (tests/conformance/cases.txt, one per line):   ID <TAB> FLAGS <TAB> ARGUMENTS
  ID         a name, unique;  FLAGS  "-" or comma-separated:  slow  (skipped by --fast);
  ARGUMENTS  the command line after the executable, relative to the repository root (run, check, translate, eval, text, ...).
The programs the cases use are the examples of examples/ and the programs under tests/conformance/programs/.

The Haskimo executable is looked for in  --haskimo PATH,  $I1_HASKIMO,  build/haskimo,  dist/haskimo;  the Rustimo executable in  --rustimo PATH,
$I1_RUSTIMO,  build/rustimo,  dist/rustimo.   Exit status 0 when every selected case conforms.
"""
import argparse, concurrent.futures as cf, difflib, json, os, shlex, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))              # tests/conformance
ROOT = os.path.dirname(os.path.dirname(HERE))
CONF = HERE
CASES = os.path.join(CONF, 'cases.txt')
EXPECTED = os.path.join(CONF, 'expected.json')
LABEL = {'pymo': 'Pymo', 'haskimo': 'Haskimo', 'rustimo': 'Rustimo', 'compimo': 'Compimo', 'cimo': 'Cimo', 'ocamimo': 'OCamimo', 'rimo': 'Rimo', 'lispimo': 'Lispimo', 'schimo': 'Schimo'}
EXTRA = ('compimo', 'cimo', 'ocamimo', 'rimo', 'lispimo', 'schimo')      # further cores: run when they are named (--impl compimo), never part of 'all'


EXPDIR = os.path.join(CONF, 'expected')


def export_expected(expected):
    """the recorded outputs as plain files, for run.sh (no Python): expected/ID.out holds the standard output, expected/ID.rc the exit status when it is not 0"""
    os.makedirs(EXPDIR, exist_ok=True)
    keep = set()
    for cid, e in expected.items():
        out = os.path.join(EXPDIR, cid + '.out'); keep.add(cid + '.out')
        with open(out, 'w', encoding='utf-8', newline='') as f: f.write(e['out'])
        rc = os.path.join(EXPDIR, cid + '.rc')
        if e['rc'] != 0:
            keep.add(cid + '.rc')
            with open(rc, 'w', encoding='utf-8') as f: f.write(str(e['rc']) + '\n')
        elif os.path.exists(rc): os.remove(rc)
    for fn in os.listdir(EXPDIR):
        if fn not in keep: os.remove(os.path.join(EXPDIR, fn))


def load_cases():
    cases = []
    for ln in open(CASES, encoding='utf-8').read().split('\n'):
        if not ln.strip() or ln.lstrip().startswith('#'): continue
        parts = ln.split('\t')
        assert len(parts) == 3, f"cases.txt: bad line {ln!r}"
        cid, flags, args = parts
        cases.append((cid.strip(), set(f for f in flags.strip().split(',') if f and f != '-'), shlex.split(args)))
    ids = [c[0] for c in cases]
    assert len(ids) == len(set(ids)), "cases.txt: duplicate ids"
    return cases


def find_haskimo(arg):
    for c in (arg, os.environ.get('I1_HASKIMO'), os.environ.get('I1_HS'), os.path.join(ROOT, 'build', 'haskimo'), os.path.join(ROOT, 'dist', 'haskimo')):
        if c and os.path.isfile(c) and os.access(c, os.X_OK): return os.path.abspath(c)
    return None


def find_rustimo(arg):
    for c in (arg, os.environ.get('I1_RUSTIMO'), os.environ.get('I1_RS'), os.path.join(ROOT, 'build', 'rustimo'), os.path.join(ROOT, 'dist', 'rustimo')):
        if c and os.path.isfile(c) and os.access(c, os.X_OK): return os.path.abspath(c)
    return None


def find_extra(name):
    for c in (os.environ.get('I1_' + name.upper()), os.path.join(ROOT, 'build', name), os.path.join(ROOT, 'dist', name)):
        if c and os.path.isfile(c) and os.access(c, os.X_OK): return os.path.abspath(c)
    return None


def command(impl, exes, args):
    if impl == 'pymo': return [sys.executable, os.path.join(ROOT, 'pymo', 'i1.py')] + args
    return [exes[impl]] + args


def run_case(impl, exes, args, timeout):
    t = time.time()
    try:
        p = subprocess.run(command(impl, exes, args), cwd=ROOT, capture_output=True, timeout=timeout)
        return dict(rc=p.returncode, out=p.stdout.decode('utf-8', 'replace'), err=p.stderr.decode('utf-8', 'replace'), secs=time.time() - t)
    except subprocess.TimeoutExpired:
        return dict(rc=-9, out='', err='timeout', secs=time.time() - t)


def explain(want, got):
    if want['rc'] != got['rc']: return f"exit status {got['rc']}, expected {want['rc']}" + (f"  (stderr: {got['err'].strip()[-200:]})" if got['err'].strip() else '')
    a, b = want['out'].split('\n'), got['out'].split('\n')
    d = [x for x in difflib.unified_diff(a, b, 'expected', 'got', lineterm='', n=1)]
    return 'output differs:\n    ' + '\n    '.join(x[:200] for x in d[:12])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--impl', default='all', help='pymo, haskimo, rustimo (py, hs, rs), a comma-separated list of them, both (= pymo,haskimo) or all (default)')
    ap.add_argument('--haskimo', '--hs', dest='hs', help='path of the Haskimo executable')
    ap.add_argument('--rustimo', '--rs', dest='rs', help='path of the Rustimo executable')
    ap.add_argument('--bless', action='store_true', help='record the expected output of the selected cases: the cores are run, and a case is recorded only if they all agree')
    ap.add_argument('--bless-from', choices=['pymo', 'haskimo', 'rustimo'], help='record the expected output from one core only')
    ap.add_argument('--filter', action='append', default=[], help='only the cases whose id contains this text (repeatable)')
    ap.add_argument('--missing', action='store_true', help='only the cases that have no recorded output yet (with --bless: record just those)')
    ap.add_argument('--fast', action='store_true', help='skip the slow cases')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--export', action='store_true', help='write the recorded outputs as plain files (expected/ID.out) for run.sh and exit')
    ap.add_argument('-j', type=int, default=max(1, (os.cpu_count() or 2)), help='parallel jobs')
    ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('-v', action='store_true', help='show the details of failures')
    a = ap.parse_args()
    if a.export:
        export_expected(json.load(open(EXPECTED, encoding='utf-8'))); print('exported', len(os.listdir(EXPDIR)), 'files to', os.path.relpath(EXPDIR, ROOT)); return 0

    cases = load_cases()
    if a.filter: cases = [c for c in cases if any(f in c[0] for f in a.filter)]
    if a.fast: cases = [c for c in cases if 'slow' not in c[1]]
    if a.list:
        for cid, flags, args in cases: print(f"{cid}\t{','.join(sorted(flags)) or '-'}\t{' '.join(args)}")
        return 0
    expected = json.load(open(EXPECTED, encoding='utf-8')) if os.path.exists(EXPECTED) else {}
    if a.missing: cases = [c for c in cases if c[0] not in expected]

    exes = {'haskimo': find_haskimo(a.hs), 'rustimo': find_rustimo(a.rs)}
    for x in EXTRA: exes[x] = find_extra(x)
    short = {'py': 'pymo', 'hs': 'haskimo', 'rs': 'rustimo'}
    if a.impl == 'all': wanted = ['pymo', 'haskimo', 'rustimo']
    elif a.impl == 'both': wanted = ['pymo', 'haskimo']
    else: wanted = [short.get(x.strip(), x.strip()) for x in a.impl.split(',')]
    for w in wanted:
        if w not in ('pymo', 'haskimo', 'rustimo') + EXTRA:
            print(f"conformance: unknown core {w!r} (pymo, haskimo, rustimo, {', '.join(EXTRA)})", file=sys.stderr); return 2
    blessing = a.bless or a.bless_from
    impls = [a.bless_from] if a.bless_from else wanted
    missing = [i for i in impls if i != 'pymo' and exes[i] is None]
    if missing and a.impl == 'all' and not a.bless_from:      # the default: run the cores that are built, say which are not
        for i in missing: print(f"conformance: {i} was not found (build it: make {i}); it is skipped", file=sys.stderr)
        impls = [i for i in impls if i not in missing]
    elif missing:
        for i in missing:
            how = {'haskimo': 'make haskimo or ./haskimo/build.sh; or give --haskimo PATH / $I1_HASKIMO', 'rustimo': 'make rustimo or ./rustimo/build.sh; or give --rustimo PATH / $I1_RUSTIMO'}.get(i, f'its build script; or give $I1_{i.upper()}')
            print(f"conformance: the {i} executable was not found (build it with {how})", file=sys.stderr)
        return 2
    jobs = [(impl, cid, args) for cid, flags, args in cases for impl in impls]
    t0 = time.time()
    results = {}
    with cf.ThreadPoolExecutor(a.j) as ex:
        futs = {ex.submit(run_case, impl, exes, args, a.timeout): (impl, cid) for impl, cid, args in jobs}
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()
            if blessing: print(f"ran {futs[f][1]} on {futs[f][0]}", file=sys.stderr)

    if blessing:
        disagree = []
        for cid, flags, args in cases:
            rs = [results[(impl, cid)] for impl in impls]
            if all((r['rc'], r['out']) == (rs[0]['rc'], rs[0]['out']) for r in rs):
                expected[cid] = dict(rc=rs[0]['rc'], out=rs[0]['out'])
            else:
                disagree.append((cid, rs))
        ids = {c[0] for c in load_cases()}
        expected = {k: expected[k] for k in sorted(expected) if k in ids}
        with open(EXPECTED, 'w', encoding='utf-8') as f:
            json.dump(expected, f, ensure_ascii=False, indent=1, sort_keys=True); f.write('\n')
        export_expected(expected)
        print(f"recorded {len(cases) - len(disagree)} of {len(cases)} cases in {os.path.relpath(EXPECTED, ROOT)}"
              + (f" (from {impls[0]} alone)" if len(impls) == 1 else f" ({', '.join(LABEL[i] for i in impls)} agree on them)"))
        for cid, rs in disagree:
            print(f"DISAGREE  {cid}" + (f"\n    {explain(dict(rc=rs[0]['rc'], out=rs[0]['out']), rs[1])}" if a.v else ''))
        if disagree: print(f"{len(disagree)} cases not recorded: the cores print different bytes (-v shows how); decide from the documentation which one is wrong")
        return 1 if disagree else 0

    bad = 0
    per = {i: [0, 0, 0.0] for i in impls}
    for cid, flags, args in cases:
        want = expected.get(cid)
        for impl in impls:
            r = results[(impl, cid)]
            per[impl][0] += 1; per[impl][2] += r['secs']
            if want is None: ok, why = False, 'no expected output (run --bless)'
            else:
                ok = want['rc'] == r['rc'] and want['out'] == r['out']
                why = '' if ok else explain(want, r)
            if ok: per[impl][1] += 1
            else:
                bad += 1
                print(f"FAIL  {impl}  {cid}" + (f"\n    {why}" if a.v or want is None else ''))
    for impl in impls:
        n, ok, secs = per[impl]
        print(f"{LABEL[impl]:<8}: {ok}/{n} cases conform  (cpu time {secs:.0f} s)")
    print(f"{'ALL CONFORM' if not bad else str(bad) + ' FAILURES'}  ({time.time() - t0:.0f} s wall)")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
