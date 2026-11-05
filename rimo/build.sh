#!/bin/sh
# build Rimo, the R interpreter: nothing is compiled (the sources are R); this checks that R and the CRAN package gmp are there, writes the launcher build/rimo
# and warms the cache of the checked prelude (~/.cache/rimo, or $RIMO_CACHE), which is made on the first run and used by every run after it
cd "$(dirname "$0")/.." || exit 1
mkdir -p build
command -v Rscript >/dev/null 2>&1 || { echo "rimo: Rscript was not found (install R: apt-get install r-base-core)" >&2; exit 1; }
Rscript -e 'if (!requireNamespace("gmp", quietly = TRUE)) quit(status = 1)' 2>/dev/null || { echo "rimo: the R package gmp was not found (apt-get install r-cran-gmp, or install.packages(\"gmp\"))" >&2; exit 1; }
cat > build/rimo.tmp <<'LAUNCHER'
#!/bin/sh
here=$(cd "$(dirname "$0")" && pwd)
export LC_ALL=C.UTF-8
ulimit -s unlimited 2>/dev/null || ulimit -s 4000000 2>/dev/null
exec Rscript --max-ppsize=500000 "$here/../rimo/R/main.R" "$@"
LAUNCHER
chmod +x build/rimo.tmp && mv build/rimo.tmp build/rimo
printf 'main in \\NN := 1 + 1\n' > build/rimo-warm.hum.imo
build/rimo run build/rimo-warm.hum.imo >/dev/null && rm -f build/rimo-warm.hum.imo
