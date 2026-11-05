# quote.R -- the compiler side of statements (port of schimo/src/quote.rkt).  A statement — a relation on ℝ[i], a relation or predicate about an unknown, a connective with a statement
# operand (types.R marks them TQuote) — is simplified from DEFINITIONS whenever it is evaluated or output, so its checked term φ is replaced by a term that builds φ's CODE at run time:
#   numeral / Char / String / closed number or Boolean  (𝔮ⁿ value);  symbol  (𝔮ˢ code);  unknown x  (𝔮ˢ code of x);
#   application, λ, bound variable  (𝔮ᵃ f a) (𝔮ˡ b) (𝔮ᵛ k);  a variable bound outside φ of class Ω  its value;  prop b, decide φ, ∧Ω …  transparent
# and the statement becomes  (simplify′ ε⌜⌝ ⌜φ⌝)  where  ε⌜⌝  is one table, for the whole program, of (code, ⌜definition⌝).
unfold <- c("exp", "sin", "cos", "sinh", "cosh", "log", "atan")
env_name <- "ε⌜⌝"
transparent_names <- c("prop", "decide", "code_rd")
conn_real <- c("∧Ω" = "∧", "∨Ω" = "∨", "¬Ω" = "¬", "⇒Ω" = "⇒", "⇔Ω" = "⇔")

digits_term <- function(text) app_("↓ᶻ", list(list("TNum", text)))
nat_term <- function(k) digits_term(numeral(small_digits(k)))

has_quote <- function(t) switch(t[[1L]], TQuote = TRUE, TApp = { if (has_quote(t[[2L]])) return(TRUE); for (a in t[[3L]]) if (has_quote(a)) return(TRUE); FALSE }, TLam = has_quote(t[[3L]]), FALSE)

# sts: a list of list(trusted, statement or NULL).  Returns list(quoter, d1)
mk_quoter <- function(c, sts, d0) {
  q <- new.env(hash = FALSE, parent = emptyenv())
  defs <- new.env(hash = TRUE, parent = emptyenv()); prelude <- new.env(hash = TRUE, parent = emptyenv()); stmt <- new.env(hash = TRUE, parent = emptyenv())
  for (e in sts) {
    st <- e[[2L]]
    if (is.list(st) && st[[1L]] == "SDef") {
      n <- st[[2L]]
      if (!e[[1L]]) {
        l <- c$sigs[[n]]; cls <- if (length(l) > 0L) l[[1L]] else K_("?")
        assign(n, list(st[[3L]], st[[4L]], cls), envir = defs)
      } else if (n %in% unfold) assign(n, list(st[[3L]], st[[4L]]), envir = prelude)
    }
  }
  unknowns <- Filter(function(u) !is.null(u[[2L]]), c$unknowns)
  d1 <- copy_doc1(d0)
  for (u in unknowns) doc1_code(d1, u[[1L]], TRUE)
  for (n in ls(defs, all.names = TRUE)) if (has_quote(get(n, envir = defs)[[2L]])) assign(n, TRUE, envir = stmt)
  q$c <- c; q$defs <- defs; q$prelude <- prelude; q$unknowns <- unknowns; q$stmt <- stmt
  list(q, d1)
}

q_code <- function(st, name) {
  real <- if (name %in% names(conn_real)) conn_real[[name]] else name
  b <- doc1_code(st$doc, real, TRUE)
  digits_term(substr(b, 2L, nchar(b) - 1L))
}
need <- function(q, st, name) {
  if ((has_key(q$defs, name) || has_key(q$prelude, name) || any(vapply(q$unknowns, function(u) u[[1L]] == name, TRUE))) && !(name %in% st$needed)) st$needed <- c(st$needed, name)
}
value_class <- function(q, c0) {
  if (is.null(c0)) return(FALSE)
  c <- norm(q$c, c0)
  c[[1L]] == "K" && (identical(c, bool_ty) || leq(q$c, c, num_ty))
}
has_rel <- function(q, t) switch(t[[1L]],
  TQuote = TRUE,
  TVar = (t[[2L]] %in% rel_r) || (t[[2L]] %in% conn_o) || has_key(q$stmt, t[[2L]]),
  TApp = { if (has_rel(q, t[[2L]])) return(TRUE); for (a in t[[3L]]) if (has_rel(q, a)) return(TRUE); FALSE },
  TLam = has_rel(q, t[[3L]]),
  FALSE)
free_in <- function(t, names) switch(t[[1L]],
  TVar = t[[2L]] %in% names,
  TApp = { if (free_in(t[[2L]], names)) return(TRUE); for (a in t[[3L]]) if (free_in(a, names)) return(TRUE); FALSE },
  TLam = free_in(t[[3L]], setdiff(names, vapply(t[[2L]], function(p) p[[1L]], ""))),
  TQuote = free_in(t[[2L]], names),
  FALSE)

