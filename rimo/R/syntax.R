# syntax.R -- the SPEC notation reader of i-1 (port of schimo/src/syntax.rkt).
# spec text -> statements:  SDef name params body | SDecl name type | SFact term.
# Terms are lists with a tag in the first place: list("TNum", s) list("TChr", c) list("TStr", s) list("TVar", n) list("TApp", f, args) list("TLam", ps, body)
# list("TAsc", e, ty) list("TQuote", e, loc).  Classes: list("K", name, args), list("V", name), list("F").  The runtime term (de Bruijn):
# list("CV", k) list("CL", b) list("CA", f, x) list("CG", g).

K_ <- function(name, args = list()) list("K", name, args)
V_ <- function(name) list("V", name)
F_ <- list("F")
is_K <- function(t) t[[1L]] == "K"

# loc: an insertion-ordered named list  name -> class
loc_insert <- function(loc, n, t) { loc[[n]] <- t; loc }
loc_lookup <- function(loc, n) loc[[n]]
loc_member <- function(loc, n) !is.null(loc[[n]])

class_vars <- c("α", "β", "γ", "δ", "ε")
class_var <- function(n) n %in% class_vars

# ---------------------------------------------------------------- Haskell-style `show`
hs_names <- c("NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "a", "b", "t", "n", "v", "f", "r", "SO", "SI", "DLE", "DC1", "DC2", "DC3", "DC4",
              "NAK", "SYN", "ETB", "CAN", "EM", "SUB", "ESC", "FS", "GS", "RS", "US")
hs_show_str <- function(s) {
  cps <- str_cps(s); n <- length(cps); out <- character(n)
  for (i in seq_len(n)) {
    u <- cps[i]; nx <- if (i < n) cps[i + 1L] else NA_integer_
    out[i] <- if (u == 34L) "\\\"" else if (u == 92L) "\\\\"
      else if (u < 32L) paste0("\\", hs_names[u + 1L], if (u == 14L && !is.na(nx) && nx == 72L) "\\&" else "")
      else if (u == 127L) "\\DEL"
      else if (u > 126L) paste0("\\", u, if (!is.na(nx) && nx >= 48L && nx <= 57L) "\\&" else "")
      else intToUtf8(u)
  }
  paste0("\"", paste(out, collapse = ""), "\"")
}
hs_show_list_str <- function(xs) paste0("[", paste(vapply(xs, hs_show_str, ""), collapse = ","), "]")
hs_show_ty <- function(t) switch(t[[1L]],
  V = paste0("V ", hs_show_str(t[[2L]])),
  F = "F",
  K = paste0("K ", hs_show_str(t[[2L]]), " [", paste(vapply(t[[3L]], hs_show_ty, ""), collapse = ","), "]"))

# ---------------------------------------------------------------- lexer.  Tokens: list("Nl") list("Open") list("Close") list("num", s) list("chr", c) list("str", s) list("name", s)
.delim <- local({ d <- logical(128L); d[c(32L, 9L, 13L, 10L, 40L, 41L, 48L, 49L, 46L, 39L, 34L) + 1L] <- TRUE; d })
is_delim <- function(c) c < 128L && .delim[c + 1L]
TK_NL <- list("Nl"); TK_OPEN <- list("Open"); TK_CLOSE <- list("Close")
hs_show_tok <- function(t) switch(t[[1L]], Nl = "TNL", Open = "TOpen", Close = "TClose",
  num = paste0("TkNum ", hs_show_str(t[[2L]])), chr = paste0("TkChr ", t[[2L]]), str = paste0("TkStr ", hs_show_str(t[[2L]])), name = paste0("TkName ", hs_show_str(t[[2L]])))
comment_cp <- 0x235DL

