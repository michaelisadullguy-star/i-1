# core.R -- the lazy evaluator of i-1 (port of schimo/src/core.rkt).
# A definition is an untyped lambda term in de Bruijn form.  Evaluation is call-by-need, on an explicit stack, so that the depth of a computation is limited by memory:
# every term is compiled once to code with FLAT closures (a lambda captures exactly the variables it uses, a delayed argument too; a frame is the captured values followed by the
# arguments of the call); a chain of applications is one call, a chain of lambdas one lambda of arity n; every closed application is evaluated at most once; the decoders apply a
# language value to builder constants of the host (markers, list and pair builders, ...) and read what comes back.
#
# values (WHNF):  list(1, th) a function | VT VF VNIL | list(5, h, t) a cons cell | list(6, a, b) a pair | list(7, k) a small integer | list(8, x) .. list(12, x) codes
# thunks: environments with a state  st:  list(1, v) done | list(2, info, caps) delayed | list(3, info, caps) closure | list(4, base, held) partial application | list(5, idx) lazy global
#         | list(6, p) primitive | list(7) running | list(8, err) failed
# code: list(1, i) var | list(2, th) const | list(3, info) lam | list(4, g, args) call | list(5, i, args) callvar | list(6, spec) pap | list(7, f, args) app    (slots are 1-based)
# arguments: list(1, i) var | list(2, th) const | list(3, info) lam | list(4, info) delay | list(5, spec) pap
S_DONE <- 1L; S_DELAYED <- 2L; S_CLO <- 3L; S_PAP <- 4L; S_LAZY <- 5L; S_PRIM <- 6L; S_RUNNING <- 7L; S_FAIL <- 8L
V_FUN <- 1L; V_CONS <- 5L; V_PAIR <- 6L; V_INT <- 7L
V_T <- list(2L); V_F <- list(3L); V_NIL <- list(4L)
ST_RUNNING <- list(7L)
new_th <- function(st) { e <- new.env(hash = FALSE, parent = emptyenv()); e$st <- st; e }
done_th <- function(v) new_th(list(S_DONE, v))
prim_arity <- function(p) if (p == 1L || p == 2L || p == 5L) 2L else 1L
run_prim <- function(p, a) switch(p, list(5L, a[[1L]], a[[2L]]), list(6L, a[[1L]], a[[2L]]), list(8L, a[[1L]]), list(9L, a[[1L]]), list(10L, a[[1L]], a[[2L]]), list(11L, a[[1L]]), list(12L, a[[1L]]))
describe <- function(v) switch(v[[1L]], "function", "true", "false", "nil", "cons cell", "pair", as.character(v[[2L]]), "number code", "symbol code", "application code", "lambda code", "variable code")

# ---------------------------------------------------------------- compiling de Bruijn terms
# annotated terms: list("v", level) list("g", name) list("l", arity, body, fv) list("a", f, x, fv); fv: sorted integer vectors of levels
free_levels <- function(a) switch(a[[1L]], v = a[[2L]], g = integer(0), k = integer(0), l = a[[4L]], a = a[[4L]])
is_closed <- function(a) switch(a[[1L]], v = FALSE, g = TRUE, k = TRUE, l = length(a[[4L]]) == 0L, a = length(a[[4L]]) == 0L)
annotate <- function(t, depth) switch(t[[1L]],
  CV = list("v", depth - t[[2L]]),
  CG = list("g", t[[2L]]),
  CD = list("k", "D", t[[2L]]),
  CT = list("k", "T", t[[2L]]),
  CL = { cur <- t; n <- 0L; while (cur[[1L]] == "CL") { cur <- cur[[2L]]; n <- n + 1L }
         body <- annotate(cur, depth + n); fv <- free_levels(body); list("l", n, body, fv[fv < depth]) },
  CA = { fa <- annotate(t[[2L]], depth); xa <- annotate(t[[3L]], depth); list("a", fa, xa, sort(unique(c(free_levels(fa), free_levels(xa))))) })

scope_new <- function() new.env(hash = TRUE, parent = emptyenv())
scope_slot <- function(sc, level) { r <- sc[[as.character(level)]]; if (is.null(r)) stop("i-1: internal error: a free variable is not in the frame"); r }
scope_set <- function(sc, level, slot) assign(as.character(level), slot, envir = sc)

