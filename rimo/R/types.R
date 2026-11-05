# types.R -- the class checker of i-1 (port of schimo/src/types.rkt).
# Rules: every symbol must be DECLARED (name ∶ class) before it is defined or used; classes are terms (atoms and constructors); a symbol may carry several declarations (overloads);
# facts (⊆ A B) subclass, (≣ A B) class equation, (↪ f) f is a canonical (widening) coercion; lambda binders must be annotated; numerals get the smallest class containing their value;
# 'trusted' files (the prelude) have their signatures recorded but their bodies are NOT checked.  A class error is raised as a class_err (the host's own exceptions are host_err).
cerr <- function(s) stop(structure(class = c("class_err", "error", "condition"), list(message = s, call = NULL, msg = s)))

arrow <- "→"
rel_r <- c("≐ᴿ", "≠ᴿ", "≺ᴿ", "⩽ᴿ", "≻ᴿ", "⩾ᴿ")
conn_o <- c("∧Ω", "∨Ω", "¬Ω", "⇒Ω", "⇔Ω")
coercion_cost <- function(name) if (name == "decide") 2L else 1L
domains <- list(list("ℕ", 6L), list("ℤ", 5L), list("ℚ", 3L), list("ℤ[i]", 4L), list("ℚ[i]", 2L), list("ℝ", 1L), list("ℝ[i]", 0L))
prop_ty <- K_("Ω"); bool_ty <- K_("𝔹"); num_ty <- K_("ℚ[i]")
flip <- function(m) if (m == "pos") "neg" else if (m == "neg") "pos" else "eq"

# the key of a class term (for hashing)
tkey <- function(t) switch(t[[1L]], V = paste0("'", t[[2L]]), F = "⊥", K = { a <- t[[3L]]; if (length(a) == 0L) t[[2L]] else paste0(t[[2L]], "(", paste(vapply(a, tkey, ""), collapse = ","), ")") })

# class variable -> class: a named list; insertion keeps the order
subst_get <- function(s, n) s[[n]]
subst_insert <- function(s, n, t) { s[[n]] <- t; s }

chain <- function(t) {
  ps <- list()
  while (t[[1L]] == "K" && t[[2L]] == arrow && length(t[[3L]]) == 2L) { ps[[length(ps) + 1L]] <- t[[3L]][[1L]]; t <- t[[3L]][[2L]] }
  list(ps, t)
}
mk_chain <- function(ps, r) { for (i in rev(seq_along(ps))) r <- K_(arrow, list(ps[[i]], r)); r }

# the same class, where the flexible class ⊥ equals anything
flex_eq <- function(x, y) {
  if (identical(x, y) || x[[1L]] == "F" || y[[1L]] == "F") return(TRUE)
  if (x[[1L]] == "K" && y[[1L]] == "K") {
    xs <- x[[3L]]; ys <- y[[3L]]
    if (x[[2L]] != y[[2L]] || length(xs) != length(ys)) return(FALSE)
    for (i in seq_along(xs)) if (!flex_eq(xs[[i]], ys[[i]])) return(FALSE)
    return(TRUE)
  }
  FALSE
}
has_var <- function(t) switch(t[[1L]], V = TRUE, K = { for (a in t[[3L]]) if (has_var(a)) return(TRUE); FALSE }, FALSE)

# substitute class variables; with flex, the unbound ones become the flexible class ⊥
apply_subst <- function(t, s, flex) switch(t[[1L]],
  V = { r <- s[[t[[2L]]]]; if (!is.null(r)) r else if (flex) F_ else t },
  K = if (length(t[[3L]]) == 0L) t else list("K", t[[2L]], lapply(t[[3L]], function(x) apply_subst(x, s, flex))),
  F_)

comma_sep <- function(xs) paste(xs, collapse = ", ")
semi_sep <- function(xs) paste(xs, collapse = "; ")