lex_spec <- function(text) {
  cps <- str_cps(text); n <- length(cps)
  toks <- vector("list", 4096L); nt <- 0L; d <- 0L; i <- 1L
  while (i <= n) {
    c <- cps[i]; tk <- NULL
    if (c == 32L || c == 9L || c == 13L) { i <- i + 1L; next }
    if (c == 10L) { i <- i + 1L; if (d == 0L) tk <- TK_NL else next }
    else if (c == 40L) { i <- i + 1L; d <- d + 1L; tk <- TK_OPEN }
    else if (c == 41L) { i <- i + 1L; d <- d - 1L; tk <- TK_CLOSE }
    else if (c == 48L || c == 49L || c == 46L) {
      j <- i
      while (j <= n && (cps[j] == 48L || cps[j] == 49L || cps[j] == 46L)) j <- j + 1L
      s <- cps_str(cps[i:(j - 1L)])
      dots <- sum(cps[i:(j - 1L)] == 46L)
      if (dots > 1L) parse_err(sprintf("bad numeral %s (spec notation allows one radix point)", py_repr(s)))
      i <- j; tk <- list("num", s)
    } else if (c == 39L || c == 34L) {
      body <- integer(0); j <- i + 1L; blen <- 0L; first <- NA_integer_
      repeat {
        if (j > n) parse_err("unterminated literal")
        x <- cps[j]
        if (x == c) { j <- j + 1L; break }
        if (x == 92L) {
          if (j + 1L > n) parse_err("string index out of range")
          y0 <- cps[j + 1L]; y <- if (y0 == 110L) 10L else if (y0 == 116L) 9L else y0
          body[length(body) + 1L] <- y; blen <- blen + 1L; if (is.na(first)) first <- y
          j <- j + 2L
        } else { body[length(body) + 1L] <- x; blen <- blen + 1L; if (is.na(first)) first <- x; j <- j + 1L }
      }
      if (c == 39L) {
        if (blen == 1L) tk <- list("chr", first) else parse_err(sprintf("char literal needs exactly one character: %s", py_repr_cps(body)))
      } else tk <- list("str", cps_str(body))
      i <- j
    } else {
      j <- i
      while (j <= n && !is_delim(cps[j])) j <- j + 1L
      name <- cps_str(cps[i:(j - 1L)])
      if (j - i == 1L && cps[i] == comment_cp) {
        k <- j
        while (k <= n && cps[k] != 10L) k <- k + 1L
        i <- k; next
      }
      i <- j; tk <- list("name", name)
    }
    nt <- nt + 1L; if (nt > length(toks)) length(toks) <- 2L * length(toks)
    toks[[nt]] <- tk
  }
  toks[seq_len(nt)]
}

# token trees: an atom (a token) or a parenthesised group list("grp", items)
hs_show_tt <- function(t) {
  if (t[[1L]] == "grp") paste0("Grp [", paste(vapply(t[[2L]], hs_show_tt, ""), collapse = ","), "]")
  else { s <- hs_show_tok(t); if (grepl(" ", s, fixed = TRUE)) paste0("Atom (", s, ")") else paste0("Atom ", s) }
}

# token list (one line, no Nl) -> token trees
trees <- function(ts) {
  stack <- list(list()); depth <- 1L
  for (t in ts) {
    k <- t[[1L]]
    if (k == "Open") { depth <- depth + 1L; stack[[depth]] <- list() }
    else if (k == "Close") {
      if (depth == 1L) parse_err("unexpected )")
      g <- list("grp", stack[[depth]]); stack[[depth]] <- NULL; depth <- depth - 1L
      stack[[depth]][[length(stack[[depth]]) + 1L]] <- g
    } else stack[[depth]][[length(stack[[depth]]) + 1L]] <- t
  }
  if (depth > 1L) parse_err("missing )")
  stack[[1L]]
}

# the logical lines (split at top-level newlines) of a token stream, each as a list of token trees
logical_lines <- function(toks) {
  out <- list(); cur <- list()
  flush <- function() { if (length(cur) > 0L) { tt <- trees(cur); if (length(tt) > 0L) out[[length(out) + 1L]] <<- tt }; cur <<- list() }
  for (t in toks) { if (t[[1L]] == "Nl") flush() else cur[[length(cur) + 1L]] <- t }
  flush()
  out
}