# the chain of applications of an open application, as its head and its arguments in order; a closed inner application is the head (it is shared)
spine <- function(a) {
  cur <- a; args <- list(); first <- TRUE
  while (cur[[1L]] == "a" && (first || !is_closed(cur))) { args <- c(list(cur[[3L]]), args); cur <- cur[[2L]]; first <- FALSE }
  list(cur, args)
}
link_global <- function(lk, g) {
  r <- getk(lk$globals, g)
  if (is.null(r)) new_th(list(S_FAIL, host_err("eval", sprintf("i-1: %s has no compiled body", g)))) else r
}
# a literal node as a shared value, built iteratively: "D" the digits of a numeral (a list of Booleans), "T" the code points of a string (a list of pairs (numeral, 1))
.digit_cache <- new.env(hash = TRUE, parent = emptyenv())
const_thunk <- function(lk, a) {
  m <- lk$m; consg <- link_global(lk, "∷"); tv <- link_global(lk, "⊤"); fv <- link_global(lk, "⊥")
  bits_list <- function(ds) { acc <- fv; for (i in rev(seq_along(ds))) acc <- app_th(m, consg, list(if (ds[i] == 0L) fv else tv, acc)); acc }
  if (a[[2L]] == "D") return(bits_list(a[[3L]]))
  pairg <- link_global(lk, "⊗"); acc <- link_global(lk, "⊘"); one <- bits_list(1L)
  for (cp in rev(a[[3L]])) {
    key <- as.character(cp); ds <- .digit_cache[[key]]
    if (is.null(ds)) { ds <- small_digits(cp); .digit_cache[[key]] <- ds }
    acc <- app_th(m, consg, list(app_th(m, pairg, list(bits_list(ds), one)), acc))
  }
  acc
}
gen_lam <- function(lk, a, depth, sc) {
  arity <- a[[2L]]; fv <- a[[4L]]
  caps <- vapply(fv, function(l) scope_slot(sc, l), 1L)
  inner <- scope_new()
  for (j in seq_along(fv)) scope_set(inner, fv[j], j)
  for (p in seq_len(arity)) scope_set(inner, depth + p - 1L, length(fv) + p)
  list(arity, caps, gen(lk, a[[3L]], depth + arity, inner, FALSE))      # laminfo: list(arity, caps, body)
}
gen_thunk <- function(lk, a, depth, sc) {
  fv <- free_levels(a)
  caps <- vapply(fv, function(l) scope_slot(sc, l), 1L)
  inner <- scope_new()
  for (j in seq_along(fv)) scope_set(inner, fv[j], j)
  list(caps, gen(lk, a, depth, inner, TRUE))                            # thunkinfo: list(caps, body)
}
shared <- function(lk, a, depth) {
  if (a[[1L]] == "l") new_th(list(S_CLO, gen_lam(lk, a, depth, scope_new()), list()))
  else new_th(list(S_DELAYED, list(integer(0), gen(lk, a, depth, scope_new(), TRUE)), list()))
}
known_arity <- function(lk, g) getk(lk$arities, g)
gen_arg <- function(lk, a, depth, sc) {
  k <- a[[1L]]
  if (k == "v") list(1L, scope_slot(sc, a[[2L]]))
  else if (k == "g") list(2L, link_global(lk, a[[2L]]))
  else if (k == "k") list(2L, const_thunk(lk, a))
  else if (is_closed(a)) list(2L, shared(lk, a, depth))
  else if (k == "l") list(3L, gen_lam(lk, a, depth, sc))
  else {
    sp <- spine(a); head <- sp[[1L]]; args <- sp[[2L]]
    n <- if (head[[1L]] == "g") known_arity(lk, head[[2L]]) else NULL
    if (!is.null(n) && length(args) < n) list(5L, gen_pap(lk, head[[2L]], args, depth, sc))
    else list(4L, gen_thunk(lk, a, depth, sc))
  }
}
gen_pap <- function(lk, g, args, depth, sc) list(link_global(lk, g), lapply(args, function(x) gen_arg(lk, x, depth, sc)))    # papspec: list(g, args)
gen <- function(lk, a, depth, sc, root) {
  k <- a[[1L]]
  if (k == "v") return(list(1L, scope_slot(sc, a[[2L]])))
  if (k == "g") return(list(2L, link_global(lk, a[[2L]])))
  if (k == "k") return(list(2L, const_thunk(lk, a)))
  if (k == "l") return(if (is_closed(a)) list(2L, shared(lk, a, depth)) else list(3L, gen_lam(lk, a, depth, sc)))
  if (!root && is_closed(a)) return(list(2L, shared(lk, a, depth)))
  sp <- spine(a); cur <- sp[[1L]]; args <- sp[[2L]]
  gargs <- function() lapply(args, function(x) gen_arg(lk, x, depth, sc))
  n <- if (cur[[1L]] == "g") known_arity(lk, cur[[2L]]) else NULL
  if (!is.null(n)) {
    if (length(args) >= n) list(4L, link_global(lk, cur[[2L]]), gargs()) else list(6L, gen_pap(lk, cur[[2L]], args, depth, sc))
  } else if (cur[[1L]] == "v") list(5L, scope_slot(sc, cur[[2L]]), gargs())
  else { head <- gen(lk, cur, depth, sc, FALSE); list(7L, head, gargs()) }
}
# the state of a global definition: a closed lambda is a function value at once, anything else a delayed expression
gen_def <- function(lk, c) {
  a <- annotate(c, 0L)
  if (a[[1L]] == "l") list(S_CLO, gen_lam(lk, a, 0L, scope_new()), list())
  else list(S_DELAYED, list(integer(0), gen(lk, a, 0L, scope_new(), TRUE)), list())
}

