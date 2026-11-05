#!/bin/sh
# run_case.sh 'IMPL<TAB>ID<TAB>ARGS' -- one conformance case on one core: the standard output and the exit status must be those recorded in expected/ID.out and ID.rc.
# Prints  ok ID  or  FAIL ID  and the first lines of the difference.  No Python.
here=$(cd "$(dirname "$0")" && pwd -P); root=$(dirname "$(dirname "$here")")
TAB=$(printf '\t'); IFS=$TAB read -r impl id args <<EOT
$1
EOT
IFS=' 	
'
cd "$root" || exit 2
tmp=$(mktemp "${TMPDIR:-/tmp}/conf.XXXXXX") || exit 2
eval "set -- $args"
timeout "${CASE_TIMEOUT:-1800}" "$root/i1" --impl "$impl" "$@" >"$tmp" 2>/dev/null
rc=$?
want=0; [ -f "$here/expected/$id.rc" ] && want=$(cat "$here/expected/$id.rc")
if [ "$rc" = "$want" ] && cmp -s "$tmp" "$here/expected/$id.out"; then echo "ok $id"; else
  echo "FAIL $id (exit $rc, want $want)"; diff "$here/expected/$id.out" "$tmp" 2>&1 | head -4 | cut -c1-200 | sed 's/^/    /'
fi
rm -f "$tmp"
