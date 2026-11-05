#!/bin/sh
# build Schimo, the Racket (Scheme) interpreter: the data module is generated, the modules are compiled by raco make, and build/schimo is a
# launcher that runs the compiled program with racket (the compiled files are kept in schimo/src/compiled); output: build/schimo
cd "$(dirname "$0")/.." || exit 1
mkdir -p build
./schimo/gen_data.sh || exit 1
raco make -v schimo/src/main.rkt || exit 1
cat > build/schimo.tmp <<'LAUNCHER'
#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
exec racket "$here/../schimo/src/main.rkt" "$@"
LAUNCHER
chmod +x build/schimo.tmp && mv build/schimo.tmp build/schimo