# the smallest class containing the value of a numeral written in base i-1
num_class <- function(text) {
  k0 <- regexpr(".", text, fixed = TRUE)[1L]
  bits <- if (k0 > 0L) paste0(substr(text, 1L, k0 - 1L), substr(text, k0 + 1L, nchar(text))) else text
  k <- if (k0 > 0L) nchar(text) - k0 else 0L
  ds <- rev(as.integer(strsplit(bits, "")[[1]]))
  z <- val_digits(ds)
  den <- list(as.bigz(1), as.bigz(0))
  for (i in seq_len(k)) den <- list(-(den[[1]] + den[[2]]), den[[1]] - den[[2]])
  d0 <- den[[1]]; d1 <- den[[2]]
  nn <- d0 * d0 + d1 * d1
  re_num <- z[[1]] * d0 + z[[2]] * d1
  im_num <- z[[2]] * d0 - z[[1]] * d1
  divisible <- function(x) x %% nn == 0
  if (im_num == 0) { if (divisible(re_num)) { if (re_num >= 0) K_("ℕ") else K_("ℤ") } else K_("ℚ") }
  else if (divisible(re_num) && divisible(im_num)) K_("ℤ[i]") else K_("ℚ[i]")
}

# ---------------------------------------------------------------- the checker: an environment
new_checker <- function() {
  c <- new.env(hash = FALSE, parent = emptyenv())
  e <- function() new.env(hash = TRUE, parent = emptyenv())
  c$classes <- e(); c$formers <- e(); c$sigs <- e(); c$facts <- list(); c$fact_idx <- e(); c$eqs <- e(); c$coercions <- character(0); c$cov <- e(); c$defined <- e()
  c$overloads <- e(); c$unknowns <- list(); c$user_defined <- e(); c$raw_taint <- e(); c$taint <- e(); c$has_eqs <- FALSE
  assign("→", 2L, envir = c$classes); assign("𝒦", 0L, envir = c$classes); assign("𝒮", 0L, envir = c$classes)
  for (s in c("𝔏", "𝔖", "𝔗", "𝔓")) assign(s, TRUE, envir = c$cov)
  c
}
copy_env <- function(e) list2env(as.list(e, all.names = TRUE), hash = TRUE, parent = emptyenv())
copy_checker <- function(c) {
  r <- new.env(hash = FALSE, parent = emptyenv())
  for (n in c("classes", "formers", "sigs", "fact_idx", "eqs", "cov", "defined", "overloads", "user_defined", "raw_taint", "taint")) assign(n, copy_env(get(n, envir = c)), envir = r)
  r$facts <- c$facts; r$coercions <- c$coercions; r$unknowns <- c$unknowns; r$has_eqs <- c$has_eqs
  r
}

# ---------------------------------------------------------------- class terms
term_to_type <- function(t) {
  if (t[[1L]] == "TVar") { if (class_var(t[[2L]])) V_(t[[2L]]) else K_(t[[2L]]) }
  else if (t[[1L]] == "TApp" && t[[2L]][[1L]] == "TVar") K_(t[[2L]][[2L]], lapply(t[[3L]], term_to_type))
  else cerr(paste0("not a class expression: ", repr_term(t)))
}

# ---------------------------------------------------------------- classes
norm <- function(c, t) {
  if (t[[1L]] != "K") return(t)
  a <- t[[3L]]
  if (length(a) == 0L) { if (!c$has_eqs) return(t); e <- c$eqs[[t[[2L]]]]; if (is.null(e)) t else norm(c, e) }
  else list("K", t[[2L]], lapply(a, function(x) norm(c, x)))
}
wf <- function(c, t) {
  if (t[[1L]] == "K") {
    name <- t[[2L]]; args <- t[[3L]]; k <- c$classes[[name]]
    if (is.null(k)) cerr(paste0("undeclared class ", name))
    if (k != length(args)) cerr(sprintf("class %s takes %d argument(s), got %d", name, k, length(args)))
    for (a in args) wf(c, a)
  }
  invisible(NULL)
}

