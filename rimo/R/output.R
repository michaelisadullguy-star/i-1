# output.R -- printing values: the output side of the three notations, and the `main` entry point (port of schimo/src/output.rkt).
# A value is printed as a NORMAL-FORM TERM in the chosen notation.  Nothing is computed on the host: the normal forms are computed IN THE LANGUAGE (⊜, showq / showc, decimals); the host
# walks the value as its declared class describes it, reads digit strings and turns code points into characters.  main ∶ 𝕊: its text is the output; main ∶ 𝔏 𝕊 / 𝔖 𝕊: one line per element;
# any other class: the value as a term.
modes <- c("bin", "spec", "hum")
undetermined <- "undetermined: this truth value is neither proved nor refuted — a statement that depends on its unknowns, or a relation on ℝ[i] that no rule decides (declare it Prop to print its simplest form instead of a Bool)"

new_printer <- function(p, mode, n) { pr <- new.env(hash = FALSE, parent = emptyenv()); pr$p <- p; pr$mode <- mode; pr$n <- n; pr }
mach <- function(pr) pr$p$machine
chk <- function(pr) pr$p$checker
is_hum <- function(pr) pr$mode == "hum"

esc <- function(q, s) {                            # s: a string; q: the quote (code point)
  cps <- str_cps(s); out <- character(length(cps))
  for (i in seq_along(cps)) { c <- cps[i]; out[i] <- if (c == 92L) "\\\\" else if (c == 10L) "\\n" else if (c == 9L) "\\t" else if (c == q) paste0("\\", intToUtf8(c)) else cp_string(c) }
  paste(out, collapse = "")
}
# take a list / string cell apart (a cons value, or VNIL); ⍰ (an undetermined Boolean inside the text) is reported, never printed as text
cell_of <- function(pr, v) { c <- cell_or_nil(mach(pr), v); if (c[[1L]] == 5L || c[[1L]] == 4L) c else print_err(undetermined) }
boolean_of <- function(pr, v) {
  m <- mach(pr); r <- apply_whnf(m, v, list(m$vt, m$vf))
  if (r[[1L]] == 2L) TRUE else if (r[[1L]] == 3L) FALSE else print_err(undetermined)
}
call_th <- function(pr, f, args) call_g(mach(pr), f, args)

# a 𝕮 value (a natural numeral, as a ℚ[i] pair) -> code point; its canonical form is a pair (n, 1)
char_of <- function(pr, v) {
  m <- mach(pr); canon <- call_th(pr, "⊜", list(v)); pz <- to_pair(m, canon)
  zd <- to_list(m, pz[[1L]]); ok_den <- identical(to_list(m, pz[[2L]]), 1L)
  r <- val_digits_small(zd)
  cp <- if (!is.null(r) && r[[2L]] == 0 && r[[1L]] >= 0 && r[[1L]] <= 1114111) as.integer(r[[1L]]) else NULL
  if (!is.null(cp) && ok_den) { if (cp >= 55296L && cp <= 57343L) 65533L else cp } else 65533L
}
# a 𝕊 value -> a vector of code points
text_cps <- function(pr, v) {
  out <- integer(64L); n <- 0L; cell <- cell_of(pr, v)
  while (cell[[1L]] == 5L) {
    n <- n + 1L; if (n > length(out)) length(out) <- 2L * length(out)
    out[n] <- cp_ok(char_of(pr, cell[[2L]])); cell <- cell_of(pr, cell[[3L]])
  }
  out[seq_len(n)]
}
text_of <- function(pr, v) { cps <- text_cps(pr, v); cps <- cps[cps != 0L]; cps_str(cps) }
digits_str <- function(pr, v) numeral(to_list(mach(pr), v))
is_class <- function(pr, cls, name) leq(chk(pr), cls, K_(name)) && leq(chk(pr), K_(name), cls)

strip_quotes <- function(t) switch(t[[1L]], TQuote = strip_quotes(t[[2L]]), TApp = list("TApp", strip_quotes(t[[2L]]), lapply(t[[3L]], strip_quotes)), TLam = list("TLam", t[[2L]], strip_quotes(t[[3L]])), t)

