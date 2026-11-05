# hum.R -- the HUMAN notation of i-1 and doc 2 (port of schimo/src/hum.rkt).
# doc 2 line   <hum symbol> := <rhs> | <rhs> | ...  ; <role>          (⍝ starts a comment)
#   rhs   a spec symbol, or a bin symbol (a numeral such as 11, or .B.)
#   role  class | value | literal | infixl P | infixr P | infix P | prefix P
# human statements (one per logical line):  name in Class := expr | name in Class | name(x, y) in A -> B -> C := expr | A subseteq B

# ---------------------------------------------------------------- doc 2.  entry: list(hum, rhs (character vector), role, prec (integer or NULL)); doc2: list(entries, by_hum)
doc2_make <- function(entries) {
  h <- new.env(hash = TRUE, parent = emptyenv())
  for (e in entries) { cur <- getk(h, e[[1L]]); assign(e[[1L]], c(cur, list(e)), envir = h) }
  list(entries, h)
}
num_or_null <- function(s) { v <- suppressWarnings(as.numeric(s)); if (is.na(v) || v != floor(v)) NULL else as.integer(v) }
doc2_parse <- function(text) {
  acc <- list()
  for (ln0 in split_on(text, "\n")) {
    ln1 <- strip(ln0)
    if (ln1 == "" || starts_with(ln1, "⍝")) next
    k0 <- find_sub(ln1, " ⍝ "); ln <- if (!is.null(k0)) substr(ln1, 1L, k0 - 1L) else ln1
    k <- find_sub(ln, " := ")
    if (is.null(k)) parse_err(sprintf("doc2: bad line %s", py_repr(ln)))
    hd <- substr(ln, 1L, k - 1L); rest <- substr(ln, k + 4L, nchar(ln))
    j <- rfind_sub(rest, " ; ")
    rhs <- if (!is.null(j)) substr(rest, 1L, j - 1L) else ""
    role <- split_ws(if (!is.null(j)) substr(rest, j + 3L, nchar(rest)) else rest)
    if (length(role) == 0L) parse_err("Prelude.head: empty list")
    acc[[length(acc) + 1L]] <- list(strip(hd), vapply(split_on(rhs, " | "), strip, ""), role[1L], if (length(role) > 1L) num_or_null(role[2L]) else NULL)
  }
  doc2_make(acc)
}
# the first entry for a human symbol that has one of the roles
doc2_find <- function(d, hum, roles) {
  es <- getk(d[[2L]], hum)
  for (e in es) if (e[[3L]] %in% roles) return(e)
  NULL
}
all_bin_chars <- function(s) grepl("^[01.]*$", s)
# key -> [spec symbols]  (bin-literal right-hand sides are handled by the reader, not listed here)
overload_table <- function(d) {
  m <- new.env(hash = TRUE, parent = emptyenv())
  for (e in d[[1L]]) {
    if (!(e[[3L]] %in% c("class", "literal", "syntax"))) {
      key <- if (e[[3L]] == "prefix") paste0("hum:prefix ", e[[1L]]) else paste0("hum:", e[[1L]])
      assign(key, Filter(function(x) !(x != "" && all_bin_chars(x)), e[[2L]]), envir = m)
    }
  }
  m
}
# a bin symbol on the right of doc 2 means the spec symbol that doc 1 gives that code to
doc2_remap <- function(d, d1) {
  doc2_make(lapply(d[[1L]], function(e) {
    rhs <- vapply(e[[2L]], function(x) if (bin_sym(x)) { r <- getk(d1$b2s, x); if (is.null(r)) x else r } else x, "")
    list(e[[1L]], unname(rhs), e[[3L]], e[[4L]])
  }))
}

# ---------------------------------------------------------------- lexer.  Tokens: list("num", s) list("str", s) list("chr", c) list("id", s) list("op", s)
show_tok <- function(t) switch(t[[1L]], num = sprintf("('NUM', %s)", py_repr(t[[2L]])), str = sprintf("('STR', %s)", py_repr(t[[2L]])), chr = sprintf("('CHR', %d)", t[[2L]]),
  id = sprintf("('ID', %s)", py_repr(t[[2L]])), op = sprintf("('OP', %s)", py_repr(t[[2L]])))
is_digit <- function(c) c >= 48L && c <= 57L
is_letter <- function(c) (c >= 97L && c <= 122L) || (c >= 65L && c <= 90L)

