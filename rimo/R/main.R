# main.R -- command line of Rimo, the R interpreter of i-1 (port of schimo/src/main.rkt).
#   rimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  rimo FILE...)
#   rimo check   FILE...                                load the prelude and FILE(s), run the class checker
#   rimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table
#   rimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)
#   rimo text    FILE... NAME                           evaluate NAME as a String and print it
options(expressions = 500000, warn = 1)
invisible(Sys.setlocale("LC_ALL", "C.UTF-8"))
.script <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1L])
rimo_src <- dirname(normalizePath(.script))
RIMO_ROOT <- dirname(dirname(rimo_src))
for (.f in c("base.R", "syntax.R", "layers.R", "core.R", "hum.R", "types.R", "quote.R", "program.R", "output.R")) source(file.path(rimo_src, .f), encoding = "UTF-8")

usage <- paste0(
  "rimo -- Rimo, the R interpreter of i-1 (same commands and output as Pymo, Haskimo, Rustimo, OCamimo, Schimo and Cimo)\n\n",
  "  rimo run     FILE... [--out bin|spec|hum] [--n N]   run the program: evaluate `main` and print it (also:  rimo FILE...)\n",
  "  rimo check   FILE...                                load the prelude and FILE(s), run the class checker\n",
  "  rimo translate FILE... --to spec|bin                  re-spell the checked program (prelude excluded); `bin` also prints the local symbol table\n",
  "  rimo eval    FILE... NAME [N]                       evaluate NAME and print it by its declared class (value, stream element N, tree, string, Bool)\n",
  "  rimo text    FILE... NAME                           evaluate NAME as a String and print it\n\n",
  "`run` prints main ∶ 𝕊 as text, a list or stream of strings line by line, and any other value as a normal-form term in the output\n",
  "notation: --out, else an `@out bin|spec|hum` line in the program, else the notation main is written in.  --n N picks the stream\n",
  "element shown for a stream (default 10), or the number of lines of a stream of strings.\n\n",
  "FILE notation follows the extension:  x.imo / x.spec.imo = spec,  x.hum.imo = human,  x.bin.imo = binary (prelude.bin.imo is trusted).\n")

OUT <- newbuf()
put <- function(s) bpush(OUT, s)
line <- function(s) { bpush(OUT, s); bpush(OUT, "\n") }
flush_out <- function() { if (OUT$n > 0L) cat(paste(bvals(OUT), collapse = ""), sep = ""); OUT$n <- 0L }
is_file <- function(x) file.exists(x) && !dir.exists(x)

load_files <- function(files, build) {
  srcs <- lapply(files, function(f) {
    text <- tryCatch(read_utf8(f),
      bad_utf8 = function(e) stop(host_err("parse", sprintf("%s: hGetContents: invalid argument (%s)", f, conditionMessage(e)))),
      error = function(e) if (inherits(e, "host_err")) stop(e) else stop(host_err("parse", sprintf("%s: openFile: %s", f, if (is_file(f)) conditionMessage(e) else "does not exist (No such file or directory)"))))
    list(f, text)
  })
  prelude <- Filter(function(f) ends_with(f, "prelude.bin.imo"), files)
  p <- load_program(srcs, prelude, length(prelude) == 0L)
  miss <- missing_globals(p)
  if (length(miss) > 0L) parse_err(paste0("these symbols are used and not defined: ", paste(miss, collapse = " ")))
  if (build && length(p$errors) == 0L) build_machine(p)
  p
}
report_errors <- function(p) {
  for (e in p$errors) { f <- e[[1L]]; w <- e[[2L]]; m <- e[[3L]]; line(sprintf("error in %s: %s", basename_of(f), if (starts_with(m, w)) m else paste0(w, ": ", m))) }
}