# ---------------------------------------------------------------- the Speller: the human spelling of the code of a statement
# nodes: list("N", x) list("S", x) list("A", f, a) list("L") list("Var")     pieces: list(text, precedence, kind)
formula_args <- c("∧", "∨", "¬", "⇒", "⇔", "∧Ω", "∨Ω", "¬Ω", "⇒Ω", "⇔Ω", "prop", "decide", "code_rd")
spell_transparent <- c("⇡", "prop", "decide", "code_rd")
tight <- c("*", "/", "^")
assoc_ops <- c("+", "*")
par_ <- function(pc, need, avoid) if (pc[[2L]] < need || pc[[3L]] %in% avoid) paste0("(", pc[[1L]], ")") else pc[[1L]]

node_of <- function(pr, v) {
  m <- mach(pr)
  not_a_code <- function() print_err("a statement whose code is not a code (undetermined, or not built by the simplifier)")
  r <- tryCatch(apply_whnf(m, v, m$code_cbs), host_err = function(e) e)
  if (inherits(r, "host_err")) { if (r$kind == "unknown") stop(r) else not_a_code() }
  tg <- r[[1L]]
  if (tg == 8L) list("N", r[[2L]]) else if (tg == 9L) list("S", r[[2L]]) else if (tg == 10L) list("A", r[[2L]], r[[3L]]) else if (tg == 11L) list("L") else if (tg == 12L) list("Var") else not_a_code()
}
symbol_name <- function(pr, c) {
  ds <- trim_digits(to_list(mach(pr), c)); b <- paste0(".", numeral(ds), ".")
  r <- getk(pr$p$doc1$b2s, b)
  if (is.null(r)) print_err(sprintf("a statement mentions the symbol code %s, which neither doc 1 nor this program names", b))
  r
}
# reverse doc 2: the first entry that has the spec symbol on its right
rev_entry <- function(pr, spec) {
  for (e in pr$p$doc2[[1L]]) if (e[[3L]] %in% c("value", "infixl", "infixr", "infix", "prefix") && spec %in% e[[2L]]) return(e)
  NULL
}
number_piece <- function(pr, q) {
  t <- tryCatch(text_of(pr, call_th(pr, "showc", list(q))), host_err = function(e) if (e$kind == "eval") print_err("a statement holds a value that is not a number where a number is expected") else stop(e))
  p <- if (contains_sub(t, " + ") || contains_sub(t, " - ")) 6L else if (ends_with(t, "i") || contains_sub(t, "/")) 7L else if (starts_with(t, "-")) 8L else 10L
  list(t, p, "num")
}
go <- function(pr, v, formula) {
  n <- node_of(pr, v); k <- n[[1L]]
  if (k == "N") {
    if (formula) {
      m <- mach(pr); r <- apply_whnf(m, n[[2L]], list(m$vt, m$vf))
      if (r[[1L]] == 2L) list("true", 10L, "atom") else if (r[[1L]] == 3L) list("false", 10L, "atom") else print_err(undetermined)
    } else number_piece(pr, n[[2L]])
  } else if (k == "S") app_piece(pr, symbol_name(pr, n[[2L]]), list(), formula)
  else if (k == "A") {
    args <- list(n[[3L]]); cur <- node_of(pr, n[[2L]])
    repeat {
      if (cur[[1L]] == "A") { args <- c(list(cur[[3L]]), args); cur <- node_of(pr, cur[[2L]]) }
      else if (cur[[1L]] == "S") return(app_piece(pr, symbol_name(pr, cur[[2L]]), args, formula))
      else print_err("a statement applies something that is not a symbol (a λ): it has no human spelling")
    }
  } else print_err("a statement contains a λ or a bound variable: it has no human spelling yet")
}
app_piece <- function(pr, name, args, formula) {
  k <- length(args)
  if ((name == "⊤" || name == "⊥") && k == 0L) return(list(if (name == "⊤") "true" else "false", 10L, "atom"))
  if (name %in% spell_transparent && k == 1L) return(go(pr, args[[1L]], formula && name != "⇡"))
  if (name == "⊘" && k == 0L) return(list("[]", 10L, "atom"))
  if (name == "∷" && k == 2L) { first <- go(pr, args[[1L]], FALSE)[[1L]]; items <- list_loop(pr, args[[2L]], first); return(list(paste0("[", paste(items, collapse = ", "), "]"), 10L, "atom")) }
  if ((name == "∨" || name == "∨Ω") && k == 2L) { a <- go(pr, args[[1L]], TRUE); b <- go(pr, args[[2L]], TRUE); return(list(paste0(par_(a, 3L, "and"), " or ", par_(b, 2L, "and")), 2L, "or")) }
  if ((name == "∧" || name == "∧Ω") && k == 2L) { a <- go(pr, args[[1L]], TRUE); b <- go(pr, args[[2L]], TRUE); return(list(paste0(par_(a, 4L, character(0)), " and ", par_(b, 3L, character(0))), 3L, "and")) }
  if ((name == "¬" || name == "¬Ω") && k == 1L) { a <- go(pr, args[[1L]], TRUE); return(list(paste0("not ", par_(a, 4L, character(0))), 4L, "not")) }
  sub <- name %in% formula_args
  entry <- rev_entry(pr, name)
  h <- if (!is.null(entry)) entry[[1L]] else name
  role <- if (!is.null(entry)) entry[[3L]] else "value"
  prec <- if (!is.null(entry) && !is.null(entry[[4L]])) entry[[4L]] else 0L
  if (role %in% c("infixl", "infixr", "infix") && k == 2L) {
    a <- go(pr, args[[1L]], sub); b <- go(pr, args[[2L]], sub)
    if (h == "^") { ln <- 10L; rn <- prec }
    else if (role == "infixl") { ln <- prec; rn <- if (h %in% assoc_ops) prec else prec + 1L }
    else if (role == "infixr") { ln <- prec + 1L; rn <- prec }
    else { ln <- prec + 1L; rn <- prec + 1L }
    sep <- if (h %in% tight) h else paste0(" ", h, " ")
    return(list(paste0(par_(a, ln, character(0)), sep, par_(b, rn, character(0))), prec, "op"))
  }
  if (role == "prefix" && k == 1L) {
    a <- go(pr, args[[1L]], sub); x0 <- par_(a, prec, character(0))
    x <- if (h == "-" && starts_with(x0, "-")) paste0("(", a[[1L]], ")") else x0
    c1 <- if (nchar(h) > 0L) utf8ToInt(h)[1L] else NA_integer_
    first_alpha <- !is.na(c1) && grepl("^[[:alpha:]]", intToUtf8(c1))
    return(list(if (first_alpha) paste0(h, " ", x) else paste0(h, x), prec, "op"))
  }
  if (k == 0L && role == "value") return(list(h, 10L, "atom"))
  if (role != "value") print_err(sprintf("%s applied to %d argument(s) has no human spelling", h, k))
  as <- vapply(args, function(a) go(pr, a, sub)[[1L]], "")
  list(paste0(h, "(", paste(as, collapse = ", "), ")"), 10L, "atom")
}
list_loop <- function(pr, rest, first) {
  bad <- function() print_err("a list code that does not end in ⊘")
  acc <- first; cur <- rest
  repeat {
    n <- node_of(pr, cur)
    if (n[[1L]] == "S") { if (symbol_name(pr, n[[2L]]) == "⊘") return(acc) else bad() }
    else if (n[[1L]] == "A") {
      n2 <- node_of(pr, n[[2L]])
      if (n2[[1L]] == "A") {
        n3 <- node_of(pr, n2[[2L]])
        if (n3[[1L]] == "S" && symbol_name(pr, n3[[2L]]) == "∷") { acc <- c(acc, go(pr, n2[[3L]], FALSE)[[1L]]); cur <- n[[3L]] } else bad()
      } else bad()
    } else bad()
  }
}
spell <- function(pr, v) go(pr, v, TRUE)[[1L]]