# the body of a quoted literal: any character but the quote and the backslash, or a backslash and any character but a newline;
# returns list(body code points with their backslashes, index after the closing quote) or NULL
quoted <- function(cs, start, q) {
  n <- length(cs); out <- integer(0); i <- start
  while (i <= n) {
    x <- cs[i]
    if (x == q) return(list(out, i + 1L))
    if (x == 92L) {
      if (i + 1L <= n && cs[i + 1L] != 10L) { out <- c(out, 92L, cs[i + 1L]); i <- i + 2L } else return(NULL)
    } else { out <- c(out, x); i <- i + 1L }
  }
  NULL
}
unescape <- function(s) {                           # s: code points
  n <- length(s); out <- integer(0); i <- 1L
  while (i <= n) {
    if (s[i] == 92L && i + 1L <= n) { y <- s[i + 1L]; out <- c(out, if (y == 110L) 10L else if (y == 116L) 9L else y); i <- i + 2L }
    else { out <- c(out, s[i]); i <- i + 1L }
  }
  out
}
two_char_ops <- list(utf8ToInt(":="), utf8ToInt("|->"), utf8ToInt("->"), utf8ToInt("=="), utf8ToInt("!="), utf8ToInt("++"))
single_ops <- utf8ToInt("-+*/^(),[]")

lex_hum <- function(line0) {
  cs <- str_cps(line0); n <- length(cs)
  while (n > 0L && ws_char(cs[n])) n <- n - 1L
  cs <- cs[seq_len(n)]
  toks <- list(); i <- 1L
  while (TRUE) {
    while (i <= n && ws_char(cs[i])) i <- i + 1L
    if (i > n) return(toks)
    c <- cs[i]; tok <- NULL; nexti <- NA_integer_
    if (is_digit(c)) {
      j <- i; while (j <= n && is_digit(cs[j])) j <- j + 1L
      ip <- cps_str(cs[i:(j - 1L)])
      if (j + 1L <= n && cs[j] == 46L && is_digit(cs[j + 1L])) {
        k <- j + 1L; while (k <= n && is_digit(cs[k])) k <- k + 1L
        tok <- list("num", paste0(ip, ".", cps_str(cs[(j + 1L):(k - 1L)]))); nexti <- k
      } else { tok <- list("num", ip); nexti <- j }
    } else {
      stage <- 1L                                   # 1 string, 2 char, 3 backslash, 4 identifier, 5 operator: each stage falls through to the next
      repeat {
        if (stage == 1L) {
          if (c == 34L) { q <- quoted(cs, i + 1L, 34L); if (!is.null(q)) { tok <- list("str", cps_str(unescape(q[[1L]]))); nexti <- q[[2L]]; break } }
          stage <- 2L
        } else if (stage == 2L) {
          if (c == 39L) { q <- quoted(cs, i + 1L, 39L); if (!is.null(q)) { u <- unescape(q[[1L]]); if (length(u) == 1L) { tok <- list("chr", u); nexti <- q[[2L]]; break } } }
          stage <- 3L
        } else if (stage == 3L) {
          if (c == 92L) { j <- i + 1L; while (j <= n && is_letter(cs[j])) j <- j + 1L; if (j > i + 1L) { tok <- list("id", paste0("\\", cps_str(cs[(i + 1L):(j - 1L)]))); nexti <- j; break } }
          stage <- 4L
        } else if (stage == 4L) {
          if (is_letter(c) || c == 95L) {
            j <- i; while (j <= n && (is_letter(cs[j]) || cs[j] == 95L || is_digit(cs[j]))) j <- j + 1L
            tok <- list("id", cps_str(cs[i:(j - 1L)])); nexti <- j; break
          }
          stage <- 5L
        } else {
          rest <- cs[i:min(n, i + 2L)]; found <- NULL
          for (o in two_char_ops) if (length(rest) >= length(o) && all(rest[seq_along(o)] == o)) { found <- o; break }
          if (!is.null(found)) { tok <- list("op", cps_str(found)); nexti <- i + length(found); break }
          if (c %in% single_ops) { tok <- list("op", intToUtf8(c)); nexti <- i + 1L; break }
          parse_err(sprintf("human notation: cannot read %s", py_repr_cps(cs[i:min(n, i + 11L)])))
        }
      }
    }
    toks[[length(toks) + 1L]] <- tok; i <- nexti
  }
}