# ---------------------------------------------------------------- terms
name_is <- function(t, n) t[[1L]] == "name" && t[[2L]] == n
s_arrow <- "→"; s_mapsto <- "↦"; s_colon <- "∶"; s_assign <- "≔"
rposition <- function(pred, l) { r <- NA_integer_; for (i in seq_along(l)) if (pred(l[[i]])) r <- i; if (is.na(r)) NULL else r }
position <- function(pred, l) { for (i in seq_along(l)) if (pred(l[[i]])) return(i); NULL }

parse_item <- function(t) switch(t[[1L]],
  num = list("TNum", t[[2L]]), chr = list("TChr", t[[2L]]), str = list("TStr", t[[2L]]), name = list("TVar", t[[2L]]),
  grp = {
    inner <- t[[2L]]
    k <- rposition(function(x) name_is(x, s_mapsto), inner)
    if (!is.null(k)) list("TLam", parse_binders(inner[seq_len(k - 1L)]), parse_seq(inner[-seq_len(k)]))
    else parse_seq(inner)
  },
  parse_err(paste0("unexpected ", hs_show_tok(t))))

parse_binders <- function(ts) {
  out <- list(); i <- 1L; n <- length(ts)
  while (i <= n) {
    t <- ts[[i]]
    if (t[[1L]] != "name") parse_err(paste0("bad binder ", hs_show_tt(t)))
    nm <- t[[2L]]
    if (i + 1L <= n && name_is(ts[[i + 1L]], s_colon)) {
      r <- parse_type_atom(ts, i + 2L)
      out[[length(out) + 1L]] <- list(nm, r[[1L]]); i <- r[[2L]]
    } else { out[[length(out) + 1L]] <- list(nm, NULL); i <- i + 1L }
  }
  out
}

parse_seq <- function(ts) {
  if (length(ts) == 0L) parse_err("empty application")
  if (length(ts) == 1L) return(parse_item(ts[[1L]]))
  list("TApp", parse_item(ts[[1L]]), lapply(ts[-1L], parse_item))
}

# ---------------------------------------------------------------- types.  parse_type_atom(ts, i) -> list(type, next index)
parse_type_atom <- function(ts, i) {
  if (i > length(ts)) parse_err("list index out of range")
  t <- ts[[i]]
  if (t[[1L]] == "name") { n <- t[[2L]]; return(list(if (class_var(n)) V_(n) else K_(n), i + 1L)) }
  if (t[[1L]] == "grp") return(list(parse_type_seq(t[[2L]]), i + 1L))
  parse_err(paste0("bad type ", hs_show_tt(t)))
}
type_atoms <- function(ts, i) {
  out <- list()
  while (i <= length(ts)) { r <- parse_type_atom(ts, i); out[[length(out) + 1L]] <- r[[1L]]; i <- r[[2L]] }
  out
}
parse_type_seq <- function(inner) {
  if (length(inner) == 0L) parse_err("empty type")
  if (name_is(inner[[1L]], s_arrow)) {
    a <- type_atoms(inner, 2L)
    if (length(a) == 2L) return(K_(s_arrow, a)) else parse_err("→ takes two classes")
  }
  k <- position(function(x) name_is(x, s_arrow), inner)
  if (!is.null(k)) {
    l <- parse_type_seq(inner[seq_len(k - 1L)]); r <- parse_type_seq(inner[-seq_len(k)])
    return(K_(s_arrow, list(l, r)))
  }
  r0 <- parse_type_atom(inner, 1L); hd <- r0[[1L]]
  args <- type_atoms(inner, r0[[2L]])
  if (length(args) == 0L) hd
  else if (hd[[1L]] == "K" && length(hd[[3L]]) == 0L) K_(hd[[2L]], args)
  else parse_err(paste0("bad class application ", hs_show_ty(hd)))
}

