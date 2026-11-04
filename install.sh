#!/bin/sh
# install.sh -- install the i-1 language: Pymo (the Python interpreter), Haskimo (the Haskell interpreter), Rustimo (the Rust
# interpreter), or any of them.
#
#   ./install.sh [--prefix DIR] [--all | --pymo-only | --haskimo-only | --rustimo-only] [--default pymo|haskimo|rustimo|auto]
#                [--link] [--cabal] [--uninstall]
#
#   --prefix DIR     where to install (default: $PREFIX, else ~/.local):   DIR/bin/{i1,pymo,haskimo,rustimo}   DIR/share/i1/
#   --all            (default) every interpreter whose compiler is found: Pymo (python3), Haskimo (ghc), Rustimo (cargo); the others
#                    get a notice, not an error (--both is the same)
#   --pymo-only      only Pymo (needs python3; --python-only is the same)
#   --haskimo-only   only Haskimo (needs GHC >= 9.0 with its boot libraries: base containers mtl template-haskell directory); the
#                    executable is self-contained, Python is not needed to run it (--haskell-only is the same)
#   --rustimo-only   only Rustimo (needs cargo and rustc >= 1.70; no crates are downloaded); the executable is self-contained too
#                    (--rust-only is the same)
#   --default X      the interpreter that  i1  uses when neither --impl nor $I1_IMPL says otherwise:
#                    pymo, haskimo, rustimo, or auto (default: rustimo if installed, else haskimo, else pymo); py, hs and rs are short
#   --link           do not copy the data directory, link it to this checkout (a development install)
#   --cabal          build Haskimo with cabal instead of plain ghc
#   --uninstall      remove what an installation under the same prefix put there
#
# After installation
#   i1 run examples/hello.hum.imo                   the default interpreter
#   i1 --impl pymo    run examples/hello.hum.imo    Pymo     (--impl py)
#   i1 --impl haskimo run examples/hello.hum.imo    Haskimo  (--impl hs)
#   i1 --impl rustimo run examples/hello.hum.imo    Rustimo  (--impl rs)
#   i1 --impl all     run examples/hello.hum.imo    all of them; the output is printed once if they agree (else status 3 and a diff)
#   pymo ...  /  haskimo ...  /  rustimo ...        the interpreters directly
set -e

here=$(cd "$(dirname "$0")" && pwd -P)
prefix=${PREFIX:-$HOME/.local}
mode=all
default=auto
link=no
use_cabal=no
uninstall=no

while [ $# -gt 0 ]; do
  case $1 in
    --prefix) prefix=$2; shift 2 ;;
    --prefix=*) prefix=${1#--prefix=}; shift ;;
    --pymo-only|--python-only) mode=pymo; shift ;;
    --haskimo-only|--haskell-only) mode=haskimo; shift ;;
    --rustimo-only|--rust-only) mode=rustimo; shift ;;
    --all|--both) mode=all; shift ;;
    --default) default=$2; shift 2 ;;
    --default=*) default=${1#--default=}; shift ;;
    --link) link=yes; shift ;;
    --cabal) use_cabal=yes; shift ;;
    --uninstall) uninstall=yes; shift ;;
    -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; exit 0 ;;
    *) echo "install.sh: unknown option $1 (see --help)" >&2; exit 2 ;;
  esac
done
case $default in
  py|pymo) default=pymo ;;
  hs|haskimo) default=haskimo ;;
  rs|rustimo) default=rustimo ;;
  auto) ;;
  *) echo "install.sh: --default takes pymo, haskimo, rustimo or auto" >&2; exit 2 ;;
esac

bin=$prefix/bin
share=$prefix/share/i1

if [ "$uninstall" = yes ]; then
  rm -f "$bin/i1" "$bin/pymo" "$bin/haskimo" "$bin/rustimo" "$bin/i1-py" "$bin/i1-hs"      # the last two: the names before Pymo and Haskimo
  if [ -h "$share" ]; then rm -f "$share"; else rm -rf "$share"; fi
  echo "removed i1, pymo, haskimo, rustimo from $bin and $share"
  exit 0
fi

# ---------------------------------------------------------------- what can be installed here
have_py=no; have_ghc=no; have_cargo=no
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then have_py=yes; fi
if command -v ghc >/dev/null 2>&1; then have_ghc=yes; fi
if command -v cargo >/dev/null 2>&1 && command -v rustc >/dev/null 2>&1; then have_cargo=yes; fi

want_pymo=no; want_haskimo=no; want_rustimo=no
case $mode in
  pymo)    want_pymo=yes ;;
  haskimo) want_haskimo=yes ;;
  rustimo) want_rustimo=yes ;;
  all)     want_pymo=yes; want_haskimo=yes; want_rustimo=yes ;;