# a logical line ends at a newline outside parentheses; `--` starts a comment
hum_logical_lines <- function(text) {
  out <- character(0); cur <- character(0); depth <- 0L
  count <- function(cps, ch) sum(cps == ch)
  flush <- function() { s <- strip(paste(cur, collapse = "")); if (s != "") out[[length(out) + 1L]] <<- s; cur <<- character(0) }
  for (ln0 in split_on(text, "\n")) {
    ln <- if (contains_sub(ln0, "--") && !contains_sub(ln0, "\"")) substr(ln0, 1L, find_sub(ln0, "--") - 1L) else ln0
    cur <- c(cur, " ", ln)
    cps <- str_cps(ln)
    depth <- depth + (count(cps, 40L) - count(cps, 41L)) + (count(cps, 91L) - count(cps, 93L))
    if (depth <= 0L) { flush(); depth <- 0L }
  }
  flush()
  out
}

# ---------------------------------------------------------------- parser.  h: list(doc, infix (env op -> list(prec, kind)), prefix (env op -> prec)).  Every parser takes (ts, i) and returns list(value, next i).
mk_hum <- function(d) {
  infix <- new.env(hash = TRUE, parent = emptyenv()); prefix <- new.env(hash = TRUE, parent = emptyenv())
  for (e in d[[1L]]) {
    if (e[[3L]] %in% c("infixl", "infixr", "infix")) assign(e[[1L]], list(if (is.null(e[[4L]])) 0L else e[[4L]], e[[3L]]), envir = infix)
    if (e[[3L]] == "prefix") assign(e[[1L]], if (is.null(e[[4L]])) 0L else e[[4L]], envir = prefix)
  }
  list(d, infix, prefix)
}
oob <- function() parse_err("list index out of range")
is_op <- function(t, o) t[[1L]] == "op" && t[[2L]] == o
app_ <- function(f, xs) list("TApp", list("TVar", f), xs)
var_ <- function(n) list("TVar", n)

# classes
class_atom <- function(h, ts, i) {
  if (i > length(ts)) oob()
  t <- ts[[i]]
  if (is_op(t, "(")) {
    r <- class_expr(h, ts, i + 1L)
    if (r[[2L]] <= length(ts) && is_op(ts[[r[[2L]]]], ")")) return(list(r[[1L]], r[[2L]] + 1L)) else parse_err("missing )")
  }
  if (t[[1L]] == "id") {
    n <- t[[2L]]; e <- doc2_find(h[[1L]], n, "class")
    if (is.null(e)) parse_err(sprintf("%s is not a class in doc 2", n))
    name <- e[[2L]][1L]
    if (class_var(name)) return(list(V_(name), i + 1L))
    if (i + 1L <= length(ts) && is_op(ts[[i + 1L]], "(")) { r <- class_args(h, ts, i + 2L); return(list(K_(name, r[[1L]]), r[[2L]])) }
    return(list(K_(name), i + 1L))
  }
  parse_err(paste0("class expected, found ", show_tok(t)))
}
class_args <- function(h, ts, i) {
  out <- list()
  repeat {
    r <- class_expr(h, ts, i); out[[length(out) + 1L]] <- r[[1L]]; i <- r[[2L]]
    if (i > length(ts)) oob()
    if (is_op(ts[[i]], ",")) i <- i + 1L
    else if (is_op(ts[[i]], ")")) return(list(out, i + 1L))
    else parse_err("missing ) in class")
  }
}
class_expr <- function(h, ts, i) {
  l <- class_atom(h, ts, i); j <- l[[2L]]
  if (j <= length(ts) && is_op(ts[[j]], "->")) { r <- class_expr(h, ts, j + 1L); list(K_(s_arrow, list(l[[1L]], r[[1L]])), r[[2L]]) } else l
}

# terms
number_term <- function(text) {
  k <- regexpr(".", text, fixed = TRUE)[1L]
  if (k < 0L) list("TNum", big_numeral_text(bz_dec(text)))
  else {
    a <- substr(text, 1L, k - 1L); b <- substr(text, k + 1L, nchar(text))
    app_("hum:/", list(list("TNum", big_numeral_text(bz_dec(paste0(a, b)))), list("TNum", big_numeral_text(as.bigz(10)^nchar(b)))))
  }
}
op_key <- function(t) if (t[[1L]] == "op" || t[[1L]] == "id") t[[2L]] else NULL