is_arrow <- function(t) t[[1L]] == "K" && t[[2L]] == s_arrow
show_type <- function(t) switch(t[[1L]],
  V = t[[2L]], F = "⊥",
  K = {
    n <- t[[2L]]; args <- t[[3L]]
    if (n == s_arrow && length(args) == 2L) {
      a <- args[[1L]]; l <- show_type(a); if (is_arrow(a)) l <- paste0("(", l, ")")
      paste0(l, " → ", show_type(args[[2L]]))
    } else if (length(args) == 0L) n
    else paste0("(", n, " ", paste(vapply(args, function(a) if (is_arrow(a)) paste0("(", show_type(a), ")") else show_type(a), ""), collapse = " "), ")")
  })

# ---------------------------------------------------------------- statements
has_assign <- function(t) if (t[[1L]] == "grp") any(vapply(t[[2L]], has_assign, TRUE)) else (t[[1L]] == "name" && t[[2L]] == s_assign)

statement <- function(ln) {
  if (any(vapply(ln, has_assign, TRUE))) {
    k <- position(function(t) name_is(t, s_assign), ln)
    if (is.null(k)) parse_err("assertion failed")
    hd <- ln[seq_len(k - 1L)]; body <- ln[-seq_len(k)]
    names <- unlist(lapply(hd, function(t) if (t[[1L]] == "name") t[[2L]] else NULL))
    if (length(hd) == 0L || length(names) != length(hd)) parse_err(paste0("bad definition head ", hs_show_list_str(as.list(names))))
    list("SDef", names[1L], as.list(names[-1L]), parse_seq(body))
  } else if (length(ln) >= 3L && name_is(ln[[2L]], s_colon)) {
    if (ln[[1L]][[1L]] == "name") list("SDecl", ln[[1L]][[2L]], parse_type_seq(ln[-(1:2)])) else parse_err("assertion failed")
  } else list("SFact", parse_seq(ln))
}
parse_statements <- function(text) lapply(logical_lines(lex_spec(text)), statement)

# ---------------------------------------------------------------- erasure to the runtime (de Bruijn) term
CV_ <- function(k) list("CV", k); CL_ <- function(b) list("CL", b); CA_ <- function(f, x) list("CA", f, x); CG_ <- function(g) list("CG", g)
g_false <- CG_("⊥"); g_true <- CG_("⊤"); g_cons <- CG_("∷"); g_nil <- CG_("⊘"); g_pair <- CG_("⊗")

# a numeral's digits (a string of 0 and 1, most significant first) as a literal Core node: the list of the Booleans, least significant first.  A node of its own, not a chain of
# applications, so that nothing recurses along a long numeral (R stops recursing after a few hundred levels of a function this size).
int_ast <- function(s) list("CD", rev(utf8ToInt(s) - 48L))
# the reader's expansion of a numeral: the pair (digits, denominator), digits LSB first
num_ast <- function(s) {
  pair <- function(a, b) CA_(CA_(g_pair, a), b)
  k <- regexpr(".", s, fixed = TRUE)[1L]
  if (k < 0L) pair(int_ast(s), int_ast("1"))
  else {
    x <- substr(s, 1L, k - 1L); y <- substr(s, k + 1L, nchar(s))
    bits <- paste0(x, y)
    if (bits == "") parse_err("empty numeral")
    pair(int_ast(bits), int_ast(paste0("1", strrep("0", nchar(y)))))
  }
}

# scope: the binders in scope, a character vector, innermost FIRST
erase <- function(scope, t) switch(t[[1L]],
  TNum = num_ast(t[[2L]]),
  TChr = num_ast(int_numeral_text(t[[2L]])),
  TStr = list("CT", str_cps(t[[2L]])),
  TVar = { idx <- match(t[[2L]], scope); if (is.na(idx)) CG_(t[[2L]]) else CV_(idx) },
  TApp = { acc <- erase(scope, t[[2L]]); for (a in t[[3L]]) acc <- CA_(acc, erase(scope, a)); acc },
  TLam = {
    ps <- t[[2L]]; scope2 <- scope
    for (p in ps) scope2 <- c(p[[1L]], scope2)
    body <- erase(scope2, t[[3L]])
    for (i in seq_along(ps)) body <- CL_(body)
    body
  },
  TAsc = erase(scope, t[[2L]]),
  TQuote = erase(scope, t[[2L]]))