# ---------------------------------------------------------------- the machine
# where the code of a global comes from: list("core", c) or list("term", params, term) -- a checked definition to erase when it is first needed
term_lams <- function(t) switch(t[[1L]], TLam = length(t[[2L]]) + term_lams(t[[3L]]), TAsc = term_lams(t[[2L]]), TQuote = term_lams(t[[2L]]), 0L)
term_arity <- function(ps, body) length(ps) + term_lams(body)
core_arity <- function(c) { n <- 0L; while (c[[1L]] == "CL") { c <- c[[2L]]; n <- n + 1L }; n }

machine_build <- function(defs, extra) {
  m <- new.env(hash = FALSE, parent = emptyenv())
  globals <- new.env(hash = TRUE, parent = emptyenv()); arities <- new.env(hash = TRUE, parent = emptyenv())
  for (e in extra) assign(e[[1L]], e[[2L]], envir = globals)              # the ready values first (they win over a definition of the same name)
  nd <- length(defs); last <- new.env(hash = TRUE, parent = emptyenv())
  for (i in seq_len(nd)) assign(defs[[i]][[1L]], i, envir = last)         # a later definition of the same name wins
  lazy <- vector("list", nd)
  for (i in seq_len(nd)) {
    n <- defs[[i]][[1L]]; src <- defs[[i]][[2L]]
    if (get(n, envir = last, inherits = FALSE) == i && !has_key(globals, n)) {
      ar <- if (src[[1L]] == "core") core_arity(src[[2L]]) else term_arity(src[[2L]], src[[3L]])
      if (ar > 0L) assign(n, ar, envir = arities)
      assign(n, new_th(list(S_LAZY, i)), envir = globals)
      lazy[[i]] <- src
    }
  }
  m$globals <- globals; m$arities <- arities; m$lazy <- lazy
  m$vt <- done_th(V_T); m$vf <- done_th(V_F); m$vnil <- done_th(V_NIL)
  m$cons_cb <- new_th(list(S_PRIM, 1L)); m$pair_cb <- new_th(list(S_PRIM, 2L))
  m$ints <- list(done_th(list(7L, 0L)), done_th(list(7L, 1L)), done_th(list(7L, 2L)))
  m$code_cbs <- list(new_th(list(S_PRIM, 3L)), new_th(list(S_PRIM, 4L)), new_th(list(S_PRIM, 5L)), new_th(list(S_PRIM, 6L)), new_th(list(S_PRIM, 7L)))
  m$app_infos <- list()
  m
}

# compile a global that has not been needed before
compile_global <- function(m, idx) {
  src <- m$lazy[[idx]]; m$lazy[[idx]] <- FALSE
  lk <- list(globals = m$globals, arities = m$arities, m = m)
  if (is.list(src) && src[[1L]] == "core") gen_def(lk, src[[2L]])
  else if (is.list(src) && src[[1L]] == "term") {
    tryCatch({ c0 <- erase_def("", src[[2L]], src[[3L]])[[2L]]; gen_def(lk, c0) }, host_err = function(e) list(S_FAIL, e))
  } else list(S_FAIL, host_err("eval", "i-1: internal error: a global was compiled twice"))
}
global <- function(m, g) { r <- getk(m$globals, g); if (is.null(r)) eval_err(sprintf("i-1: %s is not defined", g)); r }
has_global <- function(m, g) has_key(m$globals, g)