hum_atom <- function(h, ts, i, scope) {
  if (i > length(ts)) oob()
  t <- ts[[i]]; k <- t[[1L]]
  if (k == "num") return(list(number_term(t[[2L]]), i + 1L))
  if (k == "str") return(list(list("TStr", t[[2L]]), i + 1L))
  if (k == "chr") return(list(list("TChr", t[[2L]]), i + 1L))
  if (is_op(t, "[")) {
    j <- i + 1L
    if (j <= length(ts) && is_op(ts[[j]], "]")) items <- list() else { r <- list_items(h, ts, j, scope); items <- r[[1L]]; j <- r[[2L]] }
    if (j > length(ts)) oob()
    if (is_op(ts[[j]], "]")) {
      e <- var_("hum:nil")
      for (a in rev(items)) e <- app_("hum:cons", list(a, e))
      return(list(e, j + 1L))
    }
    parse_err("missing ] in list")
  }
  if (is_op(t, "(")) {
    r <- hum_expr(h, ts, i + 1L, 0L, scope); e <- r[[1L]]; j <- r[[2L]]
    if (j > length(ts)) oob()
    if (ts[[j]][[1L]] == "id" && ts[[j]][[2L]] == "in") {
      c <- class_expr(h, ts, j + 1L); j3 <- c[[2L]]
      if (j3 > length(ts)) oob()
      if (is_op(ts[[j3]], ")")) return(list(list("TAsc", e, c[[1L]]), j3 + 1L))
      parse_err("missing )")
    }
    if (is_op(ts[[j]], ")")) return(list(e, j + 1L))
    parse_err("missing )")
  }
  if (k == "id") {
    name <- t[[2L]]; rj <- i + 1L
    starts_paren <- rj <= length(ts) && is_op(ts[[rj]], "(")
    lit <- if (!(name %in% scope) && !starts_paren) doc2_find(h[[1L]], name, "literal") else NULL
    if (!is.null(lit)) return(list(list("TNum", lit[[2L]][1L]), rj))
    hd <- if ((name %in% scope) || is.null(doc2_find(h[[1L]], name, "value"))) var_(name) else var_(paste0("hum:", name))
    if (starts_paren) {
      if (rj + 1L <= length(ts) && is_op(ts[[rj + 1L]], ")")) return(list(list("TApp", hd, list()), rj + 2L))
      r <- call_args(h, ts, rj + 1L, scope); return(list(list("TApp", hd, r[[1L]]), r[[2L]]))
    }
    return(list(hd, rj))
  }
  parse_err(paste0("unexpected ", show_tok(t)))
}
list_items <- function(h, ts, i, scope) {
  out <- list()
  repeat {
    r <- hum_expr(h, ts, i, 0L, scope); out[[length(out) + 1L]] <- r[[1L]]; i <- r[[2L]]
    if (i <= length(ts) && is_op(ts[[i]], ",")) i <- i + 1L else return(list(out, i))
  }
}
call_args <- function(h, ts, i, scope) {
  out <- list()
  repeat {
    r <- hum_expr(h, ts, i, 0L, scope); out[[length(out) + 1L]] <- r[[1L]]; i <- r[[2L]]
    if (i > length(ts)) oob()
    if (is_op(ts[[i]], ",")) i <- i + 1L
    else if (is_op(ts[[i]], ")")) return(list(out, i + 1L))
    else parse_err("missing ) in call")
  }
}
hum_expr <- function(h, ts, i, minprec, scope) {
  if (i > length(ts)) oob()
  # lambda:  x in Class |-> body
  if (ts[[i]][[1L]] == "id" && i + 1L <= length(ts) && ts[[i + 1L]][[1L]] == "id" && ts[[i + 1L]][[2L]] == "in") {
    c <- class_expr(h, ts, i + 2L); j <- c[[2L]]
    if (j <= length(ts) && is_op(ts[[j]], "|->")) {
      name <- ts[[i]][[2L]]
      b <- hum_expr(h, ts, j + 1L, 0L, c(scope, name))
      return(list(list("TLam", list(list(name, c[[1L]])), b[[1L]]), b[[2L]]))
    }
  }
  t0 <- ts[[i]]; key <- op_key(t0)
  pre <- if (!is.null(key)) getk(h[[3L]], key) else NULL
  if (!is.null(pre) && !(t0[[1L]] == "id" && key %in% scope)) {
    r <- hum_expr(h, ts, i + 1L, pre, scope)
    left <- app_(paste0("hum:prefix ", key), list(r[[1L]])); j <- r[[2L]]
  } else { r <- hum_atom(h, ts, i, scope); left <- r[[1L]]; j <- r[[2L]] }
  repeat {
    op <- if (j <= length(ts)) op_key(ts[[j]]) else NULL
    info <- if (!is.null(op)) getk(h[[2L]], op) else NULL
    if (!is.null(info) && info[[1L]] >= minprec) {
      r <- hum_expr(h, ts, j + 1L, if (info[[2L]] == "infixr") info[[1L]] else info[[1L]] + 1L, scope)
      left <- app_(paste0("hum:", op), list(left, r[[1L]])); j <- r[[2L]]
    } else return(list(left, j))
  }
}