leq <- function(c, a, b) {
  seen <- character(0)
  leq_s <- function(a0, b0) {
    a <- norm(c, a0); b <- norm(c, b0)
    if (identical(a, b) || a[[1L]] == "F") return(TRUE)
    s <- FALSE
    if (a[[1L]] == "K" && b[[1L]] == "K") {
      n <- a[[2L]]; xs <- a[[3L]]; ys <- b[[3L]]
      if (n == b[[2L]] && length(xs) > 0L && length(xs) == length(ys)) {
        if (n == arrow) s <- leq_s(ys[[1L]], xs[[1L]]) && leq_s(xs[[2L]], ys[[2L]])
        else if (!is.null(c$cov[[n]])) { s <- TRUE; for (i in seq_along(xs)) if (!leq_s(xs[[i]], ys[[i]])) { s <- FALSE; break } }
        else s <- flex_eq(a, b)
      }
    }
    if (s) return(TRUE)
    ka <- tkey(a); supers <- c$fact_idx[[ka]]
    if (is.null(supers)) return(FALSE)
    for (y in supers) {
      key <- paste0(ka, "\t", tkey(y))
      if (key %in% seen) next
      seen <<- c(seen, key)
      r <- leq_s(y, b)
      seen <<- seen[-length(seen)]
      if (r) return(TRUE)
    }
    FALSE
  }
  leq_s(a, b)
}

# a and every class that contains it, by the declared subclass facts
ups <- function(c, a) {
  todo <- list(norm(c, a)); out <- list()
  while (length(todo) > 0L) {
    x <- todo[[1L]]
    if (any(vapply(out, function(o) identical(o, x), TRUE))) { todo <- todo[-1L]; next }
    supers <- c$fact_idx[[tkey(x)]]
    todo <- c(rev(lapply(supers, function(y) norm(c, y))), todo[-1L])
    out[[length(out) + 1L]] <- x
  }
  out
}
mem_class <- function(x, l) any(vapply(l, function(o) identical(o, x), TRUE))

# the least class containing both a and b (e.g. ℤ[i] and ℚ give ℚ[i]); NULL if there is none or it is not unique
join <- function(c, a0, b0) {
  a <- norm(c, a0); b <- norm(c, b0)
  if (a[[1L]] == "K" && b[[1L]] == "K") {
    n <- a[[2L]]; xs <- a[[3L]]; ys <- b[[3L]]
    if (n == b[[2L]] && !is.null(c$cov[[n]]) && length(xs) > 0L && length(xs) == length(ys)) {
      js <- vector("list", length(xs))
      for (i in seq_along(xs)) {
        j <- if (leq(c, ys[[i]], xs[[i]])) xs[[i]] else if (leq(c, xs[[i]], ys[[i]])) ys[[i]] else join(c, xs[[i]], ys[[i]])
        if (is.null(j)) return(NULL)
        js[[i]] <- j
      }
      return(list("K", n, js))
    }
  }
  ub <- ups(c, b)
  common <- Filter(function(x) mem_class(x, ub), ups(c, a))
  least <- Filter(function(x) !any(vapply(common, function(d) !identical(d, x) && leq(c, d, x), TRUE)), common)
  if (length(least) == 1L) least[[1L]] else NULL
}

# ---------------------------------------------------------------- matching a pattern against an actual class
# returns the new substitution (a list) or NULL
do_match <- function(c, p0, a0, s, mode) {
  p <- norm(c, p0); a <- norm(c, a0)
  if (p[[1L]] == "V") {
    pn <- p[[2L]]; b <- s[[pn]]
    if (is.null(b)) return(subst_insert(s, pn, a))
    if (a[[1L]] == "F") return(s)
    if (b[[1L]] == "F") return(subst_insert(s, pn, a))
    if (mode == "eq") return(if (flex_eq(b, a)) s else NULL)
    if (leq(c, a, b)) return(s)
    if (leq(c, b, a)) return(if (mode == "pos") subst_insert(s, pn, a) else s)
    if (mode == "pos") { j <- join(c, a, b); return(if (!is.null(j)) subst_insert(s, pn, j) else NULL) }
    return(NULL)
  }
  if (!has_var(p)) {
    if (a[[1L]] == "F") return(s)
    ok <- if (mode == "pos") leq(c, a, p) else if (mode == "neg") leq(c, p, a) else flex_eq(p, a)
    return(if (ok) s else NULL)
  }
  if (a[[1L]] == "F") return(s)
  structural <- NULL
  if (p[[1L]] == "K" && a[[1L]] == "K" && p[[2L]] == a[[2L]] && length(p[[3L]]) == length(a[[3L]])) {
    pn <- p[[2L]]; pas <- p[[3L]]; aas <- a[[3L]]; cur <- s; cov <- !is.null(c$cov[[pn]])
    for (i in seq_along(pas)) {
      m <- if (pn == arrow) { if (i == 1L) flip(mode) else mode } else if (cov) mode else "eq"
      cur <- do_match(c, pas[[i]], aas[[i]], cur, m)
      if (is.null(cur)) break
    }
    structural <- cur
  }
  if (!is.null(structural)) return(structural)
  if (mode == "pos") {
    supers <- c$fact_idx[[tkey(a)]]
    for (y in supers) { r <- do_match(c, p, y, s, mode); if (!is.null(r)) return(r) }
  }
  NULL
}