# ---------------------------------------------------------------- values of ℚ[i], as Pymo shows them: a pair of exact rationals
qval <- function(m, v) {
  pq <- to_pair(m, v); a <- gi_of(m, pq[[1L]]); b <- gi_of(m, pq[[2L]])
  n <- b[[1L]] * b[[1L]] + b[[2L]] * b[[2L]]
  if (n == 0) eval_err("Ratio has zero denominator")
  list(as.bigq(a[[1L]] * b[[1L]] + a[[2L]] * b[[2L]], n), as.bigq(a[[2L]] * b[[1L]] - a[[1L]] * b[[2L]], n))
}
show_frac <- function(r) if (denominator(r) == 1) as.character(numerator(r)) else paste0(as.character(numerator(r)), "/", as.character(denominator(r)))
to_dbl <- function(r) ratio_double(numerator(r), denominator(r))
qfmt <- function(m, v) {
  q <- qval(m, v); re <- q[[1L]]; im <- q[[2L]]
  s <- if (numerator(im) == 0) show_frac(re) else sprintf("%s + %s i", show_frac(re), show_frac(im))
  tail <- if (numerator(im) == 0) "" else sprintf(" + %s i", fmt_g(12L, to_dbl(im)))
  sprintf("%s   (≈ %s%s)", s, fmt_g(12L, to_dbl(re)), tail)
}
sfmt <- function(m, v) {
  out <- integer(0); cur <- v
  repeat {
    c <- cell_or_nil(m, cur)
    if (c[[1L]] != 5L) break
    q <- qval(m, c[[2L]]); t <- bq_trunc(q[[1L]])
    k <- if (t >= -as.bigz(2)^63 && t < as.bigz(2)^63) { if (t >= 0 && t <= 1114111) as.integer(t) else 65533L } else 65533L
    out[length(out) + 1L] <- cp_ok(k); cur <- c[[3L]]
  }
  cps <- out[out != 0L]; cps_str(cps)
}
tfmt <- function(p, v, n) {
  m <- p$machine; left_f <- val(p, "◀"); right_f <- val(p, "▶")
  if (to_bool(m, app_th(m, left_f, list(v)))) {
    ab <- to_pair(m, app_th(m, right_f, list(v)))
    sa <- tfmt(p, ab[[1L]], n); sb <- tfmt(p, ab[[2L]], n)
    sprintf("⟨%s, %s⟩", sa, sb)
  } else {
    leaf0 <- app_th(m, right_f, list(v)); leaf <- if (!is.null(n)) stream_nth(m, leaf0, n) else leaf0
    q <- qval(m, leaf)
    if (!is.null(n)) paste0(fmt_g(10L, to_dbl(q[[1L]])), if (numerator(q[[2L]]) == 0) "" else sprintf(" + %s i", fmt_g(10L, to_dbl(q[[2L]]))))
    else if (numerator(q[[2L]]) == 0) show_frac(q[[1L]]) else sprintf("(%s + %s i)", show_frac(q[[1L]]), show_frac(q[[2L]]))
  }
}
# evaluate NAME and print it according to its declared class
show_name <- function(p, name, n) {
  c <- p$checker; m <- p$machine
  l <- c$sigs[[name]]; cls <- if (length(l) > 0L) norm(c, l[[1L]]) else eval_err("Prelude.head: empty list")
  v <- val(p, name); hd <- if (cls[[1L]] == "K") cls[[2L]] else ""
  if (cls[[1L]] == "K" && (hd == "𝔖" || hd == "ℝ")) { k <- if (is.null(n)) 10L else n; sprintf("element %d of the stream:  %s", k, qfmt(m, stream_nth(m, v, k))) }
  else if (cls[[1L]] == "K" && hd == "𝔏" && length(cls[[3L]]) == 1L && cls[[3L]][[1L]][[1L]] == "K" && cls[[3L]][[1L]][[2L]] == "𝕮") sfmt(m, v)
  else if (cls[[1L]] == "K" && hd == "𝔗" && length(cls[[3L]]) == 1L) {
    a <- cls[[3L]][[1L]]; streams <- a[[1L]] == "K" && a[[2L]] == "𝔖"; k <- if (is.null(n)) 10L else n
    body <- tfmt(p, v, if (streams) k else NULL)
    paste0(if (streams) sprintf("element %d of each leaf:  ", k) else "", body)
  }
  else if (hd == "𝔹") { if (to_bool(m, v)) "true" else "false" }
  else if (contains_sub(show_type(cls), "Ω")) show_value(new_printer(p, "hum", 10L), v, cls)
  else qfmt(m, v)
}

# ---------------------------------------------------------------- commands
take_opt <- function(opt, args) {
  i <- position(function(a) a == opt, as.list(args))
  if (!is.null(i) && i + 1L <= length(args)) list(args[i + 1L], args[-c(i, i + 1L)]) else list(NULL, args)
}
read_int <- function(s) { t <- strip(s); if (nchar(t) > 0L && grepl("^[0-9]+$", t)) as.integer(t) else eval_err("Prelude.read: no parse") }