# the lazy application of f to args (a list of thunks): a thunk that is evaluated when it is needed
app_th <- function(m, f, args) {
  n <- length(args)
  if (length(m$app_infos) <= n) {
    for (k in length(m$app_infos):n) {                                    # frame: [f, a1 .. ak]; body: f a1 .. ak
      m$app_infos[[k + 1L]] <- list(seq_len(k + 1L), if (k == 0L) list(1L, 1L) else list(7L, list(1L, 1L), lapply(seq_len(k), function(i) list(1L, i + 1L))))
    }
  }
  new_th(list(S_DELAYED, m$app_infos[[n + 1L]], c(list(f), args)))
}

make_arg <- function(a, frame) {
  switch(a[[1L]],
    frame[[a[[2L]]]],
    a[[2L]],
    new_th(list(S_CLO, a[[2L]], frame[a[[2L]][[2L]]])),
    new_th(list(S_DELAYED, a[[2L]], frame[a[[2L]][[1L]]])),
    make_pap(a[[2L]], frame))
}
make_pap <- function(spec, frame) {
  args <- spec[[2L]]; held <- vector("list", length(args))
  for (i in seq_along(args)) held[[i]] <- make_arg(args[[i]], frame)
  new_th(list(S_PAP, spec[[1L]], held))
}