# the domain code of an unknown of class t: the first number class, in the order ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i], that contains t
domain <- function(c, t0) {
  t <- norm(c, t0)
  if (t[[1L]] == "K" && !has_var(t)) for (d in domains) if (!is.null(c$classes[[d[[1L]]]]) && leq(c, t, K_(d[[1L]]))) return(d[[2L]])
  NULL
}
# is `name` an unknown, or a program symbol whose value needs the value of an unknown?
unknownish <- function(c, name) {
  for (u in c$unknowns) if (u[[1L]] == name) return(TRUE)
  b <- c$taint[[name]]
  if (is.null(b)) has_key(c$raw_taint, name) else b
}
# does the (checked) term t mention an unknown (or a symbol that needs one) — outside quoted statements?  bound: a character vector of names
mentions <- function(c, t, bound) switch(t[[1L]],
  TVar = !(t[[2L]] %in% bound) && unknownish(c, t[[2L]]),
  TApp = { if (mentions(c, t[[2L]], bound)) return(TRUE); for (a in t[[3L]]) if (mentions(c, a, bound)) return(TRUE); FALSE },
  TLam = mentions(c, t[[3L]], c(bound, vapply(t[[2L]], function(p) p[[1L]], ""))),
  FALSE)
is_prop <- function(c, t) identical(norm(c, t), prop_ty)

# ---------------------------------------------------------------- declarations and facts
declare <- function(c, name, t) {
  cr <- chain(t); ps <- cr[[1L]]; r <- cr[[2L]]
  if (identical(r, K_("𝒦"))) {
    for (p in ps) if (!identical(p, K_("𝒦"))) cerr(paste0(name, ": a class constructor takes classes only"))
    assign(name, length(ps), envir = c$classes)
  } else if (identical(r, K_("𝒮"))) assign(name, TRUE, envir = c$formers)
  else {
    wf(c, t)
    old <- c$sigs[[name]]
    if (is.null(old)) old <- list()
    if (!mem_class(t, old)) old[[length(old) + 1L]] <- t
    assign(name, old, envir = c$sigs)
  }
}
reindex <- function(c) {
  idx <- new.env(hash = TRUE, parent = emptyenv())
  for (f in c$facts) { k <- tkey(norm(c, f[[1L]])); cur <- idx[[k]]; assign(k, c(if (is.null(cur)) list() else cur, list(f[[2L]])), envir = idx) }
  c$fact_idx <- idx
}
# a declared statement: raises class_err for class errors, host_err for the exceptions of the host
fact <- function(c, term) {
  if (term[[1L]] == "TApp" && term[[2L]][[1L]] == "TVar" && !is.null(c$formers[[term[[2L]][[2L]]]])) {
    h <- term[[2L]][[2L]]; args <- term[[3L]]
    arg <- function(i) if (i <= length(args)) args[[i]] else parse_err("Prelude.!!: index too large")
    if (h == "⊆" || h == "≣") {
      a0 <- arg(1L); b0 <- arg(2L); a <- term_to_type(a0); b <- term_to_type(b0)
      wf(c, a); wf(c, b)
      if (h == "⊆") { c$facts[[length(c$facts) + 1L]] <- list(a, b); reindex(c) }
      else if (a[[1L]] == "K" && length(a[[3L]]) == 0L) { assign(a[[2L]], b, envir = c$eqs); c$has_eqs <- TRUE; reindex(c) }
      else parse_err("class equation: left side must be an atomic class")
    } else if (h == "↗") {
      if (length(args) >= 1L && args[[1L]][[1L]] == "TVar") {
        n <- args[[1L]][[2L]]; k <- c$classes[[n]]
        if (!is.null(k) && k >= 1L) assign(n, TRUE, envir = c$cov) else cerr(sprintf("covariant: %s is not a class constructor", n))
      } else cerr("covariant:  is not a class constructor")
    } else if (h == "↪") {
      if (length(args) >= 1L && args[[1L]][[1L]] == "TVar") {
        f <- args[[1L]][[2L]]
        if (has_key(c$sigs, f)) c$coercions <- c(c$coercions, f) else cerr(sprintf("coercion %s is not declared", f))
      } else cerr("coercion  is not declared")
    } else cerr(paste0("unknown statement ", h))
  } else cerr(paste0("not a declared statement: ", repr_term(term)))
  invisible(NULL)
}

