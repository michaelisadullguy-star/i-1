#!/bin/sh
# run.sh -- the conformance cases on the interpreters and the compiler, with no Python.
#   tests/conformance/run.sh [--impl NAME[,NAME...]] [--filter TEXT] [--fast | --slow] [--sample-lib N] [-j N]
# Every case of cases.txt (a command line of i1, relative to the repository root) is run, and its standard output and exit status are compared with
# expected/ID.out and ID.rc (recorded where the cores agreed; python3 tests/conformance/run.py --bless writes them).  --fast skips the slow cases, --slow runs only them, --sample-lib N runs one of every N cases of the library sweep (lib.*; the others all): for the slow cores.
here=$(cd "$(dirname "$0")" && pwd -P); root=$(dirname "$(dirname "$here")")
impls=; filter=; fast=no; samplelib=1; jobs=$(nproc 2>/dev/null || echo 2)
while [ $# -gt 0 ]; do case $1 in
  --impl) impls=$2; shift 2 ;; --filter) filter=$2; shift 2 ;; --fast) fast=yes; shift ;; --slow) fast=only; shift ;; --sample-lib) samplelib=$2; shift 2 ;; -j) jobs=$2; shift 2 ;;
  *) echo "run.sh: unknown option $1" >&2; exit 2 ;; esac; done
[ -n "$impls" ] || impls=pymo,haskimo,rustimo,compimo,ocamimo,schimo,cimo
list=$(mktemp "${TMPDIR:-/tmp}/cases.XXXXXX"); res=$(mktemp "${TMPDIR:-/tmp}/res.XXXXXX")
grep -v '^#' "$here/cases.txt" | awk -F'\t' -v f="$filter" -v fast="$fast" -v n="$samplelib" 'NF == 3 && (f == "" || index($1, f) > 0) && !(fast == "yes" && $2 ~ /slow/) && !(fast == "only" && $2 !~ /slow/) { if (index($1, "lib.") == 1 && n > 1 && (++k % n) != 0) next; print $1 "\t" $3 }' >"$list"
total=$(wc -l <"$list"); status=0
for impl in $(echo "$impls" | tr ',' ' '); do
  t0=$(date +%s)
  awk -F'\t' -v impl="$impl" '{ print impl "\t" $1 "\t" $2 }' "$list" | tr '\n' '\0' | xargs -0 -n1 -P "$jobs" "$here/run_case.sh" >"$res" 2>&1
  bad=$(grep -c '^FAIL' "$res"); good=$(grep -c '^ok' "$res")
  grep -A4 '^FAIL' "$res" | head -${SHOW:-40}
  echo "$impl: $good/$total cases conform ($(( $(date +%s) - t0 )) s)"
  [ "$bad" = 0 ] && [ "$good" = "$total" ] || status=1
done
rm -f "$list" "$res"
exit $status