# evaluate  start args  to weak head normal form.  The stack of continuations is local: k-arg = list(1, th), k-update = list(2, th)
run <- function(m, start, args) {
  conts <- vector("list", 256L); ntop <- 0L; frame <- list()
  for (k in rev(seq_along(args))) { ntop <- ntop + 1L; if (ntop > length(conts)) length(conts) <- 2L * length(conts); conts[[ntop]] <- list(1L, args[[k]]) }
  mode <- 1L; cur <- start                     # 1 force the thunk cur | 2 evaluate the code cur | 3 deliver the value cur | 4 evaluate the variable cur | 5 call a closure
  ci <- NULL; cc <- NULL; ch <- NULL; cclo <- NULL; cfirst <- NULL
  {
    repeat {
      if (mode == 3L) {                                                     # ---- deliver cur
        if (ntop <= 0L) return(cur)
        k <- conts[[ntop]]; conts[[ntop]] <- FALSE; ntop <- ntop - 1L
        if (k[[1L]] == 2L) { k[[2L]]$st <- list(S_DONE, cur); next }
        first <- k[[2L]]
        if (cur[[1L]] != 1L) unwind(conts, ntop, host_err("eval", paste0("a value that is not a function was applied: ", describe(cur))))
        f <- cur[[2L]]; st <- f$st; tag <- st[[1L]]
        if (tag == S_CLO) { ci <- st[[2L]]; cc <- st[[3L]]; ch <- list(); cclo <- f; cfirst <- first; mode <- 5L }
        else if (tag == S_PRIM) {
          p <- st[[2L]]; need <- prim_arity(p); extra <- 0L; w <- need - 1L
          while (extra < w && ntop > extra && conts[[ntop - extra]][[1L]] == 1L) extra <- extra + 1L
          a <- list(first)
          for (j in seq_len(extra)) { a[[j + 1L]] <- conts[[ntop]][[2L]]; conts[[ntop]] <- FALSE; ntop <- ntop - 1L }
          cur <- if (extra + 1L < need) list(1L, new_th(list(S_PAP, f, a))) else run_prim(p, a)
        } else {                                                            # a partial application
          b <- st[[2L]]; held <- st[[3L]]
          if (b$st[[1L]] == S_LAZY) b$st <- compile_global(m, b$st[[2L]])
          bs <- b$st
          if (bs[[1L]] == S_CLO) { ci <- bs[[2L]]; cc <- bs[[3L]]; ch <- held; cclo <- b; cfirst <- first; mode <- 5L }
          else {
            p <- bs[[2L]]; need <- prim_arity(p) - length(held); extra <- 0L; w <- need - 1L
            while (extra < w && ntop > extra && conts[[ntop - extra]][[1L]] == 1L) extra <- extra + 1L
            a <- c(held, list(first))
            for (j in seq_len(extra)) { a[[length(a) + 1L]] <- conts[[ntop]][[2L]]; conts[[ntop]] <- FALSE; ntop <- ntop - 1L }
            cur <- if (extra + 1L < need) list(1L, new_th(list(S_PAP, b, a))) else run_prim(p, a)
          }
        }
      } else if (mode == 2L) {                                              # ---- evaluate code
        code <- cur
        switch(code[[1L]],
          { cur <- frame[[code[[2L]]]]; mode <- 4L },                       # 1 var
          { cur <- code[[2L]]; mode <- 4L },                                # 2 const
          { info <- code[[2L]]; cur <- list(1L, new_th(list(S_CLO, info, frame[info[[2L]]]))); mode <- 3L },   # 3 lam
          {                                                                 # 4 call a global
            g <- code[[2L]]; cargs <- code[[3L]]; na <- length(cargs)
            if (g$st[[1L]] == S_LAZY) g$st <- compile_global(m, g$st[[2L]])
            st <- g$st
            if (st[[1L]] == S_CLO && st[[2L]][[1L]] <= na) {
              info <- st[[2L]]; n <- info[[1L]]
              if (na > n) for (j in na:(n + 1L)) { ntop <- ntop + 1L; if (ntop > length(conts)) length(conts) <- 2L * length(conts); conts[[ntop]] <- list(1L, make_arg(cargs[[j]], frame)) }
              nf <- vector("list", n)
              for (j in seq_len(n)) nf[[j]] <- make_arg(cargs[[j]], frame)
              frame <- nf; cur <- info[[3L]]
            } else {
              for (j in na:1L) { ntop <- ntop + 1L; if (ntop > length(conts)) length(conts) <- 2L * length(conts); conts[[ntop]] <- list(1L, make_arg(cargs[[j]], frame)) }
              cur <- g; mode <- 1L
            }
          },
          {                                                                 # 5 call a variable
            t <- frame[[code[[2L]]]]; cargs <- code[[3L]]; na <- length(cargs); st <- t$st
            if (st[[1L]] == S_CLO && st[[2L]][[1L]] == na) {
              caps <- st[[3L]]; nf <- caps
              for (j in seq_len(na)) nf[[length(nf) + 1L]] <- make_arg(cargs[[j]], frame)
              frame <- nf; cur <- st[[2L]][[3L]]
            } else {
              for (j in na:1L) { ntop <- ntop + 1L; if (ntop > length(conts)) length(conts) <- 2L * length(conts); conts[[ntop]] <- list(1L, make_arg(cargs[[j]], frame)) }
              cur <- t; mode <- 4L
            }
          },
          { cur <- list(1L, make_pap(code[[2L]], frame)); mode <- 3L },     # 6 pap
          {                                                                 # 7 app
            cargs <- code[[3L]]
            for (j in length(cargs):1L) { ntop <- ntop + 1L; if (ntop > length(conts)) length(conts) <- 2L * length(conts); conts[[ntop]] <- list(1L, make_arg(cargs[[j]], frame)) }
            cur <- code[[2L]]
          })
      } else if (mode == 4L) {                                              # ---- evaluate a variable (a thunk)
        st <- cur$st; tag <- st[[1L]]
        if (tag == S_DONE) { cur <- st[[2L]]; mode <- 3L }
        else if (tag == S_CLO || tag == S_PAP || tag == S_PRIM) { cur <- list(1L, cur); mode <- 3L }
        else mode <- 1L
      } else if (mode == 1L) {                                              # ---- force a thunk
        st <- cur$st; tag <- st[[1L]]
        if (tag == S_DONE) { cur <- st[[2L]]; mode <- 3L }
        else if (tag == S_CLO || tag == S_PAP || tag == S_PRIM) { cur <- list(1L, cur); mode <- 3L }
        else if (tag == S_RUNNING) unwind(conts, ntop, host_err("eval", "<<loop>>"))
        else if (tag == S_FAIL) unwind(conts, ntop, st[[2L]])
        else if (tag == S_LAZY) cur$st <- compile_global(m, st[[2L]])
        else {                                                              # delayed
          cur$st <- ST_RUNNING; frame <- st[[3L]]
          ntop <- ntop + 1L; if (ntop > length(conts)) length(conts) <- 2L * length(conts); conts[[ntop]] <- list(2L, cur)
          cur <- st[[2L]][[2L]]; mode <- 2L
        }
      } else {                                                              # ---- mode 5: call a closure: ci info, cc caps, ch held, cclo the thunk, cfirst the first new argument
        nh <- length(ch); need <- ci[[1L]] - nh; extra <- 0L; w <- need - 1L
        while (extra < w && ntop > extra && conts[[ntop - extra]][[1L]] == 1L) extra <- extra + 1L
        if (extra + 1L < need) {                                            # not enough arguments yet: a partial application
          h <- c(ch, list(cfirst))
          for (j in seq_len(extra)) { h[[length(h) + 1L]] <- conts[[ntop]][[2L]]; conts[[ntop]] <- FALSE; ntop <- ntop - 1L }
          cur <- list(1L, new_th(list(S_PAP, cclo, h))); mode <- 3L
        } else {
          fr <- c(cc, ch, list(cfirst))
          for (j in seq_len(need - 1L)) { fr[[length(fr) + 1L]] <- conts[[ntop]][[2L]]; conts[[ntop]] <- FALSE; ntop <- ntop - 1L }
          frame <- fr; cur <- ci[[3L]]; mode <- 2L
        }
      }
    }
  }
}
# an error: the thunks under evaluation keep it (evaluating them again gives the same error), the rest of the work is dropped
unwind <- function(conts, ntop, e) {
  while (ntop > 0L) { k <- conts[[ntop]]; if (is.list(k) && k[[1L]] == 2L) k[[2L]]$st <- list(S_FAIL, e); ntop <- ntop - 1L }
  stop(e)
}