# ---------------------------------------------------------------- terms
# candidate list(symbol, class) pairs for a head symbol
entries_for <- function(c, hd) {
  names <- c$overloads[[hd]]
  if (is.null(names)) names <- hd
  out <- list()
  for (n in names) {
    es <- c$sigs[[n]]
    if (is.null(es)) cerr(paste0("undeclared symbol ", n))
    for (e in es) out[[length(out) + 1L]] <- list(n, e)
  }
  out
}
sigs_of <- function(c, cn) { r <- c$sigs[[cn]]; if (is.null(r)) list() else r }

best_coercion <- function(c, p, a_ty, s) {
  best <- NULL                                     # list(name, class, subst)
  for (cn in c$coercions) for (ce in sigs_of(c, cn)) {
    cr <- chain(ce); cps <- cr[[1L]]; cres <- cr[[2L]]
    if (length(cps) == 1L && leq(c, a_ty, cps[[1L]])) {
      s1 <- do_match(c, p, apply_subst(cres, list(), FALSE), s, "pos")
      if (!is.null(s1)) best <- if (is.null(best)) list(cn, cres, s1) else if (leq(c, cres, best[[2L]])) list(cn, cres, s1) else best
    }
  }
  if (is.null(best)) NULL else list(best[[1L]], best[[3L]])
}

# apply a class `entry` to args (a list of list(class, term)).  -> list(result class, new args, cost) or NULL
try_apply <- function(c, entry, args) {
  t <- entry; s <- list(); cost <- 0L; nw <- vector("list", length(args)); k <- 0L
  for (arg in args) {
    a_ty <- arg[[1L]]; term <- arg[[2L]]
    nt <- norm(c, t)
    if (!(nt[[1L]] == "K" && nt[[2L]] == arrow && length(nt[[3L]]) == 2L)) return(NULL)
    p <- nt[[3L]][[1L]]; r <- nt[[3L]][[2L]]
    s2 <- do_match(c, p, a_ty, s, "pos")
    k <- k + 1L
    if (!is.null(s2)) { s <- s2; nw[[k]] <- term }
    else {
      bc <- best_coercion(c, p, a_ty, s)
      if (is.null(bc)) return(NULL)
      s <- bc[[2L]]; cost <- cost + coercion_cost(bc[[1L]]); nw[[k]] <- list("TApp", var_(bc[[1L]]), list(term))
    }
    t <- r
  }
  list(apply_subst(t, s, TRUE), nw, cost)
}