# the spec term of a human statement, read in the program's context (unknowns declared): the checker chooses ≐ or ≐ᴿ, inserts ⇡ and prop, and marks statements — the marks are dropped
reread <- function(pr, text) {
  c <- chk(pr)
  term <- tryCatch({
    ts <- lex_hum(text); r <- hum_expr(pr$p$hum, ts, 1L, 0L, character(0))
    if (r[[2L]] <= length(ts)) parse_err(paste0("unexpected ", show_tok(ts[[r[[2L]]]])))
    r[[1L]]
  }, host_err = function(e) if (e$kind == "parse") print_err(sprintf("the statement %s cannot be read in the human notation (%s)", py_repr(text), e$msg)) else stop(e))
  r <- tryCatch(synth(c, list(), term), class_err = function(e) e)
  if (inherits(r, "class_err")) print_err(sprintf("the statement %s does not read back in this program: %s", py_repr(text), r$msg))
  fitted <- fit(c, r[[2L]], r[[1L]], prop_ty)
  if (!is.null(fitted)) pp_term(strip_quotes(fitted)) else print_err(sprintf("%s reads back as a %s, not as a statement", py_repr(text), show_type(r[[1L]])))
}
statement_text <- function(pr, v) { text <- spell(pr, v); if (is_hum(pr)) text else reread(pr, text) }
number_text <- function(pr, v, cls) {
  m <- mach(pr)
  if (is_hum(pr)) text_of(pr, call_th(pr, if (leq(chk(pr), cls, K_("ℚ"))) "showq" else "showc", list(v)))
  else {
    canon <- call_th(pr, "⊜", list(v)); pz <- to_pair(m, canon)
    zt <- digits_str(pr, pz[[1L]]); mt <- digits_str(pr, pz[[2L]])
    if (mt == "1") zt else sprintf("(÷ %s %s)", zt, mt)
  }
}
# the normal-form term of v (of class raw) in spec or hum notation (bin is spelled from spec)
term_of <- function(pr, v, raw) {
  c <- chk(pr); m <- mach(pr); hum <- is_hum(pr); cls <- norm(c, raw)
  if (cls[[1L]] != "K") print_err(sprintf("cannot print a value whose class is not known (%s)", show_type(raw)))
  hd <- cls[[2L]]; args <- cls[[3L]]
  if (identical(cls, prop_ty)) return(statement_text(pr, v))
  if (is_class(pr, raw, "𝕊") || (hd == "𝔏" && length(args) > 0L && identical(norm(c, args[[1L]]), K_("𝕮")))) return(paste0("\"", esc(34L, text_of(pr, v)), "\""))
  if (leq(c, raw, K_("𝕮"))) return(paste0("'", esc(39L, cp_string(char_of(pr, v))), "'"))
  if (leq(c, raw, num_ty)) return(number_text(pr, v, raw))
  if (hd == "𝔹") { b <- boolean_of(pr, v); return(if (hum) (if (b) "true" else "false") else if (b) "⊤" else "⊥") }
  if (hd == "𝔒") { k <- to_ord(m, v); return((if (hum) c("less", "same", "greater") else c("⋖", "≖", "⋗"))[min(k, 2L) + 1L]) }
  if (hd == "𝔏") {
    el <- args[[1L]]; cell_of(pr, v)
    if (identical(norm(c, el), bool_ty) && !hum) return(sprintf("(◀ %s)", digits_str(pr, v)))
    items <- character(0); cell <- cell_of(pr, v)
    while (cell[[1L]] == 5L) { items <- c(items, term_of(pr, cell[[2L]], el)); cell <- cell_of(pr, cell[[3L]]) }
    if (hum) return(paste0("[", paste(items, collapse = ", "), "]"))
    out <- "⊘"; for (x in rev(items)) out <- sprintf("(∷ %s %s)", x, out)
    return(out)
  }
  if (hd == "𝔓") {
    ab <- to_pair(m, v); x <- term_of(pr, ab[[1L]], args[[1L]]); y <- term_of(pr, ab[[2L]], args[[2L]])
    return(if (hum) sprintf("pair(%s, %s)", x, y) else sprintf("(⊗ %s %s)", x, y))
  }
  if (hd == "𝔗") {
    tb <- to_pair(m, v)
    if (to_bool(m, tb[[1L]])) {
      ab <- to_pair(m, tb[[2L]]); x <- term_of(pr, ab[[1L]], cls); y <- term_of(pr, ab[[2L]], cls)
      return(if (hum) sprintf("node(%s, %s)", x, y) else sprintf("(❁ %s %s)", x, y))
    }
    x <- term_of(pr, tb[[2L]], args[[1L]])
    return(if (hum) sprintf("leaf(%s)", x) else sprintf("(❀ %s)", x))
  }
  if (hd == "𝔖") return(term_of(pr, stream_nth(m, v, pr$n), args[[1L]]))
  if (hd == "→" || hd == "𝔄") print_err(sprintf("a value of class %s has no normal form to print (it is a function)", show_type(raw)))
  print_err(sprintf("cannot print a value of class %s", show_type(raw)))
}
# the language value of a small natural number, built from its digits (the reader's numeral expansion)
lit_value <- function(pr, k) { m <- mach(pr); call_g(m, "⊗", list(list_value(m, small_digits(k)), list_value(m, 1L))) }