esac
if [ "$have_py" = yes ] && ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "notice: Pymo is tested on Python 3.11 and newer; $(python3 --version 2>&1) may work but is untested" >&2
fi
if [ "$want_pymo" = yes ] && [ "$have_py" = no ]; then
  if [ "$mode" = pymo ]; then echo "install.sh: python3 (>= 3.8) was not found" >&2; exit 1; fi
  echo "notice: python3 (>= 3.8) was not found: Pymo is not installed" >&2; want_pymo=no
fi
if [ "$want_haskimo" = yes ] && [ "$have_ghc" = no ]; then
  if [ "$mode" = haskimo ]; then echo "install.sh: ghc was not found (install GHC, e.g. with ghcup or your package manager)" >&2; exit 1; fi
  echo "notice: ghc was not found: Haskimo is not installed (install GHC and run  ./install.sh --haskimo-only)" >&2; want_haskimo=no
fi
if [ "$want_rustimo" = yes ] && [ "$have_cargo" = no ]; then
  if [ "$mode" = rustimo ]; then echo "install.sh: cargo and rustc were not found (install Rust, e.g. with rustup)" >&2; exit 1; fi
  echo "notice: cargo was not found: Rustimo is not installed (install Rust and run  ./install.sh --rustimo-only)" >&2; want_rustimo=no
fi
if [ "$want_pymo" = no ] && [ "$want_haskimo" = no ] && [ "$want_rustimo" = no ]; then echo "install.sh: nothing to install" >&2; exit 1; fi

mkdir -p "$bin" "$share"

# ---------------------------------------------------------------- the data directory (also Pymo itself)
if [ "$link" = yes ]; then
  rm -rf "$share"; ln -s "$here" "$share"
else
  for d in pymo lib docs examples; do rm -rf "$share/$d"; cp -R "$here/$d" "$share/$d"; done
  find "$share" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
  for f in README.md LICENSE COMMERCIAL.md; do [ -f "$here/$f" ] && cp "$here/$f" "$share/$f"; done
fi

# ---------------------------------------------------------------- Pymo, the Python interpreter
if [ "$want_pymo" = yes ]; then
  cat > "$bin/pymo" <<EOF
#!/bin/sh
# pymo -- Pymo, the Python interpreter of i-1 (python3 pymo/i1.py)
exec "\${I1_PYTHON:-python3}" "$share/pymo/i1.py" "\$@"
EOF
  chmod +x "$bin/pymo"
  echo "installed Pymo, the Python interpreter: $bin/pymo"
fi

# ---------------------------------------------------------------- Haskimo, the Haskell interpreter
if [ "$want_haskimo" = yes ]; then
  echo "building Haskimo, the Haskell interpreter, with $(ghc --version) ..."
  if [ "$use_cabal" = yes ]; then
    command -v cabal >/dev/null 2>&1 || { echo "install.sh: cabal was not found" >&2; exit 1; }
    ( cd "$here" && cabal build exe:haskimo )
    exe=$(cd "$here" && cabal list-bin exe:haskimo)
  else
    ( cd "$here" && ./haskimo/build.sh -v0 )
    exe=$here/build/haskimo
  fi
  [ -x "$exe" ] || { echo "install.sh: the build did not produce $exe" >&2; exit 1; }
  cp "$exe" "$bin/haskimo"; chmod +x "$bin/haskimo"
  echo "installed Haskimo, the Haskell interpreter: $bin/haskimo"
fi

# ---------------------------------------------------------------- Rustimo, the Rust interpreter
if [ "$want_rustimo" = yes ]; then
  echo "building Rustimo, the Rust interpreter, with $(rustc --version) ..."
  ( cd "$here" && ./rustimo/build.sh --quiet )
  exe=$here/build/rustimo
  [ -x "$exe" ] || { echo "install.sh: the build did not produce $exe" >&2; exit 1; }
  cp "$exe" "$bin/rustimo"; chmod +x "$bin/rustimo"
  echo "installed Rustimo, the Rust interpreter: $bin/rustimo"
fi

# ---------------------------------------------------------------- the dispatcher and the default
cp "$here/i1" "$bin/i1"; chmod +x "$bin/i1"
case $default in
  auto) rm -f "$share/impl" ;;
  *)    if [ -h "$share" ]; then echo "notice: --link and --default together: the default is not written (set I1_IMPL instead)" >&2
        else echo "$default" > "$share/impl"; fi ;;
esac

echo
echo "installed under $prefix:  $bin/i1  (dispatcher)"
if [ "$want_pymo" = yes ]; then echo "   Pymo    : $bin/pymo        python3 pymo/i1.py"; fi
if [ "$want_haskimo" = yes ]; then echo "   Haskimo : $bin/haskimo     the Haskell executable"; fi
if [ "$want_rustimo" = yes ]; then echo "   Rustimo : $bin/rustimo     the Rust executable"; fi
case ":$PATH:" in *":$bin:"*) ;; *) echo "note: $bin is not on your PATH" ;; esac
echo "try:  i1 run $share/examples/hello.hum.imo        (choose with --impl pymo|haskimo|rustimo|all or I1_IMPL)"