resolve_app <- function(c, hd, args, label) {
  ents <- entries_for(c, hd)
  cands <- list()
  for (e in ents) { r <- try_apply(c, e[[2L]], args); if (!is.null(r)) cands[[length(cands) + 1L]] <- list(e[[1L]], e[[2L]], r) }
  if (length(cands) == 0L)
    cerr(sprintf("no declaration of %s accepts (%s);  candidates: %s", label, comma_sep(vapply(args, function(a) show_type(a[[1L]]), "")),
                 comma_sep(vapply(ents, function(e) paste0(e[[1L]], " ∶ ", show_type(e[[2L]])), ""))))
  cost_of <- function(cd) cd[[3L]][[3L]]
  mn <- min(vapply(cands, cost_of, 0L))
  cands2 <- Filter(function(cd) cost_of(cd) == mn, cands)
  more_specific <- function(x, y) {
    p1 <- chain(x[[2L]])[[1L]]; p2 <- chain(y[[2L]])[[1L]]
    n <- min(length(args), length(p1), length(p2))
    for (i in seq_len(n)) if (!leq(c, p1[[i]], p2[[i]])) return(FALSE)
    TRUE
  }
  best <- Filter(function(x) all(vapply(cands2, function(y) more_specific(x, y), TRUE)), cands2)
  pool <- if (length(best) == 0L) cands2 else best
  if (length(best) != 1L) {
    keys <- unique(vapply(pool, function(cd) paste0(cd[[1L]], "\t", tkey(cd[[3L]][[1L]])), ""))
    if (length(keys) != 1L)
      cerr(sprintf("ambiguous use of %s: %s", label, semi_sep(vapply(cands2, function(cd) paste0(cd[[1L]], " ∶ ", show_type(cd[[2L]])), ""))))
  }
  cd <- pool[[1L]]
  list(cd[[1L]], cd[[3L]][[1L]], cd[[3L]][[2L]])
}

# the checked application (name new…) of class rt — marked as a quoted statement (class Ω) when it is one
statement_of <- function(c, loc, name, rt, nw) {
  app_t <- list("TApp", var_(name), nw)
  bound <- names(loc); r <- norm(c, rt)
  if (name %in% rel_r && length(nw) == 2L) return(list(prop_ty, list("TQuote", app_t, loc)))
  if (name %in% conn_o && is_prop(c, rt)) return(list(prop_ty, list("TQuote", app_t, loc)))
  if ((identical(r, prop_ty) || identical(r, bool_ty)) && any(vapply(nw, function(a) mentions(c, a, bound), TRUE))) return(list(prop_ty, list("TQuote", app_t, loc)))
  list(rt, app_t)
}

# returns list(class, term)
synth <- function(c, loc, t) {
  switch(t[[1L]],
    TNum = list(num_class(t[[2L]]), t),
    TChr = list(K_("𝕮"), t),
    TStr = list(K_("𝕊"), t),
    TVar = {
      n <- t[[2L]]; ty <- loc[[n]]
      if (!is.null(ty)) list(ty, t)
      else {
        ents <- entries_for(c, n)
        if (length(ents) == 1L) list(apply_subst(ents[[1L]][[2L]], list(), TRUE), var_(ents[[1L]][[1L]]))
        else cerr(sprintf("%s is overloaded (%d declarations): use it applied to arguments", n, length(ents)))
      }
    },
    TAsc = {
      ty <- t[[3L]]; wf(c, ty); r <- synth(c, loc, t[[2L]]); fixed <- fit(c, r[[2L]], r[[1L]], ty)
      if (!is.null(fixed)) list(ty, fixed) else cerr(sprintf("ascription: a term of class %s is not in %s", show_type(r[[1L]]), show_type(ty)))
    },
    TLam = {
      ps <- t[[2L]]; loc2 <- loc; ptys <- list()
      for (p in ps) {
        n <- p[[1L]]; mty <- p[[2L]]
        if (is.null(mty)) cerr(sprintf("binder %s has no class: write (%s ∶ class ↦ …)", n, n))
        wf(c, mty); loc2[[n]] <- mty; ptys[[length(ptys) + 1L]] <- mty
      }
      r <- synth(c, loc2, t[[3L]])
      list(mk_chain(ptys, r[[1L]]), list("TLam", ps, r[[2L]]))
    },
    TQuote = list(prop_ty, t),
    TApp = {
      f <- t[[2L]]; as <- t[[3L]]
      args <- vector("list", length(as))
      for (i in seq_along(as)) args[[i]] <- synth(c, loc, as[[i]])
      if (f[[1L]] == "TVar" && is.null(loc[[f[[2L]]]])) {
        h <- f[[2L]]
        r <- tryCatch(resolve_app(c, h, args, h), class_err = function(e) e)
        if (inherits(r, "class_err")) {
          j <- join_list(c, loc, t)
          if (!is.null(j)) j else stop(r)
        } else statement_of(c, loc, r[[1L]], r[[2L]], r[[3L]])
      } else {
        ft <- synth(c, loc, f)
        res <- try_apply(c, ft[[1L]], args)
        if (!is.null(res)) list(res[[1L]], list("TApp", ft[[2L]], res[[2L]]))
        else cerr(sprintf("cannot apply a function of class %s to (%s)", show_type(ft[[1L]]), comma_sep(vapply(args, function(a) show_type(a[[1L]]), ""))))
      }
    })
}