# the remark printed after a stream element (none in bin: the binary notation has no comments)
comment_text <- function(pr, v, cls0) {
  c <- chk(pr); m <- mach(pr); cls <- norm(c, cls0)
  if (cls[[1L]] == "K" && cls[[2L]] == "𝔖" && length(cls[[3L]]) == 1L && pr$mode != "bin") {
    el <- cls[[3L]][[1L]]; mark <- if (is_hum(pr)) "--" else "⍝"; approx <- ""
    if (leq(c, el, num_ty)) {
      x <- stream_nth(m, v, pr$n)
      re_v <- call_th(pr, "ℜ", list(x)); re <- text_of(pr, call_th(pr, "decimals", list(re_v, lit_value(pr, 12L))))
      im <- call_th(pr, "ℑ", list(x)); eq0 <- call_th(pr, "≐", list(im, lit_value(pr, 0L)))
      if (!to_bool(m, eq0)) {
        imt <- text_of(pr, call_th(pr, "decimals", list(im, lit_value(pr, 12L))))
        stripped <- sub("^-+", "", imt)
        approx <- sprintf(", ≈ %s %s %s i", re, if (starts_with(imt, "-")) "-" else "+", stripped)
      } else approx <- sprintf(", ≈ %s", re)
    }
    sprintf("   %s element %d of the stream%s", mark, pr$n, approx)
  } else ""
}
show_value <- function(pr, v, cls) {
  t <- term_of(pr, v, cls)
  t2 <- if (pr$mode == "bin") spec_term_to_bin(t, copy_doc1(pr$p$doc1)) else t
  paste0(t2, comment_text(pr, v, cls))
}