run_cmd <- function(args0) {
  r1 <- take_opt("--out", args0); o <- r1[[1L]]; r2 <- take_opt("--n", r1[[2L]]); n_opt <- r2[[1L]]; rest <- r2[[2L]]
  if (!is.null(o) && !(o %in% modes)) { line(paste0("--out takes one of ", paste(modes, collapse = ", "))); return(2L) }
  p <- load_files(rest, TRUE)
  if (length(p$errors) > 0L) { report_errors(p); return(1L) }
  n <- if (!is.null(n_opt)) read_int(n_opt) else NULL
  tryCatch({ run_main(p, o, n, put); 0L }, host_err = function(e) if (e$kind == "print") { line(paste0("error: ", e$msg)); 1L } else stop(e))
}
translate_cmd <- function(rest) {
  i <- position(function(a) a == "--to", as.list(rest))
  to <- if (!is.null(i) && i + 1L <= length(rest)) rest[i + 1L] else eval_err("--to is missing")
  files <- rest[rest != "--to" & rest != to]
  p <- load_files(files, FALSE)
  if (length(p$errors) > 0L) { report_errors(p); return(1L) }
  if (to == "spec") put(spec_text(p))
  else { put(bin_text(p)); if (length(p$doc1$local) > 0L) put(paste0("\n", local_table(p))) }
  0L
}
query_cmd <- function(cmd, rest) {
  if (cmd == "check") { files <- rest; name <- NULL; n <- NULL }
  else {
    isf <- vapply(rest, is_file, TRUE); files <- rest[isf]; tl <- rest[!isf]
    if (length(tl) == 0L) parse_err("a name is expected")
    name <- tl[1L]; n <- if (length(tl) > 1L) read_int(tl[2L]) else NULL
  }
  p <- load_files(files, cmd != "check")
  if (length(p$errors) > 0L) { report_errors(p); return(1L) }
  if (cmd == "check") { line(sprintf("ok: %d statements checked", length(user_statements(p)))); return(0L) }
  nm <- spec_name(p$hum, if (is.null(name)) "" else name)
  r <- tryCatch(if (cmd == "text") sfmt(p$machine, val(p, nm)) else show_name(p, nm, n), host_err = function(e) if (e$kind %in% c("unknown", "print")) e else stop(e))
  if (inherits(r, "host_err")) { line(paste0("error: ", r$msg)); 1L } else { line(r); 0L }
}
dispatch <- function(args) {
  if (length(args) == 0L) { put(usage); return(0L) }
  if (args[1L] %in% c("-h", "--help")) { put(usage); return(0L) }
  cmd <- args[1L]; known <- c("run", "check", "eval", "text", "translate")
  if (!(cmd %in% known) && is_file(cmd)) { cmd2 <- "run"; rest <- args } else { cmd2 <- cmd; rest <- args[-1L] }
  if (cmd2 == "run") run_cmd(rest) else if (cmd2 == "translate") translate_cmd(rest) else if (cmd2 %in% c("check", "eval", "text")) query_cmd(cmd2, rest) else { put(usage); 2L }
}
real_main <- function(args) {
  trace <- function(e) {                           # RIMO_TRACE=1: the last calls before an internal error, on the standard error
    if (nzchar(Sys.getenv("RIMO_TRACE")) && !inherits(e, "host_err") && !inherits(e, "class_err")) {
      cs <- sys.calls(); n <- length(cs)
      cat("rimo: depth", n, ":", paste(vapply(cs[max(1L, n - 30L):n], function(x) substr(paste(deparse(x[[1L]]), collapse = ""), 1L, 30L), ""), collapse = " > "), "\n", file = stderr())
    }
  }
  code <- withCallingHandlers(tryCatch(dispatch(args),
    host_err = function(e) { flush_out(); cat(sprintf("rimo: %s\n", e$msg), file = stderr()); 1L },
    bad_utf8 = function(e) { flush_out(); cat(sprintf("rimo: %s\n", conditionMessage(e)), file = stderr()); 1L },
    error = function(e) { flush_out(); cat(sprintf("rimo: internal error: %s\n", conditionMessage(e)), file = stderr()); 1L }), error = trace)
  flush_out()
  code
}
quit(save = "no", status = real_main(commandArgs(trailingOnly = TRUE)))