# the code of a term.  ib: binders inside the quote (innermost last) as list(name, class or NULL); outer: classes of variables bound outside (a named list); typed: Boolean
q_term <- function(q, st, t, ib, outer, typed) {
  names <- vapply(ib, function(b) b[[1L]], "")
  switch(t[[1L]],
    TQuote = q_term(q, st, t[[2L]], ib, outer, typed),
    TNum = app_("𝔮ⁿ", list(t)), TChr = app_("𝔮ⁿ", list(t)), TStr = app_("𝔮ⁿ", list(t)),
    TVar = {
      n <- t[[2L]]; idx <- rposition(function(m) m == n, as.list(names))
      oc <- outer[[n]]
      if (!is.null(idx)) app_("𝔮ᵛ", list(nat_term(length(names) - idx + 1L)))
      else if (!is.null(oc)) {
        if (value_class(q, oc)) app_("𝔮ⁿ", list(t))
        else if (is_prop(q$c, oc)) app_("code_rd", list(t))
        else { pos <- match(n, names(outer)) - 1L; if (is.na(pos)) pos <- 0L; app_("𝔮ᵛ", list(nat_term(length(names) + 1L + pos))) }
      }
      else if (any(vapply(q$unknowns, function(u) u[[1L]] == n, TRUE))) { need(q, st, n); app_("𝔮ˢ", list(q_code(st, n))) }
      else if (typed && !has_key(q$defs, n) && has_key(q$c$sigs, n) && all(vapply(q$c$sigs[[n]], function(s) value_class(q, s), TRUE))) app_("𝔮ⁿ", list(t))
      else {
        d <- getk(q$defs, n)
        if (!is.null(d) && value_class(q, d[[3L]]) && !has_key(q$stmt, n) && !unknownish(q$c, n)) app_("𝔮ⁿ", list(t))
        else { need(q, st, n); app_("𝔮ˢ", list(q_code(st, n))) }
      }
    },
    TApp = {
      f <- t[[2L]]; args <- t[[3L]]
      if (typed && f[[1L]] == "TVar" && f[[2L]] %in% transparent_names && !(f[[2L]] %in% names) && is.null(outer[[f[[2L]]]]) && length(args) == 1L)
        return(q_term(q, st, args[[1L]], ib, outer, typed))
      if (typed && !has_rel(q, t) && !free_in(t, names)) {
        both <- union(names(outer), names)
        if (!mentions(q$c, t, both)) {
          loc <- outer
          for (b in ib) loc[[b[[1L]]]] <- if (!is.null(b[[2L]])) b[[2L]] else F_
          klass <- tryCatch(synth(q$c, loc, t)[[1L]], class_err = function(e) NULL)
          if (value_class(q, klass)) return(app_("𝔮ⁿ", list(t)))
        }
      }
      out <- q_term(q, st, f, ib, outer, typed)
      for (a in args) { qa <- q_term(q, st, a, ib, outer, typed); out <- app_("𝔮ᵃ", list(out, qa)) }
      out
    },
    TLam = {
      ps <- t[[2L]]; inner <- c(ib, ps)
      o <- q_term(q, st, t[[3L]], inner, outer, typed)
      for (p in ps) o <- app_("𝔮ˡ", list(o))
      o
    },
    TAsc = parse_err("a statement cannot be written as a code: asc"))
}

definition_code <- function(q, st, name) {
  ui <- NULL; for (i in seq_along(q$unknowns)) if (q$unknowns[[i]][[1L]] == name) ui <- i
  if (!is.null(ui)) {
    u <- q$unknowns[[ui]]; cd <- q_code(st, "𝔲"); kn <- numeral(small_digits(u[[2L]]))
    return(app_("𝔮ᵃ", list(app_("𝔮ˢ", list(cd)), app_("𝔮ⁿ", list(list("TNum", kn))))))
  }
  d <- getk(q$defs, name)
  if (!is.null(d)) {
    params <- d[[1L]]; body <- d[[2L]]; cl <- d[[3L]]; ps <- list()
    for (p in params) {
      n <- norm(q$c, cl)
      if (n[[1L]] == "K" && length(n[[3L]]) == 2L) { ps[[length(ps) + 1L]] <- list(p, n[[3L]][[1L]]); cl <- n[[3L]][[2L]] }
      else { ps[[length(ps) + 1L]] <- list(p, NULL); cl <- F_ }
    }
    out <- q_term(q, st, body, ps, list(), TRUE)
    for (p in params) out <- app_("𝔮ˡ", list(out))
    return(out)
  }
  d <- getk(q$prelude, name)
  if (!is.null(d)) {
    params <- d[[1L]]; ps <- lapply(params, function(p) list(p, NULL))
    out <- q_term(q, st, d[[2L]], ps, list(), FALSE)
    for (p in params) out <- app_("𝔮ˡ", list(out))
    return(out)
  }
  parse_err(sprintf("no definition for %s to write as a code", name))
}

# replace every statement φ by  simplify′ ε⌜⌝ ⌜φ⌝
quote_replace <- function(q, st, t) switch(t[[1L]],
  TQuote = app_("simplify′", list(var_(env_name), q_term(q, st, t[[2L]], list(), t[[3L]], TRUE))),
  TApp = list("TApp", quote_replace(q, st, t[[2L]]), lapply(t[[3L]], function(a) quote_replace(q, st, a))),
  TLam = list("TLam", t[[2L]], quote_replace(q, st, t[[3L]])),
  t)

# the one table of definitions for the whole program
quote_table <- function(q, st) {
  entries <- list(); k <- 1L
  while (k <= length(st$needed)) {
    name <- st$needed[k]; cd <- q_code(st, name); dc <- definition_code(q, st, name)
    entries[[length(entries) + 1L]] <- list(name, app_("⊗", list(cd, dc))); k <- k + 1L
  }
  unk_names <- vapply(q$unknowns, function(u) u[[1L]], "")
  first_part <- list(); rest <- list()
  for (e in entries) { i <- match(e[[1L]], unk_names); if (!is.na(i)) first_part[[length(first_part) + 1L]] <- list(i, e[[2L]]) else rest[[length(rest) + 1L]] <- e[[2L]] }
  if (length(first_part) > 1L) first_part <- first_part[order(vapply(first_part, function(x) x[[1L]], 0L))]
  items <- c(lapply(first_part, function(x) x[[2L]]), rest)
  out <- var_("⊘")
  for (e in rev(items)) out <- app_("∷", list(e, out))
  out
}