# ---------------------------------------------------------------- main
output_mode <- function(p, override, name) { if (!is.null(override)) override else if (!is.null(p$out_mode)) p$out_mode else { r <- getk(p$notation_of, name); if (!is.null(r)) r else "spec" } }
run_main_inner <- function(p, mode0, n, write) {
  c <- p$checker; l <- c$sigs[["main"]]
  cls <- if (length(l) > 0L) l[[1L]] else print_err("this program has no main:  define  main ∶ <class>  (spec),  main in <Class> := …  (hum)")
  mode <- output_mode(p, mode0, "main"); v <- val(p, "main")
  pr <- new_printer(p, mode, if (is.null(n)) 10L else n); c0 <- norm(c, cls)
  if (leq(c, cls, K_("𝕊"))) {
    cell <- cell_of(pr, v)
    while (cell[[1L]] == 5L) { write(cp_string(char_of(pr, cell[[2L]]))); cell <- cell_of(pr, cell[[3L]]) }
    mode
  } else if (c0[[1L]] == "K" && c0[[2L]] %in% c("𝔏", "𝔖") && length(c0[[3L]]) == 1L && identical(norm(c, c0[[3L]][[1L]]), norm(c, K_("𝕊")))) {
    cell <- cell_of(pr, v); k <- 0L
    while (cell[[1L]] == 5L && (is.null(n) || k < n)) { s <- text_of(pr, cell[[2L]]); write(paste0(s, "\n")); cell <- cell_of(pr, cell[[3L]]); k <- k + 1L }
    mode
  } else { write(paste0(show_value(pr, v, cls), "\n")); mode }
}
# evaluate `main` and write its output; returns the output notation used.  An unknown whose value is needed is reported (kind print), as an undetermined truth value is.
run_main <- function(p, mode0, n, write) tryCatch(run_main_inner(p, mode0, n, write), host_err = function(e) if (e$kind == "unknown") stop(host_err("print", e$msg)) else stop(e))