erase_def <- function(name, params, body) {
  scope <- character(0); for (n in params) scope <- c(n, scope)
  c0 <- erase(scope, body)
  for (i in seq_along(params)) c0 <- CL_(c0)
  list(name, c0)
}

# ---------------------------------------------------------------- pretty printer (spec text)
pp_type <- function(t) switch(t[[1L]], V = t[[2L]], F = "⊥",
  K = { n <- t[[2L]]; args <- t[[3L]]
    if (n == s_arrow && length(args) == 2L) paste0("(→ ", pp_type(args[[1L]]), " ", pp_type(args[[2L]]), ")")
    else if (length(args) == 0L) n else paste0("(", n, " ", paste(vapply(args, pp_type, ""), collapse = " "), ")") })
esc_with <- function(s, q) {
  cps <- str_cps(s); out <- character(length(cps))
  for (i in seq_along(cps)) { c <- cps[i]; out[i] <- if (c == 92L) "\\\\" else if (c == 10L) "\\n" else if (c == q) paste0("\\", intToUtf8(c)) else cp_string(c) }
  paste(out, collapse = "")
}
pp_term <- function(t) switch(t[[1L]],
  TNum = t[[2L]],
  TChr = paste0("'", esc_with(cp_string(t[[2L]]), 39L), "'"),
  TStr = paste0("\"", esc_with(t[[2L]], 34L), "\""),
  TVar = t[[2L]],
  TApp = paste0("(", paste(c(pp_term(t[[2L]]), vapply(t[[3L]], pp_term, "")), collapse = " "), ")"),
  TLam = {
    p <- vapply(t[[2L]], function(e) if (!is.null(e[[2L]])) paste0(e[[1L]], " ∶ ", pp_type(e[[2L]])) else e[[1L]], "")
    paste0("(", paste(p, collapse = " "), " ↦ ", pp_term(t[[3L]]), ")")
  },
  TAsc = pp_term(t[[2L]]), TQuote = pp_term(t[[2L]]))
pp_statement <- function(s) switch(s[[1L]],
  SDef = paste0(paste(c(s[[2L]], unlist(s[[3L]])), collapse = " "), " ≔ ", pp_term(s[[4L]])),
  SDecl = paste0(s[[2L]], " ∶ ", pp_type(s[[3L]])),
  SFact = pp_term(s[[2L]]))

# ---------------------------------------------------------------- Python repr of the tuple form of a term (for error messages)
tuple_of <- function(xs) if (length(xs) == 0L) "()" else if (length(xs) == 1L) paste0("(", xs[[1L]], ",)") else paste0("(", paste(xs, collapse = ", "), ")")
repr_ty <- function(t) switch(t[[1L]],
  V = sprintf("('V', %s)", py_repr(t[[2L]])), F = "('F', '⊥')",
  K = sprintf("('K', %s, %s)", py_repr(t[[2L]]), tuple_of(lapply(t[[3L]], repr_ty))))
repr_term <- function(t) {
  tup <- function(xs) paste0("(", paste(xs, collapse = ", "), ")")
  switch(t[[1L]],
    TNum = tup(c("'num'", py_repr(t[[2L]]))), TChr = tup(c("'chr'", as.character(t[[2L]]))), TStr = tup(c("'str'", py_repr(t[[2L]]))), TVar = tup(c("'var'", py_repr(t[[2L]]))),
    TApp = tup(c("'app'", repr_term(t[[2L]]), paste0("[", paste(vapply(t[[3L]], repr_term, ""), collapse = ", "), "]"))),
    TLam = tup(c("'lam'", paste0("[", paste(vapply(t[[2L]], function(e) tup(c(py_repr(e[[1L]]), if (!is.null(e[[2L]])) repr_ty(e[[2L]]) else "None")), ""), collapse = ", "), "]"), repr_term(t[[3L]]))),
    TAsc = tup(c("'asc'", repr_term(t[[2L]]), repr_ty(t[[3L]]))),
    TQuote = tup(c("'quote'", repr_term(t[[2L]]))))
}