# a cons chain (a list literal) whose elements are truth values and statements is a list of statements: the truth values are made statements (prop).  NULL when that is not the case.
join_list <- function(c, loc, t) {
  items <- list(); tl <- t
  while (tl[[1L]] == "TApp" && tl[[2L]][[1L]] == "TVar" && (tl[[2L]][[2L]] == "∷" || tl[[2L]][[2L]] == "hum:cons") && length(tl[[3L]]) == 2L && is.null(loc[[tl[[2L]][[2L]]]])) {
    items[[length(items) + 1L]] <- tl[[3L]][[1L]]; tl <- tl[[3L]][[2L]]
  }
  if (length(items) == 0L || !has_key(c$sigs, "∷")) return(NULL)
  el <- lapply(items, function(x) synth(c, loc, x))
  tct <- synth(c, loc, tl); tc <- tct[[1L]]
  list_prop <- K_("𝔏", list(prop_ty))
  if (!(any(vapply(el, function(e) is_prop(c, e[[1L]]), TRUE)) || identical(norm(c, tc), list_prop)) || !leq(c, tc, list_prop)) return(NULL)
  out <- tct[[2L]]
  for (e in rev(el)) {
    cl <- e[[1L]]; x <- e[[2L]]
    if (is_prop(c, cl)) out <- list("TApp", var_("∷"), list(x, out))
    else if (leq(c, cl, bool_ty)) out <- list("TApp", var_("∷"), list(list("TApp", var_("prop"), list(x)), out))
    else return(NULL)
  }
  list(list_prop, out)
}

# term (of class got) made to fit the class want: as it is, through one coercion, element by element for a list or pair literal, or — for a λ — by fitting its body.  NULL when it does not fit.
fit <- function(c, term, got, want) {
  if (leq(c, got, want)) return(term)
  g <- norm(c, got); w <- norm(c, want)
  via <- NULL                                      # through one coercion (the last one that fits wins)
  for (cn in c$coercions) for (ce in sigs_of(c, cn)) {
    cr <- chain(ce); cps <- cr[[1L]]
    if (length(cps) == 1L && leq(c, got, cps[[1L]]) && leq(c, cr[[2L]], want)) via <- list("TApp", var_(cn), list(term))
  }
  if (!is.null(via)) return(via)
  if (identical(term, var_("⊘")) && w[[1L]] == "K" && w[[2L]] == "𝔏") return(term)
  if (term[[1L]] == "TApp" && term[[2L]][[1L]] == "TVar" && length(term[[3L]]) == 2L && g[[1L]] == "K" && w[[1L]] == "K" && g[[2L]] == w[[2L]]) {
    h <- term[[2L]][[2L]]; a0 <- term[[3L]][[1L]]; a1 <- term[[3L]][[2L]]; gargs <- g[[3L]]; wargs <- w[[3L]]
    if (h == "∷" && g[[2L]] == "𝔏") {
      h2 <- fit(c, a0, gargs[[1L]], wargs[[1L]])
      if (!is.null(h2)) { t2 <- fit(c, a1, got, want); if (!is.null(t2)) return(list("TApp", var_("∷"), list(h2, t2))) }
    }
    if (h == "⊗" && g[[2L]] == "𝔓") {
      x <- fit(c, a0, gargs[[1L]], wargs[[1L]])
      if (!is.null(x)) { y <- fit(c, a1, gargs[[2L]], wargs[[2L]]); if (!is.null(y)) return(list("TApp", var_("⊗"), list(x, y))) }
    }
  }
  if (term[[1L]] == "TLam") {
    ps <- term[[2L]]; n <- length(ps)
    cg <- chain(g); pg <- cg[[1L]]; rg <- cg[[2L]]; cw <- chain(w); pw <- cw[[1L]]; rw <- cw[[2L]]
    if (length(pg) >= n && length(pw) >= n) {
      for (i in seq_len(n)) if (!leq(c, pw[[i]], pg[[i]])) return(NULL)
      nb <- fit(c, term[[3L]], mk_chain(pg[-seq_len(n)], rg), mk_chain(pw[-seq_len(n)], rw))
      if (!is.null(nb)) return(list("TLam", ps, nb))
    }
  }
  NULL
}

