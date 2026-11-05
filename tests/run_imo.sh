#!/bin/sh
# run_imo.sh -- run the self-checking .imo tests of tests/imo directly on the interpreters and the compiler.  No Python.
#
#   tests/run_imo.sh [--impl NAME[,NAME...]] [--set full|small] [--filter TEXT] [-j N] [--timeout SECONDS]
#
# Each file of tests/imo/full (about 9800 checks) and tests/imo/small (a sample of about 3700, for Pymo, which is two orders of magnitude slower) is a program in the
# human notation that checks itself: `i1 --impl NAME run FILE` must print  PASS n  (and nothing else); a failure prints  FAIL  and the labels of the failed checks.
# The expected values in the files were computed by independent Python oracles (tests/test_*.py, which generate the files with LANGTEST_EMIT=DIR); this runner needs none of that.
# Default: every core, the full set for all of them but pymo (the small one).  The exit status is 0 when every file passes on every core named.
here=$(cd "$(dirname "$0")" && pwd -P); root=$(dirname "$here")
impls=; set_=; filter=; jobs=$(nproc 2>/dev/null || echo 2); tmo=${TIMEOUT:-3600}
while [ $# -gt 0 ]; do case $1 in
  --impl) impls=$2; shift 2 ;; --set) set_=$2; shift 2 ;; --filter) filter=$2; shift 2 ;; -j) jobs=$2; shift 2 ;; --timeout) tmo=$2; shift 2 ;;
  *) echo "run_imo.sh: unknown option $1" >&2; exit 2 ;; esac; done
[ -n "$impls" ] || impls=pymo,haskimo,rustimo,compimo,ocamimo,schimo,cimo
one() {   # one FILE IMPL
  f=$1; impl=$2; t0=$(date +%s)
  out=$(timeout "$tmo" "$root/i1" --impl "$impl" run "$f" 2>&1); rc=$?
  name=$(basename "$f")
  case $out in
    PASS*) echo "ok $name ${out#PASS } $(( $(date +%s) - t0 ))s" ;;
    *) echo "FAIL $name (exit $rc): $(printf '%s' "$out" | head -c 300)" ;;
  esac
}
if [ "$1" = "--one" ]; then :; fi
status=0
for impl in $(echo "$impls" | tr ',' ' '); do
  s=$set_; [ -n "$s" ] || { [ "$impl" = pymo ] && s=small || s=full; }
  files=$(ls "$here/imo/$s"/*.hum.imo 2>/dev/null | grep -F -- "$filter")
  res=$(mktemp "${TMPDIR:-/tmp}/imo.XXXXXX"); t0=$(date +%s)
  export root impl tmo
  printf '%s\n' $files | xargs -P "$jobs" -I{} sh -c 'f=$1; t0=$(date +%s); out=$(timeout "$tmo" "$root/i1" --impl "$impl" run "$f" 2>&1); rc=$?; n=$(basename "$f"); case $out in PASS*) echo "ok $n ${out#PASS } $(( $(date +%s) - t0 ))s";; *) echo "FAIL $n (exit $rc): $(printf "%s" "$out" | head -c 300)";; esac' _ {} >"$res"
  nf=$(printf '%s\n' $files | grep -c .); ok=$(grep -c '^ok ' "$res"); checks=$(grep '^ok ' "$res" | awk '{s += $3} END {print s + 0}')
  grep '^FAIL' "$res" | head -${SHOW:-20}
  echo "$impl: $ok/$nf files pass, $checks checks ($s set, $(( $(date +%s) - t0 )) s)"
  [ "$ok" = "$nf" ] || status=1
  rm -f "$res"
done
exit $status