whnf <- function(m, v) run(m, v, list())
apply_whnf <- function(m, f, args) run(m, f, args)

# ---------------------------------------------------------------- decoding
to_bool <- function(m, v) identical(apply_whnf(m, v, list(m$vt, m$vf))[[1L]], 2L)
# the truth value that a Boolean selects between the markers: "true", "false", or NULL for anything else (the undetermined)
tri <- function(m, v) { r <- apply_whnf(m, v, list(m$vt, m$vf)); if (r[[1L]] == 2L) "true" else if (r[[1L]] == 3L) "false" else NULL }
# take a list cell apart: a cons value, VNIL, or (for an undetermined value) something else
cell_or_nil <- function(m, v) apply_whnf(m, v, list(m$cons_cb, m$vnil))
to_ord <- function(m, v) { r <- apply_whnf(m, v, m$ints); if (r[[1L]] == 7L) r[[2L]] else eval_err("an ordering was expected") }
# a list of booleans (digits, least significant first), as an integer vector of 0 and 1
to_list <- function(m, v) {
  out <- integer(256L); n <- 0L; cur <- v
  repeat {
    c <- cell_or_nil(m, cur)
    if (c[[1L]] == 5L) { n <- n + 1L; if (n > length(out)) length(out) <- 2L * length(out); out[n] <- if (to_bool(m, c[[2L]])) 1L else 0L; cur <- c[[3L]] }
    else if (c[[1L]] == 4L) return(out[seq_len(n)])
    else eval_err("a list was expected")
  }
}
to_pair <- function(m, v) { r <- apply_whnf(m, v, list(m$pair_cb)); if (r[[1L]] == 6L) list(r[[2L]], r[[3L]]) else eval_err("a pair was expected") }
stream_nth <- function(m, v, n) {
  cur <- v; k <- n
  repeat {
    c <- cell_or_nil(m, cur)
    if (c[[1L]] == 5L) { if (k == 0L) return(c[[2L]]) else { cur <- c[[3L]]; k <- k - 1L } } else eval_err("a stream was expected")
  }
}
# the digit list (LSB first) as a language value
list_value <- function(m, ds) {
  tv <- global(m, "⊤"); fv <- global(m, "⊥"); consg <- global(m, "∷"); acc <- fv
  for (i in rev(seq_along(ds))) acc <- app_th(m, consg, list(if (ds[i] == 0L) fv else tv, acc))
  acc
}
call_g <- function(m, f, args) app_th(m, global(m, f), args)
gi_of <- function(m, v) val_digits(to_list(m, v))