# statements
spec_name <- function(h, name) {
  e <- doc2_find(h[[1L]], name, "value")
  if (!is.null(e) && length(e[[2L]]) == 1L && !all_bin_chars(e[[2L]][1L])) e[[2L]][1L] else name
}
type_to_term <- function(t) switch(t[[1L]], V = var_(t[[2L]]),
  K = if (length(t[[3L]]) == 0L) var_(t[[2L]]) else list("TApp", var_(t[[2L]]), lapply(t[[3L]], type_to_term)), F = var_("⊥"))
tok_text <- function(t) if (t[[1L]] == "chr") cp_string(t[[2L]]) else t[[2L]]
param_list <- function(ts, i) {
  out <- character(0)
  repeat {
    if (i > length(ts)) oob()
    if (is_op(ts[[i]], ")")) return(list(out, i + 1L))
    out <- c(out, tok_text(ts[[i]])); i <- i + 1L
    if (i <= length(ts) && is_op(ts[[i]], ",")) i <- i + 1L
  }
}
hum_statement <- function(h, line) {
  ts <- lex_hum(line)
  k <- position(function(t) t[[1L]] == "id" && t[[2L]] == "subseteq", ts)
  if (!is.null(k)) {
    a <- class_expr(h, ts[seq_len(k - 1L)], 1L); b <- class_expr(h, ts[-seq_len(k)], 1L)
    if (!(a[[2L]] > k - 1L && b[[2L]] > length(ts) - k)) parse_err("assertion failed")
    return(list(list("SFact", app_("⊆", list(type_to_term(a[[1L]]), type_to_term(b[[1L]]))))))
  }
  if (length(ts) > 0L && ts[[1L]][[1L]] == "id") {
    name <- ts[[1L]][[2L]]; j <- 2L; params <- character(0)
    if (j <= length(ts) && is_op(ts[[j]], "(")) { r <- param_list(ts, j + 1L); params <- r[[1L]]; j <- r[[2L]] }
    if (j <= length(ts) && ts[[j]][[1L]] == "id" && ts[[j]][[2L]] == "in") {
      c <- class_expr(h, ts, j + 1L); cls <- c[[1L]]; j3 <- c[[2L]]
      if (j3 > length(ts)) {
        if (length(params) > 0L) parse_err(sprintf("%s: a declaration without := takes no parameters (an unknown is a number)", name))
        return(list(list("SDecl", spec_name(h, name), cls)))
      }
      if (is_op(ts[[j3]], ":=")) {
        b <- hum_expr(h, ts, j3 + 1L, 0L, params); sp <- spec_name(h, name)
        if (b[[2L]] <= length(ts)) parse_err(paste0("unexpected ", show_tok(ts[[b[[2L]]]])))
        return(list(list("SDecl", sp, cls), list("SDef", sp, as.list(params), b[[1L]])))
      }
      parse_err("missing :=")
    }
    parse_err(sprintf("declare the class first:  %s in <Class> := …", name))
  }
  parse_err(sprintf("statement must start with a name: %s", py_repr(line)))
}
hum_statements <- function(h, text) {
  out <- list()
  for (l in hum_logical_lines(text)) out <- c(out, hum_statement(h, l))
  out
}