# after checking: which program symbols need the value of an unknown (the least fixed point over their checked bodies).  defs: a list of list(name, params, body)
settle_taint <- function(c, defs) {
  rm(list = ls(c$taint, all.names = TRUE), envir = c$taint)
  for (d in defs) assign(d[[1L]], FALSE, envir = c$taint)
  repeat {
    changed <- FALSE
    for (d in defs) if (!c$taint[[d[[1L]]]] && mentions(c, d[[3L]], unlist(d[[2L]]))) { assign(d[[1L]], TRUE, envir = c$taint); changed <- TRUE }
    if (!changed) break
  }
}
check_entry <- function(c, name, params, body, entry) {
  cr <- chain(entry); ps <- cr[[1L]]; r <- cr[[2L]]
  if (length(params) > length(ps)) cerr(sprintf("%s has %d parameters but its class %s has only %d", name, length(params), show_type(entry), length(ps)))
  loc <- list()
  for (i in seq_along(params)) loc[[params[[i]]]] <- ps[[i]]
  want <- mk_chain(if (length(params) > 0L) ps[-seq_along(params)] else ps, r)
  gn <- synth(c, loc, body)
  fixed <- fit(c, gn[[2L]], gn[[1L]], want)
  if (is.null(fixed)) cerr(sprintf("%s: the body has class %s but %s was declared", name, show_type(gn[[1L]]), show_type(want)))
  fixed
}

# ---------------------------------------------------------------- statements
# check one statement; the checker keeps the effects it has before an error and the resolved statement is returned (NULL: the statement is as it was written).
check_statement <- function(c, st, trusted) {
  switch(st[[1L]],
    SDecl = {
      name <- st[[2L]]; ty <- st[[3L]]
      declare(c, name, ty)
      uidx <- NULL; for (i in seq_along(c$unknowns)) if (c$unknowns[[i]][[1L]] == name) uidx <- i
      if (!trusted && !is.null(uidx)) {
        if (length(sigs_of(c, name)) > 1L) cerr(sprintf("%s is declared but never defined, so it is an unknown, and an unknown has one class", name))
        k <- domain(c, ty)
        if (is.null(k)) cerr(sprintf("%s is declared but never defined, so it is an unknown; an unknown must be a number (a class below ℕ ℤ ℚ ℤ[i] ℚ[i] ℝ ℝ[i] — human \\NN \\ZZ \\QQ \\Z \\Q \\RR \\CC), not %s", name, show_type(ty)))
        c$unknowns[[uidx]] <- list(c$unknowns[[uidx]][[1L]], k)
      }
      NULL
    },
    SFact = { fact(c, st[[2L]]); NULL },
    SDef = {
      name <- st[[2L]]; params <- st[[3L]]; body <- st[[4L]]
      if (has_key(c$defined, name)) cerr(sprintf("%s is defined twice", name))
      if (!has_key(c$sigs, name)) cerr(sprintf("%s is defined before it is declared:  write  %s ∶ <class>  first", name, name))
      assign(name, TRUE, envir = c$defined)
      if (trusted) NULL
      else {
        entries <- sigs_of(c, name); out <- NULL
        for (entry in entries) {
          newbody <- check_entry(c, name, params, body, entry)
          if (is.null(out)) { assign(name, mentions(c, newbody, unlist(params)), envir = c$taint); out <- list("SDef", name, params, newbody) }
        }
        if (is.null(out)) cerr("no declaration")
        out
      }
    })
}
